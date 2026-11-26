import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def project_comparison(data, raw):
    """The fields of a GitHub compare response that the study uses, with the checksum of the response."""
    return {"url": data["url"], "status": data["status"], "ahead_by": data["ahead_by"],
            "behind_by": data["behind_by"], "total_commits": data["total_commits"],
            "base_commit": {"sha": data["base_commit"]["sha"]},
            "merge_base_commit": {"sha": data["merge_base_commit"]["sha"]},
            "commits": [{"sha": commit["sha"], "parents": [parent["sha"] for parent in commit["parents"]]}
                        for commit in data["commits"]],
            "files": [{key: file[key] for key in ("filename", "status", "additions", "deletions", "changes", "sha")}
                      for file in data["files"]],
            "response": {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}}


def collect(output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / "results/rails_base"):
        raise ValueError("Output must be under results/rails_base")
    fixes = json.loads((ROOT / "sources/upstream_fixes.json").read_text())
    folder = output / "source"
    folder.mkdir(parents=True, exist_ok=True)
    result = {}
    for label in ("rails-pr57128", "rails-pr58709", "rails-pr56811"):
        pin = fixes[label]
        def fetch(repository, base, head, suffix):
            destination = folder / (label + suffix + ".json")
            url = f"https://api.github.com/repos/{repository}/compare/{base}...{head}"
            raw = subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error", "--retry", "2",
                                  "--max-time", "180", url], check=True, capture_output=True).stdout
            data = project_comparison(json.loads(raw), raw)
            destination.write_text(json.dumps(data, indent=2) + "\n")
            return data
        data = fetch(pin["repository"], pin["base_commit"], pin["commit"], "-compare")
        result[label] = {key: data[key] for key in ("status", "ahead_by", "behind_by", "total_commits")}
        result[label].update(merge_base=data["merge_base_commit"]["sha"],
                             changed_files=[file["filename"] for file in data["files"]])
        if data["behind_by"]:
            divergence = fetch("rails/rails", data["merge_base_commit"]["sha"], pin["base_commit"], "-base-divergence")
            result[label]["base_only_files"] = [file["filename"] for file in divergence["files"]]
        print(label, result[label], flush=True)
    (output / "source_comparisons.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "results/rails_base")
    collect(parser.parse_args().output)
