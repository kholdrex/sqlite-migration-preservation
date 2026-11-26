# Repetition of 1 November 2026

Rails `current` (ActiveRecord 8.1.4) and Drizzle `current` (ORM 0.45.4, Kit 0.31.11) were run again, and Drizzle
1.0.0-rc.5 (ORM and Kit, label `v1-rc5`) was added. All runs use the fixtures of the operation matrix.

- Rails 8.1.4: all 144 pairs agree with `results/operation_matrix.json` in populated outcome, empty outcome, rebuild
  flag and kinds of violation (48 silent loss).
- Drizzle 0.45.4: all 405 pairs agree with `results/operation_matrix.json` in the same fields.
- Drizzle 1.0.0-rc.5, migrator path: 40 of 126 pairs are silent loss, in 8 of 14 operations; none of them fails on
  the empty database. The migrator still issues `PRAGMA foreign_keys=OFF` inside its `BEGIN`.
  - `add_unique` rebuilds the parent table (Kit 1.0 emits an inline `UNIQUE` constraint), so it moves from
    preserved to silent loss in C1, C2 and C4–C6.
  - `rename_table` in C4 no longer rebuilds and is preserved.
- `drop_unique` on 1.0.0-rc.5 is left out of these counts: Kit 1.0 writes the starting schema with an inline
  constraint, while the fixture database has a named unique index, so the starting state is not one Kit 1.0 would
  produce. The nine cells were run and are in the result file; the validator accepts this one difference for them
  and reports it as `starting_schemas_with_inline_unique`.

The commands are in the experiment index of the README in the repository root. To check the retained files:

```sh
.venv/bin/python scripts/validate_operation_matrix.py results/rerun-2026-11-01/rails-current/operation_matrix.json --subset
.venv/bin/python scripts/validate_operation_matrix.py results/rerun-2026-11-01/drizzle/operation_matrix.json --subset
```
