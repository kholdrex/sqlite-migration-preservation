# Oracle validation results

Python 3.11.5; SQLite 3.41.2.

460 successful raw sqlite3 executions: 230 controls, each populated and empty. 23 operation names × 9 contexts, plus safe rebuilds and fault/scope controls.

TP 16/19 lossy trials; FN 3/19; TN 441/441 safe trials; FP 0/441.

| Population | TP | FN | TN | FP |
|---|---:|---:|---:|---:|
| empty | 6 | 1 | 223 | 0 |
| populated | 10 | 2 | 218 | 0 |

| Control / violation kind | TP | FN | TN | FP |
|---|---:|---:|---:|---:|
| change_fk_action | 2 | 0 | 0 | 0 |
| change_trigger_body | 2 | 0 | 0 | 0 |
| dangling_reference | 1 | 0 | 1 | 0 |
| delete_child | 1 | 0 | 1 | 0 |
| disable_enforcement | 2 | 0 | 0 | 0 |
| drop_index | 2 | 0 | 0 | 0 |
| drop_trigger | 2 | 0 | 0 | 0 |
| drop_view | 2 | 0 | 0 | 0 |
| heap_overwrite | 0 | 1 | 1 | 0 |
| intended_change | 0 | 0 | 414 | 0 |
| null_fk | 1 | 0 | 1 | 0 |
| overwrite_value | 1 | 0 | 1 | 0 |
| safe_heap | 0 | 0 | 2 | 0 |
| safe_heap_id | 0 | 0 | 2 | 0 |
| safe_rebuild | 0 | 0 | 18 | 0 |
| unintended_default | 0 | 2 | 0 | 0 |

| Scope | TP | FN | TN | FP |
|---|---:|---:|---:|---:|
| derived | 0 | 0 | 4 | 0 |
| limitation | 0 | 3 | 1 | 0 |
| matrix | 16 | 0 | 436 | 0 |

Populated intended-change false alarms: **0/207**. Each operation below has all nine contexts; aliases remain separate operation names.

| Operation | Populated false alarms / safe trials |
|---|---:|
| add_column | 0 / 9 |
| add_index | 0 / 9 |
| remove_column | 0 / 9 |
| rename_column | 0 / 9 |
| change_type | 0 / 9 |
| set_not_null | 0 / 9 |
| drop_not_null | 0 / 9 |
| change_default | 0 / 9 |
| add_foreign_key | 0 / 9 |
| remove_foreign_key | 0 / 9 |
| add_reference | 0 / 9 |
| add_timestamps | 0 / 9 |
| add_check_constraint | 0 / 9 |
| remove_check_constraint | 0 / 9 |
| rename_table | 0 / 9 |
| remove_index | 0 / 9 |
| drop_column | 0 / 9 |
| set_default | 0 / 9 |
| drop_default | 0 / 9 |
| drop_foreign_key | 0 / 9 |
| add_unique | 0 / 9 |
| drop_unique | 0 / 9 |
| drop_index | 0 / 9 |

Empty mutation no-ops: 5; included as TN, not FN. Each injected fault is one trial even when multiple invariants fire.

## Every FP and FN

- FN: `unintended_default` (populated): Existing payload default changed. Table SQL/defaults outside the declared target are not compared on success; state_digest is used only for failed executions.
- FN: `unintended_default` (empty): Existing payload default changed. Table SQL/defaults outside the declared target are not compared on success; state_digest is used only for failed executions.
- FN: `heap_overwrite` (populated): The heap lacks id. Both content reads fail at ORDER BY id; missing digests compare equal, and content errors are not promoted to findings. Row count is unchanged.
- No false positives.

## Scope and open problems

Content observation errors occur in 4/460 trials (derived heaps without id). The oracle does not promote those errors to findings. The safe heap controls therefore do not validate arbitrary no-primary-key tables. A heap with unique id values can be ordered, but uniqueness is not verified by the observer.

Changed trigger SQL is detected, including on an empty database. The limitation controls cover column defaults outside the declared target and failed content observations. Trigger probes cover one payload update, not all behavior. Integrity corruption, arbitrary type conversions, dependent-column renames, and framework-specific migration execution are outside these controls.

These are deterministic seeded controls, not estimates of real-world error prevalence. The operation union shares fixture SQL across frameworks and does not multiply equivalent raw controls by framework name. Main counts include limitations; scope-specific counts are retained in controls.json.

## Checker version

This run used the checker that produced the matrix results. The checker was later corrected to compare tables
without an id column by their rows and to report a failed content read
([re-analysis of 21 November 2026](../reanalysis-2026-11-21/README.md)); `scripts/oracle_validation.py` now
runs the corrected checker.

The rebuild implementation follows SQLite's [generalized ALTER TABLE procedure](https://www.sqlite.org/lang_altertable.html#otheralter). Views are saved and dropped before replacing their referenced table, then recreated before validation.

See expected_state.md for the code-derived contract, and controls.json for source hashes, full observations, direct ground truth, executed SQL, per-control verdicts, and grouped counts.
