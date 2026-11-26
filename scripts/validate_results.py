"""Check result consistency and optionally compare deterministic outcomes."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smp.checks import check_invariants, intended_change, require
from smp.report import gate_results


def outcomes(result):
    return {(r["case"], r["path"], r["version_label"]): {
        "trials": {name: {"success": trial["execution"]["success"],
                           "counts": trial["after"]["counts"], "violations": trial["violations"]}
                   for name, trial in r["trials"].items()},
        "lint": {name: [v["available"], v["detected"], sorted({f["code"] for f in (v.get("output") or {}).get("findings", [])})]
                 for name, v in r["detectors"]["lint"].items()},
    } for r in result["runs"]}


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("result", type=Path)
parser.add_argument("--compare", type=Path)
args = parser.parse_args()
result = json.loads(args.result.read_text())
require(len(outcomes(result)) == len(result["runs"]), "Duplicate run keys")
if "upstream_fixes" in result:
    expected = set()
    for case in (ROOT / "cases").iterdir():
        spec = json.loads((case / "case.json").read_text())
        paths = ("rails",) if spec["framework"] == "rails" else ("drizzle", "raw", "raw-tx")
        for label in result["pins"][spec["framework"]]:
            if label not in ("before", "current"):
                expected.update((case.name, path, label) for path in paths)
    require(set(outcomes(result)) == expected, "Incomplete upstream matrix")
    for build in result["upstream_builds"].values():
        artifact = ROOT / build["artifact"]
        require(hashlib.sha256(artifact.read_bytes()).hexdigest() == build["sha256"], "Tarball differs")
for run in result["runs"]:
    artifacts = ROOT / run["artifacts"]
    require(json.loads((artifacts / "result.json").read_text()) == run)
    spec = json.loads((ROOT / "cases" / run["case"] / "case.json").read_text())
    for trial in run["trials"].values():
        require(check_invariants(trial["before"], trial["after"], spec["expected"]) == trial["violations"])
        require(not intended_change(trial["before"], spec["expected"]))
        require(trial["execution"]["foreign_keys_before"] == 1)
        if "upstream_fixes" in run and run["path"] == "rails":
            fix = run["upstream_fixes"][run["version_label"]]
            require(trial["execution"]["activerecord_revision"] == fix["commit"])
            require(trial["execution"]["adapter_sha256"] == fix["adapter_sha256"])
            require(trial["execution"]["activerecord"] == run["pins"]["activerecord"])
        elif run["path"] == "drizzle":
            for package, version in run["pins"].items():
                require(trial["execution"][package] == version)
    require(run["detectors"]["empty_db"]["detected"] == (not run["trials"]["empty"]["execution"]["success"]))
    require(run["detectors"]["populated_invariants"]["detected"] == bool(run["trials"]["populated"]["violations"]))
    for mode, lint in run["detectors"]["lint"].items():
        # An unavailable linter is recorded with or without the output and stderr fields.
        if lint["available"]:
            require((artifacts / f"lint_{mode}.sql").exists())
            require(lint["detected"] == bool(lint["output"]["findings"]))
        else:
            require(lint["detected"] is None and not lint.get("output"))
    if run["path"] in ("drizzle", "raw", "raw-tx"):
        history = artifacts / "generated_history"
        upgrades = [path for path in history.rglob("*.sql")
                    if "after" in path.relative_to(history).as_posix()]
        require(len(upgrades) == 1, f"Expected one generated upgrade in {history}")
        generated = upgrades[0].read_text()
        for name in ("empty", "populated"):
            require((artifacts / name / "migration.sql").read_text() == generated)
require(result["gates"] == gate_results(result["runs"]))
summary = {"runs_validated": len(result["runs"])}
if args.compare:
    previous = outcomes(json.loads(args.compare.read_text()))
    current = outcomes(result)
    require(previous.keys() <= current.keys())
    require(all(value == current[key] for key, value in previous.items()), "Deterministic outcomes differ")
    summary["matching_previous_runs"] = len(previous)
print(json.dumps(summary, indent=2))
