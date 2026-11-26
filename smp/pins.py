import hashlib
import json

from .environment import ROOT


def upstream_provenance(framework, label):
    if not label.startswith(("rails-pr", "rails-base-", "drizzle-pr")):
        return {}
    fixes = json.loads((ROOT / "sources/upstream_fixes.json").read_text())
    if framework == "rails":
        return {label: fixes[label]}
    pins = json.loads((ROOT / "versions.json").read_text())[framework][label]
    builds = json.loads((ROOT / "sources/upstream_builds.json").read_text())
    selected = {}
    for name, build in builds.items():
        fix = fixes[name]
        if pins[fix["package"]] != fix["version"]:
            continue
        package = ROOT / "runners/drizzle" / label / "node_modules" / fix["package"]
        for filename, expected in build["runtime_sha256"].items():
            if hashlib.sha256((package / filename).read_bytes()).hexdigest() != expected:
                raise ValueError(f"{label}: installed upstream code differs in {filename}; run scripts/setup.py --upstream")
        selected[name] = {**fix, "artifact": build["artifact"], "artifact_sha256": build["sha256"]}
    if not selected:
        raise ValueError(f"No upstream build for {label}")
    return selected
