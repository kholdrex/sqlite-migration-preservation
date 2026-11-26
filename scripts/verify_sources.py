"""Record the upstream issue states, Rails tag sources and registry versions the pilot refers to."""
import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def collect():
    record = {"observed_at": datetime.now(timezone.utc).isoformat(), "issues": [], "rails_tags": [], "registries": {}}
    for repository, kind, number in [
        ("rails/rails", "issues", 55866), ("rails/rails", "pulls", 55907),
        ("rails/rails", "pulls", 57128), ("drizzle-team/drizzle-orm", "issues", 4938),
        ("drizzle-team/drizzle-orm", "issues", 5782),
    ]:
        url = f"https://api.github.com/repos/{repository}/{kind}/{number}"
        data = json.loads(fetch(url))
        record["issues"].append({"api_url": url, **{key: data.get(key) for key in
                                 ("html_url", "title", "state", "merged_at", "merge_commit_sha", "updated_at")}})
    versions = json.loads(fetch("https://rubygems.org/api/v1/versions/activerecord.json"))
    for version in ("7.2.2.2", "7.2.3", "8.0.3", "8.0.4", "8.1.0", "8.1.4"):
        url = f"https://raw.githubusercontent.com/rails/rails/v{version}/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb"
        source = fetch(url)
        method = source.decode().split("def alter_table(", 1)[1].split("def move_table(", 1)[0]
        record["rails_tags"].append({
            "version": version, "url": url, "source_sha256": hashlib.sha256(source).hexdigest(),
            "disable_integrity_outside_adapter_transaction": method.index("disable_referential_integrity do") < method.index("transaction do"),
            "published_at": next(v["created_at"] for v in versions if v["number"] == version),
        })
    record["registries"]["activerecord"] = {"url": "https://rubygems.org/api/v1/versions/activerecord.json",
                                               "latest_stable": next(v["number"] for v in versions if not v["prerelease"])}
    for package in ("drizzle-orm", "drizzle-kit"):
        url = f"https://registry.npmjs.org/{package}/latest"
        data = json.loads(fetch(url))
        record["registries"][package] = {"url": url, "latest_stable": data["version"], "integrity": data["dist"]["integrity"]}
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New file; sources/upstream.json is the retained record")
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"{args.output} already exists")
    args.output.write_text(json.dumps(collect(), indent=2) + "\n")


if __name__ == "__main__":
    main()
