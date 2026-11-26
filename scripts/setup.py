"""Install the pinned framework dependencies inside the checkout."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smp.environment import local_env, ruby_command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", action="store_true", help="Install the additional upstream-fix pins")
    parser.add_argument("--labels", nargs="+", help="Install only these labels")
    args = parser.parse_args()
    versions = json.loads((ROOT / "versions.json").read_text())
    fixes = json.loads((ROOT / "sources/upstream_fixes.json").read_text())
    for label, pins in versions["rails"].items():
        if args.labels and label not in args.labels:
            continue
        if (label not in ("before", "current")) != args.upstream:
            continue
        folder = ROOT / "runners/rails" / label
        folder.mkdir(parents=True, exist_ok=True)
        if label in fixes:
            fix = fixes[label]
            if "local_git" in fix:
                from build_rails_merge import build
                build(label)
                source = f'File.expand_path("../../../{fix["local_git"]}", __dir__)'
            else:
                source = f'"https://github.com/{fix["repository"]}.git"'
            gems = (f'gem "activerecord", git: {source}, '
                    f'ref: "{fix["commit"]}", glob: "{{activerecord,activemodel,activesupport}}/*.gemspec"\n'
                    f'gem "sqlite3", "{pins["sqlite3"]}"\n')
        else:
            gems = ''.join(f'gem "{name}", "{version}"\n' for name, version in pins.items())
        (folder / "Gemfile").write_text('source "https://rubygems.org"\n' + gems)
        command, env = ruby_command(fixes.get(label, {}).get("ruby", "3.3.2"))
        env["BUNDLE_GEMFILE"] = str(folder / "Gemfile")
        subprocess.run(command + ["install"], cwd=ROOT, env=env, check=True, timeout=600)
    for label, pins in versions["drizzle"].items():
        if args.labels and label not in args.labels:
            continue
        if (label not in ("before", "current")) != args.upstream:
            continue
        folder = ROOT / "runners/drizzle" / label
        folder.mkdir(parents=True, exist_ok=True)
        dependencies = dict(pins)
        if args.upstream:
            builds = json.loads((ROOT / "sources/upstream_builds.json").read_text())
            for fix_label, build in builds.items():
                fix = fixes[fix_label]
                if pins[fix["package"]] == fix["version"]:
                    artifact = ROOT / build["artifact"]
                    if not artifact.exists():
                        raise FileNotFoundError(f"Missing {artifact}; run scripts/build_upstream.py")
                    dependencies[fix["package"]] = "file:" + os.path.relpath(artifact, folder)
        manifest = {"name": f"smp-{label}".replace("+", "-and-") if args.upstream else f"smp-drizzle-{label}",
                    "private": True, "version": "0.0.0", "type": "module", "dependencies": dependencies}
        (folder / "package.json").write_text(json.dumps(manifest, indent=2) + "\n")
        locked = (folder / "package-lock.json").exists()
        if args.upstream and not locked:
            # Preserve current's transitive resolutions while replacing the affected packages.
            shutil.copyfile(ROOT / "runners/drizzle/current/package-lock.json", folder / "package-lock.json")
        subprocess.run(["npm", "ci" if locked else "install", "--no-audit", "--no-fund"],
                       cwd=folder, env=local_env(), check=True, timeout=600)


if __name__ == "__main__":
    main()
