# Rails fixes: operation preservation

Observed: 2026-10-09T23:49:22.489969+00:00.

576 additional operation/context pairs (1152 executions), plus 28 pilot pairs (56 executions). Each pin runs all 16 Rails operations across C0–C8 on populated and empty databases. The original pilot has 13 cases total: seven Rails and six Drizzle; all seven existing Rails cases are run on each new pin, with the fixtures, invariants and outcome classification of the operation matrix.

Both combined pins have **no silent-loss cells in this matrix**, on either population. #56811 alone retains 36 populated FK-loss cells; #58709 alone retains 12 trigger-loss cells. All matrix and pilot executions succeed. These results cover the tested contexts, not arbitrary migrations.

## Pins and merge resolution

| Pin | Resolved revision | Adapter SHA-256 |
|---|---|---|
| rails-pr56811 | `7ddc17783418454c0e406181ae442d0aaf558ad8` | `4e2dcdb37f62b271860e8499126dd69191f4afab8d04895dca0f38b77b78c66b` |
| rails-pr58709 | `428884a88b3a42c914f5227819b6b672325b3312` | `9220aa27221b0f375b3539f0771b55507f3abf5af0aafffd1037c0ae8f088552` |
| rails-pr57128+56811 | `5827151e652ee67ed7060e7da20c67ab2a75fb31` | `e6bc36419cf43a71ed55c42a629410f8c7dadfe43335457ed93b23319bfff5b5` |
| rails-pr58709+56811 | `bec5f3e1d7ec75a43f65af23b7b58e65b20caf9e` | `2755a1e844ac04931777305ad20fb4c586165d3902e6f4d1c67f57c2b5c18e38` |

Each Gemfile uses a full Git SHA and the ActiveRecord/ActiveModel/ActiveSupport gemspec glob. Every populated and empty execution records the Bundler resolved revision and loaded adapter SHA-256; both are checked against `sources/upstream_fixes.json`. New pins use installed Ruby 3.4.3 and Bundler 2.6.7, ActiveRecord 8.2.0.alpha, sqlite3 gem 2.9.6 and SQLite 3.53.2. Current uses Ruby 3.3.2 and ActiveRecord 8.1.4; #57128 uses Ruby 3.4.3. Observers use Python SQLite 3.41.2. Lockfiles retain full dependency resolutions. These are upstream-head comparisons with different base dates, not isolated patches on current.

The #57128 + #56811 pin is a local derived merge of `8823c1370c7bc8910e609d1b6f27f4fc34f3d81d` and `7ddc17783418454c0e406181ae442d0aaf558ad8`, with merge base `3faf056f240966b268dd6fa52c559e241a370d06`. The actual merge conflicted in four files: `activerecord/CHANGELOG.md`, the SQLite schema statements, the SQLite adapter, and its adapter tests. The resolution retains #57128's newer code and both changelog/test additions, adds #56811's `triggers(table_name)` query and argument, and recreates triggers immediately after the second `move_table` inside #57128's transaction. No unrelated code is changed.

The resolution patch `sources/rails-pr57128+56811-resolution.patch` is the complete 145-line addition against the first parent. `scripts/build_rails_merge.py` applies it to that immutable parent and verifies the resolved tree, source hashes and deterministic two-parent merge object. The shallow local repository is regenerated during setup.

The #58709 + #56811 pin merges `428884a88b3a42c914f5227819b6b672325b3312` and `7ddc17783418454c0e406181ae442d0aaf558ad8`, using the same merge base `3faf056f240966b268dd6fa52c559e241a370d06`. It conflicted in `activerecord/CHANGELOG.md` and `activerecord/lib/active_record/connection_adapters/sqlite3/schema_statements.rb`; the adapter and adapter tests merged cleanly. The resolution retains #58709's newer code, both changelog entries, and #56811's trigger query. Its resolution patch `sources/rails-pr58709+56811-resolution.patch` is another 145-line delta from its first parent. The same builder verifies the merged tree and immutable two-parent revision. It combines Migrator-level FK disabling with trigger recreation.

## Counts

Counts are cells per pin and population. Loud means failed with application state rolled back; loud-partial means failed with committed application changes.

| Pin | Population | Silent-loss | Loud | Loud-partial | Preserved |
|---|---|---:|---:|---:|---:|
| current | populated | 48 | 0 | 0 | 96 |
| current | empty | 12 | 0 | 0 | 132 |
| rails-pr57128 | populated | 12 | 0 | 0 | 132 |
| rails-pr57128 | empty | 12 | 0 | 0 | 132 |
| rails-pr56811 | populated | 36 | 0 | 0 | 108 |
| rails-pr56811 | empty | 0 | 0 | 0 | 144 |
| rails-pr58709 | populated | 12 | 0 | 0 | 132 |
| rails-pr58709 | empty | 12 | 0 | 0 | 132 |
| rails-pr57128+56811 | populated | 0 | 0 | 0 | 144 |
| rails-pr57128+56811 | empty | 0 | 0 | 0 | 144 |
| rails-pr58709+56811 | populated | 0 | 0 | 0 | 144 |
| rails-pr58709+56811 | empty | 0 | 0 | 0 | 144 |

## Operation × context

Both populations are shown below. **Bold** cells differ from current for that population in outcome, invariant codes or observed rebuild. `†` means CREATE TABLE and DROP TABLE appeared in the executed trace. D = content digest; R = row count; O = schema object; T = trigger behavior. All empty cells preserve for #56811 and both combined pins; #58709's empty table matches its populated table (the same 12 C5 losses).

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

### rails-pr56811 / populated

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | **preserved†** | preserved† | preserved† | preserved† |
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | **preserved†** | preserved† | preserved† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_reference | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | **preserved†** | preserved† | preserved† | preserved† |
| add_timestamps | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | **preserved†** | preserved† | preserved† | preserved† |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | **preserved†** | preserved† | preserved† | preserved† |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | **preserved†** | preserved† | preserved† | preserved† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | **preserved†** | preserved† | preserved† | preserved† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | **preserved†** | preserved† | preserved† | preserved† |
| remove_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | **preserved†** | preserved† | preserved† | preserved† |
| remove_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | **preserved†** | preserved† | preserved† | preserved† |
| remove_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | **preserved†** | preserved† | preserved† | preserved† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | **preserved†** | preserved† | preserved† | preserved† |

### rails-pr56811 / empty

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| add_timestamps | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| remove_column | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| remove_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| remove_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |

### rails-pr58709 / populated

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_check_constraint | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_reference | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_timestamps | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| change_default | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| change_type | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| drop_not_null | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_check_constraint | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_column | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_foreign_key | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| set_not_null | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | silent-loss(O,T)† | preserved† | preserved† | preserved† |

### rails-pr58709 / empty

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_timestamps | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | preserved† | preserved† | preserved† |

### rails-pr57128+56811 / populated

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_check_constraint | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_reference | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| add_timestamps | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| change_default | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| change_type | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| drop_not_null | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| remove_check_constraint | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| remove_column | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| remove_foreign_key | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| remove_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| set_not_null | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |

### rails-pr57128+56811 / empty

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| add_timestamps | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| remove_column | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| remove_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| remove_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |

### rails-pr58709+56811 / populated

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_check_constraint | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_reference | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| add_timestamps | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| change_default | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| change_type | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| drop_not_null | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| remove_check_constraint | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| remove_column | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| remove_foreign_key | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| remove_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| set_not_null | preserved† | **preserved†** | **preserved†** | preserved† | **preserved†** | **preserved†** | preserved† | preserved† | preserved† |

### rails-pr58709+56811 / empty

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_reference | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| add_timestamps | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| change_default | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| remove_check_constraint | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| remove_column | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| remove_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| remove_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | **preserved†** | preserved† | preserved† | preserved† |

## Residual losses and code

**#56811:** the 12 rebuilding operations each lose rows in C1 and C4 and FK values in C2 (36 cells). C4 loses children and grandchildren. C2 keeps row counts but replaces referencing values with NULL. Trigger preservation fixes all 12 C5 cells. The adapter still calls `disable_referential_integrity do` around `transaction do` at [lines 642–647](https://github.com/aka-nez/rails/blob/7ddc17783418454c0e406181ae442d0aaf558ad8/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L642). That occurs inside Migrator's outer transaction, so `PRAGMA foreign_keys = OFF` ([line 315](https://github.com/aka-nez/rails/blob/7ddc17783418454c0e406181ae442d0aaf558ad8/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L315)) does not disable FK actions. The added line is:

```ruby
triggers.each { |trigger_sql| execute(trigger_sql) if trigger_sql.present? }
```

**#58709:** all 36 FK-loss cells become preserved, but the 12 rebuilding C5 cells still lose `trg_external` and its behavior, including on empty databases. Migrator now calls `connection.transaction_for_migration(&block)` at [migration line 1607](https://github.com/nicolasva/rails/blob/428884a88b3a42c914f5227819b6b672325b3312/activerecord/lib/active_record/migration.rb#L1607). The SQLite override at [adapter lines 201–205](https://github.com/nicolasva/rails/blob/428884a88b3a42c914f5227819b6b672325b3312/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L201) disables FK enforcement before opening the migration transaction:

```ruby
disable_referential_integrity do
  transaction(&block)
end
```

The rebuild still uses `copy_table(from, to, options, &block)` followed by `drop_table(from)` ([adapter move_table](https://github.com/nicolasva/rails/blob/428884a88b3a42c914f5227819b6b672325b3312/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L714)); indexes are copied, but there is no trigger recreation. The trace confirms the missing CREATE TRIGGER.

**#57128 comparison:** its 12 remaining losses are also C5 triggers. Its adapter restores indexes with `copy_table_indexes(from, to, options[:rename] || {})` ([line 792](https://github.com/emirn/rails/blob/8823c1370c7bc8910e609d1b6f27f4fc34f3d81d/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L792)) but has no trigger-copy step. **Both combined pins:** the merged code adds #56811's quoted trigger recreation inside each rebuild path. Each preserves all 144 populated and 144 empty cells.

The 12 rebuilding operations are add_check_constraint, add_foreign_key, add_reference, add_timestamps, change_default, change_type, drop_not_null, remove_check_constraint, remove_column, remove_foreign_key, rename_column and set_not_null. Empty execution reports no errors on any new pin, so the existing empty-db detector catches none of the populated silent losses. The raw rows retain all four unchanged lint detector results.

## Controls and regressions

| Pin | Current-preserved cells that regress | #57128-preserved cells that regress | Clean pilot controls |
|---|---:|---:|---:|
| rails-pr56811 | 0 | 36 | 3/3 |
| rails-pr58709 | 0 | 0 | 3/3 |
| rails-pr57128+56811 | 0 | 0 | 3/3 |
| rails-pr58709+56811 | 0 | 0 | 3/3 |

No previously preserved current cell regresses in either population. C0 preserves for all 16 operations on all new pins, and all four operations without rebuilds preserve in every context. Relative to #57128, #56811 alone loses the 36 FK cells that its trigger-only fix does not address; #58709 and both combined pins have no regressions. All three original Rails pilot controls remain clean.

## Original Rails pilot

Each entry describes populated/empty preservation under the original, unchanged pilot checks. All executions succeed; `rows / clean` means populated child loss with an empty trial that passes its invariants. `trigger / trigger` means the trigger disappears in both populations.

| Case | current | rails-pr57128 | rails-pr56811 | rails-pr58709 | rails-pr57128+56811 | rails-pr58709+56811 |
|---|---|---|---|---|---|---|
| rails_add_column | clean / clean | clean / clean | clean / clean | clean / clean | clean / clean | clean / clean |
| rails_add_fk | rows / clean | clean / clean | rows / clean | clean / clean | clean / clean | clean / clean |
| rails_add_index | clean / clean | clean / clean | clean / clean | clean / clean | clean / clean | clean / clean |
| rails_default | rows / clean | clean / clean | rows / clean | clean / clean | clean / clean | clean / clean |
| rails_fk_no_transaction | clean / clean | clean / clean | clean / clean | clean / clean | clean / clean | clean / clean |
| rails_objects | trigger / trigger | trigger / trigger | clean / clean | trigger / trigger | clean / clean | clean / clean |
| rails_rebuild_control | clean / clean | clean / clean | clean / clean | clean / clean | clean / clean | clean / clean |

## Transactions and atomicity

Counts below come from exact executed SQL for populated cells; empty cells show the same transaction counts. Bookkeeping queries are included, so these describe observed boundaries, not a general atomicity guarantee.

| Pin | Cells with one COMMIT | Cells with two COMMITs | Cells with SAVEPOINT |
|---|---:|---:|---:|
| current | 144 | 0 | 0 |
| rails-pr57128 | 108 | 36 | 36 |
| rails-pr56811 | 144 | 0 | 0 |
| rails-pr58709 | 144 | 0 | 0 |
| rails-pr57128+56811 | 108 | 36 | 36 |
| rails-pr58709+56811 | 144 | 0 | 0 |

For #57128 and #57128 + #56811, each of the 36 C1/C2/C4 rebuild cells contains an intermediate COMMIT, then FK disabling, a rebuild within a SAVEPOINT, FK restoration, and another BEGIN/COMMIT. Their restart condition remains `open_transactions == 1 && current_transaction.joinable? && referenced_by_destructive_foreign_key?(table_name)` ([#57128 line 704](https://github.com/emirn/rails/blob/8823c1370c7bc8910e609d1b6f27f4fc34f3d81d/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L704)). Successful preservation therefore does not establish whole-migration atomicity: writes before that COMMIT could survive a later failure. The separate failure-injection experiment below tests that directly without changing the operation matrix.

#58709 and #58709 + #56811 disable foreign_keys before BEGIN and restore it after the sole COMMIT, including for operations without rebuilds. It avoids #57128's intermediate-commit pattern in these traces. #56811 also has one COMMIT, but its rebuild PRAGMA occurs after BEGIN and does not prevent the measured FK losses. All new trials finish with FK enforcement ON. Nested transactions, arbitrary trigger dependencies and concurrent writes remain outside this experiment.

## Failure injection: migration atomicity

Observed: 2026-10-09T23:50:16.405024+00:00. 48 executions across 6 pins, all starting with two parents, three C1 cascade children and a marker row.

Each migration first updates `markers.note` to `written before rebuild` (data variant), or adds `markers.stage_note` with default `added before rebuild` (schema variant). It then runs `change_column_default :parents, :value, from: '5', to: '9'`, which rebuilds the parent. After recording the in-transaction state, it either raises `atomicity injected failure` or executes `UPDATE parents SET payload = NULL WHERE id = 1`, violating NOT NULL. All four combinations also run with `disable_ddl_transaction!`, giving eight variants per pin.

For a transactional migration, the expected result is the original application rows and schema, including parent default '5', and unchanged `schema_migrations`. The latter is pre-created and seeded with version `20260101000000`; the failed migration is `20261010000001`. The observer reopens the database after the runner disconnects. Full rows, table definitions, column metadata, FK/integrity checks, failure messages and exact SQL are retained. `ar_internal_metadata` and SQLite internal tables are excluded from application comparison; `schema_migrations` rows and definition are included.

`Fully rolled back` means persisted rows and schema match the starting state. `Partially committed` means intended changes survive the error. `Data loss` takes precedence if existing parent or child rows disappear or change; the JSON retains individual damaged rows and surviving intended changes. A transient loss that is restored by rollback is reported separately from persisted damage.

### Transactional variants

| Pin | Data + raise | Data + NOT NULL | Schema + raise | Schema + NOT NULL |
|---|---|---|---|---|
| current | fully rolled back | fully rolled back | fully rolled back | fully rolled back |
| rails-pr57128 | partially committed | partially committed | partially committed | partially committed |
| rails-pr58709 | fully rolled back | fully rolled back | fully rolled back | fully rolled back |
| rails-pr56811 | fully rolled back | fully rolled back | fully rolled back | fully rolled back |
| rails-pr57128+56811 | partially committed | partially committed | partially committed | partially committed |
| rails-pr58709+56811 | fully rolled back | fully rolled back | fully rolled back | fully rolled back |

### Surviving changes

Both failure types have the same result for a given pin and precursor. The SQL failure itself does not persist a NULL parent payload.

| Pin | Transactional data variant | Transactional schema variant | Children after failure | schema_migrations |
|---|---|---|---|---|
| current | none | none | 3/3 | unchanged |
| rails-pr57128 | marker write, parent default '9' | marker column, parent default '9' | 3/3 | unchanged |
| rails-pr58709 | none | none | 3/3 | unchanged |
| rails-pr56811 | none | none | 3/3 | unchanged |
| rails-pr57128+56811 | marker write, parent default '9' | marker column, parent default '9' | 3/3 | unchanged |
| rails-pr58709+56811 | none | none | 3/3 | unchanged |

#57128 and #57128 + #56811 persist both the precursor and the completed parent rebuild despite the error. The failed migration version is absent, so migration bookkeeping does not signal the already committed application changes. Current, #56811, #58709 and #58709 + #56811 roll back all four transactional variants completely.

Current and #56811 have zero children at the after-rebuild checkpoint in transactional variants: the rebuild did cascade-delete them. Their final ROLLBACK restores all three. The other four pins retain all children even at that checkpoint. Across these 48 failures, no pin leaves persisted parent/child data loss, FK violations or integrity errors. Every execution reaches the intended failure and finishes with foreign_keys ON.

### Transaction boundaries and responsible code

For transactional #57128 and its trigger-preserving combination, the trace is `BEGIN → precursor → COMMIT → SAVEPOINT → rebuild → RELEASE → BEGIN → failure → ROLLBACK`. The first COMMIT makes the precursor durable. With no outer database transaction open, releasing that outermost savepoint commits the rebuild. The final ROLLBACK cannot undo either. The adapter explicitly does this at [#57128 lines 704–718](https://github.com/emirn/rails/blob/8823c1370c7bc8910e609d1b6f27f4fc34f3d81d/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L704):

```ruby
restart = open_transactions == 1 && current_transaction.joinable? && referenced_by_destructive_foreign_key?(table_name)
commit_db_transaction
transaction(requires_new: restart) do
# ...
begin_db_transaction if restart
```

These are excerpts, not a contiguous replacement method. The combined adapter retains this code at lines 705–720; its only additional rebuild statement restores triggers. Exact numbered runtime excerpts and full-file hashes for all six pins are in [rails_atomicity.json](rails_atomicity.json).

#58709 and #58709 + #56811 instead trace `foreign_keys=OFF → BEGIN → precursor → rebuild → failure → ROLLBACK → foreign_keys=ON`, with no intervening COMMIT or SAVEPOINT. Migrator calls `connection.transaction_for_migration(&block)` ([line 1607](https://github.com/nicolasva/rails/blob/428884a88b3a42c914f5227819b6b672325b3312/activerecord/lib/active_record/migration.rb#L1607)), whose SQLite implementation wraps `transaction(&block)` in `disable_referential_integrity` ([adapter lines 201–205](https://github.com/nicolasva/rails/blob/428884a88b3a42c914f5227819b6b672325b3312/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L201)). These runs demonstrate rollback for the tested writes and rebuild, including a database error.

### Explicitly disabled migration transactions

| Pin | Partial commits | Full rollbacks | Persisted data-loss trials | schema_migrations unchanged |
|---|---:|---:|---:|---:|
| current | 4/4 | 0 | 0 | 4/4 |
| rails-pr57128 | 4/4 | 0 | 0 | 4/4 |
| rails-pr58709 | 4/4 | 0 | 0 | 4/4 |
| rails-pr56811 | 4/4 | 0 | 0 | 4/4 |
| rails-pr57128+56811 | 4/4 | 0 | 0 | 4/4 |
| rails-pr58709+56811 | 4/4 | 0 | 0 | 4/4 |

All six pins retain the marker write or added marker column and the parent default '9' in all four no-transaction variants. All three children survive. 
With transactions disabled the precursor is autocommitted and the adapter commits its own rebuild transaction before the injected failure, so no migration transaction remains to roll back. The responsible Migrator guard is `!migration.disable_ddl_transaction && connection.supports_ddl_transactions?`; when false, `ddl_transaction` simply executes `yield` ([#58709 lines 1605–1614](https://github.com/nicolasva/rails/blob/428884a88b3a42c914f5227819b6b672325b3312/activerecord/lib/active_record/migration.rb#L1605)). Equivalent guards are retained in the other pins' runtime excerpts.

The experiment covers one rebuild and two precursor/failure types with C1 populated fixtures. It does not establish behavior for nested transactions, concurrent connections, multiple rebuilds or every migration operation. Compressed per-trial evidence is linked by the raw rows under `results/rails-atomicity/`; temporary databases are removed after observation.

## Reproduction and evidence

```sh
.venv/bin/python scripts/setup.py --upstream --labels rails-pr56811 rails-pr58709 rails-pr57128+56811 rails-pr58709+56811
.venv/bin/python -m smp rails-fixes --output results/<new directory> --workers 8
.venv/bin/python -m smp rails-atomicity --output results/<new directory>
.venv/bin/python scripts/validate_rails_fixes.py results/<new directory>/rails_fixes.json
```

A run writes to a new output directory; evidence is reused only by the linter, pins and code that produced it. [Raw rows](rails_fixes.json) include comparison rows, pilot observations, detector findings, pins and per-trial transaction counts. Row artifact paths link to gzip JSON containing exact fixtures, SQL, runtime metadata and logs.
