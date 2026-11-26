import hashlib
import json
import os
import platform
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .checks import check_invariants, create_database, intended_change, snapshot
from .environment import ROOT, scratch_scope
from .generate import generate
from .runners import execute
from .report import gate_results, write_report
from .pins import upstream_provenance

DEFAULT_DOCTOR = None


def resolve_doctor(doctor=None):
    candidate = os.fspath(doctor) if doctor is not None else os.environ.get("SMP_DOCTOR") or "sqlite-doctor"
    resolved = shutil.which(candidate)
    return Path(resolved).resolve() if resolved else Path(candidate).expanduser().resolve()


def lint(doctor, sql, output):
    output.write_text(sql)
    try:
        result = subprocess.run([str(doctor), "--format", "json", str(output)],
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "detected": None, "returncode": None, "output": None, "stderr": "", "error": str(exc)}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        data = None
    available = result.returncode in (0, 1) and data is not None
    return {"available": available, "detected": result.returncode == 1 if available else None,
            "returncode": result.returncode, "output": data, "stderr": result.stderr}


def run_case(case, path, label, output, doctor=DEFAULT_DOCTOR, generated=None):
    doctor = resolve_doctor(doctor)
    case, output = Path(case).resolve(), Path(output).resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Output must be inside the repository")
    spec = json.loads((case / "case.json").read_text())
    pins = json.loads((ROOT / "versions.json").read_text())
    if label not in pins[spec["framework"]]:
        raise ValueError(f"Unknown {spec['framework']} pin: {label}")
    if path == "rails" and spec["framework"] != "rails":
        raise ValueError("Rails requires a Rails case")
    if path != "rails" and spec["framework"] != "drizzle":
        raise ValueError("Drizzle and raw paths require a generated-SQL case")
    provenance = upstream_provenance(spec["framework"], label)
    output.mkdir(parents=True, exist_ok=False)
    if generated is None and spec["framework"] == "drizzle":
        generated = generate(case, label, scope=scratch_scope(output))
    if generated:
        shutil.copytree(generated / "history", output / "generated_history")
        shutil.copyfile(generated / "generation.json", output / "generation.json")
    schema, seed = (case / spec["schema"]).read_text(), (case / spec["seed"]).read_text()
    trials = {}
    for populated in (True, False):
        name = "populated" if populated else "empty"
        folder = output / name
        folder.mkdir()
        database = folder / "database.db"
        create_database(database, schema, seed, populated)
        before = snapshot(database, spec["tables"])
        if before["foreign_key_check"] or before["integrity_check"] != ["ok"] or before["errors"] or before["view_errors"]:
            raise ValueError(f"Invalid fixture: {before}")
        if intended_change(before, spec["expected"]):
            raise ValueError("Intended change already holds before migration")
        execution = execute(case, spec, path, label, database, folder, generated)
        if path == "rails" and provenance:
            fix = provenance[label]
            if execution.get("activerecord_revision") != fix["commit"]:
                raise ValueError("Rails runner did not load the pinned PR revision")
            if execution.get("adapter_sha256") != fix["adapter_sha256"]:
                raise ValueError("Rails runner adapter differs from the pinned PR source")
        after = snapshot(database, spec["tables"])
        trials[name] = {"execution": execution, "before": before, "after": after,
                        "violations": check_invariants(before, after, spec["expected"])}
    populated = output / "populated"
    trace = populated / "executed.sql"
    migration = (populated / "migration.sql").read_text()
    lint_results = {}
    if trace.exists():
        for name, sql in {"executed": trace.read_text(), "migration_only": migration,
                          "schema_and_executed": schema + "\n" + trace.read_text(),
                          "schema_and_migration": schema + "\n" + migration}.items():
            lint_results[name] = lint(doctor, sql, output / f"lint_{name}.sql")
    else:
        lint_results = {name: {"available": False, "detected": None, "returncode": None, "output": None,
                               "stderr": "", "error": "Missing SQL trace"}
                        for name in ("executed", "migration_only", "schema_and_executed", "schema_and_migration")}
    result = {"case": spec["id"], "role": spec["role"], "path": path, "version_label": label,
              "pins": json.loads((ROOT / "versions.json").read_text())[spec["framework"]][label],
              "sqlite_doctor_sha256": hashlib.sha256(doctor.read_bytes()).hexdigest() if doctor.is_file() else None,
              "provenance": spec["provenance"], "description": spec["description"],
              "artifacts": str(output.relative_to(ROOT)), "trials": trials,
              "detectors": {"empty_db": {"detected": not trials["empty"]["execution"]["success"]},
                            "lint": lint_results,
                            "populated_invariants": {"detected": bool(trials["populated"]["violations"]),
                                                     "violations": trials["populated"]["violations"]}}}
    if provenance:
        result["upstream_fixes"] = provenance
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def run_pilot(output, doctor=DEFAULT_DOCTOR, upstream=False, labels=None):
    doctor = resolve_doctor(doctor)
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Output must be inside the repository")
    output.mkdir(parents=True, exist_ok=True)
    runs = []
    pins = json.loads((ROOT / "versions.json").read_text())
    available = {label for framework in pins.values() for label in framework
                 if (label not in ("before", "current")) == upstream}
    if labels is not None and (not labels or set(labels) - available):
        raise ValueError(f"Labels must select from: {', '.join(sorted(available))}")
    pins = {framework: {label: pin for label, pin in versions.items()
                        if (label not in ("before", "current")) == upstream
                        and (labels is None or label in labels)}
            for framework, versions in pins.items()}
    for case in sorted((ROOT / "cases").iterdir()):
        spec = json.loads((case / "case.json").read_text())
        for label in pins[spec["framework"]]:
            generated = generate(case, label, scope=scratch_scope(output)) if spec["framework"] == "drizzle" else None
            paths = ("drizzle", "raw", "raw-tx") if generated else ("rails",)
            for path in paths:
                print(f"Running {case.name} / {path} / {label}", flush=True)
                runs.append(run_case(case, path, label, output / "runs" / f"{case.name}--{path}--{label}",
                                     doctor, generated))
    result = {"format_version": 1, "observed_at": datetime.now(timezone.utc).isoformat(),
              "environment": {"platform": platform.platform(), "python": platform.python_version(),
                              "observer_sqlite": sqlite3.sqlite_version,
                              "sqlite_doctor": str(doctor),
                              "sqlite_doctor_sha256": hashlib.sha256(doctor.read_bytes()).hexdigest() if doctor.is_file() else None},
              "pins": pins,
              "upstream_evidence": json.loads((ROOT / "sources/upstream.json").read_text()), "runs": runs}
    result["gates"] = gate_results(runs)
    if upstream:
        from .upstream_report import write_upstream_report
        result["upstream_fixes"] = json.loads((ROOT / "sources/upstream_fixes.json").read_text())
        result["upstream_builds"] = json.loads((ROOT / "sources/upstream_builds.json").read_text())
        (output / "upstream_fixes.json").write_text(json.dumps(result, indent=2) + "\n")
        write_upstream_report(result, output / "upstream_fixes.md")
    else:
        (output / "pilot.json").write_text(json.dumps(result, indent=2) + "\n")
        write_report(result, output / "pilot_report.md")
    return result
