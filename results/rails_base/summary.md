# Rails same-base control

Observed: 2026-11-02T02:29:34.534305+00:00.

432 operation/context pairs (864 executions) and 24 atomicity probes on 3 bases. The PR and local-merge results they are compared with come from the earlier runs in `results/rails_fixes.json` and `results/rails_atomicity.json`.

Each base loses preservation in 48/144 populated cells and 12/144 empty cells. #57128 and #58709 each eliminate the 36 populated FK-loss cells but retain 12 trigger-loss cells. #56811 eliminates the 12 trigger-loss cells in both populations but retains 36 populated FK-loss cells. Both combinations preserve all 288/288 matrix executions. No base-preserved matrix cell regresses. The bases fully roll back 12/12 transactional failures; #57128 and its combination each partially commit 4/4 transactional failures, while #58709, #56811 and the #58709 combination each roll back 4/4. These differences persist with identical loaded dependency versions, Ruby and SQLite within every comparison.

## Reproduce

```sh
.venv/bin/python scripts/build_rails_base.py --output results/rails_base/<new directory>
.venv/bin/python -m smp.rails_base --output results/rails_base/<new directory> --workers 6
```

Builds use frozen Gemfile.lock resolutions and a runtime directory of their own under the output. The run command validates cached evidence before reporting. The method is described in `PROTOCOL_rails_base.md`.

## Provenance

| Base pin | Commit | PRs covered | Ruby | SQLite |
|---|---|---|---|---|
| rails-base-b8725ee9a909 | `b8725ee9a90988129738197fecdb3eacb8b2e138` | rails-pr57128 | 3.4.3 | 3.53.2 |
| rails-base-704aa9785156 | `704aa9785156f3b52f825b8c4dae8460e669bc97` | rails-pr56811 | 3.4.3 | 3.53.2 |
| rails-base-bd885faee983 | `bd885faee983c6986da1919d96ee6f671a35164c` | rails-pr58709 | 3.4.3 | 3.53.2 |

| Historical comparator | Commit |
|---|---|
| rails-pr56811 | `7ddc17783418454c0e406181ae442d0aaf558ad8` |
| rails-pr57128 | `8823c1370c7bc8910e609d1b6f27f4fc34f3d81d` |
| rails-pr57128+56811 | `5827151e652ee67ed7060e7da20c67ab2a75fb31` |
| rails-pr58709 | `428884a88b3a42c914f5227819b6b672325b3312` |
| rails-pr58709+56811 | `bec5f3e1d7ec75a43f65af23b7b58e65b20caf9e` |

Full PR and derived-merge commits, input checksums, dependency differences and lockfile hashes are in [comparison.json](comparison.json). Gemfiles and lockfiles are under `builds/<base-pin>/`; historical comparator lockfiles are under `comparators/<pin>/`. Loaded source snapshots are under `source/`. Raw observations and SQL traces are in `operation_evidence/` and `rails-atomicity/`.

### Recorded bases and branch points

The saved GitHub commit comparisons show #57128 is 12 commits ahead of its recorded base and #58709 is one commit ahead; neither is behind. Their runtime deltas are confined to the SQLite adapter for #57128, and the SQLite adapter plus migration transaction methods for #58709. #56811 is one commit ahead and two commits behind its recorded base. Its true branch point is `3faf056f240966b268dd6fa52c559e241a370d06`; the two base-only commits change only `activerecord/test/cases/adapters/postgresql/bytea_test.rb`, with no runtime changes. The recorded base was therefore retained.

Commit comparisons are in [source_comparisons.json](source_comparisons.json) and `source/*compare.json` / `source/*divergence.json`.

## Counts

| Comparison | Population | Base silent loss | Head silent loss | Fixed loss | Preserved → non-preserved |
|---|---|---:|---:|---:|---:|
| rails-pr57128 | populated | 48/144 | 12/144 | 36/144 | 0/144 |
| rails-pr57128 | empty | 12/144 | 12/144 | 0/144 | 0/144 |
| rails-pr56811 | populated | 48/144 | 36/144 | 12/144 | 0/144 |
| rails-pr56811 | empty | 12/144 | 0/144 | 12/144 | 0/144 |
| rails-pr58709 | populated | 48/144 | 12/144 | 36/144 | 0/144 |
| rails-pr58709 | empty | 12/144 | 12/144 | 0/144 | 0/144 |
| rails-pr57128+56811 | populated | 48/144 | 0/144 | 48/144 | 0/144 |
| rails-pr57128+56811 | empty | 12/144 | 0/144 | 12/144 | 0/144 |
| rails-pr58709+56811 | populated | 48/144 | 0/144 | 48/144 | 0/144 |
| rails-pr58709+56811 | empty | 12/144 | 0/144 | 12/144 | 0/144 |

| Pin | Population | Preserved | Silent loss | Failed loudly | Failed partially |
|---|---|---:|---:|---:|---:|
| rails-base-b8725ee9a909 | populated | 96/144 | 48/144 | 0/144 | 0/144 |
| rails-base-b8725ee9a909 | empty | 132/144 | 12/144 | 0/144 | 0/144 |
| rails-pr57128 | populated | 132/144 | 12/144 | 0/144 | 0/144 |
| rails-pr57128 | empty | 132/144 | 12/144 | 0/144 | 0/144 |
| rails-base-704aa9785156 | populated | 96/144 | 48/144 | 0/144 | 0/144 |
| rails-base-704aa9785156 | empty | 132/144 | 12/144 | 0/144 | 0/144 |
| rails-pr56811 | populated | 108/144 | 36/144 | 0/144 | 0/144 |
| rails-pr56811 | empty | 144/144 | 0/144 | 0/144 | 0/144 |
| rails-base-bd885faee983 | populated | 96/144 | 48/144 | 0/144 | 0/144 |
| rails-base-bd885faee983 | empty | 132/144 | 12/144 | 0/144 | 0/144 |
| rails-pr58709 | populated | 132/144 | 12/144 | 0/144 | 0/144 |
| rails-pr58709 | empty | 132/144 | 12/144 | 0/144 | 0/144 |
| rails-pr57128+56811 | populated | 144/144 | 0/144 | 0/144 | 0/144 |
| rails-pr57128+56811 | empty | 144/144 | 0/144 | 0/144 | 0/144 |
| rails-pr58709+56811 | populated | 144/144 | 0/144 | 0/144 | 0/144 |
| rails-pr58709+56811 | empty | 144/144 | 0/144 | 0/144 | 0/144 |

## Atomicity

Each comparison has four transactional and four explicitly nontransactional scenarios. Intermediate children are counted immediately after rebuild; final children after failure, each out of three. Survivors list durable intended changes. Full assessment details and bookkeeping are retained in JSON.

| Pin | Transactional rollback | Transactional partial commit | Disabled-transaction partial commit | Persisted data loss |
|---|---:|---:|---:|---:|
| rails-base-b8725ee9a909 | 4/4 | 0/4 | 4/4 | 0/8 |
| rails-pr57128 | 0/4 | 4/4 | 4/4 | 0/8 |
| rails-base-704aa9785156 | 4/4 | 0/4 | 4/4 | 0/8 |
| rails-pr56811 | 4/4 | 0/4 | 4/4 | 0/8 |
| rails-base-bd885faee983 | 4/4 | 0/4 | 4/4 | 0/8 |
| rails-pr58709 | 4/4 | 0/4 | 4/4 | 0/8 |
| rails-pr57128+56811 | 0/4 | 4/4 | 4/4 | 0/8 |
| rails-pr58709+56811 | 4/4 | 0/4 | 4/4 | 0/8 |

### rails-base-b8725ee9a909 → rails-pr57128

| Scenario | Base outcome | Head outcome | Intermediate children base/head | Final children base/head | Surviving changes base/head | Bookkeeping unchanged base/head |
|---|---|---|---|---|---|---|
| transaction_data_raise | fully rolled back | partially committed | 0/3 / 3/3 | 3/3 / 3/3 | none / precursor_data, rebuilt_parent_default | True / True |
| transaction_data_not_null | fully rolled back | partially committed | 0/3 / 3/3 | 3/3 / 3/3 | none / precursor_data, rebuilt_parent_default | True / True |
| transaction_schema_raise | fully rolled back | partially committed | 0/3 / 3/3 | 3/3 / 3/3 | none / precursor_schema, rebuilt_parent_default | True / True |
| transaction_schema_not_null | fully rolled back | partially committed | 0/3 / 3/3 | 3/3 / 3/3 | none / precursor_schema, rebuilt_parent_default | True / True |
| no_transaction_data_raise | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_data, rebuilt_parent_default / precursor_data, rebuilt_parent_default | True / True |
| no_transaction_data_not_null | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_data, rebuilt_parent_default / precursor_data, rebuilt_parent_default | True / True |
| no_transaction_schema_raise | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_schema, rebuilt_parent_default / precursor_schema, rebuilt_parent_default | True / True |
| no_transaction_schema_not_null | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_schema, rebuilt_parent_default / precursor_schema, rebuilt_parent_default | True / True |

### rails-base-704aa9785156 → rails-pr56811

| Scenario | Base outcome | Head outcome | Intermediate children base/head | Final children base/head | Surviving changes base/head | Bookkeeping unchanged base/head |
|---|---|---|---|---|---|---|
| transaction_data_raise | fully rolled back | fully rolled back | 0/3 / 0/3 | 3/3 / 3/3 | none / none | True / True |
| transaction_data_not_null | fully rolled back | fully rolled back | 0/3 / 0/3 | 3/3 / 3/3 | none / none | True / True |
| transaction_schema_raise | fully rolled back | fully rolled back | 0/3 / 0/3 | 3/3 / 3/3 | none / none | True / True |
| transaction_schema_not_null | fully rolled back | fully rolled back | 0/3 / 0/3 | 3/3 / 3/3 | none / none | True / True |
| no_transaction_data_raise | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_data, rebuilt_parent_default / precursor_data, rebuilt_parent_default | True / True |
| no_transaction_data_not_null | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_data, rebuilt_parent_default / precursor_data, rebuilt_parent_default | True / True |
| no_transaction_schema_raise | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_schema, rebuilt_parent_default / precursor_schema, rebuilt_parent_default | True / True |
| no_transaction_schema_not_null | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_schema, rebuilt_parent_default / precursor_schema, rebuilt_parent_default | True / True |

### rails-base-bd885faee983 → rails-pr58709

| Scenario | Base outcome | Head outcome | Intermediate children base/head | Final children base/head | Surviving changes base/head | Bookkeeping unchanged base/head |
|---|---|---|---|---|---|---|
| transaction_data_raise | fully rolled back | fully rolled back | 0/3 / 3/3 | 3/3 / 3/3 | none / none | True / True |
| transaction_data_not_null | fully rolled back | fully rolled back | 0/3 / 3/3 | 3/3 / 3/3 | none / none | True / True |
| transaction_schema_raise | fully rolled back | fully rolled back | 0/3 / 3/3 | 3/3 / 3/3 | none / none | True / True |
| transaction_schema_not_null | fully rolled back | fully rolled back | 0/3 / 3/3 | 3/3 / 3/3 | none / none | True / True |
| no_transaction_data_raise | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_data, rebuilt_parent_default / precursor_data, rebuilt_parent_default | True / True |
| no_transaction_data_not_null | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_data, rebuilt_parent_default / precursor_data, rebuilt_parent_default | True / True |
| no_transaction_schema_raise | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_schema, rebuilt_parent_default / precursor_schema, rebuilt_parent_default | True / True |
| no_transaction_schema_not_null | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_schema, rebuilt_parent_default / precursor_schema, rebuilt_parent_default | True / True |

### rails-base-b8725ee9a909 → rails-pr57128+56811

| Scenario | Base outcome | Head outcome | Intermediate children base/head | Final children base/head | Surviving changes base/head | Bookkeeping unchanged base/head |
|---|---|---|---|---|---|---|
| transaction_data_raise | fully rolled back | partially committed | 0/3 / 3/3 | 3/3 / 3/3 | none / precursor_data, rebuilt_parent_default | True / True |
| transaction_data_not_null | fully rolled back | partially committed | 0/3 / 3/3 | 3/3 / 3/3 | none / precursor_data, rebuilt_parent_default | True / True |
| transaction_schema_raise | fully rolled back | partially committed | 0/3 / 3/3 | 3/3 / 3/3 | none / precursor_schema, rebuilt_parent_default | True / True |
| transaction_schema_not_null | fully rolled back | partially committed | 0/3 / 3/3 | 3/3 / 3/3 | none / precursor_schema, rebuilt_parent_default | True / True |
| no_transaction_data_raise | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_data, rebuilt_parent_default / precursor_data, rebuilt_parent_default | True / True |
| no_transaction_data_not_null | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_data, rebuilt_parent_default / precursor_data, rebuilt_parent_default | True / True |
| no_transaction_schema_raise | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_schema, rebuilt_parent_default / precursor_schema, rebuilt_parent_default | True / True |
| no_transaction_schema_not_null | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_schema, rebuilt_parent_default / precursor_schema, rebuilt_parent_default | True / True |

### rails-base-bd885faee983 → rails-pr58709+56811

| Scenario | Base outcome | Head outcome | Intermediate children base/head | Final children base/head | Surviving changes base/head | Bookkeeping unchanged base/head |
|---|---|---|---|---|---|---|
| transaction_data_raise | fully rolled back | fully rolled back | 0/3 / 3/3 | 3/3 / 3/3 | none / none | True / True |
| transaction_data_not_null | fully rolled back | fully rolled back | 0/3 / 3/3 | 3/3 / 3/3 | none / none | True / True |
| transaction_schema_raise | fully rolled back | fully rolled back | 0/3 / 3/3 | 3/3 / 3/3 | none / none | True / True |
| transaction_schema_not_null | fully rolled back | fully rolled back | 0/3 / 3/3 | 3/3 / 3/3 | none / none | True / True |
| no_transaction_data_raise | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_data, rebuilt_parent_default / precursor_data, rebuilt_parent_default | True / True |
| no_transaction_data_not_null | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_data, rebuilt_parent_default / precursor_data, rebuilt_parent_default | True / True |
| no_transaction_schema_raise | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_schema, rebuilt_parent_default / precursor_schema, rebuilt_parent_default | True / True |
| no_transaction_schema_not_null | partially committed | partially committed | 3/3 / 3/3 | 3/3 / 3/3 | precursor_schema, rebuilt_parent_default / precursor_schema, rebuilt_parent_default | True / True |

## Cell-by-cell matrix

† = observed rebuild; D = content digest, R = row count, O = schema object, T = trigger behavior. Each row shows both populations; unchanged cells are included.

### rails-base-b8725ee9a909 → rails-pr57128

| Operation | Context | Base populated | Head populated | Base empty | Head empty |
|---|---|---|---|---|---|
| add_check_constraint | C0 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_check_constraint | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_check_constraint | C3 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_check_constraint | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| add_check_constraint | C6 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C7 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C8 | preserved† | preserved† | preserved† | preserved† |
| add_column | C0 | preserved | preserved | preserved | preserved |
| add_column | C1 | preserved | preserved | preserved | preserved |
| add_column | C2 | preserved | preserved | preserved | preserved |
| add_column | C3 | preserved | preserved | preserved | preserved |
| add_column | C4 | preserved | preserved | preserved | preserved |
| add_column | C5 | preserved | preserved | preserved | preserved |
| add_column | C6 | preserved | preserved | preserved | preserved |
| add_column | C7 | preserved | preserved | preserved | preserved |
| add_column | C8 | preserved | preserved | preserved | preserved |
| add_foreign_key | C0 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_foreign_key | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_foreign_key | C3 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_foreign_key | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| add_foreign_key | C6 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C7 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C8 | preserved† | preserved† | preserved† | preserved† |
| add_index | C0 | preserved | preserved | preserved | preserved |
| add_index | C1 | preserved | preserved | preserved | preserved |
| add_index | C2 | preserved | preserved | preserved | preserved |
| add_index | C3 | preserved | preserved | preserved | preserved |
| add_index | C4 | preserved | preserved | preserved | preserved |
| add_index | C5 | preserved | preserved | preserved | preserved |
| add_index | C6 | preserved | preserved | preserved | preserved |
| add_index | C7 | preserved | preserved | preserved | preserved |
| add_index | C8 | preserved | preserved | preserved | preserved |
| add_reference | C0 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_reference | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_reference | C3 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_reference | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| add_reference | C6 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C7 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C8 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C0 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_timestamps | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_timestamps | C3 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_timestamps | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| add_timestamps | C6 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C7 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C8 | preserved† | preserved† | preserved† | preserved† |
| change_default | C0 | preserved† | preserved† | preserved† | preserved† |
| change_default | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_default | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| change_default | C3 | preserved† | preserved† | preserved† | preserved† |
| change_default | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_default | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| change_default | C6 | preserved† | preserved† | preserved† | preserved† |
| change_default | C7 | preserved† | preserved† | preserved† | preserved† |
| change_default | C8 | preserved† | preserved† | preserved† | preserved† |
| change_type | C0 | preserved† | preserved† | preserved† | preserved† |
| change_type | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_type | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| change_type | C3 | preserved† | preserved† | preserved† | preserved† |
| change_type | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_type | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| change_type | C6 | preserved† | preserved† | preserved† | preserved† |
| change_type | C7 | preserved† | preserved† | preserved† | preserved† |
| change_type | C8 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C0 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| drop_not_null | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| drop_not_null | C3 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| drop_not_null | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| drop_not_null | C6 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C7 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_check_constraint | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| remove_check_constraint | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_check_constraint | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| remove_check_constraint | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_column | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| remove_column | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_column | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| remove_column | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_foreign_key | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| remove_foreign_key | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_foreign_key | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| remove_foreign_key | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_index | C0 | preserved | preserved | preserved | preserved |
| remove_index | C1 | preserved | preserved | preserved | preserved |
| remove_index | C2 | preserved | preserved | preserved | preserved |
| remove_index | C3 | preserved | preserved | preserved | preserved |
| remove_index | C4 | preserved | preserved | preserved | preserved |
| remove_index | C5 | preserved | preserved | preserved | preserved |
| remove_index | C6 | preserved | preserved | preserved | preserved |
| remove_index | C7 | preserved | preserved | preserved | preserved |
| remove_index | C8 | preserved | preserved | preserved | preserved |
| rename_column | C0 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| rename_column | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| rename_column | C3 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| rename_column | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| rename_column | C6 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C7 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C8 | preserved† | preserved† | preserved† | preserved† |
| rename_table | C0 | preserved | preserved | preserved | preserved |
| rename_table | C1 | preserved | preserved | preserved | preserved |
| rename_table | C2 | preserved | preserved | preserved | preserved |
| rename_table | C3 | preserved | preserved | preserved | preserved |
| rename_table | C4 | preserved | preserved | preserved | preserved |
| rename_table | C5 | preserved | preserved | preserved | preserved |
| rename_table | C6 | preserved | preserved | preserved | preserved |
| rename_table | C7 | preserved | preserved | preserved | preserved |
| rename_table | C8 | preserved | preserved | preserved | preserved |
| set_not_null | C0 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| set_not_null | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| set_not_null | C3 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| set_not_null | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| set_not_null | C6 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C7 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C8 | preserved† | preserved† | preserved† | preserved† |

### rails-base-704aa9785156 → rails-pr56811

| Operation | Context | Base populated | Head populated | Base empty | Head empty |
|---|---|---|---|---|---|
| add_check_constraint | C0 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C1 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| add_check_constraint | C2 | silent-loss(D)† | silent-loss(D)† | preserved† | preserved† |
| add_check_constraint | C3 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C4 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| add_check_constraint | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| add_check_constraint | C6 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C7 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C8 | preserved† | preserved† | preserved† | preserved† |
| add_column | C0 | preserved | preserved | preserved | preserved |
| add_column | C1 | preserved | preserved | preserved | preserved |
| add_column | C2 | preserved | preserved | preserved | preserved |
| add_column | C3 | preserved | preserved | preserved | preserved |
| add_column | C4 | preserved | preserved | preserved | preserved |
| add_column | C5 | preserved | preserved | preserved | preserved |
| add_column | C6 | preserved | preserved | preserved | preserved |
| add_column | C7 | preserved | preserved | preserved | preserved |
| add_column | C8 | preserved | preserved | preserved | preserved |
| add_foreign_key | C0 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C1 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| add_foreign_key | C2 | silent-loss(D)† | silent-loss(D)† | preserved† | preserved† |
| add_foreign_key | C3 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C4 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| add_foreign_key | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| add_foreign_key | C6 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C7 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C8 | preserved† | preserved† | preserved† | preserved† |
| add_index | C0 | preserved | preserved | preserved | preserved |
| add_index | C1 | preserved | preserved | preserved | preserved |
| add_index | C2 | preserved | preserved | preserved | preserved |
| add_index | C3 | preserved | preserved | preserved | preserved |
| add_index | C4 | preserved | preserved | preserved | preserved |
| add_index | C5 | preserved | preserved | preserved | preserved |
| add_index | C6 | preserved | preserved | preserved | preserved |
| add_index | C7 | preserved | preserved | preserved | preserved |
| add_index | C8 | preserved | preserved | preserved | preserved |
| add_reference | C0 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C1 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| add_reference | C2 | silent-loss(D)† | silent-loss(D)† | preserved† | preserved† |
| add_reference | C3 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C4 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| add_reference | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| add_reference | C6 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C7 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C8 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C0 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C1 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| add_timestamps | C2 | silent-loss(D)† | silent-loss(D)† | preserved† | preserved† |
| add_timestamps | C3 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C4 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| add_timestamps | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| add_timestamps | C6 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C7 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C8 | preserved† | preserved† | preserved† | preserved† |
| change_default | C0 | preserved† | preserved† | preserved† | preserved† |
| change_default | C1 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| change_default | C2 | silent-loss(D)† | silent-loss(D)† | preserved† | preserved† |
| change_default | C3 | preserved† | preserved† | preserved† | preserved† |
| change_default | C4 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| change_default | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| change_default | C6 | preserved† | preserved† | preserved† | preserved† |
| change_default | C7 | preserved† | preserved† | preserved† | preserved† |
| change_default | C8 | preserved† | preserved† | preserved† | preserved† |
| change_type | C0 | preserved† | preserved† | preserved† | preserved† |
| change_type | C1 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| change_type | C2 | silent-loss(D)† | silent-loss(D)† | preserved† | preserved† |
| change_type | C3 | preserved† | preserved† | preserved† | preserved† |
| change_type | C4 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| change_type | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| change_type | C6 | preserved† | preserved† | preserved† | preserved† |
| change_type | C7 | preserved† | preserved† | preserved† | preserved† |
| change_type | C8 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C0 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C1 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| drop_not_null | C2 | silent-loss(D)† | silent-loss(D)† | preserved† | preserved† |
| drop_not_null | C3 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C4 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| drop_not_null | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| drop_not_null | C6 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C7 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C1 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| remove_check_constraint | C2 | silent-loss(D)† | silent-loss(D)† | preserved† | preserved† |
| remove_check_constraint | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C4 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| remove_check_constraint | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| remove_check_constraint | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C1 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| remove_column | C2 | silent-loss(D)† | silent-loss(D)† | preserved† | preserved† |
| remove_column | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C4 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| remove_column | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| remove_column | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C1 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| remove_foreign_key | C2 | silent-loss(D)† | silent-loss(D)† | preserved† | preserved† |
| remove_foreign_key | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C4 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| remove_foreign_key | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| remove_foreign_key | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_index | C0 | preserved | preserved | preserved | preserved |
| remove_index | C1 | preserved | preserved | preserved | preserved |
| remove_index | C2 | preserved | preserved | preserved | preserved |
| remove_index | C3 | preserved | preserved | preserved | preserved |
| remove_index | C4 | preserved | preserved | preserved | preserved |
| remove_index | C5 | preserved | preserved | preserved | preserved |
| remove_index | C6 | preserved | preserved | preserved | preserved |
| remove_index | C7 | preserved | preserved | preserved | preserved |
| remove_index | C8 | preserved | preserved | preserved | preserved |
| rename_column | C0 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C1 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| rename_column | C2 | silent-loss(D)† | silent-loss(D)† | preserved† | preserved† |
| rename_column | C3 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C4 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| rename_column | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| rename_column | C6 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C7 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C8 | preserved† | preserved† | preserved† | preserved† |
| rename_table | C0 | preserved | preserved | preserved | preserved |
| rename_table | C1 | preserved | preserved | preserved | preserved |
| rename_table | C2 | preserved | preserved | preserved | preserved |
| rename_table | C3 | preserved | preserved | preserved | preserved |
| rename_table | C4 | preserved | preserved | preserved | preserved |
| rename_table | C5 | preserved | preserved | preserved | preserved |
| rename_table | C6 | preserved | preserved | preserved | preserved |
| rename_table | C7 | preserved | preserved | preserved | preserved |
| rename_table | C8 | preserved | preserved | preserved | preserved |
| set_not_null | C0 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C1 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| set_not_null | C2 | silent-loss(D)† | silent-loss(D)† | preserved† | preserved† |
| set_not_null | C3 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C4 | silent-loss(D,R)† | silent-loss(D,R)† | preserved† | preserved† |
| set_not_null | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| set_not_null | C6 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C7 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C8 | preserved† | preserved† | preserved† | preserved† |

### rails-base-bd885faee983 → rails-pr58709

| Operation | Context | Base populated | Head populated | Base empty | Head empty |
|---|---|---|---|---|---|
| add_check_constraint | C0 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_check_constraint | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_check_constraint | C3 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_check_constraint | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| add_check_constraint | C6 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C7 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C8 | preserved† | preserved† | preserved† | preserved† |
| add_column | C0 | preserved | preserved | preserved | preserved |
| add_column | C1 | preserved | preserved | preserved | preserved |
| add_column | C2 | preserved | preserved | preserved | preserved |
| add_column | C3 | preserved | preserved | preserved | preserved |
| add_column | C4 | preserved | preserved | preserved | preserved |
| add_column | C5 | preserved | preserved | preserved | preserved |
| add_column | C6 | preserved | preserved | preserved | preserved |
| add_column | C7 | preserved | preserved | preserved | preserved |
| add_column | C8 | preserved | preserved | preserved | preserved |
| add_foreign_key | C0 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_foreign_key | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_foreign_key | C3 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_foreign_key | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| add_foreign_key | C6 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C7 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C8 | preserved† | preserved† | preserved† | preserved† |
| add_index | C0 | preserved | preserved | preserved | preserved |
| add_index | C1 | preserved | preserved | preserved | preserved |
| add_index | C2 | preserved | preserved | preserved | preserved |
| add_index | C3 | preserved | preserved | preserved | preserved |
| add_index | C4 | preserved | preserved | preserved | preserved |
| add_index | C5 | preserved | preserved | preserved | preserved |
| add_index | C6 | preserved | preserved | preserved | preserved |
| add_index | C7 | preserved | preserved | preserved | preserved |
| add_index | C8 | preserved | preserved | preserved | preserved |
| add_reference | C0 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_reference | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_reference | C3 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_reference | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| add_reference | C6 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C7 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C8 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C0 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_timestamps | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_timestamps | C3 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_timestamps | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| add_timestamps | C6 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C7 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C8 | preserved† | preserved† | preserved† | preserved† |
| change_default | C0 | preserved† | preserved† | preserved† | preserved† |
| change_default | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_default | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| change_default | C3 | preserved† | preserved† | preserved† | preserved† |
| change_default | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_default | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| change_default | C6 | preserved† | preserved† | preserved† | preserved† |
| change_default | C7 | preserved† | preserved† | preserved† | preserved† |
| change_default | C8 | preserved† | preserved† | preserved† | preserved† |
| change_type | C0 | preserved† | preserved† | preserved† | preserved† |
| change_type | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_type | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| change_type | C3 | preserved† | preserved† | preserved† | preserved† |
| change_type | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_type | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| change_type | C6 | preserved† | preserved† | preserved† | preserved† |
| change_type | C7 | preserved† | preserved† | preserved† | preserved† |
| change_type | C8 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C0 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| drop_not_null | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| drop_not_null | C3 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| drop_not_null | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| drop_not_null | C6 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C7 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_check_constraint | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| remove_check_constraint | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_check_constraint | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| remove_check_constraint | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_column | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| remove_column | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_column | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| remove_column | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_foreign_key | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| remove_foreign_key | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_foreign_key | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| remove_foreign_key | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_index | C0 | preserved | preserved | preserved | preserved |
| remove_index | C1 | preserved | preserved | preserved | preserved |
| remove_index | C2 | preserved | preserved | preserved | preserved |
| remove_index | C3 | preserved | preserved | preserved | preserved |
| remove_index | C4 | preserved | preserved | preserved | preserved |
| remove_index | C5 | preserved | preserved | preserved | preserved |
| remove_index | C6 | preserved | preserved | preserved | preserved |
| remove_index | C7 | preserved | preserved | preserved | preserved |
| remove_index | C8 | preserved | preserved | preserved | preserved |
| rename_column | C0 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| rename_column | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| rename_column | C3 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| rename_column | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| rename_column | C6 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C7 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C8 | preserved† | preserved† | preserved† | preserved† |
| rename_table | C0 | preserved | preserved | preserved | preserved |
| rename_table | C1 | preserved | preserved | preserved | preserved |
| rename_table | C2 | preserved | preserved | preserved | preserved |
| rename_table | C3 | preserved | preserved | preserved | preserved |
| rename_table | C4 | preserved | preserved | preserved | preserved |
| rename_table | C5 | preserved | preserved | preserved | preserved |
| rename_table | C6 | preserved | preserved | preserved | preserved |
| rename_table | C7 | preserved | preserved | preserved | preserved |
| rename_table | C8 | preserved | preserved | preserved | preserved |
| set_not_null | C0 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| set_not_null | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| set_not_null | C3 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| set_not_null | C5 | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† | silent-loss(O,T)† |
| set_not_null | C6 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C7 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C8 | preserved† | preserved† | preserved† | preserved† |

### rails-base-b8725ee9a909 → rails-pr57128+56811

| Operation | Context | Base populated | Head populated | Base empty | Head empty |
|---|---|---|---|---|---|
| add_check_constraint | C0 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_check_constraint | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_check_constraint | C3 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_check_constraint | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| add_check_constraint | C6 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C7 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C8 | preserved† | preserved† | preserved† | preserved† |
| add_column | C0 | preserved | preserved | preserved | preserved |
| add_column | C1 | preserved | preserved | preserved | preserved |
| add_column | C2 | preserved | preserved | preserved | preserved |
| add_column | C3 | preserved | preserved | preserved | preserved |
| add_column | C4 | preserved | preserved | preserved | preserved |
| add_column | C5 | preserved | preserved | preserved | preserved |
| add_column | C6 | preserved | preserved | preserved | preserved |
| add_column | C7 | preserved | preserved | preserved | preserved |
| add_column | C8 | preserved | preserved | preserved | preserved |
| add_foreign_key | C0 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_foreign_key | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_foreign_key | C3 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_foreign_key | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| add_foreign_key | C6 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C7 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C8 | preserved† | preserved† | preserved† | preserved† |
| add_index | C0 | preserved | preserved | preserved | preserved |
| add_index | C1 | preserved | preserved | preserved | preserved |
| add_index | C2 | preserved | preserved | preserved | preserved |
| add_index | C3 | preserved | preserved | preserved | preserved |
| add_index | C4 | preserved | preserved | preserved | preserved |
| add_index | C5 | preserved | preserved | preserved | preserved |
| add_index | C6 | preserved | preserved | preserved | preserved |
| add_index | C7 | preserved | preserved | preserved | preserved |
| add_index | C8 | preserved | preserved | preserved | preserved |
| add_reference | C0 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_reference | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_reference | C3 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_reference | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| add_reference | C6 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C7 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C8 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C0 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_timestamps | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_timestamps | C3 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_timestamps | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| add_timestamps | C6 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C7 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C8 | preserved† | preserved† | preserved† | preserved† |
| change_default | C0 | preserved† | preserved† | preserved† | preserved† |
| change_default | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_default | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| change_default | C3 | preserved† | preserved† | preserved† | preserved† |
| change_default | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_default | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| change_default | C6 | preserved† | preserved† | preserved† | preserved† |
| change_default | C7 | preserved† | preserved† | preserved† | preserved† |
| change_default | C8 | preserved† | preserved† | preserved† | preserved† |
| change_type | C0 | preserved† | preserved† | preserved† | preserved† |
| change_type | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_type | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| change_type | C3 | preserved† | preserved† | preserved† | preserved† |
| change_type | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_type | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| change_type | C6 | preserved† | preserved† | preserved† | preserved† |
| change_type | C7 | preserved† | preserved† | preserved† | preserved† |
| change_type | C8 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C0 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| drop_not_null | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| drop_not_null | C3 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| drop_not_null | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| drop_not_null | C6 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C7 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_check_constraint | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| remove_check_constraint | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_check_constraint | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| remove_check_constraint | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_column | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| remove_column | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_column | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| remove_column | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_foreign_key | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| remove_foreign_key | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_foreign_key | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| remove_foreign_key | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_index | C0 | preserved | preserved | preserved | preserved |
| remove_index | C1 | preserved | preserved | preserved | preserved |
| remove_index | C2 | preserved | preserved | preserved | preserved |
| remove_index | C3 | preserved | preserved | preserved | preserved |
| remove_index | C4 | preserved | preserved | preserved | preserved |
| remove_index | C5 | preserved | preserved | preserved | preserved |
| remove_index | C6 | preserved | preserved | preserved | preserved |
| remove_index | C7 | preserved | preserved | preserved | preserved |
| remove_index | C8 | preserved | preserved | preserved | preserved |
| rename_column | C0 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| rename_column | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| rename_column | C3 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| rename_column | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| rename_column | C6 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C7 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C8 | preserved† | preserved† | preserved† | preserved† |
| rename_table | C0 | preserved | preserved | preserved | preserved |
| rename_table | C1 | preserved | preserved | preserved | preserved |
| rename_table | C2 | preserved | preserved | preserved | preserved |
| rename_table | C3 | preserved | preserved | preserved | preserved |
| rename_table | C4 | preserved | preserved | preserved | preserved |
| rename_table | C5 | preserved | preserved | preserved | preserved |
| rename_table | C6 | preserved | preserved | preserved | preserved |
| rename_table | C7 | preserved | preserved | preserved | preserved |
| rename_table | C8 | preserved | preserved | preserved | preserved |
| set_not_null | C0 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| set_not_null | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| set_not_null | C3 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| set_not_null | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| set_not_null | C6 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C7 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C8 | preserved† | preserved† | preserved† | preserved† |

### rails-base-bd885faee983 → rails-pr58709+56811

| Operation | Context | Base populated | Head populated | Base empty | Head empty |
|---|---|---|---|---|---|
| add_check_constraint | C0 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_check_constraint | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_check_constraint | C3 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_check_constraint | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| add_check_constraint | C6 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C7 | preserved† | preserved† | preserved† | preserved† |
| add_check_constraint | C8 | preserved† | preserved† | preserved† | preserved† |
| add_column | C0 | preserved | preserved | preserved | preserved |
| add_column | C1 | preserved | preserved | preserved | preserved |
| add_column | C2 | preserved | preserved | preserved | preserved |
| add_column | C3 | preserved | preserved | preserved | preserved |
| add_column | C4 | preserved | preserved | preserved | preserved |
| add_column | C5 | preserved | preserved | preserved | preserved |
| add_column | C6 | preserved | preserved | preserved | preserved |
| add_column | C7 | preserved | preserved | preserved | preserved |
| add_column | C8 | preserved | preserved | preserved | preserved |
| add_foreign_key | C0 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_foreign_key | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_foreign_key | C3 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_foreign_key | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| add_foreign_key | C6 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C7 | preserved† | preserved† | preserved† | preserved† |
| add_foreign_key | C8 | preserved† | preserved† | preserved† | preserved† |
| add_index | C0 | preserved | preserved | preserved | preserved |
| add_index | C1 | preserved | preserved | preserved | preserved |
| add_index | C2 | preserved | preserved | preserved | preserved |
| add_index | C3 | preserved | preserved | preserved | preserved |
| add_index | C4 | preserved | preserved | preserved | preserved |
| add_index | C5 | preserved | preserved | preserved | preserved |
| add_index | C6 | preserved | preserved | preserved | preserved |
| add_index | C7 | preserved | preserved | preserved | preserved |
| add_index | C8 | preserved | preserved | preserved | preserved |
| add_reference | C0 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_reference | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_reference | C3 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_reference | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| add_reference | C6 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C7 | preserved† | preserved† | preserved† | preserved† |
| add_reference | C8 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C0 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_timestamps | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| add_timestamps | C3 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| add_timestamps | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| add_timestamps | C6 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C7 | preserved† | preserved† | preserved† | preserved† |
| add_timestamps | C8 | preserved† | preserved† | preserved† | preserved† |
| change_default | C0 | preserved† | preserved† | preserved† | preserved† |
| change_default | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_default | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| change_default | C3 | preserved† | preserved† | preserved† | preserved† |
| change_default | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_default | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| change_default | C6 | preserved† | preserved† | preserved† | preserved† |
| change_default | C7 | preserved† | preserved† | preserved† | preserved† |
| change_default | C8 | preserved† | preserved† | preserved† | preserved† |
| change_type | C0 | preserved† | preserved† | preserved† | preserved† |
| change_type | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_type | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| change_type | C3 | preserved† | preserved† | preserved† | preserved† |
| change_type | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| change_type | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| change_type | C6 | preserved† | preserved† | preserved† | preserved† |
| change_type | C7 | preserved† | preserved† | preserved† | preserved† |
| change_type | C8 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C0 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| drop_not_null | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| drop_not_null | C3 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| drop_not_null | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| drop_not_null | C6 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C7 | preserved† | preserved† | preserved† | preserved† |
| drop_not_null | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_check_constraint | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| remove_check_constraint | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_check_constraint | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| remove_check_constraint | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_check_constraint | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_column | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| remove_column | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_column | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| remove_column | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_column | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C0 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_foreign_key | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| remove_foreign_key | C3 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| remove_foreign_key | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| remove_foreign_key | C6 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C7 | preserved† | preserved† | preserved† | preserved† |
| remove_foreign_key | C8 | preserved† | preserved† | preserved† | preserved† |
| remove_index | C0 | preserved | preserved | preserved | preserved |
| remove_index | C1 | preserved | preserved | preserved | preserved |
| remove_index | C2 | preserved | preserved | preserved | preserved |
| remove_index | C3 | preserved | preserved | preserved | preserved |
| remove_index | C4 | preserved | preserved | preserved | preserved |
| remove_index | C5 | preserved | preserved | preserved | preserved |
| remove_index | C6 | preserved | preserved | preserved | preserved |
| remove_index | C7 | preserved | preserved | preserved | preserved |
| remove_index | C8 | preserved | preserved | preserved | preserved |
| rename_column | C0 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| rename_column | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| rename_column | C3 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| rename_column | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| rename_column | C6 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C7 | preserved† | preserved† | preserved† | preserved† |
| rename_column | C8 | preserved† | preserved† | preserved† | preserved† |
| rename_table | C0 | preserved | preserved | preserved | preserved |
| rename_table | C1 | preserved | preserved | preserved | preserved |
| rename_table | C2 | preserved | preserved | preserved | preserved |
| rename_table | C3 | preserved | preserved | preserved | preserved |
| rename_table | C4 | preserved | preserved | preserved | preserved |
| rename_table | C5 | preserved | preserved | preserved | preserved |
| rename_table | C6 | preserved | preserved | preserved | preserved |
| rename_table | C7 | preserved | preserved | preserved | preserved |
| rename_table | C8 | preserved | preserved | preserved | preserved |
| set_not_null | C0 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C1 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| set_not_null | C2 | silent-loss(D)† | preserved† | preserved† | preserved† |
| set_not_null | C3 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C4 | silent-loss(D,R)† | preserved† | preserved† | preserved† |
| set_not_null | C5 | silent-loss(O,T)† | preserved† | silent-loss(O,T)† | preserved† |
| set_not_null | C6 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C7 | preserved† | preserved† | preserved† | preserved† |
| set_not_null | C8 | preserved† | preserved† | preserved† | preserved† |

## Dependency differences

- rails-pr57128: none in loaded gems, Ruby or SQLite.
- rails-pr56811: none in loaded gems, Ruby or SQLite.
- rails-pr58709: none in loaded gems, Ruby or SQLite.
- rails-pr57128+56811: none in loaded gems, Ruby or SQLite.
- rails-pr58709+56811: none in loaded gems, Ruby or SQLite.

## Deviations and limitations

Notes recorded with the run are in the `deviations` field of [comparison.json](comparison.json).

The two local merges are descriptive comparisons against their first-parent PR base. They combine different branch histories and do not isolate both patches on a common base. Recorded PR base-to-head differences can also include intervening upstream changes; these controls remove the Rails-release and Ruby-version mismatch, but do not substitute for rebasing each minimal patch onto a single common commit. The matrix and eight atomicity scenarios do not cover arbitrary migrations, nesting or concurrency.
