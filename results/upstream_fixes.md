# Upstream SQLite migration fixes

Observed: 2026-10-09T21:00:13.840850+00:00.

61 populated/empty pairs; 122/122 successful executions. 12 populated trials still violate preservation invariants. 30/30 designated control pairs preserve the checked invariants.

Each individual fix prevents its framework's measured cascade losses, including Rails' outer migration transaction. Manual-object losses remain. Combining the Drizzle fixes also preserves the cascade cases.

## Pins

| Pin | Resolved head | Runtime packages |
|---|---|---|
| rails-pr57128 | `8823c1370c7bc8910e609d1b6f27f4fc34f3d81d` | activerecord 8.2.0.alpha; sqlite3 2.9.6 |
| drizzle-pr5784 | `2b3f6d8c4b016cb470fa06caa883038d1a93babb` | drizzle-orm 0.45.3-smp.pr5784; drizzle-kit 0.31.11; better-sqlite3 12.4.1 |
| drizzle-pr5074 | `72e975734e73d4bc7f4c80a7b4f411a4ff60437e` | drizzle-orm 0.45.4; drizzle-kit 0.31.8-smp.pr5074; better-sqlite3 12.4.1 |
| drizzle-pr5784+5074 | Heads of drizzle-pr5784 and drizzle-pr5074 | drizzle-orm 0.45.3-smp.pr5784; drizzle-kit 0.31.8-smp.pr5074; better-sqlite3 12.4.1 |

## Detector comparison

Every row is a populated/empty pair, with the fixtures and invariants of the pilot. `Success` is populated execution; `Empty` reports only execution errors. `—` means no finding. Exec lint includes transaction boundaries; file lint uses untouched generated SQL for Drizzle and the migration-only trace for Rails. Warnings describe patterns, not realized loss.

| Case | Path | Pin | Success | Empty | Exec lint | File lint | Populated invariants |
|---|---|---|---|---|---|---|---|
| drizzle_add_column | drizzle | drizzle-pr5784 | yes | — | — | — | — |
| drizzle_add_column | raw | drizzle-pr5784 | yes | — | — | — | — |
| drizzle_add_column | raw-tx | drizzle-pr5784 | yes | — | — | — | — |
| drizzle_add_column | drizzle | drizzle-pr5074 | yes | — | — | — | — |
| drizzle_add_column | raw | drizzle-pr5074 | yes | — | — | — | — |
| drizzle_add_column | raw-tx | drizzle-pr5074 | yes | — | — | — | — |
| drizzle_add_column | drizzle | drizzle-pr5784+5074 | yes | — | — | — | — |
| drizzle_add_column | raw | drizzle-pr5784+5074 | yes | — | — | — | — |
| drizzle_add_column | raw-tx | drizzle-pr5784+5074 | yes | — | — | — | — |
| drizzle_add_index | drizzle | drizzle-pr5784 | yes | — | — | — | — |
| drizzle_add_index | raw | drizzle-pr5784 | yes | — | — | — | — |
| drizzle_add_index | raw-tx | drizzle-pr5784 | yes | — | — | — | — |
| drizzle_add_index | drizzle | drizzle-pr5074 | yes | — | — | — | — |
| drizzle_add_index | raw | drizzle-pr5074 | yes | — | — | — | — |
| drizzle_add_index | raw-tx | drizzle-pr5074 | yes | — | — | — | — |
| drizzle_add_index | drizzle | drizzle-pr5784+5074 | yes | — | — | — | — |
| drizzle_add_index | raw | drizzle-pr5784+5074 | yes | — | — | — | — |
| drizzle_add_index | raw-tx | drizzle-pr5784+5074 | yes | — | — | — | — |
| drizzle_default | drizzle | drizzle-pr5784 | yes | — | — | — | — |
| drizzle_default | raw | drizzle-pr5784 | yes | — | — | — | — |
| drizzle_default | raw-tx | drizzle-pr5784 | yes | — | SQLD002 | — | children 3→0 |
| drizzle_default | drizzle | drizzle-pr5074 | yes | — | SQLD002 | — | — |
| drizzle_default | raw | drizzle-pr5074 | yes | — | — | — | — |
| drizzle_default | raw-tx | drizzle-pr5074 | yes | — | SQLD002 | — | — |
| drizzle_default | drizzle | drizzle-pr5784+5074 | yes | — | — | — | — |
| drizzle_default | raw | drizzle-pr5784+5074 | yes | — | — | — | — |
| drizzle_default | raw-tx | drizzle-pr5784+5074 | yes | — | SQLD002 | — | — |
| drizzle_not_null | drizzle | drizzle-pr5784 | yes | — | — | — | — |
| drizzle_not_null | raw | drizzle-pr5784 | yes | — | — | — | — |
| drizzle_not_null | raw-tx | drizzle-pr5784 | yes | — | SQLD002 | — | children 3→0 |
| drizzle_not_null | drizzle | drizzle-pr5074 | yes | — | SQLD002 | — | — |
| drizzle_not_null | raw | drizzle-pr5074 | yes | — | — | — | — |
| drizzle_not_null | raw-tx | drizzle-pr5074 | yes | — | SQLD002 | — | — |
| drizzle_not_null | drizzle | drizzle-pr5784+5074 | yes | — | — | — | — |
| drizzle_not_null | raw | drizzle-pr5784+5074 | yes | — | — | — | — |
| drizzle_not_null | raw-tx | drizzle-pr5784+5074 | yes | — | SQLD002 | — | — |
| drizzle_objects | drizzle | drizzle-pr5784 | yes | — | — | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | raw | drizzle-pr5784 | yes | — | — | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | raw-tx | drizzle-pr5784 | yes | — | SQLD002 | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | drizzle | drizzle-pr5074 | yes | — | SQLD002 | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | raw | drizzle-pr5074 | yes | — | — | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | raw-tx | drizzle-pr5074 | yes | — | SQLD002 | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | drizzle | drizzle-pr5784+5074 | yes | — | — | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | raw | drizzle-pr5784+5074 | yes | — | — | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_objects | raw-tx | drizzle-pr5784+5074 | yes | — | SQLD002 | — | lost index:idx_parents_tenant_manual; lost trigger:trg_parents_update |
| drizzle_rebuild_control | drizzle | drizzle-pr5784 | yes | — | — | — | — |
| drizzle_rebuild_control | raw | drizzle-pr5784 | yes | — | — | — | — |
| drizzle_rebuild_control | raw-tx | drizzle-pr5784 | yes | — | SQLD002 | — | — |
| drizzle_rebuild_control | drizzle | drizzle-pr5074 | yes | — | SQLD002 | — | — |
| drizzle_rebuild_control | raw | drizzle-pr5074 | yes | — | — | — | — |
| drizzle_rebuild_control | raw-tx | drizzle-pr5074 | yes | — | SQLD002 | — | — |
| drizzle_rebuild_control | drizzle | drizzle-pr5784+5074 | yes | — | — | — | — |
| drizzle_rebuild_control | raw | drizzle-pr5784+5074 | yes | — | — | — | — |
| drizzle_rebuild_control | raw-tx | drizzle-pr5784+5074 | yes | — | SQLD002 | — | — |
| rails_add_column | rails | rails-pr57128 | yes | — | — | — | — |
| rails_add_fk | rails | rails-pr57128 | yes | — | — | — | — |
| rails_add_index | rails | rails-pr57128 | yes | — | — | — | — |
| rails_default | rails | rails-pr57128 | yes | — | — | — | — |
| rails_fk_no_transaction | rails | rails-pr57128 | yes | — | — | — | — |
| rails_objects | rails | rails-pr57128 | yes | — | SQLD002 | — | lost trigger:trg_parents_update |
| rails_rebuild_control | rails | rails-pr57128 | yes | — | SQLD002 | — | — |

### Schema context

Framework paths below show both supplemental detectors. All raw-path inputs and findings are also retained in the aggregate JSON.

| Case | Pin | Schema + executed | Schema + migration only |
|---|---|---|---|
| drizzle_add_column | drizzle-pr5784 | — | — |
| drizzle_add_column | drizzle-pr5074 | — | — |
| drizzle_add_column | drizzle-pr5784+5074 | — | — |
| drizzle_add_index | drizzle-pr5784 | — | — |
| drizzle_add_index | drizzle-pr5074 | — | — |
| drizzle_add_index | drizzle-pr5784+5074 | — | — |
| drizzle_default | drizzle-pr5784 | — | — |
| drizzle_default | drizzle-pr5074 | SQLD001, SQLD002 | — |
| drizzle_default | drizzle-pr5784+5074 | — | — |
| drizzle_not_null | drizzle-pr5784 | — | — |
| drizzle_not_null | drizzle-pr5074 | SQLD001, SQLD002 | — |
| drizzle_not_null | drizzle-pr5784+5074 | — | — |
| drizzle_objects | drizzle-pr5784 | SQLD003 | SQLD003 |
| drizzle_objects | drizzle-pr5074 | SQLD002, SQLD003 | SQLD003 |
| drizzle_objects | drizzle-pr5784+5074 | SQLD003 | SQLD003 |
| drizzle_rebuild_control | drizzle-pr5784 | — | — |
| drizzle_rebuild_control | drizzle-pr5074 | SQLD002 | — |
| drizzle_rebuild_control | drizzle-pr5784+5074 | — | — |
| rails_add_column | rails-pr57128 | — | — |
| rails_add_fk | rails-pr57128 | — | — |
| rails_add_index | rails-pr57128 | — | — |
| rails_default | rails-pr57128 | — | — |
| rails_fk_no_transaction | rails-pr57128 | — | — |
| rails_objects | rails-pr57128 | SQLD002 | — |
| rails_rebuild_control | rails-pr57128 | SQLD002 | — |

## What each fix changes

Comparisons below use the recorded `current` pilot outcomes; `before` had the same cascade
and object losses, except that Rails' no-transaction diagnostic also lost children there.
The baseline is the [pilot report](pilot_report.md) and [pilot.json](pilot.json).

### Rails #57128

`rails_add_fk` and `rails_default` now preserve all three child rows under the normal
outer migration transaction; both lost all three on 8.1.4. `rails_fk_no_transaction`
continues to preserve them, as it already did on `current`. The PR is therefore effective
for the existing outer-transaction cases. The executed trace contains an initial
BEGIN/COMMIT, then foreign-key disabling, the rebuild in a savepoint, restoration of
foreign-key enforcement, and a new outer BEGIN/COMMIT. This is observable in
[the add-FK trace](runs/rails_add_fk--rails--rails-pr57128/populated/executed.sql).

The guard is narrower than arbitrary nested transaction support. At
[adapter line 704](https://github.com/emirn/rails/blob/8823c1370c7bc8910e609d1b6f27f4fc34f3d81d/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L704):

```ruby
restart = open_transactions == 1 && current_transaction.joinable? && referenced_by_destructive_foreign_key?(table_name)
```

This matrix does not test nested/nonjoinable transactions, rollback atomicity, or changes
made earlier in the outer transaction. The observed intermediate COMMIT means that row
preservation here must not be read as evidence of end-to-end migration atomicity.

`rails_objects` still loses `trg_parents_update` on populated and empty databases; both
indexes, including `idx_parents_tenant_manual`, survive. The PR retains the copy/drop
operation at [lines 735–738](https://github.com/emirn/rails/blob/8823c1370c7bc8910e609d1b6f27f4fc34f3d81d/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L735):

```ruby
copy_table(from, to, options, &block)
drop_table(from)
```

The copy path explicitly restores indexes at
[line 792](https://github.com/emirn/rails/blob/8823c1370c7bc8910e609d1b6f27f4fc34f3d81d/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L792):

```ruby
copy_table_indexes(from, to, options[:rename] || {})
```

It has no corresponding trigger-copy step. The runtime trace confirms the trigger is
never recreated. All three Rails controls remain clean. SQLD002 disappears from the two
cascade cases, including schema-prefixed lint, but remains for `rails_objects` and the
safe rebuild control: neither has a destructive incoming FK that selects the restart
path. Rails file-only lint remains clean, and schema context still does not diagnose
its missing trigger.

### Drizzle ORM #5784

With **current Kit 0.31.11 generating the SQL**, the PR migrator preserves all three
children for `drizzle_default` and `drizzle_not_null`. Its runtime trace places
`foreign_keys=OFF` before BEGIN, skips in-file FK toggles, and restores enforcement after
COMMIT. All six generated upgrades are byte-for-byte identical to the corresponding
`current` upgrades. Raw autocommit stays safe for the cascade cases; `raw-tx` still deletes
the three children because that path does not invoke the patched ORM migrator.

`drizzle_objects` still loses the manual index and trigger in all three paths, on both
populated and empty databases. The PR changes transaction orchestration, while retaining
execution of the generator's rebuild statements at
[dialect lines 993–996](https://github.com/Zelys-DFKH/drizzle-orm/blob/2b3f6d8c4b016cb470fa06caa883038d1a93babb/drizzle-orm/src/sqlite-core/dialect.ts#L993):

```typescript
if (needsFkHoist && fkPragmaRe.test(stmt)) continue;
session.run(sql.raw(stmt));
```

The current generator still drops the original table and recreates only the declared
index, as the [object-case SQL](runs/drizzle_objects--drizzle--drizzle-pr5784/generated_history/0001_after.sql)
shows. Hoisting PRAGMAs cannot restore objects absent from that SQL. All three controls
remain clean on all paths. Framework exec lint loses SQLD002 on every rebuild, and
schema-prefixed exec lint loses SQLD001 for the cascade cases; SQLD003 still diagnoses
the manual objects with schema context. File-only and both raw paths' lint are unchanged.

### Drizzle Kit #5074

With **current ORM 0.45.4 executing the PR Kit's SQL**, `drizzle_default` and
`drizzle_not_null` preserve children on all three paths, including raw-tx. The generated
upgrade backs up the declared cascade-dependent table before dropping the parent and
restores its rows afterwards. These statements come from the unchanged PR source at
[sqlgenerator lines 3781–3783 and 3828–3831](https://github.com/ZerGo0/drizzle-orm/blob/72e975734e73d4bc7f4c80a7b4f411a4ff60437e/drizzle-kit/src/sqlgenerator.ts#L3781):

```typescript
sqlStatements.push(`CREATE TEMP TABLE \`__bak_${dep}\` AS SELECT * FROM \`${dep}\`;`);
sqlStatements.push(`INSERT OR REPLACE INTO \`${dep}\` SELECT * FROM \`__bak_${dep}\`;`);
```

The manual index and trigger are still lost in `drizzle_objects`, on every path and in
both populations. The generator obtains indexes from the declared schema and emits
only those at [statementCombiner lines 79–81](https://github.com/ZerGo0/drizzle-orm/blob/72e975734e73d4bc7f4c80a7b4f411a4ff60437e/drizzle-kit/src/statementCombiner.ts#L79):

```typescript
if (Object.keys(indexes).length) {
    statements.push(...prepareCreateIndexesJson(name, '', indexes));
}
```

Neither manual object is declared in the case's TypeScript schema. The fix backs up
rows, not schema objects; the declared index survives. All three controls remain clean
on all paths. Relative to current, lint code sets and finding counts do not change on
any path; line numbers shift where backup/restore statements are added. SQLD002 correctly
notes the ineffective in-transaction PRAGMAs. Schema-prefixed SQLD001 still warns about
cascade deletion even though the generated restore repairs the measured row counts.
File-only lint remains clean; schema-prefixed object lint retains SQLD003.

### Combined #5784 + #5074

The combination uses the same PR Kit tarball as #5074 and the same PR ORM tarball as
#5784. Its generated upgrades are byte-for-byte identical to #5074's. All cascade cases
preserve rows on all paths. On the framework path, FK enforcement is disabled before
BEGIN and the generated backup/restore still runs. All controls pass. Object losses
remain exactly the same. Framework lint matches #5784 (no SQLD002; schema-prefixed
SQLD003 for objects); raw paths match #5074. This matrix finds no additional preservation
benefit over either individual fix on the framework path, and no regression from combining
them. It does not assess multi-level cascades, concurrent writes, or restore-trigger effects.

## Build and provenance

The PR states were recorded as open and unmerged on 2026-10-09. Full head/base commits,
repository names, branches, and the Rails adapter hash are in
`sources/upstream_fixes.json`. Pins are fixed commits,
not branch tips. The local `-smp.pr…` package suffix identifies a derived artifact; it
is not an upstream release version.

Rails uses a git Gemfile with the full SHA and the ActiveRecord/ActiveModel/ActiveSupport
gemspec glob. The lockfile and every trial record the resolved revision. Each run also
checks the loaded adapter's SHA-256 against the fetched PR file. This head reports
`8.2.0.alpha` and requires Ruby >=3.3.5, so the runner uses installed Ruby 3.4.3 with
Bundler 2.6.7; the baseline used Ruby 3.3.2/Bundler 2.7.0. Both use sqlite3 gem 2.9.6
and runtime SQLite 3.53.2. The head includes other Rails development changes, and the
runtime difference is a comparison limitation.

#5784 is built by **recompiling the affected module in the published base package**,
not by a full workspace build: the upstream build also runs Prisma generation and
declaration compilation for every driver, which this comparison does not need. The script downloads ORM
0.45.3 and asserts that the `dialect.ts` embedded in its source map is byte-for-byte equal
to the recorded PR base file. It then compiles the immutable head's complete
`drizzle-orm/src/sqlite-core/dialect.ts` with esbuild 0.25.4 to replace only
`sqlite-core/dialect.js`, `dialect.cjs`, and their source maps. Import specifiers are
resolved to the published relative `.js`/`.cjs` paths. The source-level delta is retained
in `sources/drizzle-pr5784.patch`; it contains the PR's shared
FK matching and synchronous/asynchronous migration changes. Unaffected runtime files
and type declarations remain from 0.45.3; only package version/provenance metadata is
also changed. The public dialect signatures do not change. Thus the executed synchronous
migrator is compiled from the actual PR source, with the base implementation elsewhere.
The async changes are included but not exercised by better-sqlite3.

For #5074, **all package runtime JavaScript entries are built from the PR source**:
`bin.cjs`, `utils.js/mjs`, `index.js/mjs`, and `api.js/mjs`. The script extracts only
drizzle-kit from the immutable source archive and uses the entry points, CLI version
define, Node 16 target, external driver list, and API require rewrite from upstream
`build.ts`. A small locked build toolchain replaces installation of the whole monorepo;
esbuild emits the runtime entries without running tsup declaration/type validation.
Published 0.31.8 supplies packaging and type declarations. Every PR runtime change is
included: `src/sqlgenerator.ts`, `src/statementCombiner.ts`, `src/utils/cascade.ts`,
`src/cli/commands/sqlitePushUtils.ts`, and `src/cli/commands/libSqlPushUtils.ts`;
`src/jsonStatements.ts` contributes the internal statement type. Only `generate` is
exercised here; push, API, and D1 execution are not tested. The builder retains esbuild
input manifests inside the tarball to show which sources enter each bundle.

All runner installs retain better-sqlite3 **12.4.1** and Node **v22.22.2**, with runtime
SQLite **3.50.4**. The unaffected top-level package stays at current: Kit 0.31.11 for
#5784, ORM 0.45.4 for #5074. Existing shared npm dependency resolutions are preserved
from current's lockfile. Kit 0.31.8's loader dependency is esbuild-register 3.6.0 (with
debug/ms), replacing current Kit's tsx loader dependency; that is part of the affected
package's upstream dependency graph. The PR bases are older than current, so these
are pinned-head comparisons, not claims about a patch applied to the latest release.
Raw execution and snapshots continue to use Python 3.11.5 / SQLite 3.41.2.

`sources/upstream_builds.json` records base-tarball
integrity, source and runtime hashes, and output-tarball hashes. The harness checks
installed runtime hashes before accepting each PR trial. The tarballs total about
3.1 MiB and are retained alongside all runner and build-tool lockfiles. Build workspaces
are temporary directories inside the checkout and removed by the build script.
No generated migration SQL is edited.

A second build of both tarballs produced identical files; their hashes and sizes are in
`results/upstream_build_validation.json`.

## Outcomes and limits

No documented cascade case loses rows on a framework path, and all 12 framework control
runs pass. Four framework object-loss runs succeed on an empty database. All lint
inputs are available.

All intended schema changes hold, both SQLite checks are clean, and foreign-key
enforcement returns to ON in all 122 trials. The object-loss cases also fail schema
invariants on empty databases; the `Empty` detector deliberately measures execution
errors only. Equal row counts do not prove row-value preservation, SQL equivalence,
trigger behavior, transaction atomicity, or safety for every migration.

## Reproduction

Install the retained tarballs and run into a fresh result directory:

```sh
.venv/bin/python scripts/setup.py --upstream
.venv/bin/python -m smp upstream-fixes --labels rails-pr57128 drizzle-pr5784 drizzle-pr5074 drizzle-pr5784+5074 --output results/upstream-reproduction
.venv/bin/python scripts/validate_results.py results/upstream-reproduction/upstream_fixes.json --compare results/upstream_fixes.json
```

To rebuild the tarballs first, run `.venv/bin/python scripts/build_upstream.py`.
The README in the repository root lists the pins and commands. Raw observations are in
[upstream_fixes.json](upstream_fixes.json); each row links through its `artifacts` field
to generated histories, populated/empty snapshots, execution traces, and all four lint
inputs.
