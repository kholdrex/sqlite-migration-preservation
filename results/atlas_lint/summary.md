# Atlas RQ2 baseline

Image: `arigaio/atlas@sha256:dc27586a3d1097ff47e90124f13cbed884a27026c374a82e523699645a6d5d57`.

atlas community version v1.3.1-f851298-canary

479 cells; 1916 input slots. Counts are per populated cell and input. Unavailable inputs are not clean.

The starting schema is prior migration history for schema-context inputs; only the target file is analyzed. No schema is added to context-free inputs.

## Overall

Silent loss:

| Input | Flagged / paper denominator | Flagged / all | Names dependent / all | Analyzed | Clean | Unavailable | Flagged / analyzed |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| migration_only | 0/215 | 0/215 | 0/215 | 0 | 0 | 215 | N/A (0 analyzed) |
| executed | 0/178 | 0/215 | 0/215 | 0 | 0 | 215 | N/A (0 analyzed) |
| schema_and_migration | 215/215 | 215/215 | 0/215 | 215 | 0 | 0 | 215/215 |
| schema_and_executed | 64/178 | 64/215 | 0/215 | 64 | 0 | 151 | 64/64 |

Preserved or rolled-back rebuilding cells:

| Input | Flags / paper denominator | Flags / all rebuilds | Flags / analyzed | Clean | Unavailable | Loud flags |
| --- | --- | --- | --- | ---: | ---: | ---: |
| migration_only | 0/264 | 0/264 | N/A (0 analyzed) | 0 | 264 | 0 |
| executed | 0/204 | 0/264 | N/A (0 analyzed) | 0 | 264 | 0 |
| schema_and_migration | 245/264 | 245/264 | 245/245 | 0 | 19 | 7 |
| schema_and_executed | 53/204 | 53/264 | 53/53 | 0 | 211 | 7 |

## alembic

Silent loss:

| Input | Flagged / paper denominator | Flagged / all | Names dependent / all | Analyzed | Clean | Unavailable | Flagged / analyzed |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| migration_only | 0/70 | 0/70 | 0/70 | 0 | 0 | 70 | N/A (0 analyzed) |
| executed | 0/70 | 0/70 | 0/70 | 0 | 0 | 70 | N/A (0 analyzed) |
| schema_and_migration | 70/70 | 70/70 | 0/70 | 70 | 0 | 0 | 70/70 |
| schema_and_executed | 28/70 | 28/70 | 0/70 | 28 | 0 | 42 | 28/28 |

Preserved or rolled-back rebuilding cells:

| Input | Flags / paper denominator | Flags / all rebuilds | Flags / analyzed | Clean | Unavailable | Loud flags |
| --- | --- | --- | --- | ---: | ---: | ---: |
| migration_only | 0/28 | 0/28 | N/A (0 analyzed) | 0 | 28 | 0 |
| executed | 0/28 | 0/28 | N/A (0 analyzed) | 0 | 28 | 0 |
| schema_and_migration | 28/28 | 28/28 | 28/28 | 0 | 0 | 0 |
| schema_and_executed | 28/28 | 28/28 | 28/28 | 0 | 0 | 0 |

## django

Silent loss:

| Input | Flagged / paper denominator | Flagged / all | Names dependent / all | Analyzed | Clean | Unavailable | Flagged / analyzed |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| migration_only | 0/24 | 0/24 | 0/24 | 0 | 0 | 24 | N/A (0 analyzed) |
| executed | 0/24 | 0/24 | 0/24 | 0 | 0 | 24 | N/A (0 analyzed) |
| schema_and_migration | 24/24 | 24/24 | 0/24 | 24 | 0 | 0 | 24/24 |
| schema_and_executed | 0/24 | 0/24 | 0/24 | 0 | 0 | 24 | N/A (0 analyzed) |

Preserved or rolled-back rebuilding cells:

| Input | Flags / paper denominator | Flags / all rebuilds | Flags / analyzed | Clean | Unavailable | Loud flags |
| --- | --- | --- | --- | ---: | ---: | ---: |
| migration_only | 0/84 | 0/84 | N/A (0 analyzed) | 0 | 84 | 0 |
| executed | 0/84 | 0/84 | N/A (0 analyzed) | 0 | 84 | 0 |
| schema_and_migration | 72/84 | 72/84 | 72/72 | 0 | 12 | 0 |
| schema_and_executed | 0/84 | 0/84 | N/A (0 analyzed) | 0 | 84 | 0 |

## drizzle

Silent loss:

| Input | Flagged / paper denominator | Flagged / all | Names dependent / all | Analyzed | Clean | Unavailable | Flagged / analyzed |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| migration_only | 0/36 | 0/36 | 0/36 | 0 | 0 | 36 | N/A (0 analyzed) |
| executed | 0/36 | 0/36 | 0/36 | 0 | 0 | 36 | N/A (0 analyzed) |
| schema_and_migration | 36/36 | 36/36 | 0/36 | 36 | 0 | 0 | 36/36 |
| schema_and_executed | 36/36 | 36/36 | 0/36 | 36 | 0 | 0 | 36/36 |

Preserved or rolled-back rebuilding cells:

| Input | Flags / paper denominator | Flags / all rebuilds | Flags / analyzed | Clean | Unavailable | Loud flags |
| --- | --- | --- | --- | ---: | ---: | ---: |
| migration_only | 0/32 | 0/32 | N/A (0 analyzed) | 0 | 32 | 0 |
| executed | 0/32 | 0/32 | N/A (0 analyzed) | 0 | 32 | 0 |
| schema_and_migration | 25/32 | 25/32 | 25/25 | 0 | 7 | 7 |
| schema_and_executed | 25/32 | 25/32 | 25/25 | 0 | 7 | 7 |

## prisma

Silent loss:

| Input | Flagged / paper denominator | Flagged / all | Names dependent / all | Analyzed | Clean | Unavailable | Flagged / analyzed |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| migration_only | 0/37 | 0/37 | 0/37 | 0 | 0 | 37 | N/A (0 analyzed) |
| executed | N/A (0 analyzed) | 0/37 | 0/37 | 0 | 0 | 37 | N/A (0 analyzed) |
| schema_and_migration | 37/37 | 37/37 | 0/37 | 37 | 0 | 0 | 37/37 |
| schema_and_executed | N/A (0 analyzed) | 0/37 | 0/37 | 0 | 0 | 37 | N/A (0 analyzed) |

Preserved or rolled-back rebuilding cells:

| Input | Flags / paper denominator | Flags / all rebuilds | Flags / analyzed | Clean | Unavailable | Loud flags |
| --- | --- | --- | --- | ---: | ---: | ---: |
| migration_only | 0/60 | 0/60 | N/A (0 analyzed) | 0 | 60 | 0 |
| executed | N/A (0 analyzed) | 0/60 | N/A (0 analyzed) | 0 | 60 | 0 |
| schema_and_migration | 60/60 | 60/60 | 60/60 | 0 | 0 | 0 |
| schema_and_executed | N/A (0 analyzed) | 0/60 | N/A (0 analyzed) | 0 | 60 | 0 |

## rails

Silent loss:

| Input | Flagged / paper denominator | Flagged / all | Names dependent / all | Analyzed | Clean | Unavailable | Flagged / analyzed |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| migration_only | 0/48 | 0/48 | 0/48 | 0 | 0 | 48 | N/A (0 analyzed) |
| executed | 0/48 | 0/48 | 0/48 | 0 | 0 | 48 | N/A (0 analyzed) |
| schema_and_migration | 48/48 | 48/48 | 0/48 | 48 | 0 | 0 | 48/48 |
| schema_and_executed | 0/48 | 0/48 | 0/48 | 0 | 0 | 48 | N/A (0 analyzed) |

Preserved or rolled-back rebuilding cells:

| Input | Flags / paper denominator | Flags / all rebuilds | Flags / analyzed | Clean | Unavailable | Loud flags |
| --- | --- | --- | --- | ---: | ---: | ---: |
| migration_only | 0/60 | 0/60 | N/A (0 analyzed) | 0 | 60 | 0 |
| executed | 0/60 | 0/60 | N/A (0 analyzed) | 0 | 60 | 0 |
| schema_and_migration | 60/60 | 60/60 | 60/60 | 0 | 0 | 0 |
| schema_and_executed | 0/60 | 0/60 | N/A (0 analyzed) | 0 | 60 | 0 |

## Unavailability

| Cohort | Input | Reason | Cells |
| --- | --- | --- | ---: |
| silent | migration_only | analysis_error | 4 |
| silent | migration_only | missing_table | 211 |
| silent | executed | analysis_error | 48 |
| silent | executed | missing_table | 130 |
| silent | executed | missing_trace | 37 |
| silent | schema_and_executed | analysis_error | 48 |
| silent | schema_and_executed | missing_table | 66 |
| silent | schema_and_executed | missing_trace | 37 |
| safe_rebuild | migration_only | missing_table | 264 |
| safe_rebuild | executed | analysis_error | 60 |
| safe_rebuild | executed | missing_table | 144 |
| safe_rebuild | executed | missing_trace | 60 |
| safe_rebuild | schema_and_migration | missing_table | 19 |
| safe_rebuild | schema_and_executed | analysis_error | 60 |
| safe_rebuild | schema_and_executed | missing_table | 91 |
| safe_rebuild | schema_and_executed | missing_trace | 60 |

Diagnostics on analyzed inputs: CD101: 12, DS102: 595, DS103: 16, LT101: 100.

The paper's available-input denominators are 215 silent / 264 safe cells for migration inputs and 178 silent / 204 safe cells for executed inputs. The full cohorts remain 215 and 264. Atlas failures remain in both relevant cohort totals; only the conditional analyzed denominator excludes them.

`analysis_error` includes unbound query parameters in retained Rails traces and other replay errors. Exact error messages, including statement text, are retained in each input's `diagnostics.jsonl.gz` record.

## Limitations

On the pinned image the table-drop control was flagged and the added-table control was not. 647 inputs were retried with the transaction directive; 0 of them could then be analysed.

The image identifies itself as a canary Community build. Its exact digest and platform are retained; the results do not characterize licensed Atlas Pro or other releases. The current Community documentation lists lint as unavailable, whereas the retained image demonstrably runs it. [Edition documentation](https://atlasgo.io/community-edition).

Atlas must replay SQL on an empty dev database. Context-free failures therefore measure input compatibility, not absence of migration risk. The schema-only dev database has no application rows. Repeated callback trace statements and incomplete rolled-back traces are preserved; replay failures remain unavailable. The transaction directive is the only retry. [Lint workflow](https://atlasgo.io/versioned/lint), [transaction directive](https://atlasgo.io/lint/analyzers).

A general diagnostic counts as flagged even if it concerns an intended column drop or rename. Only diagnostic messages matching an observed dependent count as naming the loss. False alarms use the paper's preservation endpoint, not a claim that the warning is wrong about every possible deployment risk. Rates over analyzed inputs have selection bias; counts over full denominators are observed flags, not estimates for unavailable inputs.

## Reproduction and evidence

```sh
.venv/bin/python -B scripts/atlas_lint.py --output results/atlas_lint/reproduction
```

The runner pulls only the pinned digest if absent, repeats both controls, hashes retained sources, and writes raw command output and decisions in `diagnostics.jsonl.gz` and `inputs.jsonl.gz`. `report.json` contains all decisions, source/archive hashes, image inspection, tool version, protocol/script hashes, totals, and framework breakdowns. Existing sources are checked again after the run. `supporting.json.gz` holds the files of the two controls; in the retained run it also holds the image discovery.
