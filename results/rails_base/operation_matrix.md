# SQLite operation preservation matrix

Observed: 2026-11-02T02:29:34.534305+00:00.

432 populated/empty pairs (864 executions); 0 infrastructure errors.

Cells: preserved; loud = failed-loudly (application state rolled back); loud-partial = failed-loudly-partial; silent-loss = successful execution with a violated invariant. **Bold** cells differ from current on the same path. A trailing `†` marks a table rebuild in the executed SQL, including rebuilds of dependent tables: a CREATE TABLE together with a DROP TABLE. A failing execution may stop before reaching a planned rebuild.

Invariants: R row count; D content digest; O schema object; T trigger behavior; V view rows/compilation; E FK enforcement; F foreign_key_check; K FK definition; I integrity_check; Q snapshot error; C intended change.

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

## Counts

Counts are operation × context cells per execution path, not estimates of ecosystem prevalence.

| Framework | Pin | Path | Cells | Silent-loss | Loud | Loud-partial | Preserved | Rebuilds |
|---|---|---|---:|---:|---:|---:|---:|---:|
| rails | rails-base-704aa9785156 | rails | 144 | 48 | 0 | 0 | 96 | 108 |
| rails | rails-base-b8725ee9a909 | rails | 144 | 48 | 0 | 0 | 96 | 108 |
| rails | rails-base-bd885faee983 | rails | 144 | 48 | 0 | 0 | 96 | 108 |

Every selected operation/pin/path successfully applies its intended change in at least one context. No unsupported operations were observed.

## Findings

Across the selected pins and paths, 144 populated pairs silently violate preservation, 0 fail with application state rolled back, 0 fail after partial commit, and 288 preserve the checked state.

- rails / rails-base-b8725ee9a909, framework path: 48/144 silent-loss cells (C1: 12, C2: 12, C4: 12, C5: 12).
- rails / rails-base-bd885faee983, framework path: 48/144 silent-loss cells (C1: 12, C2: 12, C4: 12, C5: 12).
- rails / rails-base-704aa9785156, framework path: 48/144 silent-loss cells (C1: 12, C2: 12, C4: 12, C5: 12).

Empty execution catches 0/144 populated silent-loss cells; checking invariants on those empty trials would catch 36. The empty-db detector intentionally measures execution errors only. Equal row counts miss C2 value losses.

Every silent-loss trial still has its intended change, FK enforcement ON, and clean foreign_key_check and integrity_check results.

## rails / rails-base-704aa9785156 / rails

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_reference | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_timestamps | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |

## rails / rails-base-b8725ee9a909 / rails

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_reference | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_timestamps | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |

## rails / rails-base-bd885faee983 / rails

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_reference | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| add_timestamps | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| change_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_check_constraint | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| remove_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |
| rename_table | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | preserved† | silent-loss(D,R)† | silent-loss(O,T)† | preserved† | preserved† | preserved† |

## Detector coverage of every silent-loss cell

Rows group contexts only when the operation, pin, path, violations and detector results are identical. Empty-db means execution error only. Lint warnings are pattern findings, not proof of loss. The unchanged schema-prefixed lint variants are also retained in JSON.

| Framework | Pin | Path | Operation | Contexts | Violations | Empty-db | Exec lint | File lint | Populated invariants |
|---|---|---|---|---|---|---|---|---|---|
| rails | rails-base-704aa9785156 | rails | add_check_constraint | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | add_check_constraint | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | add_check_constraint | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | add_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | add_reference | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | add_reference | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | add_reference | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | add_timestamps | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | add_timestamps | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | add_timestamps | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | change_default | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | change_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | change_default | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | change_type | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | change_type | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | change_type | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | drop_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | remove_check_constraint | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | remove_check_constraint | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | remove_check_constraint | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | remove_column | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | remove_column | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | remove_column | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | remove_foreign_key | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | remove_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | remove_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | rename_column | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | rename_column | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | rename_column | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | set_not_null | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | set_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-704aa9785156 | rails | set_not_null | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | add_check_constraint | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | add_check_constraint | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | add_check_constraint | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | add_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | add_reference | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | add_reference | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | add_reference | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | add_timestamps | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | add_timestamps | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | add_timestamps | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | change_default | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | change_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | change_default | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | change_type | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | change_type | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | change_type | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | drop_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | remove_check_constraint | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | remove_check_constraint | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | remove_check_constraint | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | remove_column | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | remove_column | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | remove_column | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | remove_foreign_key | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | remove_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | remove_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | rename_column | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | rename_column | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | rename_column | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | set_not_null | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | set_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-b8725ee9a909 | rails | set_not_null | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | add_check_constraint | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | add_check_constraint | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | add_check_constraint | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | add_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | add_reference | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | add_reference | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | add_reference | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | add_timestamps | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | add_timestamps | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | add_timestamps | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | change_default | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | change_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | change_default | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | change_type | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | change_type | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | change_type | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | drop_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | remove_check_constraint | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | remove_check_constraint | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | remove_check_constraint | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | remove_column | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | remove_column | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | remove_column | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | remove_foreign_key | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | remove_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | remove_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | rename_column | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | rename_column | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | rename_column | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | set_not_null | C2 | D | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | set_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | rails-base-bd885faee983 | rails | set_not_null | C5 | O,T | — | SQLD002 | — | yes |

## Scope, interpretation, and reproduction

All listed operations are attempted through the installed framework DSL or real Kit schema diff and generate command. Rename prompts select the single old column/table; generated migration SQL is never edited. No execution failure is automatically labeled unsupported. The operation names set/drop_not_null map to Rails change_column_null(false/true); change_type maps to Rails change_column(:integer). The complete-matrix validator requires successful execution with the intended change in at least one context for every operation/pin/path.

The common parent contains id, payload, value and tenant_id. Incoming FKs target its stable id. The changed column is value; the external trigger updates audit on a payload update, the external index covers tenant_id, and the view selects id,payload. C8 has a separate ancestor_id cascading FK, so add/drop_foreign_key still changes tenant_id. C3 uses RESTRICT, not a separate NO ACTION variant. Each operation is one migration. add_timestamps explicitly allows NULL; existing rows have distinct non-NULL numeric text values; the type conversion checks their text-normalized values. This does not cover every option, affinity conversion, dependency on a removed column, nested transaction, concurrent write, trigger restore side effect, D1 driver, or framework release.

Content digests use SHA-256 over ordered primary-key projections. Intentional column drops omit only the dropped field; renames map old to new names. New columns are checked structurally. View result rows and compilation are checked, and the trigger is probed under a rolled-back savepoint on both populated and empty databases. FK enforcement is read on the migration connection before it closes, not inferred from an observer connection. SQLite FK/integrity checks remain enabled. Failed-loudly versus partial compares persisted application schema and all application rows, including newly left-over tables; framework bookkeeping is excluded. Intermediate commits with no net application-state change are not classified as partial. No failed migration is classified as silent-loss, even when it leaves damage.

Pins, runtime differences and the PR packages are described in `results/upstream_fixes.md`. Snapshots/raw paths use Python SQLite; Rails and Drizzle use their installed native SQLite versions. The PR pins include their upstream base/head differences and are not patches on current.

The README in the repository root gives the command with the pin labels of each retained run. A run writes to a new output directory, for example `.venv/bin/python -m smp operation-matrix --output results/<new directory>`, and is checked with `.venv/bin/python scripts/validate_operation_matrix.py results/<new directory>/operation_matrix.json`. `--frameworks`, `--operations`, `--contexts`, and `--labels` select subsets. Compact specs and templates live in `smp/matrix_spec.py`; generated fixtures are temporary. Raw rows, snapshots, outcomes and full lint responses are in [operation_matrix.json](operation_matrix.json). Each row links to a compressed JSON archive containing exact traces, runner logs, fixture SQL and its spec; shared per-case/per-pin generation archives retain both Kit migrations, snapshots, journal and prompt logs. Per-trial databases and redundant lint SQL copies are removed after observation; lint input strings reconstruct exactly from fixture SQL plus the retained traces/migration SQL.
