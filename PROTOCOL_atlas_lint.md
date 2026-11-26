# Atlas baseline: method

This file describes how the Atlas comparison in `results/atlas_lint/` was made.
`report.json` there records the SHA-256 of an earlier text of this protocol;
that text is not part of this package.

## Tool

Atlas migration analysis (`atlas migrate lint`) was run from the official
Docker image only, never from an Atlas binary installed on the host. The image
is pinned by digest in `scripts/atlas_lint.py`; its tag, image ID, architecture
and version output are in `results/atlas_lint/supporting.json.gz`. Only the
analyzers available without an Atlas account were used. The image was chosen
by two controls that do not involve study cells: a migration that drops a
table has to be flagged and a migration that adds a table must not be.

Atlas documentation used: [Docker images](https://atlasgo.io/guides/atlas-in-docker),
[Community edition](https://atlasgo.io/community-edition),
[lint command](https://atlasgo.io/versioned/lint),
[analyzers and the transaction directive](https://atlasgo.io/lint/analyzers).

## Cells and inputs

The cells come from `results/operation_matrix.json`, `results/rails_fixes.json`
and `results/orm_matrix.json` with the Current selection of
`scripts/paper_numbers.py`: native paths of `current`, `django-current`,
`prisma-stable` and Alembic `auto` (`rails_fixes.json` contributes no row).
Two groups are analysed, by the outcome on the populated database:

1. all 215 silent-loss cells;
2. all 264 preserved or rolled-back cells with a rebuild (`rebuild=true`, or
   `rebuild=null` and `planned_rebuild=true`). Cells that fail and leave partial
   changes and cells without a rebuild are left out.

Each cell has the four inputs of `scripts/relint.py` (`migration_only`,
`schema_and_migration`, `executed`, `schema_and_executed`), 1,916 inputs in
total. A cell without a runtime trace has no `executed` inputs (37 silent-loss
and 60 safe cells); these are unavailable.

Atlas replays a migration directory against an empty SQLite database. For the
inputs with schema, the starting schema is file `1_schema.sql` and the
migration or trace is `2_target.sql`, and only the last file is analysed
(`--latest 1`), so the existing tables count as earlier history and not as
tables created by the migration under review. Inputs without schema consist of
`2_target.sql` alone. No rows are supplied. Checksums are written by
`atlas migrate hash`; lint runs with `--dev-url sqlite://file?mode=memory`,
JSON output and the default analyzers, in a separate directory per input.

## Retry and unavailable inputs

An input is first submitted unchanged. If it is unavailable and either Atlas
reports a transaction error or the SQL contains `BEGIN`, `COMMIT`, `ROLLBACK`,
`SAVEPOINT` or `RELEASE`, it is submitted once more with the file directive
`-- atlas:txmode none`, which changes how Atlas wraps the file and leaves the
SQL as it is. Nothing else is changed: no statement is removed, repaired or
completed. In the retained run 647 inputs were retried (431 after a missing
table, 216 after another analysis error) and none became available. An input that Atlas cannot replay or parse (unsupported syntax,
repeated callback statements, missing tables, timeouts) is unavailable, with
the reason recorded, and is never counted as clean.

## Classification

- **Available**: Atlas completes the analysis of `2_target.sql` and returns a
  well-formed report without a replay, parse or infrastructure error. A
  non-zero exit status caused only by diagnostics is available.
- **Flagged**: at least one analyzer diagnostic for `2_target.sql`, of any
  severity or kind. Exit status, schema diffs, echoed SQL and errors do not
  count.
- **Names the lost dependent**: the message of a diagnostic names a trigger,
  index or view that the cell lost or changed, or the child table that lost
  rows or values through a `CASCADE`, `SET NULL` or `SET DEFAULT` reference to
  the rebuilt parent. The message must contain the typed identifier (for
  example `table "children"`) and one of the terms drop, delete, loss, lost,
  remove, cascade, null, change, modify, rename, break. Identifiers are
  compared exactly and case-insensitively. A warning that names only the
  rebuilt parent does not count.
- **False alarm**: a flagged, available cell of group 2, counted once per cell
  and input. Rolled-back cells are also reported separately.
- **Unavailable**: `available=false`, `flagged=null`, `names_lost_dependent=null`.

## Reported counts

For each input, detections and named dependents are reported over all 215
silent-loss cells, with the numbers analysed, clean and unavailable. False
alarms are reported over the paper's denominators (264 cells for migration
inputs, 204 for executed inputs), over all 264 cells and over the cells Atlas
analysed. `summary.md` also gives the counts by framework and the reasons for
unavailable inputs.
