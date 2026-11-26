# Rails base-commit control: method

This file describes the runs in `results/rails_base/`.

## Design

The Rails pull requests were first run at their heads and compared with Rails
8.1.4, which differs from each head by more than the pull request and ran on
another Ruby version. This control runs the base commit recorded for each pull
request. The bases and heads are the ones in `sources/upstream_fixes.json`,
not the current branch tips:

| PR | Base commit | PR head |
|---|---|---|
| #57128 | b8725ee9a90988129738197fecdb3eacb8b2e138 | 8823c1370c7bc8910e609d1b6f27f4fc34f3d81d |
| #58709 | bd885faee983c6986da1919d96ee6f671a35164c | 428884a88b3a42c914f5227819b6b672325b3312 |
| #56811 | 704aa9785156f3b52f825b8c4dae8460e669bc97 | 7ddc17783418454c0e406181ae442d0aaf558ad8 |

#57128 and #58709 are ahead of their recorded base and not behind it. #56811
is one commit ahead of and two commits behind its recorded base; its branch
point is 3faf056f240966b268dd6fa52c559e241a370d06, and the two commits it lacks
change only a PostgreSQL test file.

Each base runs the Rails operation matrix (16 operations, contexts C0–C8,
populated and empty: 288 executions) and the eight atomicity scenarios in
context C1 on a populated database. The scenarios cross migration transactions
enabled or disabled, a data or schema change before the rebuild, and a failure
by explicit exception or by a NOT NULL violation. The final state is read from
a new connection. Three bases give 432 matrix pairs (864 executions) and 24
atomicity executions.

## Builds

Every base is installed from Git by its full commit hash, with Ruby 3.4.3 and
sqlite3 gem 2.9.6, starting from the lockfile of the corresponding pull-request
pin so that dependency versions match where they can. The run checks the
resolved revision, the Ruby version and the hash of the loaded SQLite adapter.
Gemfiles and lockfiles are in `results/rails_base/builds/`, the lockfiles of
the pull-request pins in `results/rails_base/comparators/`, and the loaded
adapter sources in `results/rails_base/source/`.

## Comparison

Each base is compared with the results recorded for its pull request in
`results/rails_fixes.json` (including `comparison_rows`) and
`results/rails_atomicity.json`; the pull-request pins are not run again.
Invariants and outcome classes are those of the operation matrix. The two
locally merged pins are compared with the base of their first parent. They
combine two branches, so that comparison describes the merge and does not
isolate either patch.

`summary.md` reports the outcome counts for each population, every
operation and context with its invariant codes and rebuild flag, the cells
where a head fixes or keeps a loss or introduces one, and each atomicity
scenario with its rollback class, surviving changes and child-row counts.
Partial commits with migration transactions disabled are expected. A run is
rejected when a cell is missing or duplicated, an execution fails for an
infrastructure reason, the Ruby version, revision or source hash differs, or
a scenario does not reach its injected failure. Differences in loaded
dependency versions between a base and a head are listed in `comparison.json`.
