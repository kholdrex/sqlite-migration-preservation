import json
import sqlite3
from pathlib import Path

import pytest

from smp.realworld import Unreplayable, compare, content, dependencies, raw, rebuilds, replay, validate_sql
from smp.realworld_seed import SeedError, seed


def test_seed_composite_nullable_fk_unique_enum_check_generated():
    db = sqlite3.connect(':memory:', isolation_level=None)
    db.executescript('''
      CREATE TABLE parent (a INTEGER, b TEXT, PRIMARY KEY(a,b));
      CREATE TABLE child (id INTEGER PRIMARY KEY, pa INTEGER, pb TEXT,
        status TEXT NOT NULL CHECK(status IN ('open','closed')), amount INTEGER NOT NULL CHECK(amount > 0),
        email TEXT NOT NULL UNIQUE, detail TEXT CHECK(json_valid(detail)),
        double_amount INTEGER GENERATED ALWAYS AS (amount*2),
        FOREIGN KEY(pa,pb) REFERENCES parent(a,b) ON DELETE SET NULL);
    ''')
    assert seed(db) == {'child': 3, 'parent': 3}
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    assert db.execute('SELECT count(*) FROM child WHERE pa IS NOT NULL AND pb IS NOT NULL').fetchone()[0] == 3
    assert db.execute('SELECT count(DISTINCT email) FROM child').fetchone()[0] == 3
    assert db.execute('SELECT count(*) FROM child WHERE double_amount=2*amount').fetchone()[0] == 3


def test_self_reference_and_multiple_parents():
    db = sqlite3.connect(':memory:', isolation_level=None)
    db.executescript('''
      CREATE TABLE tree(id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL REFERENCES tree(id));
      CREATE TABLE other(id TEXT PRIMARY KEY);
      CREATE TABLE child(id INTEGER PRIMARY KEY, tree_id INTEGER NOT NULL REFERENCES tree(id), other_id TEXT REFERENCES other(id));
    ''')
    assert seed(db) == {'child': 3, 'other': 3, 'tree': 3}
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []


def test_seed_failure_rolls_back_all_tables():
    db = sqlite3.connect(':memory:', isolation_level=None)
    db.executescript('CREATE TABLE good(id INTEGER PRIMARY KEY); CREATE TABLE impossible(v INTEGER CHECK(v > 999999) NOT NULL);')
    with pytest.raises(SeedError, match='CHECK constraint failed'):
        seed(db)
    assert db.execute('SELECT count(*) FROM good').fetchone()[0] == 0


def test_existing_records_rejected_without_changes():
    db = sqlite3.connect(':memory:', isolation_level=None)
    db.executescript('CREATE TABLE t(id INTEGER); INSERT INTO t VALUES (999);')
    with pytest.raises(SeedError, match='history contains data'):
        seed(db)
    assert db.execute('SELECT id FROM t').fetchall() == [(999,)]


def test_cycle_fails_explicitly():
    db = sqlite3.connect(':memory:', isolation_level=None)
    db.executescript('CREATE TABLE a(id INTEGER PRIMARY KEY,b INTEGER REFERENCES b(id)); CREATE TABLE b(id INTEGER PRIMARY KEY,a INTEGER REFERENCES a(id));')
    with pytest.raises(SeedError, match='cyclic'):
        seed(db)


def test_seed_deterministic():
    fixtures = []
    for _ in range(2):
        db = sqlite3.connect(':memory:', isolation_level=None)
        db.execute('CREATE TABLE t(id TEXT PRIMARY KEY, b BLOB, n INTEGER NOT NULL UNIQUE)')
        seed(db)
        fixtures.append(db.execute('SELECT * FROM t').fetchall())
    assert fixtures[0] == fixtures[1]


@pytest.mark.parametrize('sql', ['ATTACH DATABASE \'x\' AS other;', "SELECT load_extension('x');", "INSERT INTO t VALUES ('record');", 'PRAGMA writable_schema=ON;'])
def test_reject_unsafe_or_literal_records(sql):
    with pytest.raises(Unreplayable):
        validate_sql(sql)


def test_sql_comments_and_rebuild_detection():
    sql = '-- hello\n PRAGMA foreign_keys=OFF;\n INSERT INTO `__new_parent` SELECT * FROM parent;'
    validate_sql(sql)
    assert rebuilds(sql) == ['parent']


@pytest.mark.parametrize('action', ['CASCADE', 'SET NULL'])
def test_replay_raw_differential_detects_loss(tmp_path, action):
    baseline = tmp_path / 'baseline.db'
    with sqlite3.connect(baseline, isolation_level=None) as db:
        db.executescript(f'CREATE TABLE parent(id INTEGER PRIMARY KEY); CREATE TABLE child(id INTEGER PRIMARY KEY, p INTEGER REFERENCES parent(id) ON DELETE {action});')
        seed(db)
    import shutil
    sql = 'PRAGMA foreign_keys=OFF; CREATE TABLE __new_parent(id INTEGER PRIMARY KEY, note TEXT); INSERT INTO __new_parent(id) SELECT id FROM parent; DROP TABLE parent; ALTER TABLE __new_parent RENAME TO parent; PRAGMA foreign_keys=ON;'
    before = content(baseline)
    reference = tmp_path / 'reference.db'
    shutil.copyfile(baseline, reference)
    assert raw(reference, sql, reference=True)['success']
    expected = content(reference)
    trial = tmp_path / 'tx.db'
    shutil.copyfile(baseline, trial)
    execution = raw(trial, sql, transactional=True)
    assert execution['success']
    after = content(trial)
    findings = compare(before, expected, after, sql, execution)
    assert any(f['kind'] == 'content_digest' and f['table'] == 'child' for f in findings)
    assert after['counts']['child'] == (0 if action == 'CASCADE' else 3)
    deps = dependencies(baseline, ['parent'])
    assert deps[0]['seeded_references'] == 3
    assert deps[0]['on_delete'] == action
    assert compare(before, expected, expected, sql, {'foreign_keys_after': 1}) == []


def test_implicit_trigger_loss_detected_even_in_reference(tmp_path):
    dbpath = tmp_path / 'x.db'
    with sqlite3.connect(dbpath) as db:
        db.executescript('CREATE TABLE p(id INTEGER PRIMARY KEY); CREATE TRIGGER observe AFTER UPDATE ON p BEGIN SELECT 1; END;')
        seed(db)
    before = content(dbpath)
    sql = 'CREATE TABLE __new_p(id INTEGER PRIMARY KEY); INSERT INTO __new_p SELECT * FROM p; DROP TABLE p; ALTER TABLE __new_p RENAME TO p;'
    execution = raw(dbpath, sql)
    after = content(dbpath)
    assert any(f['kind'] == 'implicit_object_loss' for f in compare(before, after, after, sql, execution))


def test_seed_interdependent_checks_and_nullable_fields():
    db = sqlite3.connect(':memory:', isolation_level=None)
    db.executescript('''
      CREATE TABLE checked(id INTEGER PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('a','b')),
        a TEXT, b TEXT, n INTEGER NOT NULL, other TEXT,
        CHECK((kind='a' AND a IS NOT NULL AND b IS NULL AND n=1)
           OR (kind='b' AND a IS NULL AND b IS NOT NULL AND n=0)),
        CHECK(other IS NULL));
    ''')
    assert seed(db) == {'checked': 3}
    assert db.execute('SELECT count(*) FROM checked WHERE other IS NULL').fetchone()[0] == 3


def test_rebuild_tracks_preceding_rename():
    assert rebuilds('ALTER TABLE parents RENAME TO parent; CREATE TABLE __new_parent(id INTEGER); INSERT INTO __new_parent SELECT * FROM parent;') == ['parents']


def test_seed_overlapping_composite_self_and_external_fk():
    db = sqlite3.connect(':memory:', isolation_level=None)
    db.executescript('''
      CREATE TABLE parent(id TEXT PRIMARY KEY);
      CREATE TABLE item(id TEXT PRIMARY KEY, parent_id TEXT NOT NULL, group_id TEXT,
        UNIQUE(parent_id,id),
        FOREIGN KEY(parent_id) REFERENCES parent(id),
        FOREIGN KEY(parent_id,group_id) REFERENCES item(parent_id,id));
    ''')
    assert seed(db) == {'item': 3, 'parent': 3}
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    assert db.execute('SELECT count(*) FROM item WHERE group_id IS NOT NULL').fetchone()[0] == 3


@pytest.mark.parametrize('action', ['CASCADE', 'SET NULL'])
def test_real_migrator_only_runs_target_and_detects_loss(tmp_path, action):
    from smp.realworld import DRIVER
    if not (DRIVER / 'node_modules' / 'better-sqlite3').exists():
        pytest.skip('requires installed harness Node dependencies')
    root = tmp_path / 'extracted'
    folder = root / 'migrations'
    (folder / 'meta').mkdir(parents=True)
    (folder / 'meta' / '_journal.json').write_text(json.dumps({'version': '7', 'dialect': 'sqlite', 'entries': [
        {'idx': 0, 'version': '6', 'when': 1000, 'tag': '0000_initial', 'breakpoints': True},
        {'idx': 1, 'version': '6', 'when': 2000, 'tag': '0001_rebuild', 'breakpoints': True}]}))
    (folder / '0000_initial.sql').write_text(f'CREATE TABLE p(id INTEGER PRIMARY KEY);\n--> statement-breakpoint\nCREATE TABLE c(id INTEGER PRIMARY KEY, p INTEGER REFERENCES p(id) ON DELETE {action});')
    (folder / '0001_rebuild.sql').write_text('\n--> statement-breakpoint\n'.join([
        'PRAGMA foreign_keys=OFF;', 'CREATE TABLE __new_p(id INTEGER PRIMARY KEY, note TEXT);',
        'INSERT INTO __new_p(id) SELECT id FROM p;', 'DROP TABLE p;',
        'ALTER TABLE __new_p RENAME TO p;', 'PRAGMA foreign_keys=ON;']))
    result = replay({'repo': 'test/fixture'}, root, 'migrations/0001_rebuild.sql', None, DRIVER,
                    {'resolved': '0.45.4'}, tmp_path, 3)
    assert result['status'] == 'replayed'
    assert result['qualifying_parent_rebuild']
    assert result['paths']['raw']['outcome'] == 'preserved'
    assert result['paths']['drizzle']['outcome'] == 'silent-loss'
    assert result['paths']['drizzle']['execution']['target_journal_records'] == 1
    assert result['paths']['raw-tx']['outcome'] == 'silent-loss'


@pytest.mark.parametrize('sql', ["INSERT INTO t VALUES ('SELECT from somewhere');", "INSERT INTO t SELECT 'record';"])
def test_literal_select_seed_records_rejected(sql):
    with pytest.raises(Unreplayable):
        validate_sql(sql)


def test_intentional_table_drop_does_not_report_implicit_index_loss(tmp_path):
    database = tmp_path / 'x.db'
    with sqlite3.connect(database) as db:
        db.executescript('CREATE TABLE t(id INTEGER); CREATE INDEX t_id ON t(id); CREATE TABLE kept(id INTEGER);')
        seed(db)
    before = content(database)
    execution = raw(database, 'DROP TABLE t;')
    after = content(database)
    assert compare(before, after, after, 'DROP TABLE t;', execution) == []


def test_public_page_metadata_fallback_and_minimal_cache(tmp_path, monkeypatch):
    from smp import realworld
    import io
    monkeypatch.setattr(realworld, 'CACHE', tmp_path)
    (tmp_path / 'api-unavailable').touch()
    page = b'''<meta name="octolytics-dimension-repository_public" content="true" />
      <meta name="octolytics-dimension-repository_is_fork" content="false" />
      <script>{"stargazerCount":123,"defaultBranch":"main","license":{"spdxId":"MIT"}}</script>'''
    monkeypatch.setattr(realworld.urllib.request, 'urlopen', lambda *a, **kw: io.BytesIO(page))
    result = realworld.github('test/public')
    assert result['stars'] == 123
    assert result['license'] == 'MIT'
    assert 'public repository page' in result['metadata_source']
    saved = (tmp_path / 'metadata' / 'test--public.json').read_text()
    assert '<script>' not in saved
    monkeypatch.setattr(realworld.urllib.request, 'urlopen', lambda *a, **kw: pytest.fail('must use cached facts'))
    assert realworld.github('test/public') == result


def test_private_page_is_not_replayed(tmp_path, monkeypatch):
    from smp import realworld
    import io
    monkeypatch.setattr(realworld, 'CACHE', tmp_path)
    (tmp_path / 'api-unavailable').touch()
    monkeypatch.setattr(realworld.urllib.request, 'urlopen', lambda *a, **kw: io.BytesIO(b'{"stargazerCount":5}'))
    with pytest.raises(Unreplayable, match='visibility'):
        realworld.github('test/private')


def test_copy_source_is_not_necessarily_the_rebuilt_table():
    sql = 'CREATE TABLE __new_memberships(id INTEGER); INSERT INTO __new_memberships SELECT id FROM users; DROP TABLE memberships; ALTER TABLE __new_memberships RENAME TO memberships;'
    assert rebuilds(sql) == ['memberships']


def test_view_digest_covers_every_row_in_a_stable_order(tmp_path):
    def state(name, rows):
        path = tmp_path / name
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE t(id INTEGER PRIMARY KEY, v TEXT)')
            db.executemany('INSERT INTO t VALUES(?,?)', rows)
            db.execute('CREATE VIEW every AS SELECT v FROM t')
        return content(path)['view_rows']['view:every']
    rows = [(i, f'v{i:04d}') for i in range(1, 1202)]
    changed = rows[:-1] + [(1201, 'changed')]
    assert state('a.db', rows) == state('b.db', list(reversed(rows)))
    assert state('a2.db', rows) != state('c.db', changed)


def test_explicit_orm_version_never_falls_back(tmp_path, monkeypatch):
    from smp import realworld
    def unavailable(args, **kwargs):
        raise Unreplayable('npm pack failed (exit 1)')
    monkeypatch.setattr(realworld, 'command', unavailable)
    info = {'packages': [{'path': 'package.json', 'drizzle_orm': '^0.30.1', 'license': None}]}
    with pytest.raises(Unreplayable, match='0.30.9'):
        realworld.orm_runtime(info, 'migrations/0001.sql', tmp_path, '0.30.9')
    runtime, version = realworld.orm_runtime(info, 'migrations/0001.sql', tmp_path)
    assert runtime == realworld.DRIVER and version['fallback'] and version['resolved'] == realworld.FALLBACK


def test_resume_rejects_another_corpus(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from smp import realworld
    monkeypatch.setattr(realworld, 'CACHE', tmp_path / 'cache')
    corpus, probe = tmp_path / 'corpus.tsv', tmp_path / 'probe.json'
    corpus.write_text('owner/project\tmigrations/0001.sql\tabc\n')
    probe.write_text('[]')
    args = SimpleNamespace(evidence_dir=None, repo=None, migration=None, commit=None, orm_version=None, input=corpus,
                           probe=probe, output=tmp_path / 'out', target=20, rows=3, max_repos=None, resume=True, pins=None)
    def stop(*a, **k):
        raise AssertionError('no replay may start')
    monkeypatch.setattr(realworld, 'repository', stop)
    args.output.mkdir()
    prior = {'format_version': 1, 'rows': [], 'rows_per_table': 3, 'target_qualifying_migrations': 20,
             'source_hashes': {str(p.relative_to(realworld.ROOT)): __import__('hashlib').sha256(p.read_bytes()).hexdigest()
                               for p in (Path(realworld.__file__), realworld.ROOT / 'smp/realworld_seed.py',
                                         realworld.ROOT / 'runners/realworld/run.cjs')},
             'input_hashes': {'corpus': '0' * 64, 'probe': '0' * 64}}
    (args.output / 'realworld.json').write_text(json.dumps(prior))
    with pytest.raises(ValueError, match='input_hashes'):
        realworld.run(args)
