"""Validate the Rails supplement, original reports, and retained execution evidence."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smp.checks import require
from smp.matrix_report import write_report as matrix_report
from smp.matrix_spec import cases
from smp.rails_fixes import COMPARISONS, LABELS, transaction_counts, write_report
from smp.report import write_report as pilot_report
from smp.upstream_report import write_upstream_report
from validate_operation_matrix import validate


def check(result):
    expected = {(op, ctx, label) for fw, op, ctx in cases() if fw == "rails" for label in LABELS}
    actual = {(r["operation"], r["context"], r["version_label"]) for r in result["rows"]}
    require(actual == expected and len(result["rows"]) == len(expected), "Incomplete Rails operation product")
    require(all(r["framework"] == r["path"] == "rails" for r in result["rows"]))
    require(result["requested_groups"] == len(expected))
    require(all(set(r["trials"]) == {"populated", "empty"} for r in result["rows"]))
    require({(r["operation"], r["version_label"]) for r in result["rows"]
            if r["trials"]["populated"]["execution"]["success"]
            and not any(v["kind"] == "intended_change_missing" for v in r["trials"]["populated"]["violations"])} == {
                (op, label) for op, _, label in expected})
    summary = {"new_matrix": validate(result, complete=False)}
    summary["new_matrix"]["coverage_complete"] = True
    fixes = json.loads((ROOT / "sources/upstream_fixes.json").read_text())
    for label in LABELS:
        require(fixes[label] == result["upstream_fixes"][label])
        for row in result["rows"]:
            if row["version_label"] != label:
                continue
            for trial in row["trials"].values():
                require(trial["execution"]["ruby"] == fixes[label]["ruby"])
                require(trial["execution"]["sqlite3_gem"] == result["pins"]["rails"][label]["sqlite3"])
    for label in ("rails-pr57128+56811", "rails-pr58709+56811"):
        pin = fixes[label]
        require(hashlib.sha256((ROOT / pin["resolution_patch"]).read_bytes()).hexdigest() == pin["resolution_patch_sha256"])
    baseline = json.loads((ROOT / "results/operation_matrix.json").read_text())
    require(result["comparison_rows"] == [r for r in baseline["rows"]
                                         if r["framework"] == "rails" and r["version_label"] in COMPARISONS])
    summary["original_matrix"] = validate(baseline)
    comparison_pilots = []
    for filename in ("pilot.json", "upstream_fixes.json"):
        previous = json.loads((ROOT / "results" / filename).read_text())
        comparison_pilots.extend(r for r in previous["runs"]
                                 if r["path"] == "rails" and r["version_label"] in COMPARISONS)
        output = subprocess.check_output([sys.executable, str(ROOT / "scripts/validate_results.py"),
                                          str(ROOT / "results" / filename)], text=True)
        summary[filename] = json.loads(output)
    require(result["comparison_pilot_runs"] == comparison_pilots)
    pilot = result["pilot"]
    require(len(pilot["runs"]) == 7 * len(LABELS))
    if "atomicity" in result:
        from smp.rails_atomicity import validate as validate_atomicity
        summary["atomicity"] = validate_atomicity(result["atomicity"])
    for row in result["rows"] + result["comparison_rows"]:
        for population in ("populated", "empty"):
            require(result["transaction_counts"][row["artifacts"]][population] == transaction_counts(row, population))
    with tempfile.TemporaryDirectory(prefix="rails-validate-") as temporary:
        work = Path(temporary)
        pilot_file = work / "pilot.json"
        pilot_file.write_text(json.dumps(pilot))
        output = subprocess.check_output([sys.executable, str(ROOT / "scripts/validate_results.py"), str(pilot_file)], text=True)
        summary["new_pilot"] = json.loads(output)
        for filename, render in (("operation_matrix", matrix_report), ("pilot", pilot_report),
                                 ("upstream_fixes", write_upstream_report)):
            saved = json.loads((ROOT / "results" / f"{filename}.json").read_text())
            target = work / f"{filename}.md"
            render(saved, target)
            report_name = "pilot_report.md" if filename == "pilot" else f"{filename}.md"
            require(target.read_bytes() == (ROOT / "results" / report_name).read_bytes(), report_name)
        report = work / "rails_fixes.md"
        write_report(result, report)
        summary["report_text"] = report.read_text()
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    summary = check(result)
    if "atomicity" in result:
        require(result["atomicity"] == json.loads(args.result.with_name("rails_atomicity.json").read_text()))
    require(summary.pop("report_text") == args.result.with_suffix(".md").read_text())
    summary["reports_reproduced"] = ["pilot_report.md", "upstream_fixes.md", "operation_matrix.md", "rails_fixes.md"]
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
