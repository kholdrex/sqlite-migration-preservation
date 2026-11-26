import json
import shutil
import subprocess

from .environment import ROOT, local_env


def history_sql(history, revision):
    """Kit 0.x writes 000N_<name>.sql; Kit 1.x writes <timestamp>_<name>/migration.sql.

    history maps paths relative to the generated history directory to their SQL.
    """
    index = {"before": "0000", "after": "0001"}[revision]
    if f"{index}_{revision}.sql" in history:
        return history[f"{index}_{revision}.sql"]
    (sql,) = [text for name, text in history.items() if name.endswith(f"_{revision}/migration.sql")]
    return sql


def generate(case, label, resolve_rename=False, scope="default"):
    """Generate both schema revisions, retaining only the upgrade for execution.

    The scratch directory stays beneath the runtime, where Kit resolves its packages.
    """
    spec = json.loads((case / "case.json").read_text())
    runtime = ROOT / "runners/drizzle" / label
    pins = json.loads((ROOT / "versions.json").read_text())["drizzle"][label]
    for package, version in pins.items():
        installed = json.loads((runtime / "node_modules" / package / "package.json").read_text())["version"]
        if installed != version:
            raise ValueError(f"{package}: expected {version}, found {installed}; run scripts/setup.py")
    work = runtime / "generated" / scope / spec["id"]
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    settings = {"dialect": "sqlite", "schema": str((work / "schema.ts").relative_to(runtime)),
                "out": str((work / "history").relative_to(runtime))}
    if pins["drizzle-kit"].startswith("0."):
        config = work / "drizzle.config.json"
        config.write_text(json.dumps(settings))
    else:
        # Kit 1.x loads configs as ES modules and rejects plain JSON.
        config = work / "drizzle.config.mjs"
        config.write_text(f"export default {json.dumps(settings)};\n")
    logs = []
    for revision in ("before", "after"):
        shutil.copyfile(case / spec[revision], work / "schema.ts")
        command = ["node", str(runtime / "node_modules/drizzle-kit/bin.cjs"), "generate",
                   f"--config={config}", f"--name={revision}"]
        if resolve_rename and revision == "after":
            from .matrix_generate import rename_command
            result = rename_command(command, runtime, local_env())
        else:
            result = subprocess.run(command, cwd=runtime, env=local_env(),
                                    capture_output=True, text=True, timeout=120)
        logs.append({"revision": revision, "returncode": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
        (work / "generation.json").write_text(json.dumps(logs, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(f"drizzle-kit generate failed: {logs[-1]}")
    if not (work / "history/meta/_journal.json").exists():
        # Kit 1.x writes one folder per migration and no journal.
        # Both folders can share a timestamp, so the upgrade is found by its name.
        folders = [p for p in (work / "history").iterdir() if p.is_dir()]
        upgrades = [p for p in folders if p.name.endswith("_after")]
        if len(folders) != 2 or len(upgrades) != 1:
            raise RuntimeError(f"Expected an initial and an upgrade migration: {folders}")
        shutil.copytree(upgrades[0], work / "upgrade" / upgrades[0].name)
        return work
    journal = json.loads((work / "history/meta/_journal.json").read_text())
    if len(journal["entries"]) != 2:
        raise RuntimeError(f"Expected an initial and an upgrade migration: {journal}")
    upgrade = work / "upgrade"
    (upgrade / "meta").mkdir(parents=True)
    entry = journal["entries"][-1]
    shutil.copyfile(work / "history" / f"{entry['tag']}.sql", upgrade / f"{entry['tag']}.sql")
    journal["entries"] = [entry]
    (upgrade / "meta/_journal.json").write_text(json.dumps(journal, indent=2) + "\n")
    return work
