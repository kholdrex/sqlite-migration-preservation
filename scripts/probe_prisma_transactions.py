"""Supplement deploy evidence with connection-local PRAGMA and atomicity probes."""
import argparse
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smp.checks import create_database
from smp.orm_matrix import deploy_prisma, prepare_prisma
from smp.orm_spec import orm_fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/orm_prisma_probes.json")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        parser.error("Output must be inside the repository")
    if output.exists():
        parser.error("Use a fresh output file")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = ROOT / '.cache/orm/prisma-probes'
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    results = []
    try:
        for name in ('generated_rebuild', 'failure_no_begin', 'failure_explicit_begin'):
            folder = work / name
            folder.mkdir()
            database = folder / 'database.db'
            _, schema, seed = orm_fixture('prisma', 'set_default', 'C0')
            create_database(database, schema, seed, True)
            with sqlite3.connect(database) as db:
                db.execute('CREATE TABLE probe_observations(stage TEXT, foreign_keys INTEGER, deferred INTEGER, sqlite TEXT)')
            generated = prepare_prisma(folder, 'set_default', 'C0')
            def checkpoint(stage):
                return f"INSERT INTO probe_observations SELECT '{stage}', foreign_keys, defer_foreign_keys, sqlite_version() FROM pragma_foreign_keys, pragma_defer_foreign_keys;\n"
            sql = checkpoint('before') + generated + checkpoint('after')
            if name.startswith('failure'):
                sql += 'SELECT * FROM deliberately_missing_probe_table;\n'
            if name == 'failure_explicit_begin':
                sql = 'BEGIN;\n' + sql + 'COMMIT;\n'
            execution = deploy_prisma(folder, database, sql)
            with sqlite3.connect(database) as db:
                observations = db.execute('SELECT * FROM probe_observations').fetchall()
                columns = db.execute('PRAGMA table_info(parents)').fetchall()
                ledger = db.execute('SELECT migration_name,finished_at,rolled_back_at FROM _prisma_migrations ORDER BY migration_name').fetchall()
            results.append({'name': name, 'execution': execution, 'generated_sql': generated,
                            'probe_sql': sql, 'observations': observations, 'columns_after': columns,
                            'ledger': ledger, 'stdout': (folder / 'stdout.log').read_text(),
                            'stderr': (folder / 'stderr.log').read_text()})
        output.write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps([{k: r[k] for k in ('name', 'observations')} for r in results], indent=2))
    finally:
        shutil.rmtree(work)


if __name__ == '__main__':
    main()
