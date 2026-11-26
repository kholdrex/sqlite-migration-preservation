"""Extract paper quantities from retained results; no runners or network required."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ("pilot", "upstream_fixes", "operation_matrix", "rails_fixes",
               "rails_atomicity", "orm_matrix", "realworld")
OUTCOMES = ("preserved", "silent-loss", "loud", "loud-partial")
LINTS = ("migration_only", "executed", "schema_and_migration", "schema_and_executed")
ROW_VALUE_KINDS = {"row_count", "content_digest"}  # R, D
OBJECT_KINDS = {"missing_object", "changed_object", "trigger_behavior",
                "foreign_key_definition", "view_rows", "view_errors"}  # O, T, K, V
CONTEXT_CLASSES = {"C0": "None", "C1": "Cascade", "C2": "SetNull", "C3": "Restrict",
                   "C4": "TwoLevel", "C5": "ExternalTrigger", "C6": "ExternalIndex",
                   "C7": "View", "C8": "CascadingChild"}
# An adjudicated incident list, not a proxy based on the production_impact flag.
REAL_DATA_LOSS_INCIDENTS = (
    "rails#57128", "drizzle#4938", "drizzle#3065", "drizzle#4089",
    "drizzle#5782", "prisma#24540",
)
REALWORLD_ADJUDICATIONS = {
    ("saltbo/zpan", "migrations/0054_lively_nuke.sql"): {
        "reason": "The lost index was intentionally superseded by the migration.",
        "excluded_object": "index:activity_events_org_id_idx",
    },
}
RERUN = "results/rerun-2026-11-01"
# Kit 1.0 models the drop_unique starting schema as an inline constraint, not the fixture's named index.
RERUN_EXCLUDED_OPERATIONS = ("drop_unique",)
DIGITS = dict(zip("0123456789", ("Zero", "One", "Two", "Three", "Four", "Five",
                                  "Six", "Seven", "Eight", "Nine")))


def token(value):
    """Readable, letters-only TeX control words, including numeric pin labels."""
    value = str(value).replace("+", " Plus ")
    return "".join(DIGITS.get(c, c) for c in "".join(
        word[:1].upper() + word[1:] for word in re.findall(r"[A-Za-z0-9]+", value)))


def load_results(root=ROOT):
    return {name: json.loads((root / "results" / f"{name}.json").read_text())
            for name in EXPERIMENTS}


def outcome(row, population="populated"):
    trial = row["trials"][population]
    value = trial.get("outcome")
    if value is None:
        if trial["execution"]["success"]:
            value = "silent-loss" if trial["violations"] else "preserved"
        else:
            # Legacy pilot observations predate state_digest. Compare all retained
            # application observations; do not infer rollback from an error alone.
            value = "loud" if trial["before"] == trial["after"] else "loud-partial"
    return {"failed-loudly": "loud", "failed-loudly-partial": "loud-partial"}.get(value, value)


def framework(row):
    return row.get("framework") or row["case"].split("_", 1)[0]


def native(row):
    return row["path"] not in ("raw", "raw-tx")


def lint_findings(row, variant):
    lint = row["detectors"]["lint"][variant]
    return (lint.get("output") or {}).get("findings", []) if lint["available"] else []


def specific_lint_finding(row, finding):
    """Match retained diagnostic evidence to the observed object or cascade loss.

    SQLD002 never qualifies on its own. An unrelated non-SQLD002 warning also
    does not qualify. Only the SQLD001/003 diagnostic forms present in these
    results have matching rules; new codes require an explicit rule.
    """
    trial = row["trials"]["populated"]
    violations = trial["violations"]
    detail = finding.get("detail", "")
    if finding["code"] == "SQLD003":
        match = re.search(r"The (trigger|index) `([^`]+)`", detail)
        if not match:
            return False
        kind, name = match.groups()
        return any((v["kind"] == "missing_object" and v.get("object") == f"{kind}:{name}") or
                   (kind == "trigger" and v["kind"] == "trigger_behavior" and v.get("object") == name)
                   for v in violations)
    if finding["code"] == "SQLD001":
        match = re.search(r"Dependent table `([^`]+)` references rebuilt table `([^`]+)` "
                          r"with ON DELETE (CASCADE|SET NULL|SET DEFAULT)", detail)
        if not match:
            return False
        child, parent, action = match.groups()
        references = any(fk[2] == parent and fk[6] == action for fk in trial["before"]["foreign_keys"].get(child, []))
        if action == "CASCADE":
            return (any(v["kind"] in ROW_VALUE_KINDS and v.get("table") == child for v in violations)
                    and trial["before"]["counts"].get(child, 0) > trial["after"]["counts"].get(child, 0)
                    and references)
        # Later sqlite-doctor builds also report SET NULL/SET DEFAULT children, whose values change in place.
        return references and any(v["kind"] == "content_digest" and v.get("table") == child for v in violations)
    return False


def current_detail_numbers(book, prefix, rows, source, selector):
    add = lambda name, value, field, desc: book.add(
        prefix + name, value, source, selector + "; " + field, desc)
    silent = [r for r in rows if outcome(r) == "silent-loss"]
    kinds = [{v["kind"] for v in r["trials"]["populated"]["violations"]} for r in silent]
    row_loss = sum(bool(k & ROW_VALUE_KINDS) for k in kinds)
    object_only = sum(not k & ROW_VALUE_KINDS and bool(k & OBJECT_KINDS) for k in kinds)
    add("SilentRowOrValue", row_loss, "trials.populated.violations.kind in {row_count,content_digest}",
        "Silent-loss cells with R/D violations, including cells also losing objects")
    add("SilentObjectOnly", object_only, "trials.populated.violations.kind: O/T/K/V and no R/D",
        "Silent-loss cells with object, trigger, FK-definition or view violations and no row/value loss")
    add("SilentOther", len(silent) - row_loss - object_only, "trials.populated.violations.kind: neither R/D nor O/T/K/V",
        "Silent-loss cells outside the row/value and object categories")
    for label, subset in (("OperationsEvaluated", rows), ("OperationsWithSilentLoss", silent)):
        add(label, len({(framework(r), r["operation"]) for r in subset}),
            "distinct(framework,operation)" + (" where populated outcome=silent-loss" if subset is silent else ""),
            "Framework-operation pairs; overall sums the framework counts, regardless of shared operation names")
    safe_rebuilds = [r for r in rows if outcome(r) in ("preserved", "loud") and
                     (r["rebuild"] is True or r["rebuild"] is None and r.get("planned_rebuild") is True)]
    for variant in LINTS:
        suffix = token(variant)
        field = f"detectors.lint.{variant}; trials.populated; rebuild (planned_rebuild only if rebuild=null)"
        available = [r for r in safe_rebuilds if r["detectors"]["lint"][variant]["available"]]
        add("LintFalseAlarmEligible" + suffix, len(available), field,
            "Preserved or rolled-back loud rebuilding cells with available lint; excludes loud-partial")
        add("LintFalseAlarm" + suffix, sum(bool(lint_findings(r, variant)) for r in available), field,
            "Preserved or rolled-back loud rebuilding cells with any lint finding; one count per cell")
        add("LintFalseAlarmLoud" + suffix, sum(bool(lint_findings(r, variant)) for r in available if outcome(r) == "loud"),
            field, "Rolled-back loud rebuilding cells with any lint finding; subset of LintFalseAlarm")
        found = [(r, lint_findings(r, variant)) for r in silent]
        specific = sum(any(specific_lint_finding(r, f) for f in fs) for r, fs in found)
        generic = sum(bool(fs) and {f["code"] for f in fs} == {"SQLD002"} for _, fs in found)
        add("LintSpecific" + suffix, specific, field + ".output.findings; violations; before/after counts and FKs",
            "Silent-loss cells with a matched SQLD001 cascade/affected table or SQLD003 violated trigger/index")
        add("LintRuleFalseAlarm" + suffix, sum(any(f["code"] != "SQLD002" for f in lint_findings(r, variant))
                                              for r in available), field + ".output.findings.code",
            "Preserved or rolled-back loud rebuilding cells with a finding other than the generic SQLD002")
        add("LintRuleFalseAlarmLoud" + suffix, sum(any(f["code"] != "SQLD002" for f in lint_findings(r, variant))
                                                  for r in available if outcome(r) == "loud"),
            field + ".output.findings.code", "Rolled-back loud subset of LintRuleFalseAlarm")
        add("LintGenericOnly" + suffix, generic, field + ".output.findings.code",
            "Silent-loss cells whose findings are exclusively generic SQLD002 warnings")
        add("LintUnmatched" + suffix, sum(bool(fs) for _, fs in found) - specific - generic, field,
            "Flagged silent-loss cells with neither a matched warning nor exclusively SQLD002 findings")


def fk_action_changed(row):
    """Require a surviving matching FK whose ON UPDATE/DELETE action changed."""
    trial = row["trials"]["populated"]
    rename = row.get("spec", {}).get("table_rename", {})
    for violation in trial["violations"]:
        if violation["kind"] != "foreign_key_definition":
            continue
        definition = violation["definition"]
        table = rename.get(violation["table"], violation["table"])
        for foreign_key in trial["after"]["foreign_keys"].get(table, []):
            if foreign_key[2:5] == definition[:3] and foreign_key[5:7] != definition[3:5]:
                return True
    return False


def group_key(row):
    return framework(row), row["version_label"], row.get("mode", "default"), row["path"]


def group_token(key):
    fw, pin, mode, path = key
    return token(fw) + token(pin.removeprefix(fw + "-")) + (
        token(mode) if mode != "default" else "") + (
        token(path) if path not in (fw, mode) else "")


class Numbers:
    def __init__(self):
        self.macros = {}

    def add(self, name, value, source, field, definition):
        name = "n" + name
        if not re.fullmatch(r"[A-Za-z]+", name) or name in self.macros:
            raise ValueError(f"Invalid or duplicate macro: {name}")
        self.macros[name] = dict(value=value, source=source, field=field, definition=definition)


def summarize_cells(book, prefix, rows, source, selector, unsupported=()):
    add = lambda name, value, field, desc: book.add(
        prefix + name, value, source, selector + "; " + field, desc)
    add("Cells", len(rows), "count(rows)", "Populated/empty pairs, excluding unsupported cells")
    add("Executions", sum(len(r["trials"]) for r in rows), "sum(len(trials))", "Retained executions")
    add("Unsupported", len(unsupported), "count(unsupported)", "Unsupported operation/context cells; not executions")
    if rows and "operation" in rows[0]:
        add("Operations", len({r["operation"] for r in rows}), "distinct(operation)", "Distinct executed operations")
    for pop in ("populated", "empty"):
        counts = Counter(outcome(r, pop) for r in rows)
        if set(counts) - set(OUTCOMES):
            raise ValueError(f"Unknown outcomes: {counts}")
        for status in OUTCOMES:
            add(("" if pop == "populated" else "Empty") + token(status), counts[status],
                f"trials.{pop}.outcome (legacy: execution.success, violations, before/after)",
                f"{pop.capitalize()} {status} cells")
    if rows and all("rebuild" in r for r in rows):
        add("RebuildingCells", sum(r["rebuild"] is True for r in rows), "rebuild", "Cells with an observed populated rebuild")
        add("RebuildUnknownCells", sum(r["rebuild"] is None for r in rows), "rebuild=null", "Cells without an available runtime rebuild trace")
        add("RebuildingOperations", len({r["operation"] for r in rows if r["rebuild"]}),
            "distinct(operation where rebuild)", "Distinct operations rebuilding in at least one populated context")
        if all("planned_rebuild" in r for r in rows):
            add("PlannedRebuildingOperations", len({r["operation"] for r in rows if r["planned_rebuild"]}),
                "distinct(operation where planned_rebuild)", "Distinct operations with a rebuild in generated SQL")
    silent = [r for r in rows if outcome(r) == "silent-loss"]
    if rows and "context" in rows[0]:
        for ctx, label in CONTEXT_CLASSES.items():
            add("Silent" + label, sum(r["context"] == ctx for r in silent), "context=" + ctx,
                f"Silent-loss cells in {ctx}; context classes are disjoint")
        add("SilentFkActionChange", sum(fk_action_changed(r) for r in silent),
            "trials.populated.violations[kind=foreign_key_definition]; after.foreign_keys actions",
            "Silent-loss cells with a changed ON UPDATE/DELETE action on a surviving FK (overlaps context classes)")
    add("DetectorSilentDenominator", len(silent), "trials.populated.outcome", "Silent-loss cells eligible for detection")
    detectors = {
        "EmptyExecutionErrors": lambda r: not r["trials"]["empty"]["execution"]["success"],
        "EmptyInvariants": lambda r: bool(r["trials"]["empty"]["violations"]),
        "PopulatedInvariants": lambda r: bool(r["trials"]["populated"]["violations"]),
    }
    for name, detect in detectors.items():
        add("Detected" + name, sum(detect(r) for r in silent),
            "trials.empty.execution.success" if name == "EmptyExecutionErrors" else
            "trials." + ("empty" if name == "EmptyInvariants" else "populated") + ".violations",
            "Silent-loss cells flagged by " + name)
    for lint in LINTS:
        available = [r for r in silent if r["detectors"]["lint"][lint]["available"]]
        add("AvailableLint" + token(lint), len(available), f"detectors.lint.{lint}.available",
            "Silent-loss cells with available lint; unavailable is not a negative result")
        add("DetectedLint" + token(lint), sum(r["detectors"]["lint"][lint]["detected"] for r in available),
            f"detectors.lint.{lint}.detected", "Silent-loss cells flagged by available lint")


def summarize_groups(book, prefix, rows, source, field, unsupported=()):
    groups, missing = defaultdict(list), defaultdict(list)
    for row in rows:
        groups[group_key(row)].append(row)
    for row in unsupported:
        key = (row["framework"], row["version_label"], row["mode"],
               row["framework"] if row["mode"] == "default" else row["mode"])
        missing[key].append(row)
    for key in sorted(groups.keys() | missing.keys()):
        summarize_cells(book, prefix + group_token(key), groups[key], source,
                        f"{field}[framework,pin,mode,path={key!r}]", missing[key])


def atomicity_numbers(book, data):
    source = "results/rails_atomicity.json"
    for pin in sorted(data["pins"]):
        for transactional in (True, False):
            rows = [r for r in data["rows"] if r["version_label"] == pin
                    and r["scenario"]["transactional"] == transactional]
            prefix = "AtomicityRails" + token(pin.removeprefix("rails-")) + (
                "Transactional" if transactional else "NoTransaction")
            field = f"rows[version_label={pin},scenario.transactional={transactional}]"
            book.add(prefix + "Executions", len(rows), source, field, "Injected-failure executions")
            for label in ("fully rolled back", "partially committed"):
                book.add(prefix + token(label), sum(r["assessment"]["classification"] == label for r in rows),
                         source, field + ".assessment.classification", label)
            book.add(prefix + "DataLoss", sum(bool(r["assessment"]["data_loss"]) for r in rows), source,
                     field + ".assessment.data_loss", "Executions with retained data loss")
            if transactional:
                book.add(prefix + "Failures", sum(r["assessment"]["classification"] != "fully rolled back"
                         for r in rows), source, field + ".assessment.classification",
                         "Atomicity failure: changes survived despite a transactional migration")


def realworld_outcome(row, trial):
    """Adjudicate only the specified superseded object, preserving any other loss."""
    findings = trial.get("findings", [])
    adjudication = REALWORLD_ADJUDICATIONS.get((row["repo"], row["migration_file"]))
    if adjudication:
        findings = [f for f in findings if not (f["kind"] == "implicit_object_loss"
                    and f.get("object") == adjudication["excluded_object"])]
    status = trial["outcome"]
    if status == "silent-loss" and not findings:
        status = "preserved"
    return status, findings


def realworld_numbers(book, data):
    source, rows = "results/realworld.json", data["rows"]
    replayed = [r for r in rows if r["status"] == "replayed"]
    qualifying = [r for r in replayed if r["qualifying_parent_rebuild"]]
    controls = [r for r in replayed if r["control_no_dependents"]]
    for name, value, field in (
        ("ReposAttempted", len({r["repo"] for r in rows}), "distinct(rows.repo)"),
        ("ReposReplayed", len({r["repo"] for r in replayed}), "distinct(rows[status=replayed].repo)"),
        ("MigrationsAttempted", len(rows), "rows"),
        ("MigrationsReplayed", len(replayed), "rows[status=replayed]"),
        ("QualifyingRebuilds", len(qualifying), "rows[qualifying_parent_rebuild=true,status=replayed]"),
        ("QualifyingRepos", len({r["repo"] for r in qualifying}), "distinct(qualifying.repo)"),
        ("DistinctMigrationHashes", len({r["migration_sha256"] for r in replayed}), "distinct(replayed.migration_sha256)"),
        ("QualifyingDistinctMigrationHashes", len({r["migration_sha256"] for r in qualifying}), "distinct(qualifying.migration_sha256)"),
        ("Controls", len(controls), "rows[control_no_dependents=true,status=replayed]"),
        ("Unreplayable", len(rows) - len(replayed), "rows[status=unreplayable]"),
    ):
        book.add("Realworld" + name, value, source, field, name)
    for scope, subset in (("All", rows), ("Qualifying", qualifying), ("Control", controls)):
        for path in ("drizzle", "raw", "raw-tx"):
            prefix = "Realworld" + scope + token(path)
            outcomes = Counter(realworld_outcome(r, r["paths"][path])[0] for r in subset)
            field = f"rows[{scope}].paths.{path}"
            for status in ("silent-loss", "preserved", "loud", "unreplayable"):
                book.add(prefix + token(status), outcomes[status], source, field + ".outcome",
                         "Adjudicated outcome; intentionally superseded index excluded")
            raw_silent = sum(r["paths"][path]["outcome"] == "silent-loss" for r in subset)
            book.add(prefix + "RawSilentLoss", raw_silent, source, field + ".outcome", "Unadjudicated source count")
            book.add(prefix + "AdjudicatedExclusions", raw_silent - outcomes["silent-loss"], source,
                     field + ".findings", "Source silent-loss outcomes reclassified as preserved")
            categories = Counter()
            for row in subset:
                status, findings = realworld_outcome(row, row["paths"][path])
                if status != "silent-loss":
                    continue
                kinds = {f["kind"] for f in findings}
                row_loss = bool(kinds & {"row_count", "content_digest"})
                implicit = "implicit_object_loss" in kinds
                categories["RowOrFkValueLoss"] += row_loss
                categories["ImplicitObjectLoss"] += implicit
                categories["BothRowAndImplicitLoss"] += row_loss and implicit
                categories["ImplicitObjectOnly"] += implicit and not row_loss
                categories["OtherLossOnly"] += not implicit and not row_loss
            for name in ("RowOrFkValueLoss", "ImplicitObjectLoss", "BothRowAndImplicitLoss",
                         "ImplicitObjectOnly", "OtherLossOnly"):
                book.add(prefix + name, categories[name], source, field + ".findings.kind",
                         "Silent-loss outcomes; row/FK-value = row_count or content_digest; "
                         "implicit-object includes overlap, with overlap and exclusive counts supplied")
    transitions = Counter((realworld_outcome(r, r["paths"]["drizzle"])[0], realworld_outcome(r, r["paths"]["raw"])[0])
                          for r in qualifying)
    for (framework_outcome, raw_outcome), name in ((("silent-loss", "preserved"), "SilentToPreserved"),
                                                   (("silent-loss", "silent-loss"), "SilentToSilent"),
                                                   (("loud", "preserved"), "LoudToPreserved"),
                                                   (("loud", "loud"), "LoudToLoud")):
        book.add("RealworldQualifying" + name, transitions[(framework_outcome, raw_outcome)], source,
                 "qualifying rows; (paths.drizzle, paths.raw) adjudicated outcomes",
                 f"Qualifying replays {framework_outcome} on the framework path and {raw_outcome} on the raw path")
    reasons = Counter(r["reason"] for r in rows if r["status"] == "unreplayable")
    for index, (reason, count) in enumerate(sorted(reasons.items()), 1):
        book.add("RealworldUnreplayableReason" + token(index), count, source,
                 f"rows[status=unreplayable,reason={reason!r}]", reason)
    for version, count in sorted(Counter(r["orm"]["resolved"] for r in replayed).items()):
        book.add("RealworldVersion" + token(version) + "Replayed", count, source,
                 f"rows[status=replayed,orm.resolved={version}]", "Replays using Drizzle ORM " + version)


def kit_pair_numbers(book, root):
    source = "results/kit_pragma_pairs.json"
    probe = json.loads((root / source).read_text())
    book.add("KitPairsSeedChildren", probe["seed_rows"]["children"], source, "seed_rows.children", "Seeded cascade children")
    for result in probe["results"]:
        prefix = "KitPairs" + ("Stable" if result["label"] == "current" else "Rc")
        selector = f"results[label={result['label']}]"
        for mode in ("autocommit", "transaction"):
            book.add(prefix + token(mode) + "Children", result[mode]["children"], source, selector + f".{mode}.children",
                     f"Cascade children after applying the two-rebuild file ({mode})")


def relint_numbers(book, root, selected):
    """The same cells linted again with a later sqlite-doctor build."""
    source = "results/relint-2026-11-01/relint.json"
    relint = json.loads((root / source).read_text())
    lints = {tuple(r["key"]): r["lint"] for r in relint["rows"]}
    rows = []
    for row in selected:
        name = "operation_matrix" if row["framework"] in ("rails", "drizzle") else "orm_matrix"
        key = (name, row["framework"], row["version_label"], row.get("mode", "default"), row["path"],
               row["operation"], row["context"])
        rows.append({**row, "detectors": {**row["detectors"], "lint": lints[key]}})
    if len(rows) != len(lints):
        raise ValueError("Re-linted cells differ from the Current selection")
    book.add("RelintDoctorCommit", relint["sqlite_doctor_commit"], source, "sqlite_doctor_commit",
             "sqlite-doctor commit of the later build")
    for fw in [None] + sorted({framework(r) for r in rows}):
        subset = [r for r in rows if fw is None or framework(r) == fw]
        prefix = "RelintCurrent" + (token(fw) if fw else "Overall")
        selector = f"rows[framework={fw or 'all'},Current selection] with lint from the later build"
        summarize_cells(book, prefix, subset, source, selector)
        current_detail_numbers(book, prefix, subset, source, selector)


def rerun_numbers(book, root, recorded):
    """Repeat the latest Rails and Drizzle pins and add the Drizzle 1.0 release candidate."""
    key = lambda r: (r["framework"], r["version_label"], r["path"], r["operation"], r["context"])
    summary = lambda r: (outcome(r), r["rebuild"], outcome(r, "empty"),
                         sorted(v["kind"] for v in r["trials"]["populated"]["violations"]))
    old = {key(r): summary(r) for r in recorded["rows"]}
    for fw in ("rails", "drizzle"):
        source = f"{RERUN}/{fw}{'-current' if fw == 'rails' else ''}/operation_matrix.json"
        rows = [r for r in json.loads((root / source).read_text())["rows"] if r["version_label"] == "current"]
        book.add("Rerun" + token(fw) + "Cells", len(rows), source, "rows[version_label=current]",
                 "Repeated cells, all execution paths")
        book.add("Rerun" + token(fw) + "Differences", sum(old[key(r)] != summary(r) for r in rows),
                 source + "; results/operation_matrix.json",
                 "rows[version_label=current] vs recorded rows; outcome, rebuild, empty outcome, violation kinds",
                 "Repeated cells whose outcome or violation kinds differ from the recorded matrix")
    source = f"{RERUN}/drizzle/operation_matrix.json"
    result = json.loads((root / source).read_text())
    candidate = [r for r in result["rows"] if r["version_label"] == "v1-rc5"]
    book.add("RcDrizzleExcluded", sum(r["operation"] in RERUN_EXCLUDED_OPERATIONS for r in candidate if native(r)),
             source, "rows[version_label=v1-rc5,path=drizzle,operation=drop_unique]",
             "Excluded cells whose fixture schema differs from the Kit 1.0 starting schema")
    kept = [r for r in candidate if r["operation"] not in RERUN_EXCLUDED_OPERATIONS]
    for path in ("drizzle", "raw-tx"):
        rows = [r for r in kept if r["path"] == path]
        prefix = "RcDrizzle" + ("" if path == "drizzle" else token(path))
        selector = f"rows[version_label=v1-rc5,path={path},operation not in {RERUN_EXCLUDED_OPERATIONS}]"
        summarize_cells(book, prefix, rows, source, selector)
        if path == "drizzle":
            current_detail_numbers(book, prefix, rows, source, selector)
    baseline = [r for r in result["rows"] if r["version_label"] == "current" and r["path"] == "drizzle"
                and r["operation"] not in RERUN_EXCLUDED_OPERATIONS]
    for name, value in (("Cells", len(baseline)), ("SilentLoss", sum(outcome(r) == "silent-loss" for r in baseline))):
        book.add("RcDrizzleBaseline" + name, value, source,
                 f"rows[version_label=current,path=drizzle,operation not in {RERUN_EXCLUDED_OPERATIONS}]",
                 "Drizzle 0.45.4 on the release candidate's operation set")
    native_rows = {(r["operation"], r["context"]): r for r in kept if native(r)}
    current = {(r["operation"], r["context"]): r for r in recorded["rows"]
               if r["framework"] == "drizzle" and r["version_label"] == "current" and native(r)}
    for name, before, after in (("NewlyLost", "preserved", "silent-loss"), ("NoLongerLost", "silent-loss", "preserved")):
        cells = [k for k, r in native_rows.items() if outcome(current[k]) == before and outcome(r) == after]
        book.add("RcDrizzle" + name + "Cells", len(cells), source + "; results/operation_matrix.json",
                 "rows[path=drizzle] v1-rc5 vs current", f"Cells {before} on 0.45.4 and {after} on 1.0.0-rc.5")
        book.add("RcDrizzle" + name + "Operations", len({k[0] for k in cells}), source + "; results/operation_matrix.json",
                 "distinct(operation) of the cells above", f"Operations with a cell {before} on 0.45.4 and {after} on 1.0.0-rc.5")
    for package, version in result["pins"]["drizzle"]["v1-rc5"].items():
        book.add("VersionDrizzleRc" + token(package), version, source, f"pins.drizzle.v1-rc5.{package}",
                 "Recorded package version")


def tracker_numbers(book, labels):
    source = "results/tracker_labels.jsonl"
    by_id = {r["id"]: r for r in labels}
    if len(by_id) != len(labels) or set(REAL_DATA_LOSS_INCIDENTS) - by_id.keys():
        raise ValueError("Duplicate tracker IDs or missing adjudicated incidents")
    for orm in [None] + sorted({r["orm"] for r in labels}):
        rows = [r for r in labels if orm is None or r["orm"] == orm]
        relevant = [r for r in rows if r["relevant"]]
        prefix = "Tracker" + (token(orm) if orm else "")
        field = f"records[orm={orm or 'all'}]"
        for name, value, selector in (
            ("Inputs", len(rows), "count"), ("Relevant", len(relevant), "relevant=true"),
            ("Silent", sum(r["silent"] for r in relevant), "relevant=true,silent=true"),
            ("RealDataLossIncidents", sum(r["id"] in REAL_DATA_LOSS_INCIDENTS for r in rows),
             "id in REAL_DATA_LOSS_INCIDENTS (explicit adjudicated list)"),
            ("RealDataLossIncidentsSilent", sum(r["id"] in REAL_DATA_LOSS_INCIDENTS and r["silent"] for r in rows),
             "id in REAL_DATA_LOSS_INCIDENTS and silent=true"),
        ):
            book.add(prefix + name, value, source, field + "; " + selector, name)
        for category in ("consequence", "mechanism"):
            values = sorted({r[category] for r in labels if r["relevant"]})
            for value in values:
                for suffix, selected in (("", relevant), ("Silent", [r for r in relevant if r["silent"]])):
                    book.add(prefix + suffix + token(category) + token(value),
                             sum(r[category] == value for r in selected), source,
                             field + f"[relevant=true,{category}={value}" + (",silent=true" if suffix else "") + "]",
                             f"Relevant {suffix.lower()} records by {category}")
    # Explicit Total names retain the original aggregate names as compatible aliases.
    aggregate_names = ["Inputs", "Relevant", "Silent", "RealDataLossIncidents", "RealDataLossIncidentsSilent"]
    for category in ("consequence", "mechanism"):
        for value in sorted({r[category] for r in labels if r["relevant"]}):
            aggregate_names.extend(suffix + token(category) + token(value) for suffix in ("", "Silent"))
    for name in aggregate_names:
        entry = book.macros["nTracker" + name]
        book.add("TrackerTotal" + name, **entry)


def oracle_numbers(book, root):
    source = "results/oracle_validation/controls.json"
    data = json.loads((root / source).read_text())
    summary = data["summary"]
    book.add("OracleTrials", len(data["controls"]), source, "len(controls)", "Seeded control trials, populated and empty")
    for scope, counts in (("", summary["overall"]), ("Matrix", summary["by_scope"]["matrix"]),
                          ("Limitation", summary["by_scope"]["limitation"])):
        field = "summary." + ("overall" if not scope else f"by_scope.{scope.lower()}")
        book.add("Oracle" + scope + "LossyTrials", counts["TP"] + counts["FN"], source, field + ".TP+FN", "Trials with an injected loss")
        book.add("Oracle" + scope + "SafeTrials", counts["TN"] + counts["FP"], source, field + ".TN+FP", "Trials without a loss")
        for key in ("TP", "FN", "TN", "FP"):
            book.add("Oracle" + scope + token(key.lower()), counts[key], source, f"{field}.{key}", f"Oracle {key} trials")
    intended = summary["populated_intended_changes"]
    book.add("OracleIntendedTrials", intended["trials"], source, "summary.populated_intended_changes.trials",
             "Populated trials of intended schema changes")
    book.add("OracleIntendedFalseAlarms", intended["false_alarms"], source,
             "summary.populated_intended_changes.false_alarms", "Intended changes the oracle flagged")


def rails_base_numbers(book, root):
    source = "results/rails_base/comparison.json"
    data = json.loads((root / source).read_text())
    book.add("RailsBasePins", len(data["builds"]), source, "len(builds)", "Rails pins built from pull-request base commits")
    for comparison in data["comparisons"]:
        counts = comparison["counts"]["populated"]
        prefix = "RailsBaseFor" + token(comparison["head"].removeprefix("rails-"))
        field = f"comparisons[head={comparison['head']}].counts.populated"
        book.add(prefix + "Cells", sum(counts["base"].values()), source, field + ".base", "Populated cells per pin")
        book.add(prefix + "BaseSilentLoss", counts["base"].get("silent-loss", 0), source, field + ".base.silent-loss",
                 "Silent-loss cells at the base commit")
        book.add(prefix + "HeadSilentLoss", counts["head"].get("silent-loss", 0), source, field + ".head.silent-loss",
                 "Silent-loss cells at the pull-request pin")
    source = "results/rails_base/rails_atomicity.json"
    rows = json.loads((root / source).read_text())["rows"]
    for transactional in (True, False):
        subset = [r for r in rows if r["scenario"]["transactional"] == transactional]
        prefix = "RailsBaseAtomicity" + ("Transactional" if transactional else "NoTransaction")
        field = f"rows[scenario.transactional={transactional}]"
        book.add(prefix + "Executions", len(subset), source, field, "Injected-failure executions on base pins")
        for label in ("fully rolled back", "partially committed"):
            book.add(prefix + token(label), sum(r["assessment"]["classification"] == label for r in subset),
                     source, field + ".assessment.classification", label)


def atlas_numbers(book, root):
    source = "results/atlas_lint/report.json"
    report = json.loads((root / source).read_text())
    book.add("AtlasVersion", report["version"]["stdout"].split()[3], source, "version.stdout", "Atlas Community build")
    for group, name in (("silent", "Silent"), ("safe_rebuild", "Safe")):
        for variant, totals in report["totals"][group].items():
            prefix = "Atlas" + name + token(variant)
            field = f"totals.{group}.{variant}"
            for key in ("paper_available", "analyzed", "flagged", "clean", "unavailable", "names_lost_dependent"):
                book.add(prefix + token(key), totals[key], source, f"{field}.{key}", f"Atlas {key} inputs")
            destructive = sum(1 for row in report["rows"] if row["cohort"] == group and row["lint"][variant]["available"]
                              and any(d.get("Code", "").startswith("DS") for d in row["lint"][variant]["diagnostics"]))
            book.add(prefix + "Destructive", destructive, source,
                     f"rows[cohort={group},lint.{variant}.available].lint.{variant}.diagnostics[Code=DS*]",
                     "Analysed inputs with a destructive-change diagnostic")


def build_numbers(root=ROOT):
    data, book = load_results(root), Numbers()
    for name in EXPERIMENTS:
        result = data[name]
        if name == "rails_atomicity":
            executions = len(result["rows"])
        elif name == "realworld":
            executions = sum("execution" in p for r in result["rows"] for p in r["paths"].values())
        else:
            executions = sum(len(r["trials"]) for r in result.get("rows", result.get("runs", [])))
            if name == "rails_fixes":
                executions += sum(len(r["trials"]) for r in result["pilot"]["runs"])
        book.add("Executions" + token(name), executions, f"results/{name}.json",
                 "rows[].execution" if name == "rails_atomicity" else "rows[].paths.*.execution" if name == "realworld"
                 else "sum(len(rows/runs[].trials)); rails_fixes also pilot.runs[].trials",
                 "Executions in this experiment; copied comparison rows and embedded atomicity excluded")
    for name in ("pilot", "upstream_fixes", "operation_matrix", "rails_fixes", "orm_matrix"):
        result = data[name]
        rows = result.get("rows", result.get("runs", []))
        field = "rows" if "rows" in result else "runs"
        summarize_groups(book, token(name), rows, f"results/{name}.json", field, result.get("unsupported", []))
        summarize_cells(book, token(name) + "Overall", rows, f"results/{name}.json", field,
                        result.get("unsupported", []))
        if name == "rails_fixes":
            summarize_groups(book, "RailsFixesPilot", result["pilot"]["runs"], "results/rails_fixes.json", "pilot.runs")
    matrices = [r for name in ("operation_matrix", "rails_fixes", "orm_matrix") for r in data[name]["rows"]]
    source = "; ".join(f"results/{n}.json" for n in ("operation_matrix", "rails_fixes", "orm_matrix"))
    selected = [r for r in matrices if native(r) and (
        r["version_label"] in ("current", "django-current", "prisma-stable") or
        (r["framework"] == "alembic" and r["mode"] == "auto"))]
    for fw in [None] + sorted({framework(r) for r in selected}):
        rows = [r for r in selected if fw is None or framework(r) == fw]
        summarize_cells(book, "Current" + (token(fw) if fw else "Overall"), rows, source,
                        "rows[native path; current/django-current/prisma-stable; Alembic auto] (latest executable pins)")
        current_detail_numbers(book, "Current" + (token(fw) if fw else "Overall"), rows, source,
                               f"rows[framework={fw or 'all'},native current pins; Alembic auto; Prisma stable]")
        if fw:
            book.add("Silent" + token(fw) + "Current", sum(outcome(r) == "silent-loss" for r in rows),
                     source, f"rows[framework={fw},latest executable native path].outcome", "Current native silent-loss cells")
            book.add("Cells" + token(fw) + "Current", len(rows), source,
                     f"rows[framework={fw},latest executable native path]", "Current native cells")
    current = [r for r in selected if outcome(r) == "loud-partial"]
    for ctx in ("C3", "C7"):
        book.add("CurrentOverallLoudPartial" + CONTEXT_CLASSES[ctx], sum(r["context"] == ctx for r in current), source,
                 f"rows[latest executable native path,context={ctx}].outcome=loud-partial",
                 f"Current loud-partial cells in {ctx}")
    relint_numbers(book, root, selected)
    atomicity_numbers(book, data["rails_atomicity"])
    kit_pair_numbers(book, root)
    realworld_numbers(book, data["realworld"])
    rerun_numbers(book, root, data["operation_matrix"])
    oracle_numbers(book, root)
    rails_base_numbers(book, root)
    atlas_numbers(book, root)
    labels = [json.loads(line) for line in (root / "results/tracker_labels.jsonl").read_text().splitlines() if line.strip()]
    tracker_numbers(book, labels)
    # Pins are observations from retained results, not claims about today's releases.
    versions = data["rails_fixes"]["pins"]
    for fw, pins in versions.items():
        for pin, packages in pins.items():
            for package, version in packages.items():
                book.add("Version" + token(fw) + token(pin.removeprefix(fw + "-")) + token(package),
                         version, "results/rails_fixes.json", f"pins.{fw}.{pin}.{package}", "Recorded package version")
    for package, version in data["orm_matrix"]["pins"].items():
        if not package.endswith("_source") and package != "resolved_at":
            book.add("VersionOrm" + token(package), version, "results/orm_matrix.json", "pins." + package,
                     "Recorded package version; Prisma latest tag was unsupported")
    paths = [f"results/{n}.json" for n in EXPERIMENTS] + ["results/tracker_labels.jsonl"] + [
        f"{RERUN}/rails-current/operation_matrix.json", f"{RERUN}/drizzle/operation_matrix.json",
        "results/kit_pragma_pairs.json", "results/relint-2026-11-01/relint.json",
        "results/oracle_validation/controls.json", "results/rails_base/comparison.json",
        "results/rails_base/rails_atomicity.json", "results/atlas_lint/report.json"]
    return {
        "format_version": 1,
        "definitions": {
            "cell": "One framework/pin/mode/path/operation/context populated-empty pair; pilot uses case in place of operation/context.",
            "overall": "Current executable native paths only: Rails current, Drizzle current, Django current, Alembic auto, Prisma stable. Raw paths and Alembic always remain separately tabulated.",
            "prisma": "Latest tag 8.0.0-rc.22 is unsupported in the retained matrix; executable stable pin is 7.10.0.",
            "executions": "Count retained trial executions, not requested or unsupported cells. Rails fixes excludes copied comparisons and atomicity embedded from its separate experiment.",
            "detectors": "Coverage is conditional on populated silent loss; empty invariants include intended-change checks. Lint availability is reported separately.",
            "lint_false_alarms": "Counts of preserved or fully rolled-back loud rebuilding cells with any available lint finding, not statistical specificity rates. Loud-partial is excluded. Runtime rebuild is used when known; Prisma uses planned_rebuild because its runtime trace is unavailable. Eligible denominators exclude unavailable lint.",
            "lint_specific": "SQLD001 must name a violated child table with fewer rows and a recorded CASCADE FK to the named rebuilt parent. SQLD003 must name the missing index/trigger or violated trigger behavior. SQLD002 is generic even in a cell with row loss. Specific, GenericOnly and Unmatched partition flagged silent-loss cells; mixed specific and SQLD002 counts as specific.",
            "silent_loss_types": "SilentRowOrValue has R/D violations, including mixed row/object losses. SilentObjectOnly has O/T/K/V violations without R/D. SilentOther retains any remaining cases. These categories partition silent-loss cells.",
            "current_operations": "OperationsEvaluated and OperationsWithSilentLoss count distinct framework-operation pairs, so Overall is the sum across frameworks. Existing Operations counts distinct operation names across its scope.",
            "fk_action_change": "Changed ON UPDATE/DELETE actions on surviving FKs are reported separately from context classes and can overlap them; absent FKs alone do not count as changed actions.",
            "atomicity": "Only a partial commit in a transactional scenario is an atomicity failure; no-transaction controls are separate.",
            "realworld": "Synthetic replays are not production incidents. Silent losses exclude the explicitly superseded Zpan index. Implicit-object and row/FK-value counts can overlap; exclusive and intersection counts are supplied.",
            "relint": "The Current cells linted again with sqlite-doctor 2bf86dc, whose rules were developed after and with knowledge of these results; reconstructed inputs reproduced every recorded lint result with the recorded build (scripts/relint.py --verify). LintRuleFalseAlarm excludes the generic SQLD002.",
            "rerun": "Repeated on 2026-11-01 with unchanged fixtures. Release-candidate counts exclude drop_unique, whose fixture schema is not the starting schema Kit 1.0 generates; raw-tx is the generated SQL in one transaction.",
            "oracle": "Seeded raw-path controls (scripts/oracle_validation.py). Limitation scope holds the controls built to expose blind spots: unintended default changes on an ordinary matrix fixture and a changed value in a derived table without an id column; Matrix scope holds the other controls on matrix fixtures.",
            "rails_base": "Rails pins built from each pull request's base commit on Ruby 3.4.3, run with the same operation matrix and atomicity scenarios as the pull-request pins.",
            "atlas": "Atlas Community migration analyzers from a digest-pinned image on the four sqlite-doctor inputs. Unavailable inputs could not be replayed by Atlas (statements on tables or indexes the input does not define, framework bookkeeping queries in Rails and Django traces, other replay errors) or had no trace (Prisma); they are never counted as clean. Flagged means at least one diagnostic of any kind.",
            "tracker": "Counts are labeled issue/PR records, not deduplicated underlying bugs; real-data-loss incidents use the explicit adjudicated ID list.",
        },
        "source_sha256": {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths},
        "adjudications": {"real_data_loss_incidents": list(REAL_DATA_LOSS_INCIDENTS),
                          "realworld": [dict(repo=k[0], migration_file=k[1], **v) for k, v in REALWORLD_ADJUDICATIONS.items()]},
        "macros": dict(sorted(book.macros.items())),
    }


def tex_escape(value):
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(c, c) for c in str(value))


def write_numbers(result, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / "numbers.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    tex = ["% Generated by scripts/paper_numbers.py; edit the extractor, not this file."]
    md = ["# Paper numbers", "", "Generated from retained results by `scripts/paper_numbers.py`.", ""]
    md.extend(f"- **{key}:** {value}" for key, value in result["definitions"].items())
    md.extend(["", "| Macro | Value | Source file | Field / selection | Definition |", "|---|---:|---|---|---|"])
    for name, entry in result["macros"].items():
        tex.append("\\newcommand{\\" + name + "}{" + tex_escape(entry["value"]) + "}")
        cells = [f"`\\{name}`", str(entry["value"]), entry["source"], entry["field"], entry["definition"]]
        md.append("| " + " | ".join(c.replace("|", r"\|").replace("\n", " ") for c in cells) + " |")
    (output / "numbers.tex").write_text("\n".join(tex) + "\n")
    (output / "numbers.md").write_text("\n".join(md) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "paper")
    args = parser.parse_args()
    result = build_numbers()
    write_numbers(result, args.output)
    print(f"Wrote {len(result['macros'])} quantities to {args.output}")


if __name__ == "__main__":
    main()
