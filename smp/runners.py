import json
import platform
import re
import sqlite3
import subprocess

from .checks import statements
from .environment import ROOT, local_env, ruby_command

TRANSACTION = re.compile(r"^\s*(?:BEGIN|COMMIT|END|ROLLBACK|SAVEPOINT|RELEASE)\b", re.I)


def run_raw(database, sql, output, transactional):
    executed = []
    db = sqlite3.connect(database, isolation_level=None)
    db.execute("PRAGMA foreign_keys=ON")
    metadata = {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                "foreign_keys_before": db.execute("PRAGMA foreign_keys").fetchone()[0]}
    db.set_trace_callback(executed.append)
    try:
        if transactional:
            db.execute("BEGIN")
        for statement in statements(sql):
            db.execute(statement)
        if transactional:
            db.execute("COMMIT")
        metadata["success"] = True
    except sqlite3.Error as exc:
        metadata.update(success=False, error=f"{type(exc).__name__}: {exc}")
        if db.in_transaction:
            db.execute("ROLLBACK")
    finally:
        db.set_trace_callback(None)
        metadata["foreign_keys_after"] = db.execute("PRAGMA foreign_keys").fetchone()[0]
        db.close()
    (output / "executed.sql").write_text("\n".join(s.rstrip().rstrip(";") + ";" for s in executed) + "\n")
    (output / "runner.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def run_external(command, env, output):
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                text=True, timeout=120)
        (output / "stdout.log").write_text(result.stdout)
        (output / "stderr.log").write_text(result.stderr)
        metadata_file = output / "runner.json"
        if not metadata_file.exists():
            return {"success": False, "error": "Runner did not produce metadata",
                    "returncode": result.returncode, "stderr": result.stderr}
        metadata = json.loads(metadata_file.read_text())
        metadata["returncode"] = result.returncode
        if result.returncode != 0:
            metadata["success"] = False
        return metadata
    except subprocess.TimeoutExpired as exc:
        return {"success": False, "error": f"Runner timeout: {exc}"}


def execute(case, spec, path, label, database, output, generated=None):
    if path == "rails":
        fixes = json.loads((ROOT / "sources/upstream_fixes.json").read_text())
        command, env = ruby_command(fixes.get(label, {}).get("ruby", "3.3.2"))
        env["BUNDLE_GEMFILE"] = str(ROOT / "runners/rails" / label / "Gemfile")
        metadata = run_external(command + ["exec", "ruby", str(ROOT / "runners/rails/run.rb"),
                                          str(database), str(case / spec["migration"]), str(output)], env, output)
        trace_file = output / "executed.sql"
        if trace_file.exists():
            migration_sql = "\n".join(s for s in statements(trace_file.read_text())
                                       if not TRANSACTION.match(s)
                                       and not re.search(r'\b(schema_migrations|ar_internal_metadata)\b', s))
        else:
            migration_sql = ""
    else:
        migration_file = next((generated / "upgrade").rglob("*.sql"))
        migration_sql = migration_file.read_text()
        if path in ("raw", "raw-tx"):
            metadata = run_raw(database, migration_sql, output, path == "raw-tx")
        elif path == "drizzle":
            metadata = run_external(["node", str(ROOT / "runners/drizzle/run.mjs"),
                                     str(ROOT / "runners/drizzle" / label), str(database),
                                     str(generated / "upgrade"), str(output)], local_env(), output)
        else:
            raise ValueError(f"Unknown execution path: {path}")
    (output / "migration.sql").write_text(migration_sql)
    return metadata
