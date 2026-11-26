import sqlite3

from smp.checks import create_database
from smp.orm_checks import install_prisma_observer, observation, prisma_observations, transaction_structure
from smp.orm_matrix import checked_violations
from smp.orm_spec import orm_fixture
from smp.preservation import classify


def test_bookkeeping_does_not_hide_application_damage(tmp_path):
    spec, schema, seed = orm_fixture('django', 'add_column', 'C0')
    database = tmp_path / 'test.db'
    create_database(database, schema, seed, True)
    before = observation(database, spec)
    with sqlite3.connect(database) as db:
        for table in ('django_migrations', 'alembic_version', '_prisma_migrations'):
            db.execute(f'CREATE TABLE {table}(id INTEGER PRIMARY KEY, value TEXT)')
            db.execute(f"INSERT INTO {table} VALUES(1, 'bookkeeping')")
    ledger_only = observation(database, spec)
    assert before['state_digest'] == ledger_only['state_digest']
    assert classify(False, [], before, ledger_only) == 'failed-loudly'
    with sqlite3.connect(database) as db:
        db.execute("UPDATE parents SET payload='damaged' WHERE id=1")
    damaged = observation(database, spec)
    assert classify(False, [], before, damaged) == 'failed-loudly-partial'


def test_unknown_cli_fk_state_is_not_claimed_as_a_loss(tmp_path):
    spec, schema, seed = orm_fixture('prisma', 'add_column', 'C2')
    database = tmp_path / 'test.db'
    create_database(database, schema, seed, True)
    before = observation(database, spec)
    with sqlite3.connect(database) as db:
        db.execute('ALTER TABLE parents ADD COLUMN note TEXT')
        db.execute('UPDATE children SET parent_id=NULL')
    after = observation(database, spec, True)
    execution = {'success': True, 'trace_available': False, 'foreign_keys_after': None}
    found = checked_violations(before, after, spec, execution)
    assert {v['kind'] for v in found} == {'content_digest'}
    execution['foreign_keys_after'] = 0
    assert 'fk_enforcement' in {v['kind'] for v in checked_violations(before, after, spec, execution)}
    execution.update(trace_available=True, foreign_keys_after=0)
    assert 'fk_enforcement' in {v['kind'] for v in checked_violations(before, after, spec, execution)}


def test_transaction_structure_retains_pragma_order():
    trace = 'PRAGMA foreign_keys=OFF;\nBEGIN;\nCREATE TABLE x(id);\nPRAGMA defer_foreign_keys=ON;\nCOMMIT;\nPRAGMA foreign_keys=ON;'
    assert transaction_structure(trace) == ['PRAGMA foreign_keys=OFF;', 'BEGIN;',
        'PRAGMA defer_foreign_keys=ON;', 'COMMIT;', 'PRAGMA foreign_keys=ON;']


def test_constraint_probe_records_missing_table_after_partial_failure(tmp_path):
    spec, schema, seed = orm_fixture('alembic', 'add_unique', 'C7')
    database = tmp_path / 'test.db'
    create_database(database, schema, seed, True)
    before = observation(database, spec)
    with sqlite3.connect(database) as db:
        db.execute('DROP TABLE parents')
    after = observation(database, spec, True)
    assert after['intended_probe'] is None
    assert 'no such table' in after['intended_probe_error']
    found = checked_violations(before, after, spec, {'success': False, 'foreign_keys_after': 1})
    assert 'intended_change_missing' in {v['kind'] for v in found}
    assert classify(False, found, before, after) == 'failed-loudly-partial'


def test_prisma_ledger_observer_reads_the_writing_connection(tmp_path):
    spec, schema, seed = orm_fixture('prisma', 'add_column', 'C0')
    database = tmp_path / 'test.db'
    create_database(database, schema, seed, True)
    before = observation(database, spec)
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE _prisma_migrations(migration_name TEXT, finished_at TEXT, logs TEXT)')
    install_prisma_observer(database)
    db = sqlite3.connect(database, isolation_level=None)
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute("INSERT INTO _prisma_migrations VALUES('0002_change', NULL, NULL)")
        db.execute('PRAGMA foreign_keys=OFF')
        db.execute("UPDATE _prisma_migrations SET logs='failure'")
    finally:
        db.close()
    observed = prisma_observations(database)
    assert [(r[0], r[1]) for r in observed] == [('before', 1), ('failure', 0)]
    assert observation(database, spec)['state_digest'] == before['state_digest']


def test_state_digest_is_computed_once_with_the_runner_ledger_names(tmp_path):
    from smp.checks import canonical_sql, identifier
    from smp.preservation import digest, observe
    spec, schema, seed = orm_fixture('django', 'add_column', 'C0')
    database = tmp_path / 'test.db'
    create_database(database, schema, seed, True)
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE django_migrations(id INTEGER PRIMARY KEY, value TEXT)')
        db.execute('CREATE TABLE schema_migrations(version TEXT)')
        db.execute("INSERT INTO schema_migrations VALUES('application data here')")
        state = [[kind, name, canonical_sql(sql), db.execute(f'SELECT * FROM {identifier(name)} ORDER BY rowid').fetchall()
                  if kind == 'table' else None]
                 for kind, name, sql in db.execute('SELECT type,name,sql FROM sqlite_schema WHERE sql IS NOT NULL ORDER BY type,name')
                 if name != 'django_migrations']
    assert observation(database, spec)['state_digest'] == digest(state)
    assert observe(database, spec)['state_digest'] != digest(state)
