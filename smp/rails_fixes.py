"""Run and report the additional Rails PR pins."""
import json
import re
from collections import Counter
from pathlib import Path

from .environment import ROOT
from .matrix_report import cell, matrix_outcomes
from .matrix_spec import CONTEXTS
from .operation_matrix import read_gzip, run_matrix
from .pilot import DEFAULT_DOCTOR, run_case
from .report import OMITTED, digest, gate_results, run_outcomes

LABELS = ("rails-pr56811", "rails-pr58709", "rails-pr57128+56811", "rails-pr58709+56811")
COMPARISONS = ("current", "rails-pr57128")
FIXES_OUTCOMES = "3cda5f7619d0dc6a985f079602447db825715577474c5479cef00dc4e7e59b58"


def fixes_outcomes(result):
    return digest([matrix_outcomes(result["comparison_rows"] + result["rows"]),
                   run_outcomes(result["comparison_pilot_runs"] + result["pilot"]["runs"])])


def transaction_counts(row, population):
    sql = read_gzip(ROOT / row["artifacts"])["evidence"][population]["executed.sql"]
    return {name: len(re.findall(pattern, sql, re.I | re.M)) for name, pattern in {
        "begin": r"^BEGIN\b", "commit": r"^COMMIT\b", "rollback": r"^ROLLBACK\b",
        "savepoint": r"^SAVEPOINT\b", "release": r"^RELEASE\b",
    }.items()}


def collect(output, doctor=DEFAULT_DOCTOR, workers=6):
    output = Path(output).resolve()
    detail = output / "rails-fixes"
    result = run_matrix(detail, doctor, workers, frameworks=["rails"], labels=LABELS)
    if result["errors"]:
        raise RuntimeError("Rails matrix has infrastructure errors")
    runs = []
    for label in LABELS:
        for case in sorted((ROOT / "cases").glob("rails_*")):
            folder = detail / "pilot" / f"{case.name}--{label}"
            if (folder / "result.json").exists():
                run = json.loads((folder / "result.json").read_text())
            else:
                print(f"Pilot: {case.name} / {label}", flush=True)
                run = run_case(case, "rails", label, folder, doctor)
            runs.append(run)
            for database in folder.rglob("database.db*"):
                database.unlink()
    pilot = {"format_version": 1, "observed_at": result["observed_at"], "runs": runs,
             "gates": gate_results(runs),
             "pins": {"rails": {p: result["pins"]["rails"][p] for p in LABELS}, "drizzle": {}},
             "upstream_fixes": {p: result["upstream_fixes"][p] for p in LABELS}, "upstream_builds": {}}
    (detail / "pilot.json").write_text(json.dumps(pilot, indent=2) + "\n")
    baseline = json.loads((ROOT / "results/operation_matrix.json").read_text())
    result["comparison_rows"] = [r for r in baseline["rows"]
                                 if r["framework"] == "rails" and r["version_label"] in COMPARISONS]
    result["pilot"] = pilot
    result["comparison_pilot_runs"] = []
    for filename in ("pilot.json", "upstream_fixes.json"):
        previous = json.loads((ROOT / "results" / filename).read_text())
        result["comparison_pilot_runs"].extend(r for r in previous["runs"]
                                              if r["path"] == "rails" and r["version_label"] in COMPARISONS)
    result["transaction_counts"] = {
        r["artifacts"]: {p: transaction_counts(r, p) for p in ("populated", "empty")}
        for r in result["rows"] + result["comparison_rows"]}
    if (output / "rails_atomicity.json").exists():
        result["atomicity"] = json.loads((output / "rails_atomicity.json").read_text())
    (output / "rails_fixes.json").write_text(json.dumps(result, separators=(",", ":")) + "\n")
    write_report(result, output / "rails_fixes.md")
    for name in ("operation_matrix.json", "operation_matrix.md"):
        (detail / name).unlink()
    return result


def write_report(result, destination):
    rows = result["comparison_rows"] + result["rows"]
    labels = COMPARISONS + LABELS
    baseline = {(r["operation"], r["context"]): r for r in result["comparison_rows"]
                if r["version_label"] == "current"}
    recorded = fixes_outcomes(result) == FIXES_OUTCOMES
    lines = ["# Rails fixes: operation preservation", "", f"Observed: {result['observed_at']}.", "",
             f"{len(result['rows'])} additional operation/context pairs ({2 * len(result['rows'])} executions), "
             f"plus {len(result['pilot']['runs'])} pilot pairs ({2 * len(result['pilot']['runs'])} executions). "
             "Each pin runs all 16 Rails operations across C0–C8 on populated and empty databases. "
             "The original pilot has 13 cases total: seven Rails and six Drizzle; all seven existing Rails cases "
             "are run on each new pin, with the fixtures, invariants and outcome classification of the operation matrix.", "",
             *(["Both combined pins have **no silent-loss cells in this matrix**, on either population. "
                "#56811 alone retains 36 populated FK-loss cells; #58709 alone retains 12 trigger-loss cells. "
                "All matrix and pilot executions succeed. These results cover the tested contexts, not arbitrary migrations."]
               if recorded else [OMITTED]), "",
             "## Pins and merge resolution", "",
             "| Pin | Resolved revision | Adapter SHA-256 |", "|---|---|---|"]
    for label in LABELS:
        pin = result["upstream_fixes"][label]
        lines.append(f"| {label} | `{pin['commit']}` | `{pin['adapter_sha256']}` |")
    lines += ["", "Each Gemfile uses a full Git SHA and the ActiveRecord/ActiveModel/ActiveSupport gemspec glob. "
              "Every populated and empty execution records the Bundler resolved revision and loaded adapter SHA-256; "
              "both are checked against `sources/upstream_fixes.json`. "
              "New pins use installed Ruby 3.4.3 and Bundler 2.6.7, ActiveRecord 8.2.0.alpha, sqlite3 gem 2.9.6 "
              "and SQLite 3.53.2. Current uses Ruby 3.3.2 and ActiveRecord 8.1.4; #57128 uses Ruby 3.4.3. "
              "Observers use Python SQLite 3.41.2. Lockfiles retain full dependency resolutions. "
              "These are upstream-head comparisons with different base dates, not isolated patches on current.", "",
              "The #57128 + #56811 pin is a local derived merge of `8823c1370c7bc8910e609d1b6f27f4fc34f3d81d` "
              "and `7ddc17783418454c0e406181ae442d0aaf558ad8`, with merge base "
              "`3faf056f240966b268dd6fa52c559e241a370d06`. The actual merge conflicted in four files: "
              "`activerecord/CHANGELOG.md`, the SQLite schema statements, the SQLite adapter, and its adapter tests. "
              "The resolution retains #57128's newer code and both changelog/test additions, adds #56811's "
              "`triggers(table_name)` query and argument, and recreates triggers immediately after the second "
              "`move_table` inside #57128's transaction. No unrelated code is changed.", "",
              "The resolution patch `sources/rails-pr57128+56811-resolution.patch` is the complete "
              "145-line addition against the first parent. `scripts/build_rails_merge.py` "
              "applies it to that immutable parent and verifies the resolved tree, source hashes and deterministic "
              "two-parent merge object. The shallow local repository is regenerated during setup.", "",
              "The #58709 + #56811 pin merges `428884a88b3a42c914f5227819b6b672325b3312` and "
              "`7ddc17783418454c0e406181ae442d0aaf558ad8`, using the same merge base "
              "`3faf056f240966b268dd6fa52c559e241a370d06`. It conflicted in `activerecord/CHANGELOG.md` "
              "and `activerecord/lib/active_record/connection_adapters/sqlite3/schema_statements.rb`; "
              "the adapter and adapter tests merged cleanly. The resolution retains #58709's newer code, "
              "both changelog entries, and #56811's trigger query. Its "
              "resolution patch `sources/rails-pr58709+56811-resolution.patch` is another "
              "145-line delta from its first parent. The same builder verifies the merged tree and immutable "
              "two-parent revision. It combines Migrator-level FK disabling with trigger recreation.", "",
              "## Counts", "",
              "Counts are cells per pin and population. Loud means failed with application state rolled back; "
              "loud-partial means failed with committed application changes.", "",
              "| Pin | Population | Silent-loss | Loud | Loud-partial | Preserved |", "|---|---|---:|---:|---:|---:|"]
    for label in labels:
        group = [r for r in rows if r["version_label"] == label]
        for population in ("populated", "empty"):
            counts = Counter(r["trials"][population]["outcome"] for r in group)
            lines.append(f"| {label} | {population} | " + " | ".join(str(counts[k]) for k in
                         ("silent-loss", "failed-loudly", "failed-loudly-partial", "preserved")) + " |")
    lines += ["", "## Operation × context", "",
              "Both populations are shown below. **Bold** cells differ from current for that population in outcome, invariant codes "
              "or observed rebuild. `†` means CREATE TABLE and DROP TABLE appeared in the executed trace. "
              "D = content digest; R = row count; O = schema object; T = trigger behavior."
              + (" All empty cells preserve for #56811 and both combined pins; #58709's empty table matches its "
                 "populated table (the same 12 C5 losses)." if recorded else ""), "", "| Context | Dependency |", "|---|---|"]
    lines += [f"| {key} | {value} |" for key, value in CONTEXTS.items()]
    for label, population in ((label, population) for label in LABELS for population in ("populated", "empty")):
        group = {(r["operation"], r["context"]): r for r in result["rows"] if r["version_label"] == label}
        lines += ["", f"### {label} / {population}", "", "| Operation | " + " | ".join(CONTEXTS) + " |",
                  "|---|" + "---|" * len(CONTEXTS)]
        for operation in sorted({k[0] for k in group}):
            cells = []
            for context in CONTEXTS:
                row, previous = group[operation, context], baseline[operation, context]
                row = {**row, "outcome": row["trials"][population]["outcome"],
                       "rebuild": row["trials"][population]["rebuild"],
                       "trials": {"populated": row["trials"][population]}}
                previous = {**previous, "outcome": previous["trials"][population]["outcome"],
                            "rebuild": previous["trials"][population]["rebuild"],
                            "trials": {"populated": previous["trials"][population]}}
                value = cell(row) + ("†" if row["rebuild"] else "")
                if (cell(row), row["rebuild"]) != (cell(previous), previous["rebuild"]):
                    value = f"**{value}**"
                cells.append(value)
            lines.append(f"| {operation} | " + " | ".join(cells) + " |")
    residual = ["", "## Residual losses and code", "",
              "**#56811:** the 12 rebuilding operations each lose rows in C1 and C4 and FK values in C2 "
              "(36 cells). C4 loses children and grandchildren. C2 keeps row counts but replaces referencing "
              "values with NULL. Trigger preservation fixes all 12 C5 cells. The adapter still calls "
              "`disable_referential_integrity do` around `transaction do` at "
              "[lines 642–647](https://github.com/aka-nez/rails/blob/7ddc17783418454c0e406181ae442d0aaf558ad8/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L642). "
              "That occurs inside Migrator's outer transaction, so `PRAGMA foreign_keys = OFF` "
              "([line 315](https://github.com/aka-nez/rails/blob/7ddc17783418454c0e406181ae442d0aaf558ad8/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L315)) "
              "does not disable FK actions. The added line is:", "", "```ruby",
              "triggers.each { |trigger_sql| execute(trigger_sql) if trigger_sql.present? }", "```", "",
              "**#58709:** all 36 FK-loss cells become preserved, but the 12 rebuilding C5 cells still "
              "lose `trg_external` and its behavior, including on empty databases. Migrator now calls "
              "`connection.transaction_for_migration(&block)` at "
              "[migration line 1607](https://github.com/nicolasva/rails/blob/428884a88b3a42c914f5227819b6b672325b3312/activerecord/lib/active_record/migration.rb#L1607). "
              "The SQLite override at "
              "[adapter lines 201–205](https://github.com/nicolasva/rails/blob/428884a88b3a42c914f5227819b6b672325b3312/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L201) "
              "disables FK enforcement before opening the migration transaction:", "", "```ruby",
              "disable_referential_integrity do", "  transaction(&block)", "end", "```", "",
              "The rebuild still uses `copy_table(from, to, options, &block)` followed by `drop_table(from)` "
              "([adapter move_table](https://github.com/nicolasva/rails/blob/428884a88b3a42c914f5227819b6b672325b3312/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L714)); "
              "indexes are copied, but there is no trigger recreation. The trace confirms the missing CREATE TRIGGER.", "",
              "**#57128 comparison:** its 12 remaining losses are also C5 triggers. Its adapter restores indexes "
              "with `copy_table_indexes(from, to, options[:rename] || {})` "
              "([line 792](https://github.com/emirn/rails/blob/8823c1370c7bc8910e609d1b6f27f4fc34f3d81d/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L792)) "
              "but has no trigger-copy step. **Both combined pins:** the merged code adds #56811's quoted trigger "
              "recreation inside each rebuild path. Each preserves all 144 populated and 144 empty cells.", "",
              "The 12 rebuilding operations are add_check_constraint, add_foreign_key, add_reference, add_timestamps, "
              "change_default, change_type, drop_not_null, remove_check_constraint, remove_column, "
              "remove_foreign_key, rename_column and set_not_null. Empty execution reports no errors on any new pin, "
              "so the existing empty-db detector catches none of the populated silent losses. "
              "The raw rows retain all four unchanged lint detector results."]
    lines += residual if recorded else []
    lines += ["", "## Controls and regressions", "",
              "| Pin | Current-preserved cells that regress | #57128-preserved cells that regress | Clean pilot controls |",
              "|---|---:|---:|---:|"]
    pilots = result["comparison_pilot_runs"] + result["pilot"]["runs"]
    for label in LABELS:
        group = {(r["operation"], r["context"]): r for r in result["rows"] if r["version_label"] == label}
        regressions = []
        for previous_label in COMPARISONS:
            regressions.append(sum(r["outcome"] == "preserved" and group[r["operation"], r["context"]]["outcome"] != "preserved"
                                   for r in result["comparison_rows"] if r["version_label"] == previous_label))
        controls = [r for r in pilots if r["version_label"] == label and r["role"] == "control"]
        clean = sum(all(t["execution"]["success"] and not t["violations"] for t in r["trials"].values()) for r in controls)
        lines.append(f"| {label} | {regressions[0]} | {regressions[1]} | {clean}/{len(controls)} |")
    if recorded:
        lines += ["", "No previously preserved current cell regresses in either population. C0 preserves for all "
                  "16 operations on all new pins, and all four operations without rebuilds preserve in every context. "
                  "Relative to #57128, #56811 alone loses the 36 FK cells that its trigger-only fix does not address; "
                  "#58709 and both combined pins have no regressions. All three original Rails pilot controls remain clean."]
    lines += ["", "## Original Rails pilot", "",
              "Each entry describes populated/empty preservation under the original, unchanged pilot checks. "
              "All executions succeed; `rows / clean` means populated child loss with an empty trial that passes "
              "its invariants. `trigger / trigger` means the trigger disappears in both populations.", "",
              "| Case | " + " | ".join(labels) + " |", "|---|" + "---|" * len(labels)]
    pilot_lookup = {(r["case"], r["version_label"]): r for r in pilots}
    for case in sorted({r["case"] for r in pilots}):
        values = []
        for label in labels:
            run = pilot_lookup[case, label]
            parts = []
            for population in ("populated", "empty"):
                trial = run["trials"][population]
                kinds = {v["kind"] for v in trial["violations"]}
                parts.append("loud" if not trial["execution"]["success"] else
                             "rows" if "row_count" in kinds else "trigger" if kinds else "clean")
            values.append(" / ".join(parts))
        lines.append(f"| {case} | " + " | ".join(values) + " |")
    lines += ["", "## Transactions and atomicity", "",
              "Counts below come from exact executed SQL for populated cells; empty cells show the same "
              "transaction counts. Bookkeeping queries are included, so these describe observed boundaries, "
              "not a general atomicity guarantee.", "",
              "| Pin | Cells with one COMMIT | Cells with two COMMITs | Cells with SAVEPOINT |", "|---|---:|---:|---:|"]
    for label in labels:
        counts = [result["transaction_counts"][r["artifacts"]]["populated"] for r in rows if r["version_label"] == label]
        lines.append(f"| {label} | {sum(c['commit'] == 1 for c in counts)} | {sum(c['commit'] == 2 for c in counts)} | {sum(c['savepoint'] > 0 for c in counts)} |")
    boundaries = ["", "For #57128 and #57128 + #56811, each of the 36 C1/C2/C4 rebuild cells contains an "
              "intermediate COMMIT, then FK disabling, a rebuild within a SAVEPOINT, FK restoration, and "
              "another BEGIN/COMMIT. Their restart condition remains "
              "`open_transactions == 1 && current_transaction.joinable? && referenced_by_destructive_foreign_key?(table_name)` "
              "([#57128 line 704](https://github.com/emirn/rails/blob/8823c1370c7bc8910e609d1b6f27f4fc34f3d81d/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L704)). "
              "Successful preservation therefore does not establish whole-migration atomicity: writes before "
              "that COMMIT could survive a later failure. The separate failure-injection experiment below "
              "tests that directly without changing the operation matrix.", "",
              "#58709 and #58709 + #56811 disable foreign_keys before BEGIN and restore it after the sole COMMIT, including "
              "for operations without rebuilds. It avoids #57128's intermediate-commit pattern in these traces. "
              "#56811 also has one COMMIT, but its rebuild PRAGMA occurs after BEGIN and does not prevent "
              "the measured FK losses. All new trials finish with FK enforcement ON. Nested transactions, "
              "arbitrary trigger dependencies and concurrent writes remain outside this experiment."]
    lines += (boundaries if recorded else []) + [""]
    if "atomicity" in result:
        from .rails_atomicity import report_lines
        lines += report_lines(result["atomicity"])
    lines += ["## Reproduction and evidence", "", "```sh",
              ".venv/bin/python scripts/setup.py --upstream --labels rails-pr56811 rails-pr58709 rails-pr57128+56811 rails-pr58709+56811",
              ".venv/bin/python -m smp rails-fixes --output results/<new directory> --workers 8",
              ".venv/bin/python -m smp rails-atomicity --output results/<new directory>",
              ".venv/bin/python scripts/validate_rails_fixes.py results/<new directory>/rails_fixes.json", "```", "",
              "A run writes to a new output directory; evidence is reused only by the linter, pins and code "
              "that produced it. [Raw rows](rails_fixes.json) include comparison rows, "
              "pilot observations, detector findings, pins and per-trial transaction counts. Row artifact paths "
              "link to gzip JSON containing exact fixtures, SQL, runtime metadata and logs.", ""]
    destination.write_text("\n".join(lines))
