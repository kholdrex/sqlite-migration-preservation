"""Readable tables derived exclusively from observed matrix rows."""
from collections import Counter

from .matrix_spec import CONTEXTS
from .rebuild import CLASSIFIER
from .report import digest

ABBREVIATIONS = {"row_count": "R", "content_digest": "D", "missing_object": "O", "changed_object": "O",
                 "trigger_behavior": "T", "view_rows": "V", "view_errors": "V", "fk_enforcement": "E",
                 "foreign_key_check": "F", "foreign_key_definition": "K", "integrity_check": "I", "errors": "Q", "intended_change_missing": "C"}


def matrix_outcomes(rows):
    """What the prose of a matrix report refers to: outcome, violated invariants and rebuild flag per trial."""
    return digest(sorted([r["framework"], r["version_label"], r.get("mode", "default"), r["path"], r["operation"],
                          r["context"], [[t["outcome"], sorted({v["kind"] for v in t["violations"]}), t["rebuild"]]
                                         for _, t in sorted(r["trials"].items())]] for r in rows))


def codes(row):
    return ",".join(sorted({ABBREVIATIONS[v["kind"]] for v in row["trials"]["populated"]["violations"]}))


def cell(row):
    outcome = row["outcome"]
    if outcome == "silent-loss":
        return f"silent-loss({codes(row)})"
    if outcome.startswith("failed-loudly"):
        return "loud-partial" if outcome.endswith("partial") else "loud"
    return outcome


def lint_codes(result):
    if not result["available"]:
        return "unavailable"
    return ",".join(sorted({f["code"] for f in result["output"].get("findings", [])})) or "—"


def write_report(result, path):
    rows = result["rows"]
    lines = ["# SQLite operation preservation matrix", "", f"Observed: {result['observed_at']}.", "",
             f"{len(rows)} populated/empty pairs ({len(rows)*2} executions); {len(result['errors'])} infrastructure errors.", "",
             "Cells: preserved; loud = failed-loudly (application state rolled back); loud-partial = failed-loudly-partial; "
             "silent-loss = successful execution with a violated invariant. **Bold** cells differ from current on the same path. "
             "A trailing `†` marks a table rebuild in the executed SQL, including rebuilds of dependent tables: "
             + ("a table dropped after its rows were copied into a table created in the same SQL. "
                if result.get("rebuild_classifier") == CLASSIFIER else "a CREATE TABLE together with a DROP TABLE. ") +
             "A failing execution may stop before reaching a planned rebuild.", "",
             "Invariants: R row count; D content digest; O schema object; T trigger behavior; V view rows/compilation; "
             "E FK enforcement; F foreign_key_check; K FK definition; I integrity_check; Q snapshot error; C intended change.", "",
             "| Context | Dependency |", "|---|---|"]
    lines += [f"| {key} | {value} |" for key, value in CONTEXTS.items()]
    lines += ["", "## Counts", "", "Counts are operation × context cells per execution path, not estimates of ecosystem prevalence.", "",
              "| Framework | Pin | Path | Cells | Silent-loss | Loud | Loud-partial | Preserved | Rebuilds |", "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    groups = sorted({(r["framework"], r["version_label"], r["path"]) for r in rows})
    for fw, pin, execution in groups:
        group = [r for r in rows if (r["framework"], r["version_label"], r["path"]) == (fw, pin, execution)]
        counts = Counter(r["outcome"] for r in group)
        lines.append(f"| {fw} | {pin} | {execution} | {len(group)} | {counts['silent-loss']} | {counts['failed-loudly']} | {counts['failed-loudly-partial']} | {counts['preserved']} | {sum(r['rebuild'] for r in group)} |")
    operation_keys = {(r["framework"], r["operation"], r["version_label"], r["path"]) for r in rows}
    supported = {(r["framework"], r["operation"], r["version_label"], r["path"]) for r in rows
                 if r["trials"]["populated"]["execution"]["success"]
                 and not any(v["kind"] == "intended_change_missing" for v in r["trials"]["populated"]["violations"])}
    if supported == operation_keys:
        lines += ["", "Every selected operation/pin/path successfully applies its intended change in at least one "
                  "context. No unsupported operations were observed."]
    totals = Counter(r["outcome"] for r in rows)
    lines += ["", "## Findings", "",
              f"Across the selected pins and paths, {totals['silent-loss']} populated pairs silently violate preservation, "
              f"{totals['failed-loudly']} fail with application state rolled back, {totals['failed-loudly-partial']} "
              f"fail after partial commit, and {totals['preserved']} preserve the checked state.", ""]
    for framework in ("rails", "drizzle"):
        for pin in result["pins"][framework]:
            selected = [r for r in rows if r["framework"] == framework and r["version_label"] == pin and r["path"] == framework]
            if not selected:
                continue
            loss = [r for r in selected if r["outcome"] == "silent-loss"]
            contexts = Counter(r["context"] for r in loss)
            detail = ", ".join(f"{context}: {count}" for context, count in sorted(contexts.items())) or "none"
            lines.append(f"- {framework} / {pin}, framework path: {len(loss)}/{len(selected)} silent-loss cells ({detail}).")
    rename = [r for r in rows if r["framework"] == "drizzle" and r["version_label"] == "current"
              and r["path"] == "drizzle" and r["operation"] == "rename_table" and r["context"] == "C4"]
    if rename and rename[0]["outcome"] == "silent-loss":
        lines += ["", "Drizzle current's rename_table × C4 loses grandchildren: Kit renames the parent and then rebuilds "
                  "children to update their FK. A native parent rename can therefore trigger a dependent-table rebuild. "
                  "The retained rename_table × C4 generation archive contains the exact sequence."]
    set_null = [r for r in rows if r["framework"] == "drizzle" and r["version_label"] == "drizzle-pr5074"
                and r["path"] == "drizzle" and r["context"] == "C2" and r["outcome"] == "silent-loss"]
    if set_null:
        lines += ["", f"Kit #5074 still loses FK values in {len(set_null)} C2 framework cells while retaining row counts. "
                  "Its cascade backup does not repair these SET NULL effects. ORM #5784 changes migration connection "
                  "orchestration; raw and raw-tx bypass that code, so its benefit must be evaluated per execution path."]
    view_failures = [r for r in rows if r["context"] == "C7" and r["outcome"].startswith("failed-loudly")]
    if view_failures:
        partial = sum(r["outcome"] == "failed-loudly-partial" for r in view_failures)
        lines += ["", f"Parent-view context C7 has {len(view_failures)} failed populated pairs, including {partial} "
                  "with partial commit. Error status alone cannot distinguish those failures from rollback; "
                  "persisted application state is compared separately."]
    silent = [r for r in rows if r["outcome"] == "silent-loss"]
    empty_catches = sum(r["detectors"]["empty_db"] for r in silent)
    empty_violations = sum(bool(r["trials"]["empty"]["violations"]) for r in silent)
    lines += ["", f"Empty execution catches {empty_catches}/{len(silent)} populated silent-loss cells; checking invariants "
              f"on those empty trials would catch {empty_violations}. The empty-db detector intentionally measures "
              "execution errors only. Equal row counts miss C2 value losses."]
    checked = {"intended_change_missing", "fk_enforcement", "foreign_key_check", "integrity_check"}
    if silent and not any(v["kind"] in checked for r in silent for v in r["trials"]["populated"]["violations"]):
        lines += ["", "Every silent-loss trial still has its intended change, FK enforcement ON, and clean "
                  "foreign_key_check and integrity_check results."]
    baseline = {(r["framework"], r["path"], r["operation"], r["context"]): r for r in rows if r["version_label"] == "current"}
    for fw, pin, execution in sorted(groups, key=lambda g: (g[0], g[1] != "current", g[1], g[2])):
        group = [r for r in rows if (r["framework"], r["version_label"], r["path"]) == (fw, pin, execution)]
        lookup = {(r["operation"], r["context"]): r for r in group}
        lines += ["", f"## {fw} / {pin} / {execution}", "", "| Operation | " + " | ".join(CONTEXTS) + " |", "|---|" + "---|" * len(CONTEXTS)]
        for operation in sorted({r["operation"] for r in group}):
            cells = []
            for context in CONTEXTS:
                row = lookup.get((operation, context))
                if row is None:
                    cells.append("not run")
                    continue
                value = cell(row) + ("†" if row["rebuild"] else "")
                previous = baseline.get((fw, execution, operation, context))
                if pin != "current" and previous and (cell(previous), previous["rebuild"]) != (cell(row), row["rebuild"]):
                    value = f"**{value}**"
                cells.append(value)
            lines.append(f"| {operation} | " + " | ".join(cells) + " |")
    lines += ["", "## Detector coverage of every silent-loss cell", "",
              "Rows group contexts only when the operation, pin, path, violations and detector results are identical. "
              "Empty-db means execution error only. Lint warnings are pattern findings, not proof of loss. "
              "The unchanged schema-prefixed lint variants are also retained in JSON.", "",
              "| Framework | Pin | Path | Operation | Contexts | Violations | Empty-db | Exec lint | File lint | Populated invariants |", "|---|---|---|---|---|---|---|---|---|---|"]
    coverage = {}
    for row in rows:
        if row["outcome"] != "silent-loss":
            continue
        d = row["detectors"]
        key = (row["framework"], row["version_label"], row["path"], row["operation"], codes(row),
               "yes" if d["empty_db"] else "—", lint_codes(d["lint"]["executed"]), lint_codes(d["lint"]["migration_only"]))
        coverage.setdefault(key, []).append(row["context"])
    for key, contexts in sorted(coverage.items()):
        fw, pin, execution, operation, violations, empty, executed, file = key
        lines.append(f"| {fw} | {pin} | {execution} | {operation} | {','.join(contexts)} | {violations} | {empty} | {executed} | {file} | yes |")
    lines += ["", "## Scope, interpretation, and reproduction", "",
              "All listed operations are attempted through the installed framework DSL or real Kit schema diff and generate command. "
              "Rename prompts select the single old column/table; generated migration SQL is never edited. "
              "No execution failure is automatically labeled unsupported. The operation names set/drop_not_null map to Rails change_column_null(false/true); "
              "change_type maps to Rails change_column(:integer). The complete-matrix validator requires successful execution with the intended change in at least one context for every operation/pin/path.", "",
              "The common parent contains id, payload, value and tenant_id. Incoming FKs target its stable id. "
              "The changed column is value; the external trigger updates audit on a payload update, the external index covers tenant_id, "
              "and the view selects id,payload. C8 has a separate ancestor_id cascading FK, so add/drop_foreign_key still changes tenant_id. "
              "C3 uses RESTRICT, not a separate NO ACTION variant. Each operation is one migration. add_timestamps explicitly allows NULL; "
              "existing rows have distinct non-NULL numeric text values; the type conversion checks their text-normalized values. "
              "This does not cover every option, affinity conversion, dependency on a removed column, nested transaction, concurrent write, "
              "trigger restore side effect, D1 driver, or framework release.", "",
              "Content digests use SHA-256 over ordered primary-key projections. Intentional column drops omit only the dropped field; "
              "renames map old to new names. New columns are checked structurally. View result rows and compilation are checked, and "
              "the trigger is probed under a rolled-back savepoint on both populated and empty databases. FK enforcement is read on "
              "the migration connection before it closes, not inferred from an observer connection. SQLite FK/integrity checks remain enabled. "
              "Failed-loudly versus partial compares persisted application schema and all application rows, including newly left-over tables; "
              "framework bookkeeping is excluded. Intermediate commits with no net application-state change are not classified as partial. "
              "No failed migration is classified as silent-loss, even when it leaves damage.", "",
              "Pins, runtime differences and the PR packages are described in `results/upstream_fixes.md`. "
              "Snapshots/raw paths use Python SQLite; Rails and Drizzle use their installed native SQLite versions. "
              "The PR pins include their upstream base/head differences and are not patches on current.", "",
              "The README in the repository root gives the command with the pin labels of each retained run. A run writes to a new "
              "output directory, for example `.venv/bin/python -m smp operation-matrix --output results/<new directory>`, "
              "and is checked with `.venv/bin/python scripts/validate_operation_matrix.py results/<new directory>/operation_matrix.json`. "
              "`--frameworks`, `--operations`, `--contexts`, and `--labels` select subsets. Compact specs and templates live in `smp/matrix_spec.py`; generated fixtures are temporary. "
              "Raw rows, snapshots, outcomes and full lint responses are in [operation_matrix.json](operation_matrix.json). "
              "Each row links to a compressed JSON archive containing exact traces, runner logs, fixture SQL and its spec; "
              "shared per-case/per-pin generation archives retain both Kit migrations, snapshots, journal and prompt logs. "
              "Per-trial databases and redundant lint SQL copies are removed after observation; lint input strings reconstruct exactly "
              "from fixture SQL plus the retained traces/migration SQL.", ""]
    if result["errors"]:
        lines += ["## Infrastructure errors", "", "```", str(result["errors"]), "```", ""]
    path.write_text("\n".join(lines))
