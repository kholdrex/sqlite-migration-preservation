# SQLite migration preservation

Software and data for the paper "Successful Migrations, Lost Data: Silent
Preservation Failures in SQLite Table Rebuilds Across Five ORMs". The
experiments apply schema migrations through ActiveRecord, Drizzle, Django,
Alembic and Prisma to populated and empty SQLite databases and compare the
state before and after.

| Path | Content |
|---|---|
| `cases/`, `smp/matrix_spec.py`, `smp/orm_spec.py` | the 13 pilot fixtures and the operation and context definitions of the matrices |
| `smp/`, `runners/` | harness, ORM runners and dependency locks |
| `sources/` | upstream revisions, patches, the input lists of the replay and the tracker search queries |
| `results/` | observations, compressed evidence and reports |
| `scripts/` | experiment, validation and paper scripts |
| `paper/` | the paper's numbers and figures as generated from `results/` |

The harness and the annotations are under the MIT licence. Redistributed
packages, patches, quoted tracker text and replay evidence derived from other
projects keep their own terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
To cite the package, use [CITATION.cff](CITATION.cff).

Machine-specific paths in the evidence were replaced by the labels
`/study/harness`, `/study/rails-base-checkout`, `/study/atlas-lint-checkout`
and `/study/sqlite-doctor`. Standalone run logs are not included; the SQL
traces and logs stored inside the evidence archives are.

## Regenerate the numbers and figures

This needs Python 3.11 or later and no other software:

```sh
python3 scripts/paper_numbers.py --output reproductions/paper
cmp reproductions/paper/numbers.tex paper/numbers.tex
```

`numbers.tex` holds the LaTeX macros the paper uses, `numbers.md` the same
values as a table, and `numbers.json` the result file, field, counting rule
and source hash of every value. The figures need the `paper` extras
(`pip install -e '.[paper]'`):

```sh
python3 scripts/paper_figures.py --output reproductions/figures
```

`manifest.json` in the output lists the data behind each figure; compare it
with `paper/figures/manifest.json`. With the pinned Matplotlib, NumPy and
fontTools, `cmp` also shows `Fig1.pdf` and `Fig2.pdf` to be identical to the
files in `paper/figures/`.

## Check the retained results

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test,paper]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -p no:capture -p no:cacheprovider
```

Four replay tests are skipped unless the Node dependencies of
`runners/drizzle/current` are installed (`npm ci --prefix runners/drizzle/current`).
The validators exit with an error on any difference. Those for the pilot and
the matrices recompute violations and outcomes from the stored snapshots. For
the first replay, which has no snapshots, the validator checks the source
hashes and that the aggregate is consistent with itself. For the repetition it
also checks the evidence files, redaction and licence notices, and it
recomputes the row counts of every executed path and its row-count findings
from the snapshots; it does not recompute the other findings. Without the
unredacted replay files the last command recomputes statement positions and
views for the 25 fully published artifacts only, and it prints the checks that
redaction prevents. The validators check the retained files as they are; they
are not a defence against edited results.

```sh
P=.venv/bin/python
$P scripts/validate_results.py results/pilot.json
$P scripts/validate_results.py results/upstream_fixes.json
$P scripts/validate_operation_matrix.py results/operation_matrix.json
$P scripts/validate_orm_matrix.py results/orm_matrix.json
$P scripts/validate_rails_fixes.py results/rails_fixes.json
$P scripts/validate_rails_atomicity.py results/rails_atomicity.json
$P scripts/validate_operation_matrix.py results/rails_base/operation_matrix.json --subset
$P scripts/validate_operation_matrix.py results/rerun-2026-11-01/rails-current/operation_matrix.json --subset
$P scripts/validate_operation_matrix.py results/rerun-2026-11-01/drizzle/operation_matrix.json --subset
$P scripts/validate_realworld.py results/realworld.json
$P scripts/validate_realworld.py results/realworld-rerun-2026-11-02/realworld.json
$P scripts/atlas_lint.py --summarize
$P scripts/reanalysis.py --verify results/reanalysis-2026-11-21
```

`--subset` is for a run that covers part of the matrix; it checks the rows
that are present. None of these commands needs Docker or network access. Checking the
linter results needs the linter binary (next section):

```sh
$P scripts/relint.py --doctor "$DOCTOR" --commit a65e4287b93a252ebd7148db8504a41bd48a63a7 --verify
```

## Run the experiments

### Setup

The harness needs Python 3.11 or later, Git, Node with npm, Ruby with Bundler
and a C/C++ toolchain. The runs used Python 3.11.5, Node 22.22.2 and Ruby 3.3.2
(`.python-version`, `.nvmrc`, `.ruby-version`). The Rails pull-request pins use
Ruby 3.4.3 with Bundler 2.6.7, the Django and Alembic runners Python 3.13, and
the Atlas baseline Docker. SQLite versions depend on the interpreter and
driver builds and are recorded in the evidence.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test,paper]'
.venv/bin/python scripts/setup.py --labels before current
.venv/bin/python scripts/setup.py --upstream --labels rails-pr57128 drizzle-pr5784 drizzle-pr5074 drizzle-pr5784+5074
.venv/bin/python scripts/setup.py --upstream --labels rails-pr56811 rails-pr58709 rails-pr57128+56811 rails-pr58709+56811 v1-rc5
.venv/bin/python scripts/setup_orm.py --python python3.13
```

Setup uses the Ruby versions RVM has installed, or Ruby and Bundler on `PATH`;
`SMP_RUBY` selects another Ruby. Gems are installed under `vendor/bundle` and
npm packages from the committed lockfiles. Labels such as `current` and
`before` name fixed versions: see [versions.json](versions.json),
[runners/orm/pins.json](runners/orm/pins.json) and
[sources/upstream_fixes.json](sources/upstream_fixes.json).

The two combined Rails pins (`rails-pr57128+56811`, `rails-pr58709+56811`) are
merges that exist only here. Setup rebuilds each merge commit from its two
parents and the resolution patch in `sources/` and checks its hash. Their
lockfiles name the merge repository by an absolute path, which appears as
`/study/harness/.cache/...` in this package; setup rewrites that one line to
the location of your checkout. The two Drizzle pull-request packages are in
`runners/artifacts/`; `scripts/build_upstream.py` rebuilds them from the
sources pinned in `sources/upstream_builds.json`.

### Linter

The linter is [sqlite-doctor](https://github.com/kholdrex/sqlite-doctor). The
study used two revisions:

| Study use | Tag | Commit | Recorded binary SHA-256 |
|---|---|---|---|
| Original experiments and original-input verification | [`study-original`](https://github.com/kholdrex/sqlite-doctor/tree/study-original) | `a65e4287b93a252ebd7148db8504a41bd48a63a7` | `d5452ff61987601c7c10727f173ac897574fed1aa5273c03ee40461d78e3cb09` |
| Later re-lint | [`study-relint`](https://github.com/kholdrex/sqlite-doctor/tree/study-relint) | `2bf86dcff8bbf36d6dfd297f80b592760e4cea0f` | `f0c6fa5f8003cf8a911bf9af69063d661c2d61966472b7413573808877e9a127` |

```sh
mkdir -p .tools
git clone --branch study-original --single-branch https://github.com/kholdrex/sqlite-doctor.git .tools/doctor-original
git clone --branch study-relint --single-branch https://github.com/kholdrex/sqlite-doctor.git .tools/doctor-relint
rustup toolchain install 1.99.0
cargo +1.99.0 build --release --locked --manifest-path .tools/doctor-original/Cargo.toml
cargo +1.99.0 build --release --locked --manifest-path .tools/doctor-relint/Cargo.toml
DOCTOR="$PWD/.tools/doctor-original/target/release/sqlite-doctor"
RELINT="$PWD/.tools/doctor-relint/target/release/sqlite-doctor"
export SMP_DOCTOR="$DOCTOR"
```

The hashes in the table are those of the binaries the study ran (macOS on
arm64, Rust 1.99.0). rustc writes the absolute path of the Cargo registry into
the binary, so a build on another machine, or under another home directory,
has a different hash. Check your build of the first revision with
`relint.py --verify` above. The 801 current cells have 3,204 lint inputs; the
324 executed-SQL inputs of the 162 Prisma cells have no runtime trace, so the
command lints the other 2,880 again and fails if any result differs from the
recorded one. The harness takes the linter from `--doctor`, then `SMP_DOCTOR`,
then `sqlite-doctor` on `PATH`; the commands printed in the reports under
`results/` rely on `SMP_DOCTOR`.

### Experiments

Each row is one experiment of the paper. Give every repetition a new output
directory or file: the two matrix commands reuse evidence they find in their
output directory and write the aggregate again, and the two paper scripts in
the last rows overwrite the files in theirs.

```sh
P=.venv/bin/python
RUN=reproduction-01
OUT="reproductions/$RUN"
mkdir -p "$OUT"
```

| Paper section / RQ topic | Exact command and selection | Outputs | Validator |
|---|---|---|---|
| Mechanism pilot; preservation | `$P -m smp pilot --doctor "$DOCTOR" --output "$OUT/pilot"` (fixed `before current`) | `pilot.json`, `pilot_report.md`, `runs/` | `$P scripts/validate_results.py "$OUT/pilot/pilot.json" --compare results/pilot.json` |
| RQ1 operation matrix; RQ2 detectors | `$P -m smp operation-matrix --doctor "$DOCTOR" --labels before current rails-pr57128 drizzle-pr5784 drizzle-pr5074 drizzle-pr5784+5074 --workers 8 --output "$OUT/operations"` | `operation_matrix.json`, `.md`, `operation_evidence/` | `$P scripts/validate_operation_matrix.py "$OUT/operations/operation_matrix.json"` |
| RQ1/RQ2 ORM extension | `$P -m smp.orm_matrix --frameworks django alembic prisma --doctor "$DOCTOR" --workers 8 --output "$OUT/orm"` | `orm_matrix.json`, `.md`, `orm_evidence/` | `$P scripts/validate_orm_matrix.py "$OUT/orm/orm_matrix.json"` |
| RQ3 upstream-fix pilot | `$P -m smp upstream-fixes --labels rails-pr57128 drizzle-pr5784 drizzle-pr5074 drizzle-pr5784+5074 --doctor "$DOCTOR" --output "$OUT/upstream"` | `upstream_fixes.json`, `.md`, `runs/` | `$P scripts/validate_results.py "$OUT/upstream/upstream_fixes.json" --compare results/upstream_fixes.json` |
| RQ3 additional Rails fixes | `$P -m smp rails-fixes --doctor "$DOCTOR" --workers 8 --output "$OUT/rails"` | `rails_fixes.json`, `.md`, `rails-fixes/` | `$P scripts/validate_rails_fixes.py "$OUT/rails/rails_fixes.json"` |
| RQ3 Rails atomicity | `$P -m smp rails-atomicity --output "$OUT/rails"` | `rails_atomicity.json`, `rails-atomicity/`; attaches to the preceding Rails report | `$P scripts/validate_rails_atomicity.py "$OUT/rails/rails_atomicity.json"` |
| RQ3 Rails base control | `$P scripts/build_rails_base.py --output "results/rails_base/$RUN"` then `$P -m smp.rails_base --doctor "$DOCTOR" --workers 6 --output "results/rails_base/$RUN"` | `builds.json`, `source_comparisons.json`, `operation_matrix.json`, `rails_atomicity.json`, `comparison.json`, `summary.md`, `validation.json` | Built-in source, runtime, matrix and atomicity validation; `$P scripts/validate_operation_matrix.py "results/rails_base/$RUN/operation_matrix.json" --subset` |
| Oracle validation | `$P scripts/oracle_validation.py --recorded-checker --output "results/oracle_validation/$RUN"` (checker of the matrix runs: 16 of 19 lossy trials detected); without `--recorded-checker` the corrected checker (17 of 19) | `controls.json`, `summary.md` | The run stops if a ground-truth assertion fails; compare the summary with `results/oracle_validation/controls.json` or `results/reanalysis-2026-11-21/oracle_validation/controls.json` |
| RQ2 Atlas baseline | `$P scripts/atlas_lint.py --workers 8 --output "results/atlas_lint/$RUN"` | `report.json`, `summary.md`, `inputs.jsonl.gz`, `diagnostics.jsonl.gz`, `supporting.json.gz` | `$P scripts/atlas_lint.py --summarize --output "results/atlas_lint/$RUN"` |
| RQ4 original replay procedure | `$P -m smp realworld --input sources/realworld/drizzle_rebuild_files.tsv --probe sources/realworld/g3_probe.json --pins results/realworld.json --target 20 --rows 3 --output "$OUT/replay-original"` | `realworld.json`, `realworld.md` | `$P scripts/validate_realworld.py "$OUT/replay-original/realworld.json"` |
| RQ4 repeat of the 2026-11-02 evidence rerun | `$P -m smp realworld --input sources/realworld/drizzle_rebuild_files.tsv --probe sources/realworld/g3_probe.json --pins results/realworld.json --rows 3 --evidence-dir ".realworld-local/$RUN" --output "$OUT/replay-evidence"` | Public `realworld.json`, `.md`, `evidence/`; full local evidence separately | `$P scripts/finalize_realworld_rerun.py --local ".realworld-local/$RUN" --output "$OUT/replay-evidence"` then `$P scripts/validate_realworld.py "$OUT/replay-evidence/realworld.json"` |
| RQ4 one-migration evidence rebuild | `$P scripts/rebuild_realworld_evidence.py --pins results/realworld.json --repo dakohhh/cf_ai_speakscribe --migration migrations/0005_fat_nightcrawler.sql --evidence-dir ".realworld-local/$RUN-one" --output "$OUT/replay-one"` | Full local and publishable evidence for the pinned migration | `$P scripts/validate_realworld.py "$OUT/replay-one/realworld.json"`; artifact hashes and provenance in the aggregate |
| RQ3 Kit PRAGMA-pair probe | `$P scripts/probe_kit_pragma_pairs.py --output "$OUT/kit_pragma_pairs.json"` (fixed `current v1-rc5`) | Generated SQL, PRAGMA/drop state, autocommit and transaction row counts | Built-in execution checks; compare with `results/kit_pragma_pairs.json` |
| Prisma connection/transaction probe | `$P scripts/probe_prisma_transactions.py --output "$OUT/orm_prisma_probes.json"` (fixed `prisma-stable`) | Connection observations, injected-failure SQL, logs and ledger state | Compare with `results/orm_prisma_probes.json`; no standalone probe validator |
| November 1 Rails repeat | `$P -m smp operation-matrix --frameworks rails --labels current --doctor "$DOCTOR" --workers 6 --output "$OUT/november-rails"` | Operation aggregate and evidence | `$P scripts/validate_operation_matrix.py "$OUT/november-rails/operation_matrix.json" --subset` |
| November 1 Drizzle repeat and release candidate | `$P -m smp operation-matrix --frameworks drizzle --labels v1-rc5 current --doctor "$DOCTOR" --workers 6 --output "$OUT/november-drizzle"` | Operation aggregate and evidence | `$P scripts/validate_operation_matrix.py "$OUT/november-drizzle/operation_matrix.json" --subset` |
| RQ2 original re-lint verification | `$P scripts/relint.py --doctor "$DOCTOR" --commit a65e4287b93a252ebd7148db8504a41bd48a63a7 --verify` | Printed cell/input/mismatch counts; scratch SQL in `.cache/relint/` | `--verify` exits nonzero if availability, detection status or diagnostic output differs from the recorded result |
| RQ2 later re-lint | `$P scripts/relint.py --doctor "$RELINT" --commit 2bf86dcff8bbf36d6dfd297f80b592760e4cea0f --output "$OUT/relint/relint.json"` | Recomputed lint observations for the paper's current native-pin selection | Compare findings with `results/relint-2026-11-01/relint.json`; no separate later-linter validator |
| All paper quantities, including tracker annotations | `$P scripts/paper_numbers.py --output "$OUT/paper"` | `numbers.json`, `numbers.tex`, `numbers.md` | `cmp paper/numbers.tex "$OUT/paper/numbers.tex"` |
| Paper figures | `$P scripts/paper_figures.py --output "$OUT/figures"` | `Fig1.pdf` (operation grid), `Fig2.pdf` (silent loss per fix), `manifest.json` | Compare `manifest.json` with `paper/figures/manifest.json`; paper-number tests verify retained figure source hashes |

The base-control, oracle and Atlas commands write below their own `results/`
subdirectory. The six labels of the operation-matrix command and the four
labels of the upstream-fix command select the pins of the original runs;
without them later pins are added. The ORM command runs `django-current`,
`django-previous`, Alembic in its `auto` and `always` modes and
`prisma-stable`; `prisma-latest-tag` is recorded as unsupported. The
base control uses `rails-base-b8725ee9a909`, `rails-base-bd885faee983` and
`rails-base-704aa9785156`.

Atlas runs from the image
`arigaio/atlas@sha256:dc27586a3d1097ff47e90124f13cbed884a27026c374a82e523699645a6d5d57`
and never from an Atlas binary on the host; see
[PROTOCOL_atlas_lint.md](PROTOCOL_atlas_lint.md).

## Replay of public migration histories

`results/realworld.json` is the first replay (10 October 2026) and
[results/realworld-rerun-2026-11-02](results/realworld-rerun-2026-11-02/README.md)
its repetition with SQL traces and full snapshots. The replay applies
migrations from public Drizzle projects to databases filled with synthetic
rows. The Drizzle path runs the migrator on better-sqlite3 12.4.1 (SQLite
3.50.4); the raw and raw-tx paths run the same SQL through Python's `sqlite3`
(SQLite 3.41.2). D1, libSQL and Bun are not run, and a loss in a replay does
not show that a project lost data in production. The projects come from a code
search. GitHub marks none of the 93 repositories as a fork, but several share
migration files: the 70 replayed migrations are 63 distinct files.

The evidence of the repetition is published in full for 25 projects with a
permissive licence label and the licence files at the pinned commit
(`licenses/replay/`). For the other 68, project SQL and schema are replaced by
hashes and source positions, and `scripts/rebuild_realworld_evidence.py`
produces the full evidence again from the pinned public commit. One of the 68
is a failed attempt without project SQL and is published unchanged
(`evidence/028-fb72651f7eb73e33.json.gz`). The unredacted files of the other 67
are not published, so their recorded `full_sha256` cannot be checked from this
package.

The replay takes the Drizzle version from the `package.json` nearest to the
migration, reading the first `major.minor.patch` in the declared range, so a
prerelease suffix is ignored. If that version cannot be installed it tries the
highest other patch release of the same minor version, and it falls back to
0.45.4 when that fails too or no version is declared: 4 of the 93 attempts, 1
of the 70 replayed migrations. All versions run on one locked better-sqlite3
12.4.1 runner; there is no lockfile per project. The aggregates record the
declared and the resolved version and, for the 89 attempts that fetched a
package, its registry integrity hash; the hash of the fallback version is in
`runners/drizzle/current/package-lock.json`.

## Protocols

The `PROTOCOL_*.md` files describe the methods. Four result files record the
SHA-256 of the protocol text they were run with: `results/atlas_lint/report.json`
(`protocol_sha256`), the two `controls.json` files of the oracle validation
(`source_sha256`) and `results/realworld-rerun-2026-11-02/realworld.json`
(`source_hashes`). These earlier texts, and the earlier text of the Rails
base-commit protocol, are not part of this package, so the hashes cannot be
checked from it.

No protocol was preregistered. `results/atlas_lint/supporting.json.gz` holds
the Atlas runner as executed and the summary as first rendered; both contain
the sentence "No deviations from the preregistered protocol", which that
runner printed in every summary.

Some result files carry notes of the time they were written: test counts,
disk samples, a mention of logs that are not included and of the checkout the
run was made in. They are in `results/atlas_lint/supporting.json.gz` and
`report.json`, `results/rails_base/comparison.json` (`deviations`) and the two
`realworld.json` files. These files are published with the content they had;
the notes are not instructions for a reader.

## Re-runs and corrections

**1 November 2026.** The Rails 8.1.4 and Drizzle 0.45.4 cells of the operation
matrix were run again and Drizzle 1.0.0-rc.5 was added
([report](results/rerun-2026-11-01/README.md)). All 144 Rails and 405 Drizzle
pairs agree with the first run. The release candidate's `drop_unique` cells
are left out of the paper's counts because its starting schema differs from
the fixture.

**2 November 2026.** The replay was run again to collect traces and snapshots
(above). All outcomes and all 152 replay quantities compared at the time agree
with the first run.

**21 November 2026.** Four errors in the analysis code were corrected: the
source position recorded for a replayed statement, the rule that flags a table
rebuild, the comparison of table content that could not be read, and the digest
of view rows in the replay. No ORM was run again; the stored traces and
snapshots were analysed with the corrected code and the oracle controls were
repeated ([protocol](PROTOCOL_reanalysis.md),
[results](results/reanalysis-2026-11-21/README.md)). The corrections change:

- three counts of rebuilding cells in the ORM matrix (all cells 1,754 to 1,744,
  Prisma raw path 108 to 103, Prisma raw-tx path 107 to 102), none of which the
  paper uses;
- the source positions of 91 of 580 submitted statements, in 35 of the 70
  replayed migrations;
- the oracle controls: the checker that produced the matrix results detected
  16 of 19 lossy trials, the corrected checker detects 17 of 19, and both
  raise no false alarm in 441 safe trials.

No violation list changes in the 14,130 matrix trials. The re-analysis did not
modify the earlier result files, and the paper reports the recorded 16 of 19.
`scripts/oracle_validation.py` runs the corrected checker; with
`--recorded-checker` it runs the earlier one and gives 16 of 19 again.
`scripts/paper_numbers.py` takes the rebuild flags from
`results/reanalysis-2026-11-21/rebuild_classification.json`. The check
`scripts/reanalysis.py --verify` recomputes statement positions for the 8
corrected migrations whose evidence is published in full. It does not
recompute them for the 27 whose evidence is redacted.

## Known limits of the checks

- The preservation checker compares a column default only when the migration
  is meant to change it. Both checkers missed the two control trials in which
  the default of another column changed. The checker of the matrix runs also
  missed an overwritten value in a table without an `id` column.
- The trigger probe performs one update. Other trigger behaviour is not
  tested.
- The paper's empty-database detector counts only whether the migration raised
  an error. The matrices also check schema objects and trigger behaviour on
  the empty database, but deleted rows can be seen only on the populated one.
- Prisma does not expose the SQL it executes at run time. Its cells record the
  generated SQL and the state of the connection; inputs that need a runtime
  trace are counted as unavailable, not as clean.
- The later linter build was developed with these cells in view and then run
  on the same cells.
- The pilot compares row counts and schema objects; the matrices also compare
  row content, trigger behaviour and views.

## Tracker labels

`results/tracker_labels.jsonl` holds the labels of 656 issue-tracker reports
with the quoted evidence. `sources/tracker_queries.tsv` lists the 50 queries
that found them: ten per repository, sent to GitHub's issue search with up to
100 results each. The labelling instructions are not part of the package, so
the paper's tracker counts can be recomputed from these labels, and the search
can be repeated, but not the labelling. The six reports counted as incidents with real data
are listed as `REAL_DATA_LOSS_INCIDENTS` in `scripts/paper_numbers.py`.
`results/tracker_sample_labels.jsonl` holds the author's labels for 60 of the
reports, assigned without the existing labels in view. The sample was drawn
with one `random.Random(20261102)`: first `sample(ids, 40)` from the 167
reports labelled relevant, then `sample(ids, 20)` from the other 489, with the
ids of each group sorted as strings. The `TrackerSample` quantities compare
the two labellings; they were not reconciled.
