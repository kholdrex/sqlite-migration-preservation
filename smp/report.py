import hashlib
import json
from pathlib import Path

PILOT_OUTCOMES = "ff2293558639a21f017146bd0f32d038ab52c8c9e90f6b8b60c270fbd6487d17"
OMITTED = ("The outcomes in this result differ from the recorded run for which the interpretation of this report "
           "was written. That interpretation is left out; the counts and tables are computed from this result.")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_outcomes(runs):
    """What the prose of the pilot reports refers to: executions, violations and lint codes per run."""
    return digest(sorted([r["case"], r["path"], r["version_label"], violation_label(r),
                          [t["execution"]["success"] for _, t in sorted(r["trials"].items())],
                          [lint_codes(r, mode) for mode in sorted(r["detectors"]["lint"])]] for r in runs))


def lint_codes(run, mode):
    result = run["detectors"]["lint"][mode]
    if not result["available"]:
        return "unavailable"
    codes = sorted({finding["code"] for finding in result["output"]["findings"]})
    return ", ".join(codes) or "—"


def violation_label(run):
    labels = []
    for violation in run["trials"]["populated"]["violations"]:
        if violation["kind"] == "row_count":
            labels.append(f"{violation['table']} {violation['before']}→{violation['after']}")
        elif violation["kind"] == "missing_object":
            labels.append("lost " + violation["object"])
        else:
            labels.append(violation["kind"])
    return "; ".join(labels) or "—"


def gate_results(runs):
    framework = [r for r in runs if r["path"] in ("rails", "drizzle")]
    hazards = {r["case"] for r in framework if r["role"] == "hazard"
               and "github.com" in r["provenance"]
               and r["trials"]["populated"]["execution"]["success"]
               and r["trials"]["populated"]["violations"]}
    controls = [r for r in framework if r["role"] == "control"]
    controls_clean = bool(controls) and all(r["trials"]["populated"]["execution"]["success"]
                                          and not r["trials"]["populated"]["violations"] for r in controls)
    misses = [r for r in framework if r["trials"]["populated"]["execution"]["success"]
              and r["detectors"]["populated_invariants"]["detected"]
              and not r["detectors"]["empty_db"]["detected"]]
    lint_available = all(v["available"] for r in runs for v in r["detectors"]["lint"].values())
    return {"G1": {"status": "GO" if len(hazards) >= 2 and controls_clean else "UNCLEAR",
                    "documented_cases_reproduced": sorted(hazards), "framework_control_runs": len(controls),
                    "controls_clean": controls_clean},
            "G2": {"status": "GO" if misses and lint_available else "UNCLEAR",
                    "framework_violations_missed_by_empty_execution": len(misses),
                    "lint_available_for_all_inputs": lint_available}}


def write_report(result, output):
    runs = result["runs"]
    gates = result["gates"]
    silent = sum(r["trials"]["populated"]["execution"]["success"] and bool(r["trials"]["populated"]["violations"]) for r in runs)
    empty_success = sum(r["trials"]["empty"]["execution"]["success"] for r in runs)
    controls = [r for r in runs if r["role"] == "control"]
    clean_controls = sum(r["trials"]["populated"]["execution"]["success"] and not r["trials"]["populated"]["violations"] for r in controls)
    recorded = run_outcomes(runs) == PILOT_OUTCOMES
    lines = [
        "# SQLite migration preservation pilot", "",
        f"Observed: {result['observed_at']}.", "",
        f"{silent}/{len(runs)} populated trials completed successfully while violating preservation invariants. "
        f"All {empty_success}/{len(runs)} empty executions succeeded. "
        f"Designated controls were clean in {clean_controls}/{len(controls)} runs.", "",
        *([] if recorded else [OMITTED, ""]),
        "## Versions and execution", "",
        "`before` and `current` denote these exact pins, resolved from upstream registries on 2026-10-09:", "",
        "| Component | before | current |", "|---|---|---|",
    ]
    for framework, packages in result["pins"].items():
        for package in packages["before"]:
            lines.append(f"| {package} | {packages['before'][package]} | {packages['current'][package]} |")
    observed = {}
    for run in runs:
        metadata = run["trials"]["populated"]["execution"]
        observed[f"{run['path']}/{run['version_label']}"] = metadata.get("sqlite", "unavailable")
    lines += ["", f"Host: `{result['environment']['platform']}`. Python {result['environment']['python']} "
              f"uses SQLite {result['environment']['observer_sqlite']} for both snapshots and raw execution. "
              "Ruby 3.3.2 and Node v22.22.2 execute the framework paths. Runtime SQLite versions: "
              + "; ".join(f"{path}: {version}" for path, version in sorted(observed.items())) + ".", "",
              "Gemfile.lock and package-lock.json pin transitive dependencies. The better-sqlite3 driver is held "
              "constant across Drizzle versions. Different SQLite engines across languages remain a comparison "
              "limitation, although the same cascade mechanism reproduces in all three engines.", "",
              f"sqlite-doctor binary SHA-256: `{result['environment']['sqlite_doctor_sha256']}`. "
              "It exposes no version flag; JSON protocol version is 1. The binary is not vendored.", "",
              "ActiveRecord uses `MigrationContext#migrate`, not a direct adapter call. Drizzle uses its "
              "better-sqlite3 `migrate()` function on SQL produced by two real `drizzle-kit generate` invocations. "
              "Only the generated upgrade enters the execution journal because fixtures establish the starting schema. "
              "Each trial uses a fresh database with foreign-key enforcement enabled before migration.", "",
              "## Detector comparison", "",
              "Every row below represents one populated/empty pair. `Empty` means execution raised an error; "
              "it does not run preservation assertions. `Exec lint` uses runtime SQL, including transactions and "
              "PRAGMAs. `File lint` uses the generated Drizzle file or the Rails SQL trace with transaction and "
              "migration bookkeeping statements removed. `—` means no finding. Lint codes are warnings about SQL "
              "patterns, not proof of a realized violation. Invariant cells name the observed violation.", "",
              "| Case | Path | Pin | Success | Empty | Exec lint | File lint | Populated invariants |",
              "|---|---|---|---|---|---|---|---|" ]
    for run in runs:
        success = run["trials"]["populated"]["execution"]["success"]
        lines.append(f"| {run['case']} | {run['path']} | {run['version_label']} | {'yes' if success else 'no'} | "
                     f"{'error' if run['detectors']['empty_db']['detected'] else '—'} | "
                     f"{lint_codes(run, 'executed')} | {lint_codes(run, 'migration_only')} | {violation_label(run)} |")
    lines += ["", "### Schema context sensitivity", "",
              "These supplemental inputs prepend the starting schema; they are not file-only lint. Both pinned "
              "versions give the following results. Raw transaction behavior follows Drizzle's executed trace; "
              "raw autocommit follows its migration-only fragment.", "",
              "| Case | Path | Schema + executed | Schema + migration only |", "|---|---|---|---|"]
    for run in runs:
        if run["version_label"] == "current" and run["path"] in ("rails", "drizzle"):
            lines.append(f"| {run['case']} | {run['path']} | {lint_codes(run, 'schema_and_executed')} | {lint_codes(run, 'schema_and_migration')} |")
    interpretation = ["",
        "The `rails_fk_no_transaction` row above describes current only: before still emits SQLD002. "
        "All raw and both-version context findings are retained in pilot.json.", "",
        "SQLD002 correctly recognizes ineffective foreign-key toggles in transactional rebuilds. Removing "
        "the framework's transaction statements makes every migration-only input clean, including the "
        "migrations that actually delete children. Executed SQL without the original schema does not supply "
        "the existing child foreign-key or manual-object declarations needed for SQLD001/SQLD003.", "",
        "Adding schema context enables SQLD001 for Drizzle cascade cases and SQLD003 for its missing manual "
        "index/trigger. Rails uses two create/copy/drop passes rather than Drizzle's create/copy/drop/rename "
        "shape, so this linter still misses Rails-specific cascade/object diagnoses even with schema context. "
        "It does warn about the transactional PRAGMA via SQLD002.", "",
        "The rebuild controls have no dependent foreign keys or triggers on the rebuilt parent and preserve "
        "all invariants, yet executed lint warns SQLD002. This is a false alarm if a warning is classified as "
        "actual preservation loss; the narrower claim that the PRAGMA is ineffective is correct. Add-column "
        "and add-index controls produce no lint warnings. Thus runtime trace lint catches a mechanism but "
        "does not establish whether populated state is lost.", "",
        "## Reproduction and version boundaries", "",
        "- Rails [#55866](https://github.com/rails/rails/issues/55866): `rails_add_fk` reproduces child deletion "
        "with both 8.0.3 and 8.1.4. [The original account](https://kyrylo.org/software/2025/09/27/a-mere-add-foreign-key-can-wipe-out-your-whole-rails-sqlite-production-table.html) "
        "describes the same add-foreign-key operation on a parent with cascade children.",
        "- Rails [#55907](https://github.com/rails/rails/pull/55907), merged 2025-10-17: tag-source inspection "
        "places the adapter transaction-order fix in 7.2.3, 8.0.4, and 8.1.0; it is absent from 7.2.2.2 and "
        "8.0.3. The current 8.1.4 retains that fix. The `disable_ddl_transaction!` diagnostic loses children "
        "on 8.0.3 but preserves them on 8.1.4. Intermediate tags were source-inspected, not executed.",
        "- Rails [#57128](https://github.com/rails/rails/pull/57128) remains open in the recorded API evidence. "
        "The normal outer migration transaction defeats the adapter fix: both add-foreign-key and default "
        "changes still delete children on 8.1.4. This is a reduced reproduction of the documented transaction "
        "mechanism, not the follow-up's entire rename/SET NULL test suite.",
        "- Drizzle [#4938](https://github.com/drizzle-team/drizzle-orm/issues/4938): the reported ORM 0.44.2 / "
        "Kit 0.31.4 pair reproduces cascade deletion when a parent becomes NOT NULL. Its original report used "
        "Cloudflare D1; this pilot reproduces the mechanism through the better-sqlite3 driver, not D1.",
        "- Drizzle [#5782](https://github.com/drizzle-team/drizzle-orm/issues/5782): changing a parent default "
        "reproduces the documented better-sqlite3 migrator interaction on both pinned pairs, including ORM "
        "0.45.4 / Kit 0.31.11. No fix is observed in that latest stable pair. Raw autocommit preserves children "
        "for both generated migrations; raw-tx deletes them.",
        "- Object-loss probes are extensions grounded in SQLite's "
        "[rebuild procedure](https://www.sqlite.org/lang_altertable.html#otheralter), not claims that the "
        "linked ORM issues report trigger loss. Rails loses the manual trigger but preserves both indexes. "
        "Drizzle preserves its declared index but loses the manual index and trigger in both versions, "
        "including raw autocommit. No version-level fix for these object losses was observed.", "",
        "In every cascade-loss trial, children fall from three rows to zero while parents remain at two. "
        "Both SQLite checks return clean results: deleted children create no orphaned references or physical "
        "corruption. Every intended schema change is present. No view definition was lost or altered; the "
        "view references the stable child table, so parent-dependent view rebuild failures are untested. "
        "SQLite documents that foreign-key toggles are ineffective within a transaction "
        "([PRAGMA reference](https://www.sqlite.org/pragma.html#pragma_foreign_keys)).", "",]
    lines += interpretation if recorded else [""]
    lines += [
        "## Outcomes and limits", "",
        f"Documented hazards reproduce in {len(gates['G1']['documented_cases_reproduced'])} "
        "case families through real framework paths: " + ", ".join(gates['G1']['documented_cases_reproduced']) + ". "
        f"All {gates['G1']['framework_control_runs']} designated framework control runs preserve the checked invariants. "
        "These are multiple documented case instances, not independent root causes; cascade cases share the "
        "same transactional mechanism. Trigger/index loss adds a separate preservation failure.", "",
        f"Populated invariants detect {gates['G2']['framework_violations_missed_by_empty_execution']} "
        "framework violations missed by empty execution. File-only lint misses them all; runtime lint warns "
        "about transactional PRAGMAs, while schema context and rebuild shape determine more specific coverage. "
        "Safe rebuild warnings demonstrate why lint warnings and realized loss must be scored separately.", "",
        *(["Population is essential to exposing the nine framework cascade-loss runs. The four framework "
           "object-loss runs would also be caught on empty databases if schema invariants were checked there; "
           "the empty-db detector here measures execution success alone. Empty-trial snapshots and invariant "
           "results are retained separately in the raw data so this distinction can be inspected.", "",
           "The two safe rebuild controls were added after the first 42-pair exploratory run to measure "
           "SQLD002's specificity. The final 50-pair matrix reruns the original fixtures unchanged and includes "
           "those controls.", ""] if recorded else []),
        "This is a small, purposive deterministic pilot; rates are descriptive and do not estimate ecosystem prevalence.", "",
        "Rows with equal cardinality but changed values, SET NULL effects, reordered data, and semantic "
        "trigger behavior are outside the implemented invariants. Schema-object comparison is normalized "
        "text, not general SQL equivalence. Only declared application tables enter row-count comparisons; "
        "framework bookkeeping is excluded. The fixtures have valid data and no concurrency. Neither "
        "Cloudflare D1 nor every released ORM/driver combination is covered.", "",
        "Kit 0.31.4 prints an ENOENT and exits zero when given an absolute output path. The harness therefore "
        "uses relative output paths and verifies that both migration journal entries exist; a generation "
        "without them is a setup failure, not a migration outcome.", "",
        "## Evidence and reproduction", "",
        "Each `runs/<case>--<path>--<pin>/result.json` contains before/after snapshots, all invariant "
        "findings, execution status and versions, and the full linter JSON. Adjacent SQL files retain all "
        "four lint inputs. `populated/` and `empty/` retain runner metadata and SQL traces; Rails additionally "
        "retains structured log events. `generated_history/` retains both Drizzle "
        "migrations, snapshots, and the journal. Trial databases are not kept.", "",
        "Run `.venv/bin/python -m smp pilot --output results/<new directory>` from the repository root. "
        "The README in the repository root describes the setup. "
        "`sources/upstream.json` records registry versions, issue states, release dates, "
        "and inspected Rails source hashes. [pilot.json](pilot.json) contains the per-trial observations.", "",
    ]
    Path(output).write_text("\n".join(lines))
