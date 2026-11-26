"""Observation adapters for runner bookkeeping and SQL transaction evidence."""
import re
import sqlite3
from contextlib import closing

from .preservation import observe, probe_constraint

BOOKKEEPING = ('django_migrations', 'alembic_version', '_prisma_migrations',
               '_smp_prisma_connection', '_smp_prisma_start', '_smp_prisma_end')


def install_prisma_observer(database):
    """Read engine-connection PRAGMAs from migration-ledger trigger callbacks."""
    with closing(sqlite3.connect(database)) as db:
        db.execute('CREATE TABLE _smp_prisma_connection(stage TEXT, fk INTEGER, deferred INTEGER, sqlite TEXT)')
        for name, event, condition, stage in (
            ('start', 'INSERT', '1', "'before'"),
            ('end', 'UPDATE', 'NEW.finished_at IS NOT NULL OR NEW.logs IS NOT NULL',
             "CASE WHEN NEW.finished_at IS NOT NULL THEN 'after' ELSE 'failure' END"),
        ):
            db.execute(f'''CREATE TRIGGER _smp_prisma_{name} AFTER {event} ON _prisma_migrations
                WHEN NEW.migration_name='0002_change' AND ({condition}) BEGIN
                INSERT INTO _smp_prisma_connection
                SELECT {stage}, foreign_keys, defer_foreign_keys, sqlite_version()
                FROM pragma_foreign_keys, pragma_defer_foreign_keys;
                END''')
        db.commit()


def prisma_observations(database):
    with closing(sqlite3.connect(database)) as db:
        return db.execute('SELECT * FROM _smp_prisma_connection ORDER BY rowid').fetchall()


def observation(database, spec, after=False):
    # These runners keep their own ledgers; only those exact names are left out of the state digest.
    result = observe(database, spec, after=after,
                     bookkeeping=lambda name: name.startswith('sqlite_') or name in BOOKKEEPING)
    try:
        probe_constraint(database, spec, result)
    except sqlite3.OperationalError as exc:
        result['intended_probe'] = None
        result['intended_probe_error'] = str(exc)
        result['errors'].append(f'constraint probe: {exc}')
    return result


def transaction_structure(trace):
    return [line.strip() for line in trace.splitlines()
            if re.match(r'^\s*(BEGIN|COMMIT|END|ROLLBACK|SAVEPOINT|RELEASE|PRAGMA\s+(?:foreign_keys|defer_foreign_keys))\b', line, re.I)]
