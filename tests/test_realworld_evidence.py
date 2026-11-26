import gzip
import json
import sqlite3
from types import SimpleNamespace

import pytest

from smp.realworld import DRIVER, raw, replay, write_report
from smp.realworld_evidence import Evidence, PERMISSIVE, compare_results, encoded, redact, safe_aggregate, sha256, snapshot, write_gzip
from scripts.finalize_realworld_rerun import compact_provenance, expand_provenance


def fixture(tmp_path):
    root = tmp_path / 'extracted'
    folder = root / 'migrations'
    (folder / 'meta').mkdir(parents=True)
    journal = {'version': '7', 'dialect': 'sqlite', 'entries': [
        {'idx': 0, 'version': '6', 'when': 1000, 'tag': '0000_initial', 'breakpoints': True},
        {'idx': 1, 'version': '6', 'when': 2000, 'tag': '0001_rebuild', 'breakpoints': True}]}
    (folder / 'meta/_journal.json').write_text(json.dumps(journal))
    (folder / '0000_initial.sql').write_text('CREATE TABLE p(id INTEGER PRIMARY KEY AUTOINCREMENT);\n--> statement-breakpoint\nCREATE TABLE c(id INTEGER PRIMARY KEY, p INTEGER REFERENCES p(id) ON DELETE CASCADE, b BLOB, n INTEGER GENERATED ALWAYS AS (id * 2));')
    target = 'migrations/0001_rebuild.sql'
    sql = '\n--> statement-breakpoint\n'.join([
        'PRAGMA foreign_keys=OFF;', 'CREATE TABLE __new_p(id INTEGER PRIMARY KEY, note TEXT);',
        'INSERT INTO __new_p(id) SELECT id FROM p;', 'DROP TABLE p;',
        'ALTER TABLE __new_p RENAME TO p;', 'PRAGMA foreign_keys=ON;'])
    (root / target).write_text(sql)
    return root, target, sql


def test_raw_trace_order_and_defaults(tmp_path):
    root, target, sql = fixture(tmp_path)
    evidence = Evidence(root, target)
    database = tmp_path / 'raw.db'
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE p(id INTEGER PRIMARY KEY)')
        db.execute('INSERT INTO p VALUES(1)')
    evidence.start('raw-tx', database)
    result = raw(database, sql, transactional=True, evidence=evidence.traces['raw-tx'])
    evidence.finish('raw-tx', database)
    assert result['success']
    trace = evidence.paths['raw-tx']['trace']
    assert trace[0]['sql'] == 'PRAGMA foreign_keys=ON'
    assert trace[2]['sql'] == 'BEGIN'
    assert trace[-2]['sql'] == 'COMMIT'
    assert sum(item['origin'] == 'project' for item in trace) == 6
    assert len(evidence.paths['raw-tx']['submitted']) == 6
    assert 'trace' not in result
    assert evidence.paths['raw-tx']['before']['tables']['p']['rows'] == [(1,)]
    assert evidence.paths['raw-tx']['after']['tables']['p']['rows'] == [(1, None)]


def test_snapshot_keeps_internal_generated_blob_and_schema(tmp_path):
    database = tmp_path / 'all.db'
    with sqlite3.connect(database) as db:
        db.executescript('CREATE TABLE t(id INTEGER PRIMARY KEY AUTOINCREMENT, b BLOB, n INTEGER GENERATED ALWAYS AS(id*2)); CREATE TABLE __drizzle_migrations(hash TEXT);')
        db.execute('INSERT INTO t(b) VALUES(?)', (b'\x00\xff',))
    state = snapshot(database)
    assert set(state['tables']) == {'t', 'sqlite_sequence', '__drizzle_migrations'}
    assert state['tables']['t']['rows'] == [(1, b'\x00\xff', 2)]
    assert all(set(row) == {'type', 'name', 'tbl_name', 'rootpage', 'sql'} for row in state['sqlite_schema'])
    assert json.loads(encoded(state))['tables']['t']['rows'][0][1] == {'blob': '00ff'}


def test_failed_prepare_is_submitted_but_not_executed(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'bad.sql').write_text('DROP TABLE absent;')
    evidence = Evidence(root, 'bad.sql')
    database = tmp_path / 'bad.db'
    evidence.start('raw-tx', database)
    result = raw(database, 'DROP TABLE absent;', transactional=True, evidence=evidence.traces['raw-tx'])
    evidence.finish('raw-tx', database)
    assert not result['success']
    section = evidence.paths['raw-tx']
    assert section['submitted'][0]['sql'] == 'DROP TABLE absent;'
    assert not any(item['origin'] == 'project' for item in section['trace'])
    assert any(item['sql'] == 'ROLLBACK' for item in section['trace'])
    assert section['before'] == section['after']


def test_drizzle_full_capture_and_restricted_publication(tmp_path, monkeypatch):
    monkeypatch.setenv('SMP_RUNTIME_ROOT', '.realworld-local/test-runtime')
    if not (DRIVER / 'node_modules/better-sqlite3').exists():
        pytest.skip('requires installed harness Node dependencies')
    root, target, sql = fixture(tmp_path)
    evidence = Evidence(root, target)
    result = replay({'repo': 'test/fixture', 'license': None, 'commit': 'a' * 40}, root, target,
                    None, DRIVER, {'resolved': '0.45.4'}, tmp_path, 3, evidence)
    assert result['paths']['drizzle']['outcome'] == 'silent-loss'
    full = evidence.document(result)
    section = full['paths']['drizzle']
    assert section['before']['tables']['__drizzle_migrations']['rows']
    assert len(section['after']['tables']['__drizzle_migrations']['rows']) == 2
    assert section['before']['tables']['c']['columns'][-1] == 'n'
    assert section['after']['tables']['c']['rows'] == []
    assert any(item['sql'].lower() == 'begin' for item in section['trace'])
    assert any('insert into "__drizzle_migrations"' in item['sql'].lower() for item in section['trace'])
    assert sum(item['origin'] == 'project' for item in section['submitted']) == 6
    public = redact(full)
    for path in ('drizzle', 'raw', 'raw-tx'):
        for kind in ('trace', 'submitted'):
            for item in public['paths'][path][kind]:
                if item['origin'] == 'project':
                    assert 'sql' not in item and item['sources'] and item['sha256']
                else:
                    assert 'sql' in item
        assert public['paths'][path]['before']['tables'] == full['paths'][path]['before']['tables']
    for entry in public['paths']['drizzle']['before']['sqlite_schema']:
        assert entry.get('tbl_name') == '__drizzle_migrations' or ('sha256' in entry and 'sql' not in entry)
    for entry in full['source_statements']:
        source = entry['source']
        part = (root / source['file']).read_bytes()[source['byte_start']:source['byte_end']]
        assert sha256(part) == source['sha256']
        assert part.decode() == entry['sql']
    path = tmp_path / 'evidence.json.gz'
    ref = write_gzip(path, public)
    assert sha256(path.read_bytes()) == ref['sha256']
    assert json.loads(gzip.decompress(path.read_bytes())) == json.loads(encoded(public))
    compact = compact_provenance(public)
    assert expand_provenance(compact) == public
    assert compact_provenance(compact) == compact
    assert all(entry.get('sources_ref') == '#/schema_sources' or entry.get('tbl_name') == '__drizzle_migrations'
               for entry in compact['paths']['drizzle']['before']['sqlite_schema'])
    result['paths']['drizzle']['execution']['error'] = 'CHECK constraint failed: private expression'
    aggregate = safe_aggregate(result, evidence)
    assert aggregate['paths']['drizzle']['execution']['events'][0] == 'PRAGMA foreign_keys=ON'
    assert any(isinstance(event, dict) for event in aggregate['paths']['drizzle']['execution']['events'])
    assert isinstance(aggregate['paths']['drizzle']['execution']['error'], str)
    write_report(tmp_path / 'report', {'rows': [aggregate], 'observed_at': '2026-11-02'})
    assert 'private expression' not in (tmp_path / 'report/realworld.md').read_text()


def test_drizzle_statements_resolve_to_the_target_migration(tmp_path, monkeypatch):
    monkeypatch.setenv('SMP_RUNTIME_ROOT', '.realworld-local/test-runtime')
    if not (DRIVER / 'node_modules/better-sqlite3').exists():
        pytest.skip('requires installed harness Node dependencies')
    root, target, sql = fixture(tmp_path)
    initial = root / 'migrations/0000_initial.sql'
    initial.write_text('PRAGMA foreign_keys=OFF;\n--> statement-breakpoint\n' + initial.read_text()
                       + '\n--> statement-breakpoint\nPRAGMA foreign_keys=ON;')
    repeated = '\n--> statement-breakpoint\nCREATE INDEX IF NOT EXISTS p_note ON p(note);'
    (root / target).write_text(sql + repeated + repeated)
    evidence = Evidence(root, target)
    result = replay({'repo': 'test/fixture', 'license': None, 'commit': 'a' * 40}, root, target,
                    None, DRIVER, {'resolved': '0.45.4'}, tmp_path, 3, evidence)
    assert result['paths']['drizzle']['execution']['success']
    section = evidence.document(result)['paths']['drizzle']
    submitted = [item for item in section['submitted'] if item['origin'] == 'project']
    assert len(submitted) == 8
    for item in submitted + [item for item in section['trace'] if item['origin'] == 'project']:
        assert [source['file'] for source in item['sources']] == [target]
    assert [item['sources'][0]['statement'] for item in submitted] == list(range(1, 9))


def test_comparison_detects_counts_and_changed_values():
    row = {'repo': 'a/b', 'migration_file': 'x.sql', 'status': 'unreplayable',
           'paths': {p: {'outcome': 'unreplayable'} for p in ('drizzle', 'raw', 'raw-tx')}}
    original = {'rows': [row]}
    new = json.loads(json.dumps(original))
    new['rows'][0]['paths']['raw']['counts_after'] = {'t': 2}
    comparison = compare_results(original, new)
    assert comparison['migrations_with_differences'] == 1
    assert comparison['comparisons'][0]['differences'][0]['field'] == 'raw.counts_after'
    with pytest.raises(ValueError, match='duplicate'):
        compare_results({'rows': [row, row]}, original)


def test_publication_allowlist_is_exact():
    assert PERMISSIVE == {'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC'}


def test_redaction_rejects_missing_provenance(tmp_path):
    root, target, _ = fixture(tmp_path)
    evidence = Evidence(root, target)
    row = {'repo': 'test/fixture', 'migration_file': target, 'status': 'unreplayable', 'paths': {}}
    document = evidence.document(row)
    document['setup']['trace'].append({'sql': 'CREATE TABLE private(id);', 'origin': 'project'})
    with pytest.raises(ValueError, match='without provenance'):
        redact(document)


def test_evidence_run_rejects_input_drift_and_existing_output(tmp_path, monkeypatch):
    from smp import realworld_evidence
    monkeypatch.setattr(realworld_evidence, 'ROOT', tmp_path)
    monkeypatch.setattr('subprocess.run', lambda *a, **kw: SimpleNamespace(returncode=0))
    pins = tmp_path / 'pins.json'
    pins.write_text(json.dumps({'rows_per_table': 3, 'input_hashes': {'corpus': 'original', 'probe': 'original'}}))
    corpus, probe = tmp_path / 'corpus.tsv', tmp_path / 'probe.json'
    corpus.write_text('changed')
    probe.write_text('[]')
    args = SimpleNamespace(pins=pins, resume=False, commit=None, orm_version=None, max_repos=None,
                           rows=3, evidence_dir=tmp_path / 'local', output=tmp_path / 'public',
                           input=corpus, probe=probe)
    before = pins.read_bytes()
    with pytest.raises(ValueError, match='hashes differ'):
        realworld_evidence.run(args)
    assert not args.output.exists() and not args.evidence_dir.exists()
    args.output.mkdir()
    with pytest.raises(ValueError, match='already exists'):
        realworld_evidence.run(args)
    assert pins.read_bytes() == before


def test_evidence_directory_is_accepted_without_git_metadata(tmp_path, monkeypatch):
    from smp import realworld_evidence
    monkeypatch.setattr(realworld_evidence, 'ROOT', tmp_path)
    pins = tmp_path / 'pins.json'
    pins.write_text(json.dumps({'rows_per_table': 3, 'input_hashes': {'corpus': 'original', 'probe': 'original'}}))
    corpus, probe = tmp_path / 'corpus.tsv', tmp_path / 'probe.json'
    corpus.write_text('changed')
    probe.write_text('[]')
    args = SimpleNamespace(pins=pins, resume=False, commit=None, orm_version=None, max_repos=None,
                           rows=3, evidence_dir=tmp_path / '.realworld-local/rerun', output=tmp_path / 'public',
                           input=corpus, probe=probe)
    with pytest.raises(ValueError, match='hashes differ'):
        realworld_evidence.run(args)
    args.evidence_dir = tmp_path / 'elsewhere'
    with pytest.raises(ValueError, match='git-ignored'):
        realworld_evidence.run(args)
