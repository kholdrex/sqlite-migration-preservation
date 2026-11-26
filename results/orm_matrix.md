# SQLite ORM operation preservation matrix

Observed: 2026-10-10T01:22:54.624393+00:00.

2646 populated/empty pairs; 0 infrastructure errors. 198 unsupported operation/context combinations.

This matrix adds Django, Alembic and Prisma to the Rails/Drizzle operation matrix. Counts are cells, not ecosystem prevalence. The union has 20 operations; aliases remove/drop column, FK and index are unified. Each cell has a populated and empty execution. † = runtime CREATE/DROP rebuild; ‡ = rebuild in generated Prisma SQL, runtime trace unavailable. Loud compares persisted application state, excluding only migration bookkeeping.

Invariants: R rows; D content digest; O schema objects; T trigger behavior; V view behavior; K FK definition; E connection FK enforcement; F foreign_key_check; I integrity_check; Q snapshot error; C intended change.

| Context | Dependency |
|---|---|
| C0 | none |
| C1 | child ON DELETE CASCADE |
| C2 | child ON DELETE SET NULL |
| C3 | child ON DELETE RESTRICT |
| C4 | two-level cascade |
| C5 | external parent trigger |
| C6 | external parent index |
| C7 | parent view |
| C8 | parent is a cascading child |

## Pins and execution

- Django 6.1.2 and previous minor 6.0.9, resolved from [PyPI](https://pypi.org/pypi/Django/json). Model changes use makemigrations and call_command("migrate"); rename column uses an explicit RenameField because noninteractive autodetection cannot confirm a rename. The initial model migration is recorded as applied over the shared SQL fixture. Incoming dependency tables remain external to Django model state. C8 uses DB_CASCADE on 6.1, and CASCADE on 6.0 where the database-action API is unavailable; K measures any change to the seeded SQL action.
- Alembic 1.20.0 ([PyPI](https://pypi.org/pypi/alembic/json)) / SQLAlchemy 2.1.4 ([PyPI](https://pypi.org/pypi/SQLAlchemy/json)): command.upgrade, context.configure defaults, transaction_per_migration=False. FK enforcement is enabled on the SQLAlchemy connection; no FK-disable workaround or forced BEGIN is added. Both auto and always batch modes are measured. rename_table is op.rename_table outside batch; drop_unique drops the fixture’s unique index.
- Prisma stable 7.10.0, from [npm](https://registry.npmjs.org/prisma). The registry latest tag was 8.0.0-rc.22; that CLI replaces the migrate diff/deploy command family. The diff/deploy workflow is measured on the latest stable release, and the latest tag is recorded as unsupported. Untouched migrate diff --script output is applied by migrate deploy after baselining the existing fixture with migrate resolve. CHECK operations are unsupported in the schema language. Schema diffs have no rename identity; rename requests measure the actual drop/add result, including data loss.
- Raw paths execute generated SQL in Python SQLite with FK enforcement ON, in autocommit or one explicit BEGIN. Django sqlmigrate BEGIN/COMMIT wrappers are removed for both raw comparisons; its schema-editor PRAGMA orchestration is absent from sqlmigrate. Alembic SQL is captured from a successful empty reflection run (the dependent view omitted only during generation); Prisma SQL is unmodified.

## Cross-framework summary

Populated framework paths only. Loud includes partial commit; partial is also shown separately. Different operation sets and pins are not rankings.

| Framework / pin / mode | Cells | Silent loss | Loud (partial) | Preserved | Mechanism to inspect |
|---|---:|---:|---:|---:|---|
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / always | 180 | 95 | 38 (38) | 47 | Enforced FK actions; triggers not reflected; inline C8 FK action omitted by reflection |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto | 180 | 70 | 28 (28) | 82 | Enforced FK actions; triggers not reflected; inline C8 FK action omitted by reflection |
| django / 6.1.2 / default | 180 | 24 | 12 (0) | 144 | Model-state rebuild omits external objects; SQL FK action can change |
| django / 6.0.9 / default | 180 | 36 | 12 (0) | 132 | Model-state rebuild omits external objects; SQL FK action can change |
| drizzle / before / default | 135 | 36 | 14 (0) | 85 | FK actions and omitted external objects; pin dependent |
| drizzle / current / default | 135 | 36 | 14 (0) | 85 | FK actions and omitted external objects; pin dependent |
| drizzle / drizzle-pr5074 / default | 135 | 21 | 14 (0) | 100 | FK actions and omitted external objects; pin dependent |
| drizzle / drizzle-pr5784 / default | 135 | 14 | 7 (0) | 114 | FK actions and omitted external objects; pin dependent |
| drizzle / drizzle-pr5784+5074 / default | 135 | 14 | 7 (0) | 114 | FK actions and omitted external objects; pin dependent |
| prisma / 7.10.0 / default | 162 | 37 | 11 (11) | 114 | Schema-only rebuild omits external objects; rename diff drops data |
| rails / before / default | 144 | 48 | 0 (0) | 96 | FK cascade/SET NULL and external triggers; pin dependent |
| rails / current / default | 144 | 48 | 0 (0) | 96 | FK cascade/SET NULL and external triggers; pin dependent |
| rails / rails-pr57128 / default | 144 | 12 | 0 (0) | 132 | FK cascade/SET NULL and external triggers; pin dependent |
| prisma / 8.0.0-rc.22 | 0 | — | — | — | Command family unsupported |

## Operation mappings

The exact before/after model sources and migration files are archived per context. SQL defaults use Django db_default, Alembic server_default, and Prisma @default.

| Operation | Django | Alembic | Prisma schema diff |
|---|---|---|---|
| add_column | AddField | `batch.add_column(sa.Column('note', sa.Text()))` | Add nullable field |
| drop_column | RemoveField | `batch.drop_column('value')` | Remove field |
| rename_column | RenameField (explicit) | `batch.alter_column('value', new_column_name='renamed_value')` | Remove old / add new field |
| change_type | AlterField(TextField → IntegerField) | `batch.alter_column('value', type_=sa.Integer())` | String → Int |
| set_not_null | AlterField(null=False) | `batch.alter_column('value', nullable=False)` | Remove ? |
| drop_not_null | AlterField(null=True) | `batch.alter_column('value', nullable=True)` | Add ? |
| set_default | AlterField(db_default='9') | `batch.alter_column('value', server_default=sa.text("'9'"))` | @default("9") |
| drop_default | AlterField(remove db_default) | `batch.alter_column('value', server_default=None)` | Remove @default |
| add_foreign_key | AlterField(db_constraint=True) | `batch.create_foreign_key('fk_tenant', 'tenants', ['tenant_id'], ['id'])` | Add @relation |
| drop_foreign_key | AlterField(db_constraint=False) | `batch.drop_constraint('fk_tenant', type_='foreignkey')` | Remove @relation |
| add_unique | AlterField(unique=True) | `batch.create_unique_constraint('parents_value_unique', ['value'])` | Add @unique |
| drop_unique | AlterField(unique=False) | `batch.drop_index('parents_value_unique')` | Remove @unique |
| add_index | AddIndex | `batch.create_index('idx_operation', ['value'])` | Add @@index |
| drop_index | RemoveIndex | `batch.drop_index('idx_operation')` | Remove @@index |
| rename_table | AlterModelTable | `op.rename_table('parents', 'renamed_parents')` | Change @@map (drop/create) |
| change_default | AlterField(db_default='5' → '9') | `batch.alter_column('value', server_default=sa.text("'9'"))` | @default("5") → @default("9") |
| add_reference | AddField(ForeignKey) | `batch.add_column(sa.Column('owner_id', sa.Integer())); batch.create_foreign_key('fk_owner', 'tenants', ['owner_id'], ['id'])` | Add nullable field and @relation |
| add_timestamps | Two nullable DateTimeField additions | `batch.add_column(sa.Column('created_at', sa.DateTime())); batch.add_column(sa.Column('updated_at', sa.DateTime()))` | Two nullable DateTime fields |
| add_check_constraint | AddConstraint(CheckConstraint) | `batch.create_check_constraint('positive_value', 'CAST(value AS INTEGER) > 0')` | Unsupported |
| remove_check_constraint | RemoveConstraint | `batch.drop_constraint('positive_value', type_='check')` | Unsupported |

## SQLite runtimes

| Path | Observed SQLite versions |
|---|---|
| always | 3.53.4 |
| auto | 3.53.4 |
| django | 3.53.4 |
| prisma | 3.46.0 |
| raw | 3.41.2 |
| raw-tx | 3.41.2 |

## Counts by path and population

| Framework / pin / mode / path | Population | Cells | Silent loss | Loud | Loud partial | Preserved |
|---|---|---:|---:|---:|---:|---:|
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / always / always | populated | 180 | 95 | 0 | 38 | 47 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / always / always | empty | 180 | 38 | 0 | 19 | 123 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / always / raw | populated | 180 | 95 | 0 | 38 | 47 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / always / raw | empty | 180 | 38 | 0 | 19 | 123 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / always / raw-tx | populated | 180 | 95 | 38 | 0 | 47 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / always / raw-tx | empty | 180 | 38 | 19 | 0 | 123 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto / auto | populated | 180 | 70 | 0 | 28 | 82 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto / auto | empty | 180 | 28 | 0 | 14 | 138 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto / raw | populated | 180 | 70 | 0 | 28 | 82 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto / raw | empty | 180 | 28 | 0 | 14 | 138 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto / raw-tx | populated | 180 | 70 | 28 | 0 | 82 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto / raw-tx | empty | 180 | 28 | 14 | 0 | 138 |
| django / 6.1.2 / default / django | populated | 180 | 24 | 12 | 0 | 144 |
| django / 6.1.2 / default / django | empty | 180 | 24 | 12 | 0 | 144 |
| django / 6.1.2 / default / raw | populated | 180 | 60 | 0 | 24 | 96 |
| django / 6.1.2 / default / raw | empty | 180 | 24 | 0 | 12 | 144 |
| django / 6.1.2 / default / raw-tx | populated | 180 | 60 | 24 | 0 | 96 |
| django / 6.1.2 / default / raw-tx | empty | 180 | 24 | 12 | 0 | 144 |
| django / 6.0.9 / default / django | populated | 180 | 36 | 12 | 0 | 132 |
| django / 6.0.9 / default / django | empty | 180 | 36 | 12 | 0 | 132 |
| django / 6.0.9 / default / raw | populated | 180 | 72 | 0 | 24 | 84 |
| django / 6.0.9 / default / raw | empty | 180 | 36 | 0 | 12 | 132 |
| django / 6.0.9 / default / raw-tx | populated | 180 | 72 | 24 | 0 | 84 |
| django / 6.0.9 / default / raw-tx | empty | 180 | 36 | 12 | 0 | 132 |
| prisma / 7.10.0 / default / prisma | populated | 162 | 37 | 0 | 11 | 114 |
| prisma / 7.10.0 / default / prisma | empty | 162 | 25 | 0 | 11 | 126 |
| prisma / 7.10.0 / default / raw | populated | 162 | 37 | 0 | 11 | 114 |
| prisma / 7.10.0 / default / raw | empty | 162 | 25 | 0 | 11 | 126 |
| prisma / 7.10.0 / default / raw-tx | populated | 162 | 66 | 12 | 0 | 84 |
| prisma / 7.10.0 / default / raw-tx | empty | 162 | 25 | 11 | 0 | 126 |

## alembic / 1.20.0 / SQLAlchemy 2.1.4 / always / always

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| rename_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_index | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_index | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_reference | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_timestamps | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| rename_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_index | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_index | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_timestamps | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |

Rebuild observed or planned: add_check_constraint, add_column, add_foreign_key, add_index, add_reference, add_timestamps, add_unique, change_default, change_type, drop_column, drop_default, drop_foreign_key, drop_index, drop_not_null, drop_unique, remove_check_constraint, rename_column, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `BEGIN ; → COMMIT; → PRAGMA foreign_keys;`
- `BEGIN ; → ROLLBACK; → PRAGMA foreign_keys;`

## alembic / 1.20.0 / SQLAlchemy 2.1.4 / always / raw

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| rename_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_index | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_index | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_reference | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_timestamps | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| rename_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_index | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_index | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_timestamps | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |

Rebuild observed or planned: add_check_constraint, add_column, add_foreign_key, add_index, add_reference, add_timestamps, add_unique, change_default, change_type, drop_column, drop_default, drop_foreign_key, drop_index, drop_not_null, drop_unique, remove_check_constraint, rename_column, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `No exposed transaction/PRAGMA statements`

## alembic / 1.20.0 / SQLAlchemy 2.1.4 / always / raw-tx

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| rename_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_index | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_index | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_reference | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_timestamps | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| rename_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_index | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_index | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_timestamps | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |

Rebuild observed or planned: add_check_constraint, add_column, add_foreign_key, add_index, add_reference, add_timestamps, add_unique, change_default, change_type, drop_column, drop_default, drop_foreign_key, drop_index, drop_not_null, drop_unique, remove_check_constraint, rename_column, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `BEGIN; → COMMIT;`
- `BEGIN; → ROLLBACK;`

## alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto / auto

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| rename_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_reference | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| rename_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |

Rebuild observed or planned: add_check_constraint, add_foreign_key, add_reference, add_unique, change_default, change_type, drop_column, drop_default, drop_foreign_key, drop_not_null, remove_check_constraint, rename_column, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `BEGIN ; → COMMIT; → PRAGMA foreign_keys;`
- `BEGIN ; → ROLLBACK; → PRAGMA foreign_keys;`

## alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto / raw

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| rename_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_reference | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| rename_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud-partial† | silent-loss(K)† |

Rebuild observed or planned: add_check_constraint, add_foreign_key, add_reference, add_unique, change_default, change_type, drop_column, drop_default, drop_foreign_key, drop_not_null, remove_check_constraint, rename_column, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `No exposed transaction/PRAGMA statements`

## alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto / raw-tx

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| rename_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_reference | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| rename_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | loud† | silent-loss(K)† |

Rebuild observed or planned: add_check_constraint, add_foreign_key, add_reference, add_unique, change_default, change_type, drop_column, drop_default, drop_foreign_key, drop_not_null, remove_check_constraint, rename_column, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `BEGIN; → COMMIT;`
- `BEGIN; → ROLLBACK;`

## django / 6.1.2 / default / django

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_reference | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_reference | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

Rebuild observed or planned: add_check_constraint, add_foreign_key, add_unique, change_default, change_type, drop_default, drop_foreign_key, drop_not_null, drop_unique, remove_check_constraint, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `PRAGMA foreign_keys; → PRAGMA foreign_keys = OFF; → PRAGMA foreign_keys; → BEGIN; → COMMIT; → PRAGMA foreign_keys = ON; → PRAGMA foreign_keys;`
- `PRAGMA foreign_keys; → PRAGMA foreign_keys = OFF; → PRAGMA foreign_keys; → BEGIN; → ROLLBACK; → PRAGMA foreign_keys = ON; → PRAGMA foreign_keys;`

## django / 6.1.2 / default / raw

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_reference | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_reference | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |

Rebuild observed or planned: add_check_constraint, add_foreign_key, add_unique, change_default, change_type, drop_default, drop_foreign_key, drop_not_null, drop_unique, remove_check_constraint, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `No exposed transaction/PRAGMA statements`

## django / 6.1.2 / default / raw-tx

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_reference | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_reference | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

Rebuild observed or planned: add_check_constraint, add_foreign_key, add_unique, change_default, change_type, drop_default, drop_foreign_key, drop_not_null, drop_unique, remove_check_constraint, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `BEGIN; → COMMIT;`
- `BEGIN; → ROLLBACK;`

## django / 6.0.9 / default / django

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_reference | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_reference | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |

Rebuild observed or planned: add_check_constraint, add_foreign_key, add_unique, change_default, change_type, drop_default, drop_foreign_key, drop_not_null, drop_unique, remove_check_constraint, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `PRAGMA foreign_keys; → PRAGMA foreign_keys = OFF; → PRAGMA foreign_keys; → BEGIN; → COMMIT; → PRAGMA foreign_keys = ON; → PRAGMA foreign_keys;`
- `PRAGMA foreign_keys; → PRAGMA foreign_keys = OFF; → PRAGMA foreign_keys; → BEGIN; → ROLLBACK; → PRAGMA foreign_keys = ON; → PRAGMA foreign_keys;`

## django / 6.0.9 / default / raw

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| add_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| drop_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| add_reference | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud-partial† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| drop_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| add_reference | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | silent-loss(K)† |

Rebuild observed or planned: add_check_constraint, add_foreign_key, add_unique, change_default, change_type, drop_default, drop_foreign_key, drop_not_null, drop_unique, remove_check_constraint, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `No exposed transaction/PRAGMA statements`

## django / 6.0.9 / default / raw-tx

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_unique | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_reference | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| drop_unique | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| add_reference | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | silent-loss(K)† |

Rebuild observed or planned: add_check_constraint, add_foreign_key, add_unique, change_default, change_type, drop_default, drop_foreign_key, drop_not_null, drop_unique, remove_check_constraint, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `BEGIN; → COMMIT;`
- `BEGIN; → ROLLBACK;`

## prisma / 7.10.0 / default / prisma

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| rename_column | silent-loss(D)‡ | silent-loss(D)‡ | silent-loss(D)‡ | silent-loss(D)‡ | silent-loss(D)‡ | silent-loss(D,O,T)‡ | silent-loss(D,O)‡ | loud-partial‡ | silent-loss(D)‡ |
| change_type | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| set_not_null | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| drop_not_null | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| set_default | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| drop_default | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| add_foreign_key | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| drop_foreign_key | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | silent-loss(D,R)‡ | silent-loss(D,F,R)‡ | silent-loss(D,F,R)‡ | silent-loss(D,F,R)‡ | silent-loss(D,F,R)‡ | silent-loss(D,O,R,T)‡ | silent-loss(D,O,R)‡ | silent-loss(D,O,R,V)‡ | silent-loss(D,R)‡ |
| change_default | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| add_reference | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| remove_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| rename_column | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| change_type | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| set_not_null | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| drop_not_null | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| set_default | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| drop_default | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| add_foreign_key | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| drop_foreign_key | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | silent-loss(O,V)‡ | preserved‡ |
| change_default | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| add_reference | preserved‡ | preserved‡ | preserved‡ | preserved‡ | preserved‡ | silent-loss(O,T)‡ | silent-loss(O)‡ | loud-partial‡ | preserved‡ |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| remove_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |

Rebuild observed or planned: add_foreign_key, add_reference, change_default, change_type, drop_column, drop_default, drop_foreign_key, drop_not_null, rename_column, rename_table, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `No exposed transaction/PRAGMA statements`

## prisma / 7.10.0 / default / raw

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| rename_column | silent-loss(D)† | silent-loss(D)† | silent-loss(D)† | silent-loss(D)† | silent-loss(D)† | silent-loss(D,O,T)† | silent-loss(D,O)† | loud-partial† | silent-loss(D)† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | silent-loss(D,R)† | silent-loss(D,F,R)† | silent-loss(D,F,R)† | silent-loss(D,F,R)† | silent-loss(D,F,R)† | silent-loss(D,O,R,T)† | silent-loss(D,O,R)† | silent-loss(D,O,R,V)† | silent-loss(D,R)† |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| remove_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| rename_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | silent-loss(O,V)† | preserved† |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| remove_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |

Rebuild observed or planned: add_foreign_key, add_reference, change_default, change_type, drop_column, drop_default, drop_foreign_key, drop_not_null, rename_column, rename_table, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `No exposed transaction/PRAGMA statements`
- `PRAGMA defer_foreign_keys=ON; → PRAGMA foreign_keys=OFF;`
- `PRAGMA defer_foreign_keys=ON; → PRAGMA foreign_keys=OFF; → PRAGMA foreign_keys=ON; → PRAGMA defer_foreign_keys=OFF;`
- `PRAGMA foreign_keys=off; → PRAGMA foreign_keys=on;`
- `PRAGMA foreign_keys=off; → PRAGMA foreign_keys=on; → PRAGMA defer_foreign_keys=ON; → PRAGMA foreign_keys=OFF; → PRAGMA foreign_keys=ON; → PRAGMA defer_foreign_keys=OFF;`

## prisma / 7.10.0 / default / raw-tx

Populated:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| rename_column | silent-loss(D)† | silent-loss(D,R)† | silent-loss(D)† | silent-loss(D)† | silent-loss(D,R)† | silent-loss(D,O,T)† | silent-loss(D,O)† | loud† | silent-loss(D)† |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | silent-loss(D,R)† | silent-loss(D,R)† | silent-loss(D,R)† | loud | silent-loss(D,R)† | silent-loss(D,O,R,T)† | silent-loss(D,O,R)† | silent-loss(D,O,R,V)† | silent-loss(D,R)† |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_reference | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| remove_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |

Empty:

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| rename_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | silent-loss(O,V)† | preserved† |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_timestamps | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| remove_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |

Rebuild observed or planned: add_foreign_key, add_reference, change_default, change_type, drop_column, drop_default, drop_foreign_key, drop_not_null, rename_column, rename_table, set_default, set_not_null.

Representative executed transaction/PRAGMA sequences (deduplicated):

- `BEGIN; → COMMIT;`
- `BEGIN; → PRAGMA defer_foreign_keys=ON; → PRAGMA foreign_keys=OFF; → PRAGMA foreign_keys=ON; → PRAGMA defer_foreign_keys=OFF; → COMMIT;`
- `BEGIN; → PRAGMA defer_foreign_keys=ON; → PRAGMA foreign_keys=OFF; → ROLLBACK;`
- `BEGIN; → PRAGMA foreign_keys=off; → PRAGMA foreign_keys=on; → COMMIT;`
- `BEGIN; → PRAGMA foreign_keys=off; → PRAGMA foreign_keys=on; → PRAGMA defer_foreign_keys=ON; → PRAGMA foreign_keys=OFF; → PRAGMA foreign_keys=ON; → PRAGMA defer_foreign_keys=OFF; → COMMIT;`
- `BEGIN; → PRAGMA foreign_keys=off; → ROLLBACK;`

## Prisma / 8.0.0-rc.22 / migrate workflow

Unsupported in both populations: this CLI exposes a different migration command family. This pin has no executions. The stable-pin measurements above are separate.

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| drop_column | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| rename_column | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| change_type | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| set_not_null | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| drop_not_null | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| set_default | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| drop_default | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| add_foreign_key | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| drop_foreign_key | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| add_unique | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| drop_unique | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| add_index | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| drop_index | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| rename_table | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| change_default | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| add_reference | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| add_timestamps | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| add_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| remove_check_constraint | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |

## Detectors on populated silent losses

| Framework / pin / mode / path | Silent cells | Empty execution errors | Empty invariants | Populated invariants | Lint migration | Lint schema + migration | Lint executed | Lint schema + executed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / always / always | 95 | 0 | 38 | 95 | 0 | 0 | 0 | 0 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / always / raw | 95 | 0 | 38 | 95 | 0 | 0 | 0 | 0 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / always / raw-tx | 95 | 0 | 38 | 95 | 0 | 0 | 0 | 0 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto / auto | 70 | 0 | 28 | 70 | 0 | 0 | 0 | 0 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto / raw | 70 | 0 | 28 | 70 | 0 | 0 | 0 | 0 |
| alembic / 1.20.0 / SQLAlchemy 2.1.4 / auto / raw-tx | 70 | 0 | 28 | 70 | 0 | 0 | 0 | 0 |
| django / 6.1.2 / default / django | 24 | 0 | 24 | 24 | 0 | 0 | 0 | 0 |
| django / 6.1.2 / default / raw | 60 | 0 | 24 | 60 | 0 | 0 | 0 | 0 |
| django / 6.1.2 / default / raw-tx | 60 | 0 | 24 | 60 | 0 | 0 | 0 | 0 |
| django / 6.0.9 / default / django | 36 | 0 | 36 | 36 | 0 | 0 | 0 | 0 |
| django / 6.0.9 / default / raw | 72 | 0 | 36 | 72 | 0 | 0 | 0 | 0 |
| django / 6.0.9 / default / raw-tx | 72 | 0 | 36 | 72 | 0 | 0 | 0 | 0 |
| prisma / 7.10.0 / default / prisma | 37 | 0 | 25 | 37 | 0 | 0 | unavailable | unavailable |
| prisma / 7.10.0 / default / raw | 37 | 0 | 25 | 37 | 0 | 0 | 0 | 0 |
| prisma / 7.10.0 / default / raw-tx | 66 | 0 | 25 | 66 | 0 | 0 | 66 | 66 |

## Transaction findings

Django’s executed trace places PRAGMA foreign_keys=OFF before BEGIN and restores it after COMMIT/ROLLBACK. The schema editor also runs foreign_key_check before exiting. Its transaction protects the original table when the C7 view blocks a rebuild. Raw sqlmigrate replay lacks this FK orchestration and can therefore fire cascade/SET NULL actions.

Alembic keeps transaction_per_migration at its False default. Python sqlite3 legacy transaction behavior does not begin a transaction for the temporary CREATE TABLE; BEGIN appears at the copy INSERT. A later rollback can therefore leave a committed empty temporary table, classified loud-partial by the full application-state digest. SQLAlchemy reflects declared and external indexes, but not triggers. For the fixture’s inline C8 REFERENCES syntax, reflection omits the ON DELETE action; the rebuilt FK becomes NO ACTION, detected by K even when row contents remain intact.

Prisma’s generated rebuild files set defer_foreign_keys=ON and foreign_keys=OFF, copy/drop/rename, then set foreign_keys=ON and defer_foreign_keys=OFF. The deploy probes in `results/orm_prisma_probes.json` observe FK=1 and defer=0 before and after the successful generated rebuild on SQLite 3.46.0. An injected failure after that rebuild retains both observation rows and the changed default without BEGIN; with explicit BEGIN both disappear and the old schema returns. Thus deploy does not implicitly wrap the file in a transaction. The per-cell ledger observer also records FK enforcement left OFF when C7 interrupts a rebuild before the restoring PRAGMA. The injected-failure probes are separate from the untouched matrix migrations.

## Limits and evidence

Prisma CLI does not expose a full SQLite runtime trace. Triggers on its migration ledger read the writing connection’s foreign_keys/defer_foreign_keys settings at migration start and success/failure recording, storing them in a separate observation table. These exact observer objects are excluded from the application-state digest; generated migration SQL remains untouched. An end observation that is unavailable is recorded as unknown. An empty executed.sql means unavailable, not no SQL. Generated PRAGMAs are retained verbatim; supplemental failure probes distinguish file atomicity from successful application. Raw SQLite versions can differ from the native Prisma engine, so raw paths are mechanism comparisons, not engine-identical reproductions.

Django 6.0/C8 deliberately retains the original SQL cascade fixture despite that pin lacking a database-action API. A successful migration that changes that action is classified as silent loss of K. Type conversion uses the existing numeric text fixture and normalized value digest. Timestamp additions are nullable, without application-level automatic timestamp hooks.

All per-trial snapshots, exact migration inputs, generation sources, logs, runtime metadata and available traces are in orm_evidence/*.json.gz. Build databases and generation directories are removed after each group. Unsupported operations have no executions. These deterministic mechanism fixtures do not establish ecosystem-wide safety.
