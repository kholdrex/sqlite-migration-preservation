"""Run Django, Alembic and Prisma against the shared preservation matrix."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import traceback

from .checks import create_database, require, statements
from .environment import ROOT, claim_output, local_env, scratch_scope, source_hashes
from .matrix_spec import CONTEXTS
from .operation_matrix import read_gzip, write_gzip
from .orm_checks import install_prisma_observer, observation, prisma_observations, transaction_structure
from .orm_spec import OPERATIONS, alembic_operation, django_models, orm_fixture, prisma_schema
from .pilot import DEFAULT_DOCTOR, lint, resolve_doctor
from .preservation import classify, expected_present, violations
from .rebuild import CLASSIFIER, rebuild
from .runners import run_raw, TRANSACTION

PINS = ROOT / 'runners/orm/pins.json'
PRISMA = ROOT / 'runners/prisma/node_modules/.bin/prisma'


def command(args, cwd=ROOT, check=True):
    env = local_env()
    env.update(CHECKPOINT_DISABLE='1', PRISMA_HIDE_UPDATE_MESSAGE='1', PRISMA_TELEMETRY_DISABLED='1',
               XDG_CACHE_HOME=str(ROOT / '.cache/orm'), PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([str(a) for a in args], cwd=cwd, env=env, text=True,
                            capture_output=True, timeout=120)
    if check and result.returncode:
        raise RuntimeError(f'{args}: {result.stdout}\n{result.stderr}')
    return result


def python(label):
    return ROOT / 'runners/orm' / label / '.venv/bin/python'


def django_settings(work, database):
    (work / 'settings.py').write_text(
        "SECRET_KEY = 'local-matrix'\nINSTALLED_APPS = ['matrixapp']\n"
        f"DATABASES = {{'default': {{'ENGINE': 'django.db.backends.sqlite3', 'NAME': {str(database)!r}}}}}\n"
        "DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'\nUSE_TZ = False\n")


def prepare_django(work, label, op, ctx):
    app = work / 'matrixapp'
    (app / 'migrations').mkdir(parents=True)
    (app / '__init__.py').touch()
    (app / 'migrations/__init__.py').touch()
    django_settings(work, work / 'generation.db')
    runner = ROOT / 'runners/orm/django_runner.py'
    for after in (False, True):
        source = django_models(op, ctx, after, database_cascade=label == 'django-current')
        (work / ('after.py' if after else 'before.py')).write_text(source)
        (app / 'models.py').write_text(source)
        if after and op == 'rename_column':
            # Noninteractive autodetection cannot distinguish a rename from drop/add.
            (app / 'migrations/0002_rename.py').write_text(
                "from django.db import migrations\nclass Migration(migrations.Migration):\n"
                "    dependencies = [('matrixapp', '0001_initial')]\n"
                "    operations = [migrations.RenameField('parent', 'value', 'renamed_value')]\n")
        else:
            command([python(label), runner, work, 'generate'])
    if not list((app / 'migrations').glob('0002*.py')):
        raise RuntimeError('Autodetection produced no operation')
    command([python(label), runner, work, 'sql'])
    return (work / 'migration.sql').read_text()


def prepare_alembic(work, op, mode):
    folder = work / 'migration'
    (folder / 'versions').mkdir(parents=True)
    (folder / 'env.py').write_text(
        "from alembic import context\nconnection = context.config.attributes['connection']\n"
        "context.configure(connection=connection)\nwith context.begin_transaction():\n    context.run_migrations()\n")
    (folder / 'versions/0001_change.py').write_text(
        "from alembic import op\nimport sqlalchemy as sa\nrevision = '0001'\ndown_revision = None\n"
        "def upgrade():\n" + alembic_operation(op, mode))


def prepare_prisma(work, op, ctx):
    for after in (False, True):
        (work / ('after.prisma' if after else 'before.prisma')).write_text(prisma_schema(op, ctx, after))
    config = work / 'prisma.config.ts'
    config.write_text("export default {schema: './after.prisma', migrations: {path: './migrations'}, datasource: {url: 'file:./generation.db'}};\n")
    result = command([PRISMA, 'migrate', 'diff', '--from-schema', work / 'before.prisma',
                      '--to-schema', work / 'after.prisma', '--script', '--config', config], cwd=work)
    (work / 'generation.log').write_text(result.stderr)
    (work / 'migration.sql').write_text(result.stdout)
    return result.stdout


def prisma_config(work, database):
    (work / 'prisma.config.ts').write_text(
        "export default {schema: './after.prisma', migrations: {path: './migrations'}, datasource: {url: "
        + json.dumps('file:' + str(database)) + '}};\n')


def deploy_prisma(work, database, sql):
    prisma_config(work, database)
    migrations = work / 'migrations'
    (migrations / '0001_baseline').mkdir(parents=True)
    (migrations / 'migration_lock.toml').write_text('provider = "sqlite"\n')
    (migrations / '0001_baseline/migration.sql').write_text('-- Existing shared fixture.\n')
    resolved = command([PRISMA, 'migrate', 'resolve', '--applied', '0001_baseline', '--config', work / 'prisma.config.ts'], cwd=work)
    install_prisma_observer(database)
    (migrations / '0002_change').mkdir()
    (migrations / '0002_change/migration.sql').write_text(sql)
    result = command([PRISMA, 'migrate', 'deploy', '--config', work / 'prisma.config.ts'], cwd=work, check=False)
    (work / 'stdout.log').write_text(resolved.stdout + result.stdout)
    (work / 'stderr.log').write_text(resolved.stderr + result.stderr)
    # The ledger callbacks observe the writing connection. The generated file
    # still cannot be labeled as a full runtime trace.
    (work / 'executed.sql').write_text('')
    observed = prisma_observations(database)
    before = next((r for r in observed if r[0] == 'before'), None)
    after = next((r for r in reversed(observed) if r[0] in ('after', 'failure')), None)
    return {'success': result.returncode == 0, 'returncode': result.returncode,
            'error': result.stderr if result.returncode else None,
            'prisma': json.loads((ROOT / 'runners/prisma/node_modules/prisma/package.json').read_text())['version'],
            'foreign_keys_before': before[1] if before else None,
            'foreign_keys_after': after[1] if after else None,
            'sqlite': before[3] if before else None,
            'connection_observations': observed,
            'trace_available': False}


def execute_framework(work, fw, label, database, sql):
    if fw == 'django':
        django_settings(work, database)
        result = command([python(label), ROOT / 'runners/orm/django_runner.py', work, 'apply'])
    elif fw == 'alembic':
        result = command([python('alembic'), ROOT / 'runners/orm/alembic_runner.py', work, database])
    else:
        return deploy_prisma(work, database, sql)
    (work / 'stdout.log').write_text(result.stdout)
    (work / 'stderr.log').write_text(result.stderr)
    return json.loads((work / 'runner.json').read_text())


def checked_violations(before, after, spec, execution):
    found = violations(before, after, spec, execution)
    if execution.get('trace_available') is False and execution.get('foreign_keys_after') is None:
        # Unknown connection-local enforcement is a limitation, not an observed loss.
        found = [v for v in found if v['kind'] != 'fk_enforcement']
    return found


def group(job, output, doctor):
    fw, label, mode, op, ctx = job
    key = '_'.join(job)
    archive = output / 'orm_evidence' / (key + '.json.gz')
    if archive.exists():
        saved = read_gzip(archive)
        require((saved['spec'], saved['schema'], saved['seed']) == orm_fixture(fw, op, ctx))
        for row in saved['rows']:
            for trial in row['trials'].values():
                require(trial['violations'] == checked_violations(trial['before'], trial['after'], saved['spec'], trial['execution']))
        return saved['rows']
    work = ROOT / '.cache/orm/work' / scratch_scope(output) / key
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    spec, schema, seed = orm_fixture(fw, op, ctx)
    rows = []
    evidence = {'spec': spec, 'schema': schema, 'seed': seed, 'trials': {}}
    try:
        generation = work / 'generation'
        generation.mkdir()
        sql = ''
        if fw == 'django':
            sql = prepare_django(generation, label, op, ctx)
        elif fw == 'alembic':
            prepare_alembic(generation, op, mode)
            # Reflection requires a real database. Capture a successful C0 run
            # with this context's parent definition to obtain the complete SQL.
            probe_schema = re.sub(r'CREATE VIEW parent_view[^;]*;', '', schema)
            database = generation / 'generation.db'
            create_database(database, probe_schema, '', False)
            meta = execute_framework(generation, fw, label, database, '')
            if not meta['success']:
                raise RuntimeError(meta)
            sql = '\n'.join(s for s in statements((generation / 'executed.sql').read_text())
                            if re.match(r'^\s*(CREATE|DROP|ALTER|INSERT INTO\s+["`]?_alembic)', s, re.I)
                            and 'alembic_version' not in s)
            (generation / 'migration.sql').write_text(sql)
        else:
            sql = prepare_prisma(generation, op, ctx)
        history = {str(p.relative_to(generation)): p.read_text() for p in generation.rglob('*')
                   if p.is_file() and p.suffix in ('.py', '.prisma', '.ts', '.sql', '.log')}
        evidence['generation'] = history
        raw_sql = '\n'.join(s for s in statements(sql) if not TRANSACTION.match(s)) if fw == 'django' else sql
        for path in (mode if fw == 'alembic' else fw, 'raw', 'raw-tx'):
            trials = {}
            for populated in (True, False):
                population = 'populated' if populated else 'empty'
                trial = work / path / population
                shutil.copytree(generation, trial, ignore=shutil.ignore_patterns('*.db', '*.db-*', 'executed.sql', 'runner.json'))
                database = trial / 'database.db'
                create_database(database, schema, seed, populated)
                before = observation(database, spec)
                require(not before['errors'] and not before['foreign_key_check'])
                require(not expected_present(before, spec['expected']), spec)
                if path in ('raw', 'raw-tx'):
                    execution = run_raw(database, raw_sql, trial, path == 'raw-tx')
                else:
                    execution = execute_framework(trial, fw, label, database, sql)
                after = observation(database, spec, True)
                found = checked_violations(before, after, spec, execution)
                trace = (trial / 'executed.sql').read_text()
                trials[population] = {'execution': execution, 'before': before, 'after': after,
                    'violations': found, 'outcome': classify(execution['success'], found, before, after),
                    'rebuild': rebuild(trace) if execution.get('trace_available', True) else None,
                    'planned_rebuild': rebuild(sql), 'transaction_structure': transaction_structure(trace)}
                evidence['trials'][path + '/' + population] = {p.name: p.read_text() for p in trial.iterdir()
                    if p.suffix in ('.sql', '.log', '.json')}
            trace = evidence['trials'][path + '/populated']['executed.sql']
            lint_results = {}
            for name, fragment in {'migration_only': raw_sql, 'schema_and_migration': schema + '\n' + raw_sql,
                                   'executed': trace, 'schema_and_executed': schema + '\n' + trace}.items():
                if not trace and 'executed' in name:
                    lint_results[name] = {'available': False, 'reason': 'CLI exposes no runtime SQL trace'}
                else:
                    lint_results[name] = lint(doctor, fragment, work / ('lint_' + name + '.sql'))
            rows.append({'framework': fw, 'version_label': label, 'mode': mode, 'operation': op,
                'context': ctx, 'path': path, 'supported': True, 'spec': spec,
                'outcome': trials['populated']['outcome'], 'trials': trials,
                'rebuild': trials['populated']['rebuild'], 'planned_rebuild': rebuild(sql),
                'artifacts': str(archive.relative_to(ROOT)),
                'detectors': {'empty_db': not trials['empty']['execution']['success'],
                              'populated_invariants': bool(trials['populated']['violations']), 'lint': lint_results}})
        evidence['rows'] = rows
        write_gzip(archive, evidence)
        return rows
    finally:
        shutil.rmtree(work)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    parser.add_argument('--frameworks', nargs='+', choices=['django', 'alembic', 'prisma'], default=['django', 'alembic', 'prisma'])
    parser.add_argument('--operations', nargs='+', choices=list(OPERATIONS), default=OPERATIONS)
    parser.add_argument('--contexts', nargs='+', choices=list(CONTEXTS), default=list(CONTEXTS))
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--doctor', type=Path, default=DEFAULT_DOCTOR)
    args = parser.parse_args()
    args.doctor = resolve_doctor(args.doctor)
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError('Output must be inside the repository')
    pins = json.loads(PINS.read_text())
    doctor_sha256 = hashlib.sha256(args.doctor.read_bytes()).hexdigest() if args.doctor.exists() else None
    claim_output(output, 'orm_manifest.json', output / 'orm_evidence',
                 {'sqlite_doctor_sha256': doctor_sha256, 'pins': pins, 'rebuild_classifier': CLASSIFIER,
                  'source_sha256': source_hashes()})
    configurations = [('django', 'django-current', 'default'), ('django', 'django-previous', 'default'),
                      ('alembic', 'alembic', 'auto'), ('alembic', 'alembic', 'always'), ('prisma', 'prisma-stable', 'default')]
    jobs, unsupported = [], []
    for fw, label, mode in configurations:
        if fw not in args.frameworks:
            continue
        for op in args.operations:
            for ctx in args.contexts:
                if fw == 'prisma' and op in ('add_check_constraint', 'remove_check_constraint'):
                    unsupported.append({'framework': fw, 'version_label': label, 'mode': mode,
                                        'operation': op, 'context': ctx, 'supported': False,
                                        'reason': 'Prisma schema language cannot express CHECK constraints'})
                else:
                    jobs.append((fw, label, mode, op, ctx))
    if 'prisma' in args.frameworks:
        unsupported.extend({'framework': 'prisma', 'version_label': 'prisma-latest-tag', 'mode': 'default',
                            'operation': op, 'context': ctx, 'supported': False,
                            'reason': 'Prisma 8 CLI does not expose the migrate diff/deploy command family'}
                           for op in args.operations for ctx in args.contexts)
    rows, errors = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(group, job, output, args.doctor): job for job in jobs}
        for i, future in enumerate(as_completed(futures), 1):
            try:
                rows.extend(future.result())
                print(f'{i}/{len(jobs)} {futures[future]}', flush=True)
            except Exception as exc:
                errors.append({'job': futures[future], 'error': str(exc), 'traceback': traceback.format_exc()})
                print(f'ERROR {futures[future]}: {exc}', flush=True)
    result = {'format_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(),
              'pins': pins, 'contexts': CONTEXTS, 'operations': list(OPERATIONS),
              'requested_groups': len(jobs), 'errors': errors, 'unsupported': unsupported,
              'sqlite_doctor_sha256': doctor_sha256,
              'rebuild_classifier': CLASSIFIER,
              'rows': sorted(rows, key=lambda r: (r['framework'], r['version_label'], r['mode'], r['path'], r['operation'], r['context']))}
    (output / 'orm_matrix.json').write_text(json.dumps(result, separators=(',', ':')) + '\n')
    from .orm_report import write_report
    write_report(result, output / 'orm_matrix.md')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
