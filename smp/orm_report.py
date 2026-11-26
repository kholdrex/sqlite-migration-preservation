"""Render the ORM matrix report."""
from collections import Counter
from itertools import groupby
import json

from .environment import ROOT
from .matrix_report import ABBREVIATIONS, matrix_outcomes
from .matrix_spec import CONTEXTS
from .orm_spec import alembic_operation
from .report import OMITTED

ORM_OUTCOMES = "20e236f73361eaf06eafda8a546a7105b0004a7feff79742646098bedd1db637"


def label(row, population='populated'):
    trial = row['trials'][population]
    outcome = {'failed-loudly': 'loud', 'failed-loudly-partial': 'loud-partial'}.get(trial['outcome'], trial['outcome'])
    if outcome == 'silent-loss':
        outcome += '(' + ','.join(sorted({ABBREVIATIONS.get(v['kind'], v['kind']) for v in trial['violations']})) + ')'
    return outcome + ('†' if trial['rebuild'] else ('‡' if trial['planned_rebuild'] and trial['rebuild'] is None else ''))


def write_report(result, path):
    rows = result['rows']
    pins = result['pins']
    versions = {'django-current': pins['Django'], 'django-previous': pins['Django_previous'],
                'alembic': pins['alembic'] + ' / SQLAlchemy ' + pins['SQLAlchemy'],
                'prisma-stable': pins['prisma_stable']}

    def display(group_key):
        framework, pin, *rest = group_key
        return ' / '.join([framework, versions.get(pin, pin), *rest])
    recorded = matrix_outcomes(rows) == ORM_OUTCOMES
    lines = ['# SQLite ORM operation preservation matrix', '', f"Observed: {result['observed_at']}.", '',
        f"{len(rows)} populated/empty pairs; {len(result['errors'])} infrastructure errors. "
        f"{len(result['unsupported'])} unsupported operation/context combinations.", '',
        *([] if recorded else [OMITTED, '']),
        'This matrix adds Django, Alembic and Prisma to the Rails/Drizzle operation matrix. Counts are cells, not ecosystem prevalence. '
        'The union has 20 operations; aliases remove/drop column, FK and index are unified. '
        'Each cell has a populated and empty execution. † = runtime CREATE/DROP rebuild; '
        '‡ = rebuild in generated Prisma SQL, runtime trace unavailable. '
        'Loud compares persisted application state, excluding only migration bookkeeping.', '',
        'Invariants: R rows; D content digest; O schema objects; T trigger behavior; V view behavior; '
        'K FK definition; E connection FK enforcement; F foreign_key_check; I integrity_check; Q snapshot error; C intended change.', '',
        '| Context | Dependency |', '|---|---|']
    lines += [f'| {k} | {v} |' for k, v in CONTEXTS.items()]
    lines += ['', '## Pins and execution', '',
        f"- Django {pins['Django']} and previous minor {pins['Django_previous']}, resolved from [PyPI]({pins['Django_source']}). "
        'Model changes use makemigrations and call_command("migrate"); rename column uses an explicit RenameField because noninteractive autodetection cannot confirm a rename. '
        'The initial model migration is recorded as applied over the shared SQL fixture. Incoming dependency tables remain external to Django model state. '
        'C8 uses DB_CASCADE on 6.1, and CASCADE on 6.0 where the database-action API is unavailable; K measures any change to the seeded SQL action.',
        f"- Alembic {pins['alembic']} ([PyPI]({pins['alembic_source']})) / SQLAlchemy {pins['SQLAlchemy']} "
        f"([PyPI]({pins['SQLAlchemy_source']})): command.upgrade, context.configure defaults, transaction_per_migration=False. "
        'FK enforcement is enabled on the SQLAlchemy connection; no FK-disable workaround or forced BEGIN is added. Both auto and always batch modes are measured. '
        'rename_table is op.rename_table outside batch; drop_unique drops the fixture’s unique index.',
        f"- Prisma stable {pins['prisma_stable']}, from [npm]({pins['prisma_source']}). "
        f"The registry latest tag was {pins['prisma_latest_tag']}; that CLI replaces the migrate diff/deploy command family. "
        'The diff/deploy workflow is measured on the latest stable release, and the latest tag is recorded as unsupported. '
        'Untouched migrate diff --script output is applied by migrate deploy after baselining the existing fixture with migrate resolve. '
        'CHECK operations are unsupported in the schema language. Schema diffs have no rename identity; rename requests measure the actual drop/add result, including data loss.',
        '- Raw paths execute generated SQL in Python SQLite with FK enforcement ON, in autocommit or one explicit BEGIN. '
        'Django sqlmigrate BEGIN/COMMIT wrappers are removed for both raw comparisons; its schema-editor PRAGMA orchestration is absent from sqlmigrate. '
        'Alembic SQL is captured from a successful empty reflection run (the dependent view omitted only during generation); Prisma SQL is unmodified.', '',
        '## Cross-framework summary', '',
        'Populated framework paths only. Loud includes partial commit; partial is also shown separately. Different operation sets and pins are not rankings.', '',
        '| Framework / pin / mode | Cells | Silent loss | Loud (partial) | Preserved | Mechanism to inspect |',
        '|---|---:|---:|---:|---:|---|']
    old = json.loads((ROOT / 'results/operation_matrix.json').read_text())
    combined = [r for r in old['rows'] if r['path'] == r['framework']] + [r for r in rows if r['path'] not in ('raw', 'raw-tx')]
    key = lambda r: (r['framework'], r['version_label'], r.get('mode', 'default'))
    mechanisms = {'rails': 'FK cascade/SET NULL and external triggers; pin dependent',
                  'drizzle': 'FK actions and omitted external objects; pin dependent',
                  'django': 'Model-state rebuild omits external objects; SQL FK action can change',
                  'alembic': 'Enforced FK actions; triggers not reflected; inline C8 FK action omitted by reflection',
                  'prisma': 'Schema-only rebuild omits external objects; rename diff drops data'}
    for group_key, group_rows in groupby(sorted(combined, key=key), key=key):
        group_rows = list(group_rows)
        c = Counter(r['outcome'] for r in group_rows)
        lines.append(f"| {display(group_key)} | {len(group_rows)} | {c['silent-loss']} | {c['failed-loudly'] + c['failed-loudly-partial']} ({c['failed-loudly-partial']}) | {c['preserved']} | {mechanisms[group_key[0]]} |")
    lines.append(f"| prisma / {pins['prisma_latest_tag']} | 0 | — | — | — | Command family unsupported |")
    lines += ['', '## Operation mappings', '',
              'The exact before/after model sources and migration files are archived per context. '
              'SQL defaults use Django db_default, Alembic server_default, and Prisma @default.', '',
              '| Operation | Django | Alembic | Prisma schema diff |', '|---|---|---|---|']
    django = {
        'add_column': 'AddField', 'drop_column': 'RemoveField', 'rename_column': 'RenameField (explicit)',
        'change_type': 'AlterField(TextField → IntegerField)', 'set_not_null': 'AlterField(null=False)',
        'drop_not_null': 'AlterField(null=True)', 'set_default': "AlterField(db_default='9')",
        'change_default': "AlterField(db_default='5' → '9')", 'drop_default': 'AlterField(remove db_default)',
        'add_foreign_key': 'AlterField(db_constraint=True)', 'drop_foreign_key': 'AlterField(db_constraint=False)',
        'add_unique': 'AlterField(unique=True)', 'drop_unique': 'AlterField(unique=False)',
        'add_index': 'AddIndex', 'drop_index': 'RemoveIndex', 'rename_table': 'AlterModelTable',
        'add_reference': 'AddField(ForeignKey)', 'add_timestamps': 'Two nullable DateTimeField additions',
        'add_check_constraint': 'AddConstraint(CheckConstraint)', 'remove_check_constraint': 'RemoveConstraint',
    }
    prisma = {
        'add_column': 'Add nullable field', 'drop_column': 'Remove field', 'rename_column': 'Remove old / add new field',
        'change_type': 'String → Int', 'set_not_null': 'Remove ?', 'drop_not_null': 'Add ?',
        'set_default': '@default("9")', 'change_default': '@default("5") → @default("9")',
        'drop_default': 'Remove @default', 'add_foreign_key': 'Add @relation', 'drop_foreign_key': 'Remove @relation',
        'add_unique': 'Add @unique', 'drop_unique': 'Remove @unique', 'add_index': 'Add @@index',
        'drop_index': 'Remove @@index', 'rename_table': 'Change @@map (drop/create)',
        'add_reference': 'Add nullable field and @relation', 'add_timestamps': 'Two nullable DateTime fields',
        'add_check_constraint': 'Unsupported', 'remove_check_constraint': 'Unsupported',
    }
    for op in result['operations']:
        api = alembic_operation(op, 'auto').strip().splitlines()
        api = '; '.join(line.strip() for line in api if not line.strip().startswith('with '))
        lines.append(f'| {op} | {django[op]} | `{api}` | {prisma[op]} |')
    lines += ['', '## SQLite runtimes', '', '| Path | Observed SQLite versions |', '|---|---|']
    for execution_path in sorted({r['path'] for r in rows}):
        sqlite_versions = sorted({t['execution']['sqlite'] for r in rows if r['path'] == execution_path
                                  for t in r['trials'].values() if t['execution'].get('sqlite')})
        lines.append(f"| {execution_path} | {', '.join(sqlite_versions)} |")
    lines += ['', '## Counts by path and population', '', '| Framework / pin / mode / path | Population | Cells | Silent loss | Loud | Loud partial | Preserved |', '|---|---|---:|---:|---:|---:|---:|']
    key = lambda r: (r['framework'], r['version_label'], r['mode'], r['path'])
    groups = [(k, list(g)) for k, g in groupby(sorted(rows, key=key), key=key)]
    for k, group_rows in groups:
        for population in ('populated', 'empty'):
            counts = Counter(r['trials'][population]['outcome'] for r in group_rows)
            lines.append(f"| {display(k)} | {population} | {len(group_rows)} | " + ' | '.join(str(counts[o]) for o in ('silent-loss', 'failed-loudly', 'failed-loudly-partial', 'preserved')) + ' |')
    for k, group_rows in groups:
        lines += ['', '## ' + display(k), '']
        for population in ('populated', 'empty'):
            lines += [population.capitalize() + ':', '', '| Operation | ' + ' | '.join(CONTEXTS) + ' |', '|---|' + '---|' * len(CONTEXTS)]
            by_cell = {(r['operation'], r['context']): r for r in group_rows}
            for op in result['operations']:
                cells = [label(by_cell[op, ctx], population) if (op, ctx) in by_cell else ('unsupported' if k[0] == 'prisma' and 'check_constraint' in op else 'not run') for ctx in CONTEXTS]
                lines.append('| ' + op + ' | ' + ' | '.join(cells) + ' |')
            lines.append('')
        rebuild_ops = sorted({r['operation'] for r in group_rows if r['rebuild'] or r['planned_rebuild']})
        lines += ['Rebuild observed or planned: ' + ', '.join(rebuild_ops) + '.', '',
                  'Representative executed transaction/PRAGMA sequences (deduplicated):', '']
        sequences = sorted({tuple(r['trials']['populated']['transaction_structure']) for r in group_rows})
        for sequence in sequences:
            lines.append('- `' + (' → '.join(sequence) or 'No exposed transaction/PRAGMA statements') + '`')
    lines += ['', '## Prisma / ' + pins['prisma_latest_tag'] + ' / migrate workflow', '',
              'Unsupported in both populations: this CLI exposes a different migration command family. '
              'This pin has no executions. The stable-pin measurements above are separate.', '',
              '| Operation | ' + ' | '.join(CONTEXTS) + ' |', '|---|' + '---|' * len(CONTEXTS)]
    for op in result['operations']:
        lines.append('| ' + op + ' | ' + ' | '.join(['unsupported'] * len(CONTEXTS)) + ' |')
    silent = [r for r in rows if r['outcome'] == 'silent-loss']
    lines += ['', '## Detectors on populated silent losses', '',
              '| Framework / pin / mode / path | Silent cells | Empty execution errors | Empty invariants | Populated invariants | Lint migration | Lint schema + migration | Lint executed | Lint schema + executed |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for k, group_rows in groupby(sorted(silent, key=key), key=key):
        group_rows = list(group_rows)
        counts = [len(group_rows), sum(r['detectors']['empty_db'] for r in group_rows),
                  sum(bool(r['trials']['empty']['violations']) for r in group_rows), sum(r['detectors']['populated_invariants'] for r in group_rows)]
        for name in ('migration_only', 'schema_and_migration', 'executed', 'schema_and_executed'):
            counts.append(sum(bool(r['detectors']['lint'][name].get('detected')) for r in group_rows)
                          if all(r['detectors']['lint'][name]['available'] for r in group_rows) else 'unavailable')
        lines.append('| ' + display(k) + ' | ' + ' | '.join(map(str, counts)) + ' |')
    findings = ['', '## Transaction findings', '',
        'Django’s executed trace places PRAGMA foreign_keys=OFF before BEGIN and restores it after COMMIT/ROLLBACK. '
        'The schema editor also runs foreign_key_check before exiting. Its transaction protects the original table when the C7 view blocks a rebuild. '
        'Raw sqlmigrate replay lacks this FK orchestration and can therefore fire cascade/SET NULL actions.', '',
        'Alembic keeps transaction_per_migration at its False default. Python sqlite3 legacy transaction behavior does not begin a transaction for the temporary CREATE TABLE; '
        'BEGIN appears at the copy INSERT. A later rollback can therefore leave a committed empty temporary table, classified loud-partial by the full application-state digest. '
        'SQLAlchemy reflects declared and external indexes, but not triggers. For the fixture’s inline C8 REFERENCES syntax, reflection omits the ON DELETE action; '
        'the rebuilt FK becomes NO ACTION, detected by K even when row contents remain intact.', '',
        'Prisma’s generated rebuild files set defer_foreign_keys=ON and foreign_keys=OFF, copy/drop/rename, then set foreign_keys=ON and defer_foreign_keys=OFF. '
        'The deploy probes in `results/orm_prisma_probes.json` observe FK=1 and defer=0 before and after the successful generated rebuild on SQLite 3.46.0. '
        'An injected failure after that rebuild retains both observation rows and the changed default without BEGIN; with explicit BEGIN both disappear and the old schema returns. '
        'Thus deploy does not implicitly wrap the file in a transaction. The per-cell ledger observer also records FK enforcement left OFF when C7 interrupts a rebuild before the restoring PRAGMA. '
        'The injected-failure probes are separate from the untouched matrix migrations.']
    lines += findings if recorded else []
    lines += ['',
        '## Limits and evidence', '',
        'Prisma CLI does not expose a full SQLite runtime trace. Triggers on its migration ledger read the writing connection’s foreign_keys/defer_foreign_keys settings '
        'at migration start and success/failure recording, storing them in a separate observation table. These exact observer objects are excluded from the application-state digest; '
        'generated migration SQL remains untouched. An end observation that is unavailable is recorded as unknown. '
        'An empty executed.sql means unavailable, not no SQL. Generated PRAGMAs are retained verbatim; supplemental failure probes distinguish file atomicity from successful application. '
        'Raw SQLite versions can differ from the native Prisma engine, so raw paths are mechanism comparisons, not engine-identical reproductions.', '',
        'Django 6.0/C8 deliberately retains the original SQL cascade fixture despite that pin lacking a database-action API. '
        'A successful migration that changes that action is classified as silent loss of K. '
        'Type conversion uses the existing numeric text fixture and normalized value digest. '
        'Timestamp additions are nullable, without application-level automatic timestamp hooks.', '',
        'All per-trial snapshots, exact migration inputs, generation sources, logs, runtime metadata and available traces are in orm_evidence/*.json.gz. '
        'Build databases and generation directories are removed after each group. Unsupported operations have no executions. '
        'These deterministic mechanism fixtures do not establish ecosystem-wide safety.', '']
    if result['errors']:
        lines += ['Infrastructure failures:', ''] + [f"- {e['job']}: {e['error']}" for e in result['errors']]
    path.write_text('\n'.join(lines))
