import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smp.environment import ruby_command


def base_pins(fixes):
    groups = {}
    for label, pin in fixes.items():
        if label.startswith("rails-pr") and "base_commit" in pin:
            groups.setdefault(pin["base_commit"], []).append(label)
    result = {}
    for commit, parents in groups.items():
        label = "rails-base-" + commit[:12]
        pin = fixes[label]
        if pin["commit"] != commit or sorted(pin["base_for"]) != sorted(parents):
            raise ValueError(f"Inconsistent base mapping: {label}")
        result[label] = pin
    return result


def build(output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / "results/rails_base") or output == ROOT / "results/rails_base":
        raise ValueError("Output must be a directory of its own under results/rails_base")
    if (output / "builds.json").exists():
        raise ValueError(f"{output} already holds a build record; select a new directory")
    output.mkdir(parents=True, exist_ok=True)
    os.environ["SMP_RUNTIME_ROOT"] = str(output / "runtime")
    fixes = json.loads((ROOT / "sources/upstream_fixes.json").read_text())
    builds = {}
    for label, pin in base_pins(fixes).items():
        folder = ROOT / "runners/rails" / label
        evidence = output / "builds" / label
        evidence.mkdir(parents=True, exist_ok=True)
        command, env = ruby_command(pin["ruby"])
        env.update(BUNDLE_GEMFILE=str(folder / "Gemfile"), BUNDLE_FROZEN="true")
        print(f"Installing {label} ({pin['commit']})", flush=True)
        with (evidence / "bundle_install.log").open("w") as log:
            subprocess.run(command + ["install"], cwd=ROOT, env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=1800)
        script = '''require "active_record"; require "sqlite3"; require "json"; require "digest"
ActiveRecord::Base.establish_connection(adapter: "sqlite3", database: ":memory:")
c = ActiveRecord::Base.connection
s = Bundler.load.specs.find { |g| g.name == "activerecord" }
puts JSON.generate({ruby: RUBY_VERSION, revision: s.source.revision,
  activerecord: ActiveRecord::VERSION::STRING, sqlite3_gem: SQLite3::VERSION,
  sqlite: c.select_value("SELECT sqlite_version()"),
  adapter_source: c.method(:alter_table).source_location.first,
  gems: Gem.loaded_specs.transform_values { |g| g.version.to_s }})
'''
        runtime = json.loads(subprocess.check_output(command + ["exec", "ruby", "-e", script],
                                                     cwd=ROOT, env=env, text=True))
        if runtime["ruby"] != "3.4.3" or runtime["revision"] != pin["commit"]:
            raise ValueError(f"Wrong runtime: {runtime}")
        if runtime["activerecord"] != pin["version"] or runtime["sqlite3_gem"] != "2.9.6":
            raise ValueError(f"Wrong dependency versions: {runtime}")
        checkout = Path(runtime["adapter_source"]).parents[4]
        hashes = {}
        for name, expected in pin["source_sha256"].items():
            source = checkout / name
            actual = hashlib.sha256(source.read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError(f"Source mismatch: {label}/{name}")
            hashes[name] = actual
            destination = output / "source" / label / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        for name in ("Gemfile", "Gemfile.lock"):
            shutil.copyfile(folder / name, evidence / name)
        builds[label] = {"pin": pin, "runtime": runtime, "source_sha256": hashes,
                         "lock_sha256": hashlib.sha256((folder / "Gemfile.lock").read_bytes()).hexdigest()}
        (evidence / "provenance.json").write_text(json.dumps(builds[label], indent=2) + "\n")
        print(f"Verified {label}: Ruby {runtime['ruby']}, SQLite {runtime['sqlite']}", flush=True)
    (output / "builds.json").write_text(json.dumps(builds, indent=2) + "\n")
    from scripts.inspect_rails_base import collect
    collect(output)
    return builds


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True, help="New directory under results/rails_base")
    build(parser.parse_args().output)
