# Replay repeated with full evidence, 2 November 2026

The first replay (`results/realworld.json`, 10 October 2026) kept outcomes,
findings and the rows named in findings, but no SQL traces or full snapshots.
On 2 November 2026 all 93 attempts were run again from the recorded commits,
migration files and Drizzle versions to collect them. Every compared outcome
field and all 152 replay quantities of the paper that were compared have the
same value in both runs; `comparison.md` lists each migration, and `comparison.json` holds the
differing fields (none), the loss summary of each attempt and the compared
quantities.
Rows of the first run can be compared only where a finding recorded them.

## Files

- `realworld.json`: aggregate results, pins, source and input hashes, licence
  labels and the hash of every evidence file.
- `evidence/*.json.gz`: one file per attempt, 2,256,142 bytes in total. The 70
  replayed migrations have the SQL trace and the snapshots before and after for
  the Drizzle, raw and raw-tx paths (210 executed paths, 420 snapshots, 3,243
  trace callbacks, 1,865 submitted project statements), a reference execution
  and the setup traces. The 23 histories that could not be replayed have the
  stage and reason of the failure.
- `comparison.json`, `comparison.md`: comparison with the first run.

SQLite can call the trace callback more than once for a statement (foreign-key
and trigger activity), and a statement rejected during preparation appears
under `submitted` but not under `trace`.

## Full and redacted evidence

Project SQL and schema are published in full for the 25 repositories whose
recorded licence label is MIT (18), Apache-2.0 (6) or BSD-3-Clause (1) and whose
licence files exist at the pinned commit; the files are under
`licenses/replay/`. For the other 68 (no label 44, AGPL-3.0 14, GPL-3.0 5,
NOASSERTION 4, EUPL-1.2 1) project SQL and project-derived schema entries are
replaced by their SHA-256 and the position of the source statements in the
pinned files. Framework SQL and the synthetic rows are published for all 93.
The labels are the ones recorded when the repositories were collected.

In a redacted file a schema entry is hashed as canonical JSON (sorted keys,
UTF-8, BLOBs as `{"blob": "hex"}`), and SQL text as its UTF-8 bytes. Positions
are stored once under `schema_sources` and referenced by
`sources_ref: #/schema_sources`: one list of all schema-changing statements of
the history, shared by every redacted entry, not the statements that produced
a particular entry. `evidence.full_sha256` in the aggregate is the hash of
the unredacted file. That file is not published for these repositories, except
for one failed attempt without project SQL (`evidence/028-fb72651f7eb73e33.json.gz`),
which is published unchanged.

The source positions of 35 migrations were recorded wrongly and are corrected
in `results/reanalysis-2026-11-21/statement_provenance.json`; the files here
still hold the positions as recorded. The `release_publication` field of the
aggregate was added when the licence files were collected.

## Check the files

```sh
.venv/bin/python scripts/validate_realworld.py results/realworld-rerun-2026-11-02/realworld.json
```

The command checks the hashes of the five source files that produced the run
and of the two scripts that wrote the published files against
`sources/replay-validation/2026-11-02/`, then the 93 evidence hashes, the
redaction and the licence files, and it recomputes row counts and row-count
findings from the snapshots. The recorded hash of the protocol text is not
checked.

## Run it again

Node v22.22.2 and the Python environment of the repository are needed. The run
used Python 3.11.5 with SQLite 3.41.2 and better-sqlite3 12.4.1 with SQLite
3.50.4; the 21 Drizzle versions come from the pins in `results/realworld.json`.
Install the runner dependencies if they are absent:

```sh
npm ci --prefix runners/drizzle/current
```

`--evidence-dir` selects the attempts of the pinned run and writes full
evidence to a local directory; the output directory receives the publishable
files. Both directories must be new.

```sh
.venv/bin/python -m smp realworld \
  --pins results/realworld.json \
  --input sources/realworld/drizzle_rebuild_files.tsv \
  --probe sources/realworld/g3_probe.json \
  --evidence-dir .realworld-local/repeat \
  --output results/realworld-repeat

.venv/bin/python scripts/finalize_realworld_rerun.py \
  --local .realworld-local/repeat \
  --output results/realworld-repeat
```

The second command compares the run with `results/realworld.json`, checks the
publishable files against the full ones and writes the comparison reports. It
exits with an error if a compared field or a paper quantity differs.

To rebuild the evidence of one migration:

```sh
.venv/bin/python scripts/rebuild_realworld_evidence.py \
  --pins results/realworld.json \
  --repo dakohhh/cf_ai_speakscribe \
  --migration migrations/0005_fat_nightcrawler.sql \
  --evidence-dir .realworld-local/one \
  --output results/realworld-one
```

Any recorded repository and migration can be chosen. The command fetches the
pinned commit and Drizzle package, so both must still be available.

## Limits

The 23 histories that could not be replayed in the first run failed again for
the same reasons, so they have no target traces or snapshots. Both input files
are the ones of the first run (corpus
`b430041171ec78dd17403d764df4b4093947d63dc4527192ffccb51f213afa4d`, probe
`be00c68e386e37fb58bd869624c4339aedd1f4db9bea8e8739abbfca36ab99ba`); no
repository was added or replaced.
