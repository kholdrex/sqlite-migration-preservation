import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def runtime_root():
    value = os.environ.get("SMP_RUNTIME_ROOT")
    if not value:
        return ROOT
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError("SMP_RUNTIME_ROOT must be a new directory inside the repository")
    return path


def cache_dir():
    return runtime_root() / ".cache"


def scratch_scope(output):
    """Scratch space is keyed by the output directory, so two runs never share or delete each other's files."""
    return hashlib.sha256(str(Path(output).resolve()).encode()).hexdigest()[:12]


def claim_output(output, name, evidence, manifest):
    """Reuse evidence in an output directory only for the linter, pins and code that produced it."""
    path = output / name
    if path.exists():
        if json.loads(path.read_text()) != manifest:
            raise ValueError(f"{output} holds evidence from a different linter, pin set or harness revision; "
                             "use a fresh output directory")
    elif evidence.exists() and any(evidence.iterdir()):
        raise ValueError(f"{output} holds evidence without a run manifest; use a fresh output directory")
    else:
        output.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2) + "\n")


def source_hashes():
    package = Path(__file__).resolve().parent
    return {source.name: hashlib.sha256(source.read_bytes()).hexdigest() for source in sorted(package.glob("*.py"))}


def local_env():
    env = os.environ.copy()
    runtime = runtime_root()
    cache = cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    env.update({
        "npm_config_cache": str(cache / "npm"),
        "npm_config_devdir": str(cache / "node-gyp"),
        "PIP_CACHE_DIR": str(cache / "pip"),
        "BUNDLE_USER_HOME": str(cache / "bundle"),
        "BUNDLE_APP_CONFIG": str(runtime / ".bundle"),
        "BUNDLE_PATH": str(runtime / "vendor" / "bundle"),
        "TMPDIR": str(cache),
    })
    return env


def ruby_command(version="3.3.2"):
    env = local_env()
    ruby = os.environ.get("SMP_RUBY")
    rvm = Path.home() / ".rvm"
    default = rvm / f"rubies/ruby-{version}/bin/ruby"
    if not ruby and default.exists():
        ruby = str(default)
        gems = rvm / f"gems/ruby-{version}"
        env["GEM_HOME"] = str(gems)
        env["GEM_PATH"] = f"{gems}:{gems}@global"
        env["PATH"] = f"{default.parent}:{gems}/bin:{env['PATH']}"
    return [ruby or "ruby", "-S", "bundle"], env
