# Expected post-state contract

This describes the existing code, not a proposed stronger oracle. The raw
validation suite does not change it. The operation union contains 23 names
(including Rails remove/Drizzle drop aliases); all share the nine contexts C0–C8.

## Inputs and comparison

[`matrix_spec.fixture`](../../smp/matrix_spec.py) constructs the schema, seed,
`tables`, `preserve`, expected change, rename maps, and removed-object allowlist.
[`orm_spec.orm_fixture`](../../smp/orm_spec.py) delegates to that same generator;
`OPERATIONS` extends the Drizzle names with default/reference/timestamp/check
operations. `django_models`, `alembic_operation`, and `prisma_schema` describe
framework migrations, but do not define an alternative preservation contract.

[`checks.snapshot`](../../smp/checks.py) reads counts, `table_info`, FK lists,
index/trigger/view SQL, view compilation, `foreign_key_check`, and
`integrity_check`. [`preservation.observe`](../../smp/preservation.py) adds
projected rows/digests, view rows/digests, reversible trigger probes, and a whole
application-state digest. `digest` hashes compact JSON with SHA-256, preserving
row order and JSON scalar types (blobs use hexadecimal encoding).
`preservation.violations` compares these observations and checks the intended
change via `expected_present`/`checks.intended_change`. `classify` calls a
successful execution with any finding `silent-loss`, otherwise `preserved`.
The full state digest is used only to distinguish unchanged from partial state
after execution failure; it is not a successful-migration equality test.

## Keys, projections, and normalized values

Every table in the unmodified matrix fixture has an `id INTEGER PRIMARY KEY`.
`observe` selects the explicit `preserve[table]` columns and always orders by
`id`. This is the stable identity/order used in the experiment; it is not
discovered from SQLite metadata. Counts are compared for every tracked table.
Digests use logical pre-migration table names, even after a table rename.

There is **no generic fallback for tables without a primary key**. A heap with
an `id` column can be read, but the oracle does not check its uniqueness or
non-nullness; tied keys have no guaranteed total order. A heap without `id`
gets a content error. If both observations lack a digest, `None == None`
silently passes that comparison. Content errors are not added to snapshot
`errors`. The derived controls demonstrate both cases, including an undetected
payload overwrite without a count change. Composite keys, alternate key names,
and general `WITHOUT ROWID` support are not implemented; full state capture
also assumes `ORDER BY rowid` is valid.

The default parent projection is `id,payload,tenant_id,value` (plus
`ancestor_id` in C8); tenants, children, grandchildren, and audit have their own
explicit projections. For column drops, `value` is excluded **before and
after**. New fields are not added to preservation projections. On `change_type`
only, parent `value` is cast to TEXT on both reads: seed values `'11'` and `'22'`
compare equal to stored integers 11 and 22. This is not a general conversion
relation: leading zeroes, lossy rounding, invalid numbers, NULL policies, and
other source/target types are not covered by these fixtures.

## Per-operation expected state

All rows below inherit count, projected-value, object, FK, view, trigger, and
database-validity preservation unless an explicit exception is listed.
The definitions originate in `matrix_spec.fixture`; the predicates are in
`preservation.expected_present`, `checks.intended_change`, and
`preservation.probe_constraint`.

| Operation names | Expected post-state and comparison rules |
|---|---|
| `add_column` | `parents.note` exists. Its type, default, nullability, and populated values are not checked by the declared expectation. Preserve old columns only. |
| `remove_column`, `drop_column` | `parents` exists and `value` is absent. Exclude `value` from both projections; preserve remaining values and all row counts. |
| `rename_column` | `renamed_value` exists and `value` is absent. Map `value` to `renamed_value` when reading the parent projection after migration. No general mapping is applied to dependent-object SQL or FK column names. The matrix's dependent objects reference payload/id/tenant_id, so they need no column rewrite. |
| `rename_table` | Observe `parents` as `renamed_parents`; expect new table present and old table absent from observed counts. Rewrite table-name tokens in old object SQL and the FK target table for comparisons. The old-table absence predicate only sees the requested snapshot tables, so it is not an exhaustive sqlite_schema absence test. |
| `change_type` | `parents.value` has declared type `INTEGER` in `table_info`. Compare old/new values after CAST AS TEXT. No independent check of every stored SQLite storage class. |
| `set_not_null`, `drop_not_null` | The `value` column's `notnull` flag equals 1 or 0. Preserve all projected values, including `value`. |
| `change_default`, `set_default`, `drop_default` | The `value` default reported by `table_info` is exactly `'9'` (including SQL quotes), or `None` for removal. `change_default` and `drop_default` begin with `'5'`; `set_default` begins without a default. Existing values remain unchanged. No insert probe checks the new default's behavior. |
| `add_foreign_key` | Some parent FK has source `tenant_id` and target table `tenants`. The added FK's target column, actions, and match clause are not constrained by this intent predicate; existing FK definitions still must survive. |
| `remove_foreign_key`, `drop_foreign_key` | No parent FK uses source `tenant_id`; skip preservation of that original definition. C8's independent cascading `ancestor_id` FK must survive. |
| `add_reference` | `owner_id` exists and an FK from it targets `tenants`. Existing row projection excludes the new reference. The predicate does not require an index, specific default, type, or action. |
| `add_timestamps` | Both `created_at` and `updated_at` exist. Existing row projection excludes them; types, defaults, and values are not checked by intent. |
| `add_check_constraint`, `remove_check_constraint` | A savepoint probe inserts `value='-1'`; the intent requires rejection for add and acceptance for remove. The probe catches any IntegrityError, not the identity of the rejecting constraint. No full logical equivalence check of the CHECK expression. |
| `add_unique`, `drop_unique` | A savepoint probe attempts two rows with equal `value='-1'`; require rejection for add and acceptance for drop. For drop, allow removal of `index:parents_value_unique`. The fixture starts with a named unique index. |
| `add_index` | Require `index:idx_operation` with canonical SQL equal to `CREATE INDEX idx_operation ON parents(value)`. Existing indexes remain required. |
| `remove_index`, `drop_index` | Require `index:idx_operation` absent and exempt precisely that object from preservation. Other indexes remain required. |

The raw safe controls use explicit native statements or a create/copy/drop/rename
rebuild, independent of framework availability. For type/null/default/FK/CHECK
changes they rebuild; add-column also has an explicit rebuild control in each
context. They recreate saved indexes, triggers, and views and restore enforcement.
This follows SQLite's [generalized ALTER TABLE procedure](https://www.sqlite.org/lang_altertable.html#otheralter).
Independent ground truth checks all stored rows and column metadata, FK tuples,
object SQL, and constraint behavior before the oracle is consulted.

## Other invariants and limits

- `violations` compares each original index/trigger/view by name and canonical
  SQL, except `removed_objects`. `checks.canonical_sql` removes formatting,
  identifier quotes, and semicolons, lowercases non-literal tokens, and retains
  quoted string literals. A changed trigger body is therefore detected even
  when its single behavioral probe would pass. Unlisted added objects are not
  generally rejected. Table CREATE SQL is not compared on success.
- FK preservation compares target table, source and target columns, update and
  delete actions, and match value; PRAGMA FK id/sequence fields are omitted.
  Every original tuple must be found, with the declared removal exception.
  This is not a general composite-FK grouping equivalence check.
- Listed views are queried with `SELECT * ... ORDER BY 1`; their digest must
  remain equal. Ties in the first column lack a total-order guarantee. All
  schema views are compiled by `snapshot`; only listed views get row digests.
- For each listed trigger, `observe` uses a savepoint to insert tenant 1 and
  parent 999 if needed, update parent payload to `probe-updated`, and expect
  exactly `(999, 'probe-updated')` in audit. It handles the fixture's drop/rename
  column/table operations. It rolls back probe state and also runs on empty
  databases. This does not exhaust trigger events or branch conditions.
- After migration, require no FK-check rows, `integrity_check == ['ok']`, no
  snapshot errors, and no view compilation errors. Content/view digest read
  errors are not independently rejected when both digests are missing.
- Require `execution.foreign_keys_after == 1`, measured on the migration
  connection. The observer's own new connections cannot establish migration
  enforcement. A clean FK check does not imply enforcement is enabled.
- Unintended defaults on unrelated existing columns are outside the compared
  projection and declared intent. The default limitation control changes
  `payload`'s future insertion behavior while retaining current data and all
  checked objects. It is deliberately counted as lossy ground truth.

The smaller legacy `checks.check_invariants` checks counts, schema objects,
SQLite validity, and a limited intended-change predicate. It does not perform
the full content/FK-definition/trigger-probe contract. This validation uses
`preservation.violations` and `classify`, as the operation matrices do.
`orm_checks.observation` adds constraint probing and excludes known migration
bookkeeping from failure-state digests; the raw controls have no such ledgers.
