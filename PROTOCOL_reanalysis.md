# Re-analysis of retained evidence, 21 November 2026

On 21 November 2026 four defects were corrected in the code that records
source positions and analyses the evidence. None of them changes what an ORM
executed or what a fixture contains, so every affected quantity can be derived
again from the traces, observations and snapshots that the runs retained. This
file states how. The re-analysis is retrospective: the extent of the defects
was known when it was made.

No framework is executed. No file under `results/` that existed before this
date is modified; the earlier files remain the record of what was observed and
of the rules that were applied at the time.

## Defects and corrected rules

1. **Statement positions in the replay evidence.** `runners/realworld/run.cjs`
   looked a submitted statement up in the whole journal and took the first
   equal statement, which can belong to a migration that had already been
   applied. Corrected rule: only the pending migration runs, so each submitted
   statement is matched to the next equal chunk of that file, in file order.
   Trace callbacks take the position of the submission they belong to.
2. **Rebuild flag.** `rebuild()` accepted any `CREATE TABLE` together with any
   `DROP TABLE`. Corrected rule (`smp/rebuild.py`): a table counts as rebuilt
   when it is dropped after its rows were copied into a table created in the
   same SQL. This covers the replacement sequence (create, copy, drop, rename),
   the holding-table sequence Rails emits (copy out, drop, recreate, copy back)
   and a failing execution that stops at the `DROP`.
3. **Unreadable content.** `violations()` compared two missing digests as
   equal, so a table that could not be read before and after passed. Corrected
   rule: a comparison without a readable digest on the "before" side is a
   content violation, and a table without an `id` column is ordered by its
   projected rows instead of failing.
4. **View digests in the replays.** `content()` hashed at most 1,000 view rows
   in whatever order SQLite returned them. Corrected rule: all rows, in the
   order of their canonical JSON encoding.

## Inputs

- Matrix results and their evidence archives: `results/operation_matrix.json`,
  `results/rails_fixes.json`, `results/orm_matrix.json`, the two repetitions
  under `results/rerun-2026-11-01/`, and `results/rails_base/operation_matrix.json`.
- Oracle controls: `results/oracle_validation/controls.json`.
- Replay evidence of 2 November 2026: `results/realworld-rerun-2026-11-02/` and
  the full local copy of its 93 documents, each checked against the
  `full_sha256` recorded in the published aggregate. Project SQL of repositories
  without a permissive licence is read from the local copy only; the published
  output carries hashes and byte positions, as the evidence itself does.

## Procedure

1. Check that the earlier rebuild rule reproduces every recorded flag, apply
   the corrected rule to the same executed traces and generated SQL, and list
   every flag that differs. Count the preserved or rolled-back rebuilding cells
   under both rules.
2. Count the content and view comparisons in which neither side has a digest,
   and recompute the violations of every retained trial with the corrected
   checker. Do the same for the recorded oracle controls, then run the oracle
   controls again with the corrected checker. These are raw `sqlite3`
   executions on generated fixtures.
3. Recompute the source positions of all project statements on the Drizzle path
   of the replay evidence and list every position that differs, including the
   event positions copied into the published aggregate.
4. Count the views present in the retained replay snapshots; a view digest can
   only have been affected where a view existed.
5. Generate the paper quantities twice, with the recorded and with the
   corrected rebuild flags, and list every macro whose value differs.

## Reporting

`results/reanalysis-2026-11-21/README.md` states the outcome of each step, and
the JSON files beside it hold the complete lists. Every changed macro is
reported with its recorded and corrected value, whether or not the manuscript
uses it. `scripts/paper_numbers.py` reads the corrected rebuild flags from
`rebuild_classification.json`; all other quantities continue to come from the
original result files. The corrected oracle run is reported next to the
recorded one and does not replace it: the recorded controls describe the
checker that produced the matrix results.

`scripts/reanalysis.py --verify results/reanalysis-2026-11-21` repeats the
derivation. Without the local replay copy it recomputes the statement positions
of the fully published artifacts only.
