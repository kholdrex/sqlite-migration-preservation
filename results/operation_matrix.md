# SQLite operation preservation matrix

Observed: 2026-10-09T23:29:33.830522+00:00.

2457 populated/empty pairs (4914 executions); 0 infrastructure errors.

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
| drizzle | before | drizzle | 135 | 36 | 14 | 0 | 85 | 68 |
| drizzle | before | raw | 135 | 14 | 0 | 7 | 114 | 68 |
| drizzle | before | raw-tx | 135 | 36 | 14 | 0 | 85 | 68 |
| drizzle | current | drizzle | 135 | 36 | 14 | 0 | 85 | 68 |
| drizzle | current | raw | 135 | 14 | 0 | 7 | 114 | 68 |
| drizzle | current | raw-tx | 135 | 36 | 14 | 0 | 85 | 68 |
| drizzle | drizzle-pr5074 | drizzle | 135 | 21 | 14 | 0 | 100 | 68 |
| drizzle | drizzle-pr5074 | raw | 135 | 14 | 0 | 7 | 114 | 68 |
| drizzle | drizzle-pr5074 | raw-tx | 135 | 21 | 14 | 0 | 100 | 68 |
| drizzle | drizzle-pr5784 | drizzle | 135 | 14 | 7 | 0 | 114 | 68 |
| drizzle | drizzle-pr5784 | raw | 135 | 14 | 0 | 7 | 114 | 68 |
| drizzle | drizzle-pr5784 | raw-tx | 135 | 36 | 14 | 0 | 85 | 68 |
| drizzle | drizzle-pr5784+5074 | drizzle | 135 | 14 | 7 | 0 | 114 | 68 |
| drizzle | drizzle-pr5784+5074 | raw | 135 | 14 | 0 | 7 | 114 | 68 |
| drizzle | drizzle-pr5784+5074 | raw-tx | 135 | 21 | 14 | 0 | 100 | 68 |
| rails | before | rails | 144 | 48 | 0 | 0 | 96 | 108 |
| rails | current | rails | 144 | 48 | 0 | 0 | 96 | 108 |
| rails | rails-pr57128 | rails | 144 | 12 | 0 | 0 | 132 | 108 |

Every selected operation/pin/path successfully applies its intended change in at least one context. No unsupported operations were observed.

## Findings

Across the selected pins and paths, 449 populated pairs silently violate preservation, 126 fail with application state rolled back, 35 fail after partial commit, and 1847 preserve the checked state.

- rails / before, framework path: 48/144 silent-loss cells (C1: 12, C2: 12, C4: 12, C5: 12).
- rails / current, framework path: 48/144 silent-loss cells (C1: 12, C2: 12, C4: 12, C5: 12).
- rails / rails-pr57128, framework path: 12/144 silent-loss cells (C5: 12).
- drizzle / before, framework path: 36/135 silent-loss cells (C1: 7, C2: 7, C4: 8, C5: 7, C6: 7).
- drizzle / current, framework path: 36/135 silent-loss cells (C1: 7, C2: 7, C4: 8, C5: 7, C6: 7).
- drizzle / drizzle-pr5784, framework path: 14/135 silent-loss cells (C5: 7, C6: 7).
- drizzle / drizzle-pr5074, framework path: 21/135 silent-loss cells (C2: 7, C5: 7, C6: 7).
- drizzle / drizzle-pr5784+5074, framework path: 14/135 silent-loss cells (C5: 7, C6: 7).

Drizzle current's rename_table × C4 loses grandchildren: Kit renames the parent and then rebuilds children to update their FK. A native parent rename can therefore trigger a dependent-table rebuild. The retained rename_table × C4 generation archive contains the exact sequence.

Kit #5074 still loses FK values in 7 C2 framework cells while retaining row counts. Its cascade backup does not repair these SET NULL effects. ORM #5784 changes migration connection orchestration; raw and raw-tx bypass that code, so its benefit must be evaluated per execution path.

Parent-view context C7 has 105 failed populated pairs, including 35 with partial commit. Error status alone cannot distinguish those failures from rollback; persisted application state is compared separately.

Empty execution catches 0/449 populated silent-loss cells; checking invariants on those empty trials would catch 246. The empty-db detector intentionally measures execution errors only. Equal row counts miss C2 value losses.

Every silent-loss trial still has its intended change, FK enforcement ON, and clean foreign_key_check and integrity_check results.

## drizzle / current / drizzle

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | silent-loss(D,R)† | preserved | preserved | preserved | preserved† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

## drizzle / current / raw

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | preserved† | preserved | preserved | preserved | preserved† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |

## drizzle / current / raw-tx

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | silent-loss(D,R)† | preserved | preserved | preserved | preserved† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

## drizzle / before / drizzle

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | silent-loss(D,R)† | preserved | preserved | preserved | preserved† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

## drizzle / before / raw

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | preserved† | preserved | preserved | preserved | preserved† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |

## drizzle / before / raw-tx

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | silent-loss(D,R)† | preserved | preserved | preserved | preserved† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

## drizzle / drizzle-pr5074 / drizzle

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | **preserved†** | preserved | preserved | preserved | preserved† |
| set_default | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

## drizzle / drizzle-pr5074 / raw

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | preserved† | preserved | preserved | preserved | preserved† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |

## drizzle / drizzle-pr5074 / raw-tx

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | **preserved†** | preserved | preserved | preserved | preserved† |
| set_default | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

## drizzle / drizzle-pr5784 / drizzle

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | **preserved†** | preserved | preserved | preserved | preserved† |
| set_default | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

## drizzle / drizzle-pr5784 / raw

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | preserved† | preserved | preserved | preserved | preserved† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |

## drizzle / drizzle-pr5784 / raw-tx

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | silent-loss(D,R)† | preserved | preserved | preserved | preserved† |
| set_default | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | silent-loss(D,R)† | silent-loss(D)† | loud† | silent-loss(D,R)† | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

## drizzle / drizzle-pr5784+5074 / drizzle

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | **preserved†** | preserved | preserved | preserved | preserved† |
| set_default | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | **preserved†** | **preserved†** | **preserved†** | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

## drizzle / drizzle-pr5784+5074 / raw

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_foreign_key | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | preserved† | preserved | preserved | preserved | preserved† |
| set_default | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |
| set_not_null | preserved† | preserved† | preserved† | preserved† | preserved† | silent-loss(O,T)† | silent-loss(O)† | loud-partial† | preserved† |

## drizzle / drizzle-pr5784+5074 / raw-tx

| Operation | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|---|
| add_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_foreign_key | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| add_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| add_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| change_type | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_default | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_foreign_key | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_index | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| drop_not_null | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| drop_unique | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_column | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved | preserved |
| rename_table | preserved | preserved† | preserved† | preserved† | **preserved†** | preserved | preserved | preserved | preserved† |
| set_default | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |
| set_not_null | preserved† | **preserved†** | silent-loss(D)† | loud† | **preserved†** | silent-loss(O,T)† | silent-loss(O)† | loud† | preserved† |

## rails / current / rails

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

## rails / before / rails

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

## rails / rails-pr57128 / rails

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

## Detector coverage of every silent-loss cell

Rows group contexts only when the operation, pin, path, violations and detector results are identical. Empty-db means execution error only. Lint warnings are pattern findings, not proof of loss. The unchanged schema-prefixed lint variants are also retained in JSON.

| Framework | Pin | Path | Operation | Contexts | Violations | Empty-db | Exec lint | File lint | Populated invariants |
|---|---|---|---|---|---|---|---|---|---|
| drizzle | before | drizzle | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | drizzle | add_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | drizzle | add_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | drizzle | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | drizzle | change_type | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | drizzle | change_type | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | drizzle | change_type | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | drizzle | change_type | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | drizzle | drop_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | drizzle | drop_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | drizzle | drop_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | drizzle | drop_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | drizzle | drop_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | drizzle | drop_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | drizzle | drop_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | drizzle | drop_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | drizzle | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | drizzle | drop_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | drizzle | drop_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | drizzle | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | drizzle | rename_table | C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | drizzle | set_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | drizzle | set_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | drizzle | set_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | drizzle | set_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | drizzle | set_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | drizzle | set_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | drizzle | set_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | drizzle | set_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | raw | add_foreign_key | C6 | O | — | — | — | yes |
| drizzle | before | raw | add_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | before | raw | change_type | C6 | O | — | — | — | yes |
| drizzle | before | raw | change_type | C5 | O,T | — | — | — | yes |
| drizzle | before | raw | drop_default | C6 | O | — | — | — | yes |
| drizzle | before | raw | drop_default | C5 | O,T | — | — | — | yes |
| drizzle | before | raw | drop_foreign_key | C6 | O | — | — | — | yes |
| drizzle | before | raw | drop_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | before | raw | drop_not_null | C6 | O | — | — | — | yes |
| drizzle | before | raw | drop_not_null | C5 | O,T | — | — | — | yes |
| drizzle | before | raw | set_default | C6 | O | — | — | — | yes |
| drizzle | before | raw | set_default | C5 | O,T | — | — | — | yes |
| drizzle | before | raw | set_not_null | C6 | O | — | — | — | yes |
| drizzle | before | raw | set_not_null | C5 | O,T | — | — | — | yes |
| drizzle | before | raw-tx | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | add_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | add_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | change_type | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | change_type | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | change_type | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | change_type | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | drop_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | drop_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | drop_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | drop_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | drop_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | drop_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | drop_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | drop_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | drop_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | drop_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | rename_table | C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | set_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | set_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | set_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | set_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | set_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | set_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | set_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | before | raw-tx | set_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | drizzle | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | drizzle | add_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | drizzle | add_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | drizzle | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | drizzle | change_type | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | drizzle | change_type | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | drizzle | change_type | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | drizzle | change_type | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | drizzle | drop_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | drizzle | drop_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | drizzle | drop_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | drizzle | drop_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | drizzle | drop_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | drizzle | drop_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | drizzle | drop_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | drizzle | drop_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | drizzle | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | drizzle | drop_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | drizzle | drop_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | drizzle | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | drizzle | rename_table | C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | drizzle | set_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | drizzle | set_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | drizzle | set_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | drizzle | set_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | drizzle | set_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | drizzle | set_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | drizzle | set_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | drizzle | set_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | raw | add_foreign_key | C6 | O | — | — | — | yes |
| drizzle | current | raw | add_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | current | raw | change_type | C6 | O | — | — | — | yes |
| drizzle | current | raw | change_type | C5 | O,T | — | — | — | yes |
| drizzle | current | raw | drop_default | C6 | O | — | — | — | yes |
| drizzle | current | raw | drop_default | C5 | O,T | — | — | — | yes |
| drizzle | current | raw | drop_foreign_key | C6 | O | — | — | — | yes |
| drizzle | current | raw | drop_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | current | raw | drop_not_null | C6 | O | — | — | — | yes |
| drizzle | current | raw | drop_not_null | C5 | O,T | — | — | — | yes |
| drizzle | current | raw | set_default | C6 | O | — | — | — | yes |
| drizzle | current | raw | set_default | C5 | O,T | — | — | — | yes |
| drizzle | current | raw | set_not_null | C6 | O | — | — | — | yes |
| drizzle | current | raw | set_not_null | C5 | O,T | — | — | — | yes |
| drizzle | current | raw-tx | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | add_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | add_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | change_type | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | change_type | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | change_type | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | change_type | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | drop_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | drop_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | drop_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | drop_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | drop_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | drop_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | drop_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | drop_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | drop_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | drop_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | rename_table | C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | set_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | set_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | set_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | set_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | set_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | set_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | set_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | current | raw-tx | set_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | add_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | change_type | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | change_type | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | change_type | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | drop_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | drop_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | drop_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | drop_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | drop_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | drop_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | drop_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | set_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | set_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | set_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | set_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | set_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | drizzle | set_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw | add_foreign_key | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | add_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | change_type | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | change_type | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | drop_default | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | drop_default | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | drop_foreign_key | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | drop_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | drop_not_null | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | drop_not_null | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | set_default | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | set_default | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | set_not_null | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw | set_not_null | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | add_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | change_type | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | change_type | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | change_type | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | drop_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | drop_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | drop_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | drop_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | drop_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | drop_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | drop_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | set_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | set_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | set_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | set_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | set_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5074 | raw-tx | set_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | drizzle | add_foreign_key | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | add_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | change_type | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | change_type | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | drop_default | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | drop_default | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | drop_foreign_key | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | drop_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | drop_not_null | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | drop_not_null | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | set_default | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | set_default | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | set_not_null | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | drizzle | set_not_null | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | add_foreign_key | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | add_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | change_type | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | change_type | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | drop_default | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | drop_default | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | drop_foreign_key | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | drop_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | drop_not_null | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | drop_not_null | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | set_default | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | set_default | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | set_not_null | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw | set_not_null | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | add_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | add_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | change_type | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | change_type | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | change_type | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | change_type | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | drop_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | drop_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | drop_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | drop_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | drop_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | drop_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | drop_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | drop_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | drop_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | drop_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | rename_table | C4 | D,R | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | set_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | set_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | set_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | set_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | set_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | set_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | set_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784 | raw-tx | set_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | add_foreign_key | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | add_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | change_type | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | change_type | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | drop_default | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | drop_default | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | drop_foreign_key | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | drop_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | drop_not_null | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | drop_not_null | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | set_default | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | set_default | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | set_not_null | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | drizzle | set_not_null | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | add_foreign_key | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | add_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | change_type | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | change_type | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | drop_default | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | drop_default | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | drop_foreign_key | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | drop_foreign_key | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | drop_not_null | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | drop_not_null | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | set_default | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | set_default | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | set_not_null | C6 | O | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw | set_not_null | C5 | O,T | — | — | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | add_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | change_type | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | change_type | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | change_type | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | drop_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | drop_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | drop_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | drop_foreign_key | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | drop_foreign_key | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | drop_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | drop_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | set_default | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | set_default | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | set_default | C5 | O,T | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | set_not_null | C2 | D | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | set_not_null | C6 | O | — | SQLD002 | — | yes |
| drizzle | drizzle-pr5784+5074 | raw-tx | set_not_null | C5 | O,T | — | SQLD002 | — | yes |
| rails | before | rails | add_check_constraint | C2 | D | — | SQLD002 | — | yes |
| rails | before | rails | add_check_constraint | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | before | rails | add_check_constraint | C5 | O,T | — | SQLD002 | — | yes |
| rails | before | rails | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| rails | before | rails | add_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | before | rails | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| rails | before | rails | add_reference | C2 | D | — | SQLD002 | — | yes |
| rails | before | rails | add_reference | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | before | rails | add_reference | C5 | O,T | — | SQLD002 | — | yes |
| rails | before | rails | add_timestamps | C2 | D | — | SQLD002 | — | yes |
| rails | before | rails | add_timestamps | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | before | rails | add_timestamps | C5 | O,T | — | SQLD002 | — | yes |
| rails | before | rails | change_default | C2 | D | — | SQLD002 | — | yes |
| rails | before | rails | change_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | before | rails | change_default | C5 | O,T | — | SQLD002 | — | yes |
| rails | before | rails | change_type | C2 | D | — | SQLD002 | — | yes |
| rails | before | rails | change_type | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | before | rails | change_type | C5 | O,T | — | SQLD002 | — | yes |
| rails | before | rails | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| rails | before | rails | drop_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | before | rails | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| rails | before | rails | remove_check_constraint | C2 | D | — | SQLD002 | — | yes |
| rails | before | rails | remove_check_constraint | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | before | rails | remove_check_constraint | C5 | O,T | — | SQLD002 | — | yes |
| rails | before | rails | remove_column | C2 | D | — | SQLD002 | — | yes |
| rails | before | rails | remove_column | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | before | rails | remove_column | C5 | O,T | — | SQLD002 | — | yes |
| rails | before | rails | remove_foreign_key | C2 | D | — | SQLD002 | — | yes |
| rails | before | rails | remove_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | before | rails | remove_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| rails | before | rails | rename_column | C2 | D | — | SQLD002 | — | yes |
| rails | before | rails | rename_column | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | before | rails | rename_column | C5 | O,T | — | SQLD002 | — | yes |
| rails | before | rails | set_not_null | C2 | D | — | SQLD002 | — | yes |
| rails | before | rails | set_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | before | rails | set_not_null | C5 | O,T | — | SQLD002 | — | yes |
| rails | current | rails | add_check_constraint | C2 | D | — | SQLD002 | — | yes |
| rails | current | rails | add_check_constraint | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | current | rails | add_check_constraint | C5 | O,T | — | SQLD002 | — | yes |
| rails | current | rails | add_foreign_key | C2 | D | — | SQLD002 | — | yes |
| rails | current | rails | add_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | current | rails | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| rails | current | rails | add_reference | C2 | D | — | SQLD002 | — | yes |
| rails | current | rails | add_reference | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | current | rails | add_reference | C5 | O,T | — | SQLD002 | — | yes |
| rails | current | rails | add_timestamps | C2 | D | — | SQLD002 | — | yes |
| rails | current | rails | add_timestamps | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | current | rails | add_timestamps | C5 | O,T | — | SQLD002 | — | yes |
| rails | current | rails | change_default | C2 | D | — | SQLD002 | — | yes |
| rails | current | rails | change_default | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | current | rails | change_default | C5 | O,T | — | SQLD002 | — | yes |
| rails | current | rails | change_type | C2 | D | — | SQLD002 | — | yes |
| rails | current | rails | change_type | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | current | rails | change_type | C5 | O,T | — | SQLD002 | — | yes |
| rails | current | rails | drop_not_null | C2 | D | — | SQLD002 | — | yes |
| rails | current | rails | drop_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | current | rails | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| rails | current | rails | remove_check_constraint | C2 | D | — | SQLD002 | — | yes |
| rails | current | rails | remove_check_constraint | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | current | rails | remove_check_constraint | C5 | O,T | — | SQLD002 | — | yes |
| rails | current | rails | remove_column | C2 | D | — | SQLD002 | — | yes |
| rails | current | rails | remove_column | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | current | rails | remove_column | C5 | O,T | — | SQLD002 | — | yes |
| rails | current | rails | remove_foreign_key | C2 | D | — | SQLD002 | — | yes |
| rails | current | rails | remove_foreign_key | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | current | rails | remove_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| rails | current | rails | rename_column | C2 | D | — | SQLD002 | — | yes |
| rails | current | rails | rename_column | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | current | rails | rename_column | C5 | O,T | — | SQLD002 | — | yes |
| rails | current | rails | set_not_null | C2 | D | — | SQLD002 | — | yes |
| rails | current | rails | set_not_null | C1,C4 | D,R | — | SQLD002 | — | yes |
| rails | current | rails | set_not_null | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-pr57128 | rails | add_check_constraint | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-pr57128 | rails | add_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-pr57128 | rails | add_reference | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-pr57128 | rails | add_timestamps | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-pr57128 | rails | change_default | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-pr57128 | rails | change_type | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-pr57128 | rails | drop_not_null | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-pr57128 | rails | remove_check_constraint | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-pr57128 | rails | remove_column | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-pr57128 | rails | remove_foreign_key | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-pr57128 | rails | rename_column | C5 | O,T | — | SQLD002 | — | yes |
| rails | rails-pr57128 | rails | set_not_null | C5 | O,T | — | SQLD002 | — | yes |

## Scope, interpretation, and reproduction

All listed operations are attempted through the installed framework DSL or real Kit schema diff and generate command. Rename prompts select the single old column/table; generated migration SQL is never edited. No execution failure is automatically labeled unsupported. The operation names set/drop_not_null map to Rails change_column_null(false/true); change_type maps to Rails change_column(:integer). The complete-matrix validator requires successful execution with the intended change in at least one context for every operation/pin/path.

The common parent contains id, payload, value and tenant_id. Incoming FKs target its stable id. The changed column is value; the external trigger updates audit on a payload update, the external index covers tenant_id, and the view selects id,payload. C8 has a separate ancestor_id cascading FK, so add/drop_foreign_key still changes tenant_id. C3 uses RESTRICT, not a separate NO ACTION variant. Each operation is one migration. add_timestamps explicitly allows NULL; existing rows have distinct non-NULL numeric text values; the type conversion checks their text-normalized values. This does not cover every option, affinity conversion, dependency on a removed column, nested transaction, concurrent write, trigger restore side effect, D1 driver, or framework release.

Content digests use SHA-256 over ordered primary-key projections. Intentional column drops omit only the dropped field; renames map old to new names. New columns are checked structurally. View result rows and compilation are checked, and the trigger is probed under a rolled-back savepoint on both populated and empty databases. FK enforcement is read on the migration connection before it closes, not inferred from an observer connection. SQLite FK/integrity checks remain enabled. Failed-loudly versus partial compares persisted application schema and all application rows, including newly left-over tables; framework bookkeeping is excluded. Intermediate commits with no net application-state change are not classified as partial. No failed migration is classified as silent-loss, even when it leaves damage.

Pins, runtime differences and the PR packages are described in `results/upstream_fixes.md`. Snapshots/raw paths use Python SQLite; Rails and Drizzle use their installed native SQLite versions. The PR pins include their upstream base/head differences and are not patches on current.

The README in the repository root gives the command with the pin labels of each retained run. A run writes to a new output directory, for example `.venv/bin/python -m smp operation-matrix --output results/<new directory>`, and is checked with `.venv/bin/python scripts/validate_operation_matrix.py results/<new directory>/operation_matrix.json`. `--frameworks`, `--operations`, `--contexts`, and `--labels` select subsets. Compact specs and templates live in `smp/matrix_spec.py`; generated fixtures are temporary. Raw rows, snapshots, outcomes and full lint responses are in [operation_matrix.json](operation_matrix.json). Each row links to a compressed JSON archive containing exact traces, runner logs, fixture SQL and its spec; shared per-case/per-pin generation archives retain both Kit migrations, snapshots, journal and prompt logs. Per-trial databases and redundant lint SQL copies are removed after observation; lint input strings reconstruct exactly from fixture SQL plus the retained traces/migration SQL.
