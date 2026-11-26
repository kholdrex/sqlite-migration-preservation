"""Build small, pinned Drizzle artifacts without installing the monorepo workspace."""
import hashlib
import difflib
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smp.environment import local_env


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(url, destination):
    subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error",
                    "--retry", "2", "--connect-timeout", "15", "--max-time", "180",
                    url, "--output", str(destination)], check=True)


def pack(package, destination, cwd, env):
    result = subprocess.run(["npm", "pack", package, "--json", "--pack-destination", str(destination)],
                            cwd=cwd, env=env, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)[0]


def main():
    env = local_env()
    pins = json.loads((ROOT / "sources/upstream_fixes.json").read_text())
    artifacts = ROOT / "runners/artifacts"
    artifacts.mkdir(exist_ok=True)
    subprocess.run(["npm", "ci", "--no-audit", "--no-fund"],
                   cwd=ROOT / "runners/build-drizzle", env=env, check=True)
    builds = {}
    (ROOT / ".cache").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="upstream-build-", dir=ROOT / ".cache") as temporary:
        work = Path(temporary)
        for label in ("drizzle-pr5784", "drizzle-pr5074"):
            pin = pins[label]
            folder = work / label
            folder.mkdir()
            base = pack(f"{pin['package']}@{pin['base_version']}", folder, folder, env)
            with tarfile.open(folder / base["filename"]) as archive:
                archive.extractall(folder, filter="data")
            package = folder / "package"
            source_hashes = {}
            if label == "drizzle-pr5784":
                source = folder / "dialect.ts"
                source_path = "drizzle-orm/src/sqlite-core/dialect.ts"
                base_source = folder / "base-dialect.ts"
                for revision, destination in ((pin["commit"], source), (pin["base_commit"], base_source)):
                    download(f"https://raw.githubusercontent.com/{pin['repository']}/{revision}/{source_path}",
                             destination)
                published = json.loads((package / "sqlite-core/dialect.js.map").read_text())["sourcesContent"][0]
                if published != base_source.read_text():
                    raise ValueError("Published ORM dialect does not match the recorded PR base")
                patch = difflib.unified_diff(base_source.read_text().splitlines(True), source.read_text().splitlines(True),
                                            fromfile="a/" + source_path, tofile="b/" + source_path)
                (ROOT / "sources/drizzle-pr5784.patch").write_text("".join(patch))
                source_hashes[source_path] = digest(source)
                source_hashes["base:" + source_path] = digest(base_source)
                kind = "orm"
            else:
                archive_path = folder / "source.tgz"
                download(f"https://codeload.github.com/{pin['repository']}/tar.gz/{pin['commit']}", archive_path)
                with tarfile.open(archive_path) as archive:
                    # Only the affected package is needed, including its upstream build recipe.
                    members = [m for m in archive.getmembers() if "/drizzle-kit/" in m.name]
                    archive.extractall(folder / "source", members=members, filter="data")
                source = next((folder / "source").iterdir()) / "drizzle-kit"
                source_hashes = {str(p.relative_to(source)): digest(p) for p in sorted(source.rglob("*.ts"))
                                 if p.is_relative_to(source / "src") or p.name == "build.ts"}
                kind = "kit"
            subprocess.run(["node", str(ROOT / "scripts/build_drizzle.mjs"), kind, str(source), str(package)],
                           cwd=ROOT, env=env, check=True)
            # Normalize source-map paths; sourcesContent retains the exact upstream source.
            if kind == "orm":
                for path in (package / "sqlite-core").glob("dialect.*.map"):
                    mapping = json.loads(path.read_text())
                    mapping["sources"] = [source_path]
                    path.write_text(json.dumps(mapping, separators=(",", ":")) + "\n")
            metadata_path = package / "package.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["version"] = pin["version"]
            metadata["smp_upstream"] = {"commit": pin["commit"], "approach": pin["approach"]}
            metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
            built = pack(".", artifacts, package, env)
            artifact = artifacts / built["filename"]
            builds[label] = {
                "commit": pin["commit"], "approach": pin["approach"],
                "base_tarball": {k: base[k] for k in ("name", "version", "integrity", "shasum", "size")},
                "artifact": str(artifact.relative_to(ROOT)),
                "sha256": digest(artifact), "bytes": artifact.stat().st_size,
                "source_sha256": source_hashes,
                "runtime_sha256": {str(p.relative_to(package)): digest(p) for p in sorted(package.rglob("*"))
                                   if p.is_file() and p.suffix in (".js", ".cjs", ".mjs")},
            }
    (ROOT / "sources/upstream_builds.json").write_text(json.dumps(builds, indent=2) + "\n")


if __name__ == "__main__":
    main()
