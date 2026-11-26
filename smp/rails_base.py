import argparse
import hashlib
import json
import os
import shutil
from collections import Counter
from pathlib import Path

from .environment import ROOT
from .matrix_report import ABBREVIATIONS
from .report import OMITTED, digest
from .matrix_spec import CONTEXTS, RAILS
from .operation_matrix import read_gzip, run_matrix
from .pilot import DEFAULT_DOCTOR
from .preservation import classify, violations
from .rails_atomicity import run as run_atomicity, scenarios, validate_row

POPULATIONS = ("populated", "empty")
BASE_OUTCOMES = "8478379e7c6814bc925c7688c3209f5c723c9903d40b656c1433576ec806e881"


def base_outcomes(result):
    return digest([[c["base"], c["head"],
                    [[cell["operation"], cell["context"], cell["population"], cell["base"], cell["head"]] for cell in c["cells"]],
                    [[p["scenario"]["id"], *([p[side]["assessment"]["classification"], p[side]["children_after_rebuild"],
                                             p[side]["children_after_failure"]] for side in ("base", "head"))]
                     for p in c["atomicity"]]] for c in result["comparisons"]])


def matrix_index(rows, labels):
    selected = [r for r in rows if r["version_label"] in labels and r["framework"] == r["path"] == "rails"]
    index = {(r["version_label"], r["operation"], r["context"]): r for r in selected}
    expected = {(label, operation, context) for label in labels for operation in RAILS for context in CONTEXTS}
    if set(index) != expected or len(index) != len(selected):
        raise ValueError("Missing or duplicate Rails matrix cells")
    return index


def atomicity_index(rows, labels):
    selected = [r for r in rows if r["version_label"] in labels]
    index = {(r["version_label"], r["scenario"]["id"]): r for r in selected}
    expected = {(label, spec["id"]) for label in labels for spec in scenarios()}
    if set(index) != expected or len(index) != len(selected):
        raise ValueError("Missing or duplicate atomicity scenarios")
    return index


def validate_execution(execution, pin):
    expected = {"ruby": "3.4.3", "activerecord": pin["version"], "sqlite3_gem": "2.9.6",
                "activerecord_revision": pin["commit"], "adapter_sha256": pin["adapter_sha256"]}
    for key, value in expected.items():
        if execution.get(key) != value:
            raise ValueError(f"Runtime mismatch: {key}: {execution.get(key)} != {value}")
    if execution.get("foreign_keys_before") != 1 or execution.get("foreign_keys_after") != 1:
        raise ValueError("Foreign key enforcement was not enabled")


def validate_matrix(rows, pins):
    index = matrix_index(rows, pins)
    for (label, operation, context), row in index.items():
        row = json.loads(json.dumps(row))
        saved = read_gzip(ROOT / row["artifacts"])
        if saved["row"] != row or set(row["trials"]) != set(POPULATIONS):
            raise ValueError("Matrix archive differs from summary")
        for trial in row["trials"].values():
            validate_execution(trial["execution"], pins[label])
            found = violations(trial["before"], trial["after"], saved["spec"], trial["execution"])
            if found != trial["violations"] or trial["outcome"] != classify(
                    trial["execution"]["success"], found, trial["before"], trial["after"]):
                raise ValueError("Matrix classification differs from current checker")
    return index


def cell(trial):
    codes = sorted({ABBREVIATIONS[v["kind"]] for v in trial["violations"]})
    return {"outcome": trial["outcome"], "codes": codes, "rebuild": trial["rebuild"]}


def transition(base, head):
    if base["outcome"] == "silent-loss" and head["outcome"] == "preserved":
        return "fixed silent loss"
    if base["outcome"] == "preserved" and head["outcome"] != "preserved":
        return "regression"
    if head["outcome"] == "silent-loss":
        return "residual silent loss"
    return "unchanged" if base == head else "changed"


def compare(base_rows, head_rows, base_atomicity, head_atomicity, mappings):
    bases = {base for base, head in mappings}
    heads = {head for base, head in mappings}
    matrix = matrix_index(base_rows, bases) | matrix_index(head_rows, heads)
    atomicity = atomicity_index(base_atomicity, bases) | atomicity_index(head_atomicity, heads)
    comparisons = []
    for base, head in mappings:
        cells = []
        for operation in sorted(RAILS):
            for context in CONTEXTS:
                left, right = matrix[base, operation, context], matrix[head, operation, context]
                for population in POPULATIONS:
                    a, b = cell(left["trials"][population]), cell(right["trials"][population])
                    cells.append({"operation": operation, "context": context, "population": population,
                                  "base": a, "head": b, "transition": transition(a, b),
                                  "base_artifact": left["artifacts"], "head_artifact": right["artifacts"]})
        probes = []
        for spec in scenarios():
            pair = {side: atomicity[label, spec["id"]] for side, label in (("base", base), ("head", head))}
            probes.append({"scenario": spec, **{side: {
                "assessment": row["assessment"], "children_after_rebuild": len(row["after_rebuild"]["children"]),
                "children_after_failure": len(row["after"]["rows"]["children"]), "artifacts": row["artifacts"]}
                for side, row in pair.items()}})
        counts = {population: {
            side: dict(Counter(c[side]["outcome"] for c in cells if c["population"] == population))
            for side in ("base", "head")} for population in POPULATIONS}
        transitions = {population: dict(Counter(c["transition"] for c in cells if c["population"] == population))
                       for population in POPULATIONS}
        comparisons.append({"base": base, "head": head, "derived_merge": "+" in head,
                            "counts": counts, "transitions": transitions, "cells": cells, "atomicity": probes})
    return comparisons


def runtime_differences(left, right):
    return {key: {"base": left.get(key), "head": right.get(key)} for key in sorted(left.keys() | right.keys())
            if left.get(key) != right.get(key)}


def runtime_signature(execution):
    return {**execution["gems"], "ruby": execution["ruby"], "sqlite": execution["sqlite"]}


def validate_runtime_consistency(matrix_rows, atomicity_rows, labels):
    signatures = {}
    for label in labels:
        executions = [trial["execution"] for row in matrix_rows if row["version_label"] == label
                      for trial in row["trials"].values()]
        executions += [row["execution"] for row in atomicity_rows if row["version_label"] == label]
        first = runtime_signature(executions[0])
        if any(runtime_signature(execution) != first for execution in executions):
            raise ValueError(f"Runtime dependencies changed between trials: {label}")
        signatures[label] = first
    return signatures


def validate_matching_fixtures(base_rows, head_rows, mappings):
    bases = matrix_index(base_rows, {base for base, head in mappings})
    heads = matrix_index(head_rows, {head for base, head in mappings})
    for base, head in mappings:
        for operation in RAILS:
            for context in CONTEXTS:
                left = read_gzip(ROOT / bases[base, operation, context]["artifacts"])
                right = read_gzip(ROOT / heads[head, operation, context]["artifacts"])
                if any(left[key] != right[key] for key in ("spec", "schema", "seed")):
                    raise ValueError(f"Different fixtures: {base}/{head}/{operation}/{context}")


def display(value):
    return value["outcome"] + ("(" + ",".join(value["codes"]) + ")" if value["codes"] else "") + ("†" if value["rebuild"] else "")


def write_summary(result, output):
    recorded = base_outcomes(result) == BASE_OUTCOMES
    bases = len(result["builds"])
    lines = ["# Rails same-base control", "", f"Observed: {result['observed_at']}.", "",
             f"{bases * 144} operation/context pairs ({bases * 288} executions) and {bases * 8} atomicity probes on "
             f"{bases} bases. The PR and local-merge results they are compared with come from the earlier runs "
             "in `results/rails_fixes.json` and `results/rails_atomicity.json`.", "",
             *(["Each base loses preservation in 48/144 populated cells and 12/144 empty cells. "
                "#57128 and #58709 each eliminate the 36 populated FK-loss cells but retain 12 trigger-loss cells. "
                "#56811 eliminates the 12 trigger-loss cells in both populations but retains 36 populated FK-loss cells. "
                "Both combinations preserve all 288/288 matrix executions. No base-preserved matrix cell regresses. "
                "The bases fully roll back 12/12 transactional failures; #57128 and its combination each partially "
                "commit 4/4 transactional failures, while #58709, #56811 and the #58709 combination each roll back 4/4. "
                "These differences persist with identical loaded dependency versions, Ruby and SQLite within every comparison."]
               if recorded else [OMITTED]), "",
             "## Reproduce", "", "```sh",
             ".venv/bin/python scripts/build_rails_base.py --output results/rails_base/<new directory>",
             ".venv/bin/python -m smp.rails_base --output results/rails_base/<new directory> --workers 6", "```", "",
             "Builds use frozen Gemfile.lock resolutions and a runtime directory of their own under the output. "
             "The run command validates cached evidence before reporting. The method is described in `PROTOCOL_rails_base.md`.", "",
             "## Provenance", "", "| Base pin | Commit | PRs covered | Ruby | SQLite |", "|---|---|---|---|---|"]
    for label, build in result["builds"].items():
        pin, runtime = build["pin"], build["runtime"]
        lines.append(f"| {label} | `{pin['commit']}` | {', '.join(pin['base_for'])} | {runtime['ruby']} | {runtime['sqlite']} |")
    lines += ["", "| Historical comparator | Commit |", "|---|---|"]
    for label, pin in result["comparators"].items():
        lines.append(f"| {label} | `{pin['commit']}` |")
    lines += ["", "Full PR and derived-merge commits, input checksums, dependency differences and lockfile hashes are in "
              "[comparison.json](comparison.json). Gemfiles and lockfiles are under "
              "`builds/<base-pin>/`; historical comparator lockfiles are under `comparators/<pin>/`. "
              "Loaded source snapshots are under `source/`. Raw observations and SQL traces are in "
              "`operation_evidence/` and `rails-atomicity/`.", "",
              *((["### Recorded bases and branch points", "",
              "The saved GitHub commit comparisons show #57128 is 12 commits ahead of its recorded base "
              "and #58709 is one commit ahead; neither is behind. Their runtime deltas are confined to "
              "the SQLite adapter for #57128, and the SQLite adapter plus migration transaction methods for #58709. "
              "#56811 is one commit ahead and two commits behind its recorded base. Its true branch point is "
              "`3faf056f240966b268dd6fa52c559e241a370d06`; the two base-only commits change only "
              "`activerecord/test/cases/adapters/postgresql/bytea_test.rb`, with no runtime changes. "
              "The recorded base was therefore retained.", ""]) if recorded else []),
              "Commit comparisons are in [source_comparisons.json](source_comparisons.json) and "
              "`source/*compare.json` / `source/*divergence.json`.", "",
              "## Counts", "", "| Comparison | Population | Base silent loss | Head silent loss | Fixed loss | Preserved → non-preserved |",
              "|---|---|---:|---:|---:|---:|"]
    for comparison in result["comparisons"]:
        for population in POPULATIONS:
            counts, changes = comparison["counts"][population], comparison["transitions"][population]
            lines.append(f"| {comparison['head']} | {population} | {counts['base'].get('silent-loss', 0)}/144 | "
                         f"{counts['head'].get('silent-loss', 0)}/144 | {changes.get('fixed silent loss', 0)}/144 | "
                         f"{changes.get('regression', 0)}/144 |")
    lines += ["", "| Pin | Population | Preserved | Silent loss | Failed loudly | Failed partially |", "|---|---|---:|---:|---:|---:|"]
    seen = set()
    for comparison in result["comparisons"]:
        for side in ("base", "head"):
            label = comparison[side]
            if label in seen:
                continue
            seen.add(label)
            for population in POPULATIONS:
                counts = comparison["counts"][population][side]
                values = [str(counts.get(key, 0)) + "/144" for key in
                          ("preserved", "silent-loss", "failed-loudly", "failed-loudly-partial")]
                lines.append(f"| {label} | {population} | " + " | ".join(values) + " |")
    lines += ["", "## Atomicity", "",
              "Each comparison has four transactional and four explicitly nontransactional scenarios. "
              "Intermediate children are counted immediately after rebuild; final children after failure, each out of three. "
              "Survivors list durable intended changes. Full assessment details and bookkeeping are retained in JSON."]
    lines += ["", "| Pin | Transactional rollback | Transactional partial commit | Disabled-transaction partial commit | Persisted data loss |",
              "|---|---:|---:|---:|---:|"]
    seen = set()
    for comparison in result["comparisons"]:
        for side in ("base", "head"):
            label = comparison[side]
            if label in seen:
                continue
            seen.add(label)
            probes = comparison["atomicity"]
            transactional = Counter(p[side]["assessment"]["classification"] for p in probes if p["scenario"]["transactional"])
            disabled = Counter(p[side]["assessment"]["classification"] for p in probes if not p["scenario"]["transactional"])
            lines.append(f"| {label} | {transactional['fully rolled back']}/4 | {transactional['partially committed']}/4 | "
                         f"{disabled['partially committed']}/4 | {transactional['data loss'] + disabled['data loss']}/8 |")
    for comparison in result["comparisons"]:
        lines += ["", f"### {comparison['base']} → {comparison['head']}", "",
                  "| Scenario | Base outcome | Head outcome | Intermediate children base/head | Final children base/head | Surviving changes base/head | Bookkeeping unchanged base/head |",
                  "|---|---|---|---|---|---|---|"]
        for probe in comparison["atomicity"]:
            a, b = probe["base"], probe["head"]
            survivors = [", ".join(k for k, v in side["assessment"]["surviving_changes"].items() if v) or "none" for side in (a, b)]
            lines.append(f"| {probe['scenario']['id']} | {a['assessment']['classification']} | {b['assessment']['classification']} | "
                         f"{a['children_after_rebuild']}/3 / {b['children_after_rebuild']}/3 | "
                         f"{a['children_after_failure']}/3 / {b['children_after_failure']}/3 | {' / '.join(survivors)} | "
                         f"{a['assessment']['schema_migrations_unchanged']} / {b['assessment']['schema_migrations_unchanged']} |")
    lines += ["", "## Cell-by-cell matrix", "",
              "† = observed rebuild; D = content digest, R = row count, O = schema object, T = trigger behavior. "
              "Each row shows both populations; unchanged cells are included."]
    for comparison in result["comparisons"]:
        lines += ["", f"### {comparison['base']} → {comparison['head']}", "",
                  "| Operation | Context | Base populated | Head populated | Base empty | Head empty |", "|---|---|---|---|---|---|"]
        cells = comparison["cells"]
        for populated, empty in zip(cells[::2], cells[1::2]):
            values = [display(c[side]) for c in (populated, empty) for side in ("base", "head")]
            lines.append(f"| {populated['operation']} | {populated['context']} | " + " | ".join(values) + " |")
    lines += ["", "## Dependency differences", ""]
    for head, differences in result["runtime_differences"].items():
        lines.append(f"- {head}: " + (json.dumps(differences, sort_keys=True) if differences else "none in loaded gems, Ruby or SQLite."))
    lines += ["", "## Deviations and limitations", "",
              "Notes recorded with the run are in the `deviations` field of [comparison.json](comparison.json)."
              if result["deviations"] else "No deviation is recorded for this run.", "",
              "The two local merges are descriptive comparisons against their first-parent PR base. They combine different "
              "branch histories and do not isolate both patches on a common base. Recorded PR base-to-head differences can "
              "also include intervening upstream changes; these controls remove the Rails-release and Ruby-version mismatch, "
              "but do not substitute for rebasing each minimal patch onto a single common commit. "
              "The matrix and eight atomicity scenarios do not cover arbitrary migrations, nesting or concurrency.", ""]
    (output / "summary.md").write_text("\n".join(lines))


def run(output, workers=6, doctor=DEFAULT_DOCTOR, deviations=()):
    """deviations: statements about this run that depart from the protocol, recorded with its result."""
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / "results/rails_base") or output == ROOT / "results/rails_base":
        raise ValueError("Output must be a directory of its own under results/rails_base")
    if (output / "comparison.json").exists():
        raise ValueError(f"{output} already holds a result; select a new directory")
    os.environ["SMP_RUNTIME_ROOT"] = str(output / "runtime")
    builds = json.loads((output / "builds.json").read_text())
    fixes = json.loads((ROOT / "sources/upstream_fixes.json").read_text())
    mappings = [(base, head) for base, build in builds.items() for head in build["pin"]["base_for"]]
    for label, pin in fixes.items():
        if label.startswith("rails-pr") and "parents" in pin:
            base = next(base for base, head in mappings if fixes[head]["commit"] == pin["parents"][0])
            mappings.append((base, label))
    heads = {head for base, head in mappings}
    previous = json.loads((ROOT / "results/rails_fixes.json").read_text())
    previous_atomicity = json.loads((ROOT / "results/rails_atomicity.json").read_text())
    head_rows = previous["rows"] + previous["comparison_rows"]
    validate_matrix(head_rows, {head: fixes[head] for head in heads})
    for (label, scenario), row in atomicity_index(previous_atomicity["rows"], heads).items():
        validate_execution(row["execution"], fixes[label])
        validate_row(row, read_gzip(ROOT / row["artifacts"]))
    matrix = run_matrix(output, doctor, workers, frameworks=["rails"], labels=list(builds))
    if matrix["errors"]:
        raise RuntimeError(f"Matrix infrastructure errors: {len(matrix['errors'])}")
    validate_matrix(matrix["rows"], {base: fixes[base] for base in builds})
    atomicity = run_atomicity(output, labels=tuple(builds))
    for (label, scenario), row in atomicity_index(atomicity["rows"], builds).items():
        validate_execution(row["execution"], fixes[label])
        validate_row(row, read_gzip(ROOT / row["artifacts"]))
    validate_matching_fixtures(matrix["rows"], head_rows, mappings)
    base_runtimes = validate_runtime_consistency(matrix["rows"], atomicity["rows"], builds)
    head_runtimes = validate_runtime_consistency(head_rows, previous_atomicity["rows"], heads)
    differences = {}
    for base, head in mappings:
        differences[head] = runtime_differences(base_runtimes[base], head_runtimes[head])
        folder = output / "comparators" / head
        folder.mkdir(parents=True, exist_ok=True)
        for name in ("Gemfile", "Gemfile.lock"):
            shutil.copyfile(ROOT / "runners/rails" / head / name, folder / name)
    result = {"format_version": 1, "observed_at": matrix["observed_at"], "builds": builds,
              "comparators": {head: fixes[head] for head in sorted(heads)},
              "input_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                               ("results/rails_fixes.json", "results/rails_atomicity.json", "versions.json", "sources/upstream_fixes.json")},
              "runtime_differences": differences,
              "source_comparisons": json.loads((output / "source_comparisons.json").read_text()),
              "deviations": list(deviations),
              "comparisons": compare(matrix["rows"], head_rows, atomicity["rows"], previous_atomicity["rows"], mappings)}
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    write_summary(result, output)
    validation = {"matrix_pairs": len(matrix["rows"]), "matrix_executions": 2 * len(matrix["rows"]),
                  "atomicity_executions": len(atomicity["rows"]), "comparison_cells": sum(len(c["cells"]) for c in result["comparisons"]),
                  "infrastructure_errors": len(matrix["errors"])}
    (output / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps(validation), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True, help="Directory under results/rails_base holding builds.json")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--doctor", type=Path, default=DEFAULT_DOCTOR)
    parser.add_argument("--deviation", action="append", default=[], help="A deviation from the protocol to record with the result")
    args = parser.parse_args()
    run(args.output, args.workers, args.doctor, args.deviation)
