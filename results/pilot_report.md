# SQLite migration preservation pilot

Observed: 2026-10-09T03:44:16.803437+00:00.

21/50 populated trials completed successfully while violating preservation invariants. All 50/50 empty executions succeeded. Designated controls were clean in 24/24 runs.

## Versions and execution

`before` and `current` denote these exact pins, resolved from upstream registries on 2026-10-09:

| Component | before | current |
|---|---|---|
| activerecord | 8.0.3 | 8.1.4 |
| sqlite3 | 2.9.6 | 2.9.6 |
| drizzle-orm | 0.44.2 | 0.45.4 |
| drizzle-kit | 0.31.4 | 0.31.11 |
| better-sqlite3 | 12.4.1 | 12.4.1 |

Host: `macOS-14.5-arm64-arm-64bit`. Python 3.11.5 uses SQLite 3.41.2 for both snapshots and raw execution. Ruby 3.3.2 and Node v22.22.2 execute the framework paths. Runtime SQLite versions: drizzle/before: 3.50.4; drizzle/current: 3.50.4; rails/before: 3.53.2; rails/current: 3.53.2; raw-tx/before: 3.41.2; raw-tx/current: 3.41.2; raw/before: 3.41.2; raw/current: 3.41.2.

Gemfile.lock and package-lock.json pin transitive dependencies. The better-sqlite3 driver is held constant across Drizzle versions. Different SQLite engines across languages remain a comparison limitation, although the same cascade mechanism reproduces in all three engines.

sqlite-doctor binary SHA-256: `d5452ff61987601c7c10727f173ac897574fed1aa5273c03ee40461d78e3cb09`. It exposes no version flag; JSON protocol version is 1. The binary is not vendored.

ActiveRecord uses `MigrationContext#migrate`, not a direct adapter call. Drizzle uses its better-sqlite3 `migrate()` function on SQL produced by two real `drizzle-kit generate` invocations. Only the generated upgrade enters the execution journal because fixtures establish the starting schema. Each trial uses a fresh database with foreign-key enforcement enabled before migration.

## Detector comparison

Every row below represents one populated/empty pair. `Empty` means execution raised an error; it does not run preservation assertions. `Exec lint` uses runtime SQL, including transactions and PRAGMAs. `File lint` uses the generated Drizzle file or the Rails SQL trace with transaction and migration bookkeeping statements removed. `—` means no finding. Lint codes are warnings about SQL patterns, not proof of a realized violation. Invariant cells name the observed violation.

| Case | Path | Pin | Success | Empty | Exec lint | File lint | Populated invariants |
|---|---|---|---|---|---|---|---|
| drizzle_add_column | drizzle | before | yes | — | — | — | — |
| drizzle_add_column | raw | before | yes | — | — | — | — |
| drizzle_add_column | raw-tx | before | yes | — | — | — | — |
| drizzle_add_column | drizzle | current | yes | — | — | — | — |
| drizzle_add_column | raw | current | yes | — | — | — | — |
| drizzle_add_column | raw-tx | current | yes | — | — | — | — |
| drizzle_add_index | drizzle | before | yes | — | — | — | — |
| drizzle_add_index | raw | before | yes | — | — | — | — |
| drizzle_add_index | raw-tx | before | yes | — | — | — | — |
| drizzle_add_index | drizzle | current | yes | — | — | — | — |
| drizzle_add_index | raw | current | yes | — | — | — | — |
| drizzle_add_index | raw-tx | current | yes | — | — | — | — |
| drizzle_default | drizzle | before | yes | — | SQLD002 | — | children 3→0 |
| drizzle_default | raw | before | yes | — | — | — | — |
| drizzle_default | raw-tx | before | yes | — | SQLD002 | — | children 3→0 |
| drizzle_default | drizzle | current | yes | — | SQLD002 | — | children 3→0 |
| drizzle_default | raw | current | yes | — | — | — | — |
| drizzle_default | raw-tx | current | yes | — | SQLD002 | — | children 3→0 |
| drizzle_not_null | drizzle | before | yes | — | SQLD002 | — | children 3→0 |
| drizzle_not_null | raw | before | yes | — | — | — | — |
| drizzle_not_null | raw-tx | before | yes | — | SQLD002 | — | children 3→0 |
| drizzle_not_null | drizzle | current | yes | — | SQLD002 | — | children 3→0 |
| drizzle_not_null | raw | current | yes | — | — | — | — |
| drizzle_not_null | raw-tx | current | yes | — | SQLD002 | — | children 3→0 |
| drizzle_objects | drizzle | before | yes | — | SQLD002 | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | raw | before | yes | — | — | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | raw-tx | before | yes | — | SQLD002 | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | drizzle | current | yes | — | SQLD002 | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | raw | current | yes | — | — | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | raw-tx | current | yes | — | SQLD002 | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_rebuild_control | drizzle | before | yes | — | SQLD002 | — | — |
| drizzle_rebuild_control | raw | before | yes | — | — | — | — |
| drizzle_rebuild_control | raw-tx | before | yes | — | SQLD002 | — | — |
| drizzle_rebuild_control | drizzle | current | yes | — | SQLD002 | — | — |
| drizzle_rebuild_control | raw | current | yes | — | — | — | — |
| drizzle_rebuild_control | raw-tx | current | yes | — | SQLD002 | — | — |
| rails_add_column | rails | before | yes | — | — | — | — |
| rails_add_column | rails | current | yes | — | — | — | — |
| rails_add_fk | rails | before | yes | — | SQLD002 | — | children 3→0 |
| rails_add_fk | rails | current | yes | — | SQLD002 | — | children 3→0 |
| rails_add_index | rails | before | yes | — | — | — | — |
| rails_add_index | rails | current | yes | — | — | — | — |
| rails_default | rails | before | yes | — | SQLD002 | — | children 3→0 |
| rails_default | rails | current | yes | — | SQLD002 | — | children 3→0 |
| rails_fk_no_transaction | rails | before | yes | — | SQLD002 | — | children 3→0 |
| rails_fk_no_transaction | rails | current | yes | — | — | — | — |
| rails_objects | rails | before | yes | — | SQLD002 | — | lost trigger:trg_parents_update |
| rails_objects | rails | current | yes | — | SQLD002 | — | lost trigger:trg_parents_update |
| rails_rebuild_control | rails | before | yes | — | SQLD002 | — | — |
| rails_rebuild_control | rails | current | yes | — | SQLD002 | — | — |

### Schema context sensitivity

These supplemental inputs prepend the starting schema; they are not file-only lint. Both pinned versions give the following results. Raw transaction behavior follows Drizzle's executed trace; raw autocommit follows its migration-only fragment.

| Case | Path | Schema + executed | Schema + migration only |
|---|---|---|---|
| drizzle_add_column | drizzle | — | — |
| drizzle_add_index | drizzle | — | — |
| drizzle_default | drizzle | SQLD001, SQLD002 | — |
| drizzle_not_null | drizzle | SQLD001, SQLD002 | — |
| drizzle_objects | drizzle | SQLD002, SQLD003 | SQLD003 |
| drizzle_rebuild_control | drizzle | SQLD002 | — |
| rails_add_column | rails | — | — |
| rails_add_fk | rails | SQLD002 | — |
| rails_add_index | rails | — | — |
| rails_default | rails | SQLD002 | — |
| rails_fk_no_transaction | rails | — | — |
| rails_objects | rails | SQLD002 | — |
| rails_rebuild_control | rails | SQLD002 | — |

The `rails_fk_no_transaction` row above describes current only: before still emits SQLD002. All raw and both-version context findings are retained in pilot.json.

SQLD002 correctly recognizes ineffective foreign-key toggles in transactional rebuilds. Removing the framework's transaction statements makes every migration-only input clean, including the migrations that actually delete children. Executed SQL without the original schema does not supply the existing child foreign-key or manual-object declarations needed for SQLD001/SQLD003.

Adding schema context enables SQLD001 for Drizzle cascade cases and SQLD003 for its missing manual index/trigger. Rails uses two create/copy/drop passes rather than Drizzle's create/copy/drop/rename shape, so this linter still misses Rails-specific cascade/object diagnoses even with schema context. It does warn about the transactional PRAGMA via SQLD002.

The rebuild controls have no dependent foreign keys or triggers on the rebuilt parent and preserve all invariants, yet executed lint warns SQLD002. This is a false alarm if a warning is classified as actual preservation loss; the narrower claim that the PRAGMA is ineffective is correct. Add-column and add-index controls produce no lint warnings. Thus runtime trace lint catches a mechanism but does not establish whether populated state is lost.

## Reproduction and version boundaries

- Rails [#55866](https://github.com/rails/rails/issues/55866): `rails_add_fk` reproduces child deletion with both 8.0.3 and 8.1.4. [The original account](https://kyrylo.org/software/2025/09/27/a-mere-add-foreign-key-can-wipe-out-your-whole-rails-sqlite-production-table.html) describes the same add-foreign-key operation on a parent with cascade children.
- Rails [#55907](https://github.com/rails/rails/pull/55907), merged 2025-10-17: tag-source inspection places the adapter transaction-order fix in 7.2.3, 8.0.4, and 8.1.0; it is absent from 7.2.2.2 and 8.0.3. The current 8.1.4 retains that fix. The `disable_ddl_transaction!` diagnostic loses children on 8.0.3 but preserves them on 8.1.4. Intermediate tags were source-inspected, not executed.
- Rails [#57128](https://github.com/rails/rails/pull/57128) remains open in the recorded API evidence. The normal outer migration transaction defeats the adapter fix: both add-foreign-key and default changes still delete children on 8.1.4. This is a reduced reproduction of the documented transaction mechanism, not the follow-up's entire rename/SET NULL test suite.
- Drizzle [#4938](https://github.com/drizzle-team/drizzle-orm/issues/4938): the reported ORM 0.44.2 / Kit 0.31.4 pair reproduces cascade deletion when a parent becomes NOT NULL. Its original report used Cloudflare D1; this pilot reproduces the mechanism through the better-sqlite3 driver, not D1.
- Drizzle [#5782](https://github.com/drizzle-team/drizzle-orm/issues/5782): changing a parent default reproduces the documented better-sqlite3 migrator interaction on both pinned pairs, including ORM 0.45.4 / Kit 0.31.11. No fix is observed in that latest stable pair. Raw autocommit preserves children for both generated migrations; raw-tx deletes them.
- Object-loss probes are extensions grounded in SQLite's [rebuild procedure](https://www.sqlite.org/lang_altertable.html#otheralter), not claims that the linked ORM issues report trigger loss. Rails loses the manual trigger but preserves both indexes. Drizzle preserves its declared index but loses the manual index and trigger in both versions, including raw autocommit. No version-level fix for these object losses was observed.

In every cascade-loss trial, children fall from three rows to zero while parents remain at two. Both SQLite checks return clean results: deleted children create no orphaned references or physical corruption. Every intended schema change is present. No view definition was lost or altered; the view references the stable child table, so parent-dependent view rebuild failures are untested. SQLite documents that foreign-key toggles are ineffective within a transaction ([PRAGMA reference](https://www.sqlite.org/pragma.html#pragma_foreign_keys)).

## Outcomes and limits

Documented hazards reproduce in 4 case families through real framework paths: drizzle_default, drizzle_not_null, rails_add_fk, rails_default. All 12 designated framework control runs preserve the checked invariants. These are multiple documented case instances, not independent root causes; cascade cases share the same transactional mechanism. Trigger/index loss adds a separate preservation failure.

Populated invariants detect 13 framework violations missed by empty execution. File-only lint misses them all; runtime lint warns about transactional PRAGMAs, while schema context and rebuild shape determine more specific coverage. Safe rebuild warnings demonstrate why lint warnings and realized loss must be scored separately.

Population is essential to exposing the nine framework cascade-loss runs. The four framework object-loss runs would also be caught on empty databases if schema invariants were checked there; the empty-db detector here measures execution success alone. Empty-trial snapshots and invariant results are retained separately in the raw data so this distinction can be inspected.

The two safe rebuild controls were added after the first 42-pair exploratory run to measure SQLD002's specificity. The final 50-pair matrix reruns the original fixtures unchanged and includes those controls.

This is a small, purposive deterministic pilot; rates are descriptive and do not estimate ecosystem prevalence.

Rows with equal cardinality but changed values, SET NULL effects, reordered data, and semantic trigger behavior are outside the implemented invariants. Schema-object comparison is normalized text, not general SQL equivalence. Only declared application tables enter row-count comparisons; framework bookkeeping is excluded. The fixtures have valid data and no concurrency. Neither Cloudflare D1 nor every released ORM/driver combination is covered.

Kit 0.31.4 prints an ENOENT and exits zero when given an absolute output path. The harness therefore uses relative output paths and verifies that both migration journal entries exist; a generation without them is a setup failure, not a migration outcome.

## Evidence and reproduction

Each `runs/<case>--<path>--<pin>/result.json` contains before/after snapshots, all invariant findings, execution status and versions, and the full linter JSON. Adjacent SQL files retain all four lint inputs. `populated/` and `empty/` retain runner metadata and SQL traces; Rails additionally retains structured log events. `generated_history/` retains both Drizzle migrations, snapshots, and the journal. Trial databases are not kept.

Run `.venv/bin/python -m smp pilot --output results/<new directory>` from the repository root. The README in the repository root describes the setup. `sources/upstream.json` records registry versions, issue states, release dates, and inspected Rails source hashes. [pilot.json](pilot.json) contains the per-trial observations.
