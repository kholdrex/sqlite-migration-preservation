"""Rebuild the merge commit of a combined Rails pin as a local dependency repository."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def relocate_lockfile(label, destination):
    lockfile = ROOT / "runners/rails" / label / "Gemfile.lock"
    text = lockfile.read_text()
    pin = json.loads((ROOT / "sources/upstream_fixes.json").read_text())[label]
    if f"  revision: {pin['commit']}\n" not in text:
        raise ValueError("Combined Rails lockfile has an unexpected revision")
    relocated, count = re.subn(r"(?m)^(GIT\n  remote: )[^\n]+", lambda m: m[1] + str(destination), text)
    if count != 1:
        raise ValueError("Expected exactly one combined Rails Git source")
    if relocated != text:
        lockfile.write_text(relocated)


def build(label="rails-pr57128+56811"):
    fixes = json.loads((ROOT / "sources/upstream_fixes.json").read_text())
    pin = fixes[label]
    parent = next(p for p in fixes.values() if p["commit"] == pin["parents"][0])
    destination = ROOT / pin["local_git"]
    if destination.exists():
        revision = subprocess.check_output(["git", "-C", str(destination), "rev-parse", "HEAD"], text=True).strip()
        if revision != pin["commit"]:
            raise ValueError("Existing local Rails merge has a different revision")
        relocate_lockfile(label, destination)
        return destination
    patch = ROOT / pin["resolution_patch"]
    if hashlib.sha256(patch.read_bytes()).hexdigest() != pin["resolution_patch_sha256"]:
        raise ValueError(f"Resolution patch differs from its recorded hash: {patch.name}")
    (ROOT / ".cache").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rails-merge-", dir=ROOT / ".cache") as temporary:
        work = Path(temporary)

        def git(*args, data=None):
            return subprocess.check_output(["git", "-C", str(work), *args], input=data)

        git("init", "--quiet")
        git("fetch", "--quiet", "--no-tags", "--depth=1", f"https://github.com/{parent['repository']}.git", pin["parents"][0])
        git("checkout", "--quiet", "--detach", pin["parents"][0])
        # This patch is the complete resolved delta from the first parent. Its
        # tree was checked against the actual merge of both heads.
        git("apply", "--index", str(patch))
        tree = git("write-tree").decode().strip()
        if tree != pin["tree"]:
            raise ValueError(f"Resolved tree {tree} differs from the recorded {pin['tree']}")
        identity = pin["commit_identity"]
        payload = (f"tree {tree}\n" + "".join(f"parent {p}\n" for p in pin["parents"])
                   + f"author {identity}\ncommitter {identity}\n\n{pin['commit_message']}")
        revision = git("hash-object", "-t", "commit", "-w", "--stdin", data=payload.encode()).decode().strip()
        if revision != pin["commit"]:
            raise ValueError(f"Merge commit {revision} differs from the recorded {pin['commit']}")
        for name, expected in pin["source_sha256"].items():
            if hashlib.sha256((work / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f"Merged source differs from its recorded hash: {name}")
        # Keep only the merged snapshot: detached HEAD with a shallow boundary.
        git("update-ref", "--no-deref", "HEAD", revision)
        (work / ".git/shallow").write_text(revision + "\n")
        subprocess.run(["git", "clone", "--quiet", "--bare", "--depth=1", work.as_uri(), str(destination)], check=True)
    relocate_lockfile(label, destination)
    print(f"Rails merge: {pin['commit']} ({destination.relative_to(ROOT)})")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label", nargs="?", default="rails-pr57128+56811")
    build(parser.parse_args().label)
