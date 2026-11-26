import hashlib
import json
import sys

import pytest

from smp.environment import ROOT
from smp.replay_notices import publication_notices
from smp.source_provenance import verify_sources
from scripts.validate_realworld import validate


def test_retained_sources_do_not_require_current_files(tmp_path):
    snapshot = tmp_path / 'sources/replay-validation/original'
    snapshot.mkdir(parents=True)
    (snapshot / 'producer.py').write_bytes(b'historical source\n')
    hashes = {'producer.py': hashlib.sha256(b'historical source\n').hexdigest()}
    (snapshot.parent / 'index.json').write_text(json.dumps([{
        'directory': str(snapshot.relative_to(tmp_path)), 'source_hashes': hashes}]))
    (tmp_path / 'producer.py').write_text('changed source')
    assert verify_sources(hashes, tmp_path)['directory'] == 'sources/replay-validation/original'
    (snapshot / 'producer.py').write_text('damaged archive')
    with pytest.raises(ValueError, match='Archived source hash mismatch'):
        verify_sources(hashes, tmp_path)


def test_unknown_source_hash_cannot_pass(tmp_path):
    (tmp_path / 'producer.py').write_text('different source')
    with pytest.raises(ValueError, match='No matching source snapshot'):
        verify_sources({'producer.py': '0' * 64}, tmp_path)


def test_full_publication_requires_applicable_pinned_notice(tmp_path):
    row = {'repo': 'owner/project', 'commit': 'a' * 40, 'migration_file': 'migrations/one.sql'}
    assert publication_notices(row, tmp_path) is None
    folder = tmp_path / 'licenses/replay/owner__project'
    folder.mkdir(parents=True)
    license_file = folder / 'LICENSE'
    license_file.write_text('Original project notice')
    record = dict(row, mode='full', files=[{
        'path': 'LICENSE', 'file': str(license_file.relative_to(tmp_path)),
        'sha256': hashlib.sha256(license_file.read_bytes()).hexdigest()}])
    manifest = folder / 'provenance.json'
    manifest.write_text(json.dumps(record))
    assert publication_notices(row, tmp_path)['commit'] == row['commit']
    assert publication_notices({**row, 'commit': 'b' * 40}, tmp_path) is None
    record['files'][0]['path'] = 'unrelated/LICENSE'
    manifest.write_text(json.dumps(record))
    assert publication_notices(row, tmp_path) is None
    record['files'][0]['path'] = 'LICENSE'
    manifest.write_text(json.dumps(record))
    license_file.write_text('changed notice')
    with pytest.raises(ValueError, match='notice hash mismatch'):
        publication_notices(row, tmp_path)


def test_retained_replay_sources_and_publication_validate():
    original = json.loads((ROOT / 'results/realworld.json').read_text())
    directory = ROOT / 'results/realworld-rerun-2026-11-02'
    rerun = json.loads((directory / 'realworld.json').read_text())
    assert validate(original) == []
    assert validate(rerun, directory) == []
    assert sum(r['evidence']['mode'] == 'full' for r in rerun['rows']) == 25
    channel = next(r for r in rerun['rows'] if r['repo'] == 'skyfallwastaken/at-channel')
    record = json.loads((ROOT / channel['evidence']['license_notices']['file']).read_text())
    assert {f['path'] for f in record['files']} == {'LICENSE-APACHE', 'LICENSE-MIT'}


def test_kit_probe_writes_requested_file(tmp_path, monkeypatch):
    from scripts import probe_kit_pragma_pairs as probe
    retained = json.loads((ROOT / 'results/kit_pragma_pairs.json').read_text())
    monkeypatch.setattr(probe, 'ROOT', tmp_path)
    monkeypatch.setattr(probe, 'cache_dir', lambda: tmp_path / 'cache')
    (tmp_path / 'versions.json').write_bytes((ROOT / 'versions.json').read_bytes())
    initial = ('CREATE TABLE a_first(id INTEGER PRIMARY KEY, name TEXT);'
               'CREATE TABLE parents(id INTEGER PRIMARY KEY, name TEXT);'
               'CREATE TABLE children(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id) ON DELETE CASCADE);')
    def generate(case, label, scope=None):
        folder = tmp_path / label
        (folder / 'history').mkdir(parents=True)
        (folder / 'history/0000_before.sql').write_text(initial)
        row = next(r for r in retained['results'] if r['label'] == label)
        (folder / 'history/0001_after.sql').write_text(row['upgrade_sql'])
        return folder
    monkeypatch.setattr(probe, 'generate', generate)
    output = tmp_path / 'new/probe.json'
    monkeypatch.setattr(sys, 'argv', ['probe', '--output', str(output)])
    probe.main()
    actual = json.loads(output.read_text())
    assert actual['seed_rows'] == retained['seed_rows']
    assert actual['results'] == retained['results']


def test_permissive_label_without_notices_redacts_aggregate_events():
    from types import SimpleNamespace
    from smp.realworld_evidence import safe_aggregate
    sql = 'CREATE TABLE private_project(id INTEGER);'
    source = {'file': 'migrations/one.sql', 'sha256': hashlib.sha256(sql.encode()).hexdigest()}
    row = {'repo': 'missing-project/no-notices', 'commit': 'a' * 40,
           'migration_file': 'migrations/one.sql', 'license': 'MIT',
           'paths': {'raw': {'execution': {'events': [sql]}}}}
    evidence = SimpleNamespace(traces={'raw': SimpleNamespace(executed=[{
        'sql': sql, 'origin': 'project', 'sources': [source]}])})
    public = safe_aggregate(row, evidence)
    assert public['paths']['raw']['execution']['events'] == [{'sha256': source['sha256'], 'sources': [source]}]
    assert row['paths']['raw']['execution']['events'] == [sql]


def test_complete_evidence_rows_must_reference_an_artifact():
    directory = ROOT / 'results/realworld-rerun-2026-11-02'
    rerun = json.loads((directory / 'realworld.json').read_text())
    del rerun['rows'][0]['evidence']
    del next(r for r in rerun['rows'] if r['status'] == 'unreplayable')['evidence']
    errors = validate(rerun, directory)
    assert len([e for e in errors if e.startswith('missing evidence reference')]) == 2
    original = json.loads((ROOT / 'results/realworld.json').read_text())
    assert all('evidence' not in row for row in original['rows']) and validate(original) == []


@pytest.mark.parametrize('damage', ['field', 'one', 'empty', 'publication'])
def test_incomplete_source_manifest_is_not_verified(damage):
    directory = ROOT / 'results/realworld-rerun-2026-11-02'
    rerun = json.loads((directory / 'realworld.json').read_text())
    if damage == 'field':
        del rerun['source_hashes']
    elif damage == 'one':
        del rerun['source_hashes']['runners/realworld/run.cjs']
    elif damage == 'empty':
        rerun['source_hashes'] = {}
    else:
        del rerun['publication_source_hashes']['scripts/paper_numbers.py']
    assert any('source hash' in error for error in validate(rerun, directory))
    with pytest.raises(ValueError, match='empty'):
        verify_sources({}, ROOT)


def test_kit_probe_does_not_depend_on_directory_names(tmp_path, monkeypatch):
    from scripts import probe_kit_pragma_pairs as probe
    retained = json.loads((ROOT / 'results/kit_pragma_pairs.json').read_text())
    root = tmp_path / 'relocated'
    monkeypatch.setattr(probe, 'ROOT', root)
    monkeypatch.setattr(probe, 'cache_dir', lambda: root / 'cache')
    root.mkdir()
    (root / 'versions.json').write_bytes((ROOT / 'versions.json').read_bytes())
    def generate(case, label, scope=None):
        folder = root / label
        row = next(r for r in retained['results'] if r['label'] == label)
        if label == 'current':
            (folder / 'history').mkdir(parents=True)
            (folder / 'history/0000_before.sql').write_text('CREATE TABLE a_first(id INTEGER PRIMARY KEY, name TEXT);'
                'CREATE TABLE parents(id INTEGER PRIMARY KEY, name TEXT);'
                'CREATE TABLE children(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id) ON DELETE CASCADE);')
            (folder / 'history/0001_after.sql').write_text(row['upgrade_sql'])
        else:
            for name, sql in (('20261103000000_before', 'CREATE TABLE a_first(id INTEGER PRIMARY KEY, name TEXT);'
                               'CREATE TABLE parents(id INTEGER PRIMARY KEY, name TEXT);'
                               'CREATE TABLE children(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id) ON DELETE CASCADE);'),
                              ('20261103000000_after', row['upgrade_sql'])):
                (folder / 'history' / name).mkdir(parents=True)
                (folder / 'history' / name / 'migration.sql').write_text(sql)
        return folder
    monkeypatch.setattr(probe, 'generate', generate)
    output = root / 'new/probe.json'
    monkeypatch.setattr(sys, 'argv', ['probe', '--output', str(output)])
    probe.main()
    assert json.loads(output.read_text())['results'] == retained['results']
