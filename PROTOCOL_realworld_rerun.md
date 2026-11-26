# Replay with full evidence: method

This file describes the run in `results/realworld-rerun-2026-11-02/`.
`realworld.json` there records the SHA-256 of an earlier text of this protocol;
that text is not part of this package.

## Design

The first replay kept outcomes and findings but no traces or full snapshots.
On 2 November 2026 its 93 attempts were run again, in the recorded order, with
`--pins results/realworld.json`: repository commits, migration files, resolved
Drizzle versions, version fallbacks and the number of synthetic rows per table
are taken from the first run. The candidate list and the probe file must have
the hashes recorded there. No repository is added and the stopping rule of the
first run is not applied again. Seeding, history validation, the reference
execution and outcome classification are those of the first run. A history
that cannot be replayed stays a failed attempt, with the stage and reason.

For each executed path (drizzle, raw, raw-tx) the evidence holds the SQLite
trace callbacks in order, including framework PRAGMAs, transaction boundaries,
bookkeeping and project SQL. The callback reports statements SQLite starts to
execute, including failing ones and repeats caused by triggers and foreign
keys; a statement rejected during preparation can be absent. The statements
the migrator submitted are therefore kept separately, with their position in
the migration file. A submitted statement is taken to be a project statement
when its text equals a statement of the project's migrations, so a statement
the migrator issues itself is attributed to the project if a migration
contains the same text. In this run the position recorded was that of the
first equal statement in the whole history, which is an earlier migration for
91 of the 580 submitted project statements; the re-analysis of 21 November
2026 gives the corrected positions (`PROTOCOL_reanalysis.md`). For the Drizzle path the harness creates the
migrator's journal table and marks the earlier migrations as applied, takes
the snapshot before, and then starts the migrator; the snapshot after is taken
once the connection has closed. A snapshot holds every `sqlite_schema` entry and every
row of every table, including internal and migrator tables, generated columns
and BLOBs (as hexadecimal), with rows in a fixed order. Snapshots use their
own connections and are not part of the trace. Setup and reference executions
are kept apart from the target paths.

Full evidence is written to the directory given by `--evidence-dir`, which is
not published; the publishable files go to the output directory.

## Comparison with the first run

Attempts are joined by repository and migration file. The comparison covers
status, qualification, control status, seed counts, rebuilt tables,
dependents, reference counts, path outcomes, findings and row counts after the
migration, the lost tables and missing rows of row-count findings, the
content-digest findings, and all aggregate replay counts of the paper. The
first run kept no snapshots, so rows can be compared only where a finding
recorded them. `comparison.json` holds, for every attempt, the fields that
differ (none in this run) and its loss summary, with differences in runtime
versions listed separately from differences in outcomes, and under
`paper_counts` the 152 paper quantities of both runs. The compared fields are those of `compare_results()` in
`smp/realworld_evidence.py`.

## Published and redacted evidence

Project SQL and schema are published in full only for repositories whose
recorded licence label is MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause or ISC
and whose licence files are present at the pinned commit. The label is the one
recorded when the repository was collected. For all other repositories,
project SQL and schema entries derived from it are replaced by SHA-256 values
and source positions in the pinned files: zero-based UTF-8 byte offsets (end
exclusive), one-based line numbers and statement ordinals. A redacted schema
entry carries the hash of the entry as SQLite stores it and refers to one list
of all `CREATE`, `ALTER` and `DROP` statements of the history; the statements
that produced a particular entry are not singled out. Project SQL is also
removed from event lists and error messages. A statement whose source cannot
be located stops publication. Framework SQL and synthetic rows are published
unchanged.

`scripts/rebuild_realworld_evidence.py` fetches a pinned commit and repeats
the migration with the same seed to produce the full evidence again;
timestamps differ.
