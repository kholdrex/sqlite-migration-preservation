# Oracle validation: method

This file describes the controls in `results/oracle_validation/` and
`results/reanalysis-2026-11-21/oracle_validation/`. Both `controls.json` files
record the SHA-256 of an earlier text of this protocol; that text is not part
of this package.

## Controls

The controls test the preservation checker (`smp/checks.py`,
`smp/preservation.py`) that classified the matrix results. They run on
Python's `sqlite3` module with the fixtures of `smp.matrix_spec.fixture`, not
through an ORM. The operations are the union of the Rails and Drizzle
operations and `smp.orm_spec.OPERATIONS`.

Safe controls apply every operation in all nine contexts to a populated and
to an empty database. Where SQLite needs a rebuild, the control uses the
create, copy, drop, rename sequence with foreign keys disabled before `BEGIN`,
indexes, triggers and views restored, checks before `COMMIT` and enforcement
restored afterwards. Each context also has a safe add-column rebuild.

Lossy controls complete an add-column operation and then inject one fault:
delete one child row, set one child foreign key to NULL, overwrite one non-key
value, drop a trigger, drop an index, change a foreign-key delete action, drop
a view, leave enforcement disabled, leave a dangling foreign key, or change a
trigger body. Each uses the smallest context that contains the object. One
fault can violate several invariants and still counts as one trial.

Two further lossy controls were built to show what the checker does not cover:
an unintended default on an existing column (table SQL is not compared in
general), and an overwritten value in an added table without an `id` column.
That table also has a safe control, as does a table with a unique `id` and no
declared primary key. These are reported under a separate scope.

## Ground truth

The expected label of a control comes from the declared transformation and
from direct SQL reads of schema, rows, columns, foreign keys and the PRAGMA
values of the migrating connection, not from the checker. For safe controls
the copied rows are compared with the original rows; only the intended
projection, rename, added nullable column or integer conversion may differ. A
control whose setup or ground-truth assertion fails stops the run.

Every control runs on a fresh populated and a fresh empty fixture. An `UPDATE`
or `DELETE` fault on an empty fixture changes nothing and is a safe trial;
schema and connection faults are lossy on both. Enforcement is read on the
connection that executed the migration.

The checker is applied as in the matrix: `preservation.observe` before and
after, `probe_constraint`, then `violations` and `classify`. A lossy control is
detected when its successful execution is classified `silent-loss`.

## Reported counts

`summary.md` gives true and false positives and negatives overall, by
population and by kind of control, every missed or falsely flagged control
with its cause, and the false alarms on populated safe controls per operation.
`controls.json` holds the SQL, the observations and the findings of every
trial, so the classification can be recomputed.
`results/oracle_validation/expected_state.md` states what the checker of the
first run compares for each operation; the corrected checker differs from it
in the two points below.

The first run (`results/oracle_validation/`) used the checker that produced
the matrix results: 16 of 19 lossy trials detected, no false alarm in 441 safe
trials. That checker ordered every table by `id` and treated two unreadable
tables as equal. The run of 21 November 2026
(`results/reanalysis-2026-11-21/oracle_validation/`) used the corrected checker,
which orders a table without `id` by its rows and reports an unreadable table
as a violation (`PROTOCOL_reanalysis.md`): 17 of 19, no false alarm in 441.
`scripts/oracle_validation.py` runs the corrected checker and, with
`--recorded-checker`, the earlier one.
