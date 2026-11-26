"""Execute the deterministic operation/context product on installed pins."""
import os
import gzip
import hashlib
import json
import shutil
import sqlite3
import subprocess
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from .checks import create_database, require
from .environment import ROOT, cache_dir, claim_output, scratch_scope, source_hashes
from .generate import generate
from .matrix_spec import CONTEXTS, DRIZZLE, RAILS, cases, materialize
from .pins import upstream_provenance
from .pilot import DEFAULT_DOCTOR, resolve_doctor, lint
from .preservation import classify, expected_present, observe, probe_constraint, violations
from .rebuild import CLASSIFIER, rebuild
from .runners import execute


def write_gzip(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(value, separators=(",", ":")).encode(), mtime=0))


def read_gzip(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def run_pair(case, spec, label, path, generated, folder, doctor):
    folder.mkdir(parents=True, exist_ok=True)
    schema = (case / "schema.sql").read_text()
    seed = (case / "seed.sql").read_text()
    trials, evidence = {}, {}
    for populated in (True, False):
        name = "populated" if populated else "empty"
        output = folder / name
        output.mkdir()
        database = output / "database.db"
        create_database(database, schema, seed, populated)
        before = observe(database, spec)
        probe_constraint(database, spec, before)
        require(not before["errors"] and not before["foreign_key_check"] and not before["view_errors"])
        require(all(p["fires"] for p in before["trigger_probes"].values()), before)
        require(not expected_present(before, spec["expected"]), spec)
        execution = execute(case, spec, path, label, database, output, generated)
        if "foreign_keys_after" not in execution:
            raise RuntimeError(f"Runner infrastructure failure: {execution}")
        after = observe(database, spec, after=True)
        try:
            probe_constraint(database, spec, after)
        except sqlite3.OperationalError as exc:
            after["intended_probe"] = None
            after["intended_probe_error"] = str(exc)
            after["errors"].append(f"constraint probe: {exc}")
        found = violations(before, after, spec, execution)
        trace = (output / "executed.sql").read_text()
        trials[name] = {"execution": execution, "before": before, "after": after, "violations": found,
                        "outcome": classify(execution["success"], found, before, after),
                        "rebuild": rebuild(trace)}
        evidence[name] = {p.name: p.read_text() for p in output.iterdir()
                          if p.suffix in (".sql", ".json", ".log")}
        # The closed database is redundant with content snapshots and SQL traces.
        for p in output.glob("database.db*"):
            p.unlink(missing_ok=True)
    trace, migration = evidence["populated"]["executed.sql"], evidence["populated"]["migration.sql"]
    detectors = {"empty_db": not trials["empty"]["execution"]["success"],
                 "populated_invariants": bool(trials["populated"]["violations"]), "lint": {}}
    for name, sql in {"executed": trace, "migration_only": migration,
                      "schema_and_executed": schema + "\n" + trace,
                      "schema_and_migration": schema + "\n" + migration}.items():
        detectors["lint"][name] = lint(doctor, sql, folder / f"lint_{name}.sql")
    return {"framework": spec["framework"], "operation": spec["operation"], "context": spec["context"],
            "case": spec["id"], "version_label": label, "path": path, "supported": True,
            "outcome": trials["populated"]["outcome"], "rebuild": trials["populated"]["rebuild"],
            "trials": trials, "detectors": detectors}, evidence


def run_group(item, output, doctor):
    framework, operation, context, label = item
    work = cache_dir() / "operation-matrix" / scratch_scope(output) / f"{framework}_{operation}_{context}_{label}"
    case, spec = materialize(work / "case", framework, operation, context)
    paths = ("rails",) if framework == "rails" else ("drizzle", "raw", "raw-tx")
    row_files = [output / "operation_evidence" / f"{spec['id']}--{path}--{label}.json.gz" for path in paths]
    def completed(archive):
        saved = read_gzip(archive)
        if (saved["spec"] != spec or saved["schema"] != (case / "schema.sql").read_text()
                or saved["seed"] != (case / "seed.sql").read_text()):
            raise ValueError(f"Stale fixture evidence in {archive}; use a fresh output directory")
        row = saved["row"]
        for trial in row["trials"].values():
            found = violations(trial["before"], trial["after"], spec, trial["execution"])
            if found != trial["violations"]:
                raise ValueError(f"Stale checker evidence in {archive}; use a fresh output directory")
        return row

    if all(p.exists() for p in row_files):
        rows = [completed(p) for p in row_files]
        shutil.rmtree(work)
        return rows
    provenance = upstream_provenance(framework, label)
    generated = None
    if framework == "drizzle":
        generated = generate(case, label, resolve_rename=operation.startswith("rename"), scope=scratch_scope(output))
        history = {str(p.relative_to(generated)): p.read_text() for p in generated.rglob("*") if p.is_file()}
        write_gzip(output / "operation_evidence" / f"{spec['id']}--{label}--generation.json.gz", history)
    rows = []
    try:
        for path, archive in zip(paths, row_files):
            if archive.exists():
                rows.append(completed(archive))
                continue
            folder = work / path
            if folder.exists():
                shutil.rmtree(folder)
            row, evidence = run_pair(case, spec, label, path, generated, folder, doctor)
            if framework == "rails" and provenance:
                for trial in row["trials"].values():
                    require(trial["execution"]["activerecord_revision"] == provenance[label]["commit"])
                    require(trial["execution"]["adapter_sha256"] == provenance[label]["adapter_sha256"])
            row["artifacts"] = str(archive.relative_to(ROOT))
            write_gzip(archive, {"row": row, "spec": spec, "schema": (case / "schema.sql").read_text(),
                                 "seed": (case / "seed.sql").read_text(), "evidence": evidence})
            rows.append(row)
    finally:
        shutil.rmtree(work)
        if generated:
            shutil.rmtree(generated)
    return rows


def run_matrix(output, doctor=DEFAULT_DOCTOR, workers=6, frameworks=None, operations=None, labels=None, contexts=None):
    doctor = resolve_doctor(doctor)
    if not doctor.is_file() or not os.access(doctor, os.X_OK):
        raise FileNotFoundError(
            f"sqlite-doctor is unavailable: {doctor}. Supply --doctor, set SMP_DOCTOR, "
            "or install sqlite-doctor on PATH.")
    try:
        probe = subprocess.run([str(doctor), "--format", "json", "-"], input="SELECT 1;",
                               capture_output=True, text=True, timeout=30)
        available = probe.returncode in (0, 1) and isinstance(json.loads(probe.stdout), dict)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise ValueError(f"sqlite-doctor could not run: {doctor}: {exc}. Supply a working --doctor or SMP_DOCTOR.") from exc
    if not available:
        raise ValueError(f"sqlite-doctor returned invalid output: {doctor}. Supply a working --doctor or SMP_DOCTOR.")
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Output must be inside the repository")
    pins = json.loads((ROOT / "versions.json").read_text())
    known = {"frameworks": set(pins), "operations": {*RAILS, *DRIZZLE}, "contexts": set(CONTEXTS),
             "labels": {label for versions in pins.values() for label in versions}}
    for name, requested in (("frameworks", frameworks), ("operations", operations),
                            ("labels", labels), ("contexts", contexts)):
        unknown = sorted(set(requested or ()) - known[name])
        if unknown:
            raise ValueError(f"Unknown {name}: {', '.join(unknown)}")
    jobs = [(fw, op, ctx, label) for fw, op, ctx in cases() for label in pins[fw]
            if (not frameworks or fw in frameworks) and (not operations or op in operations)
            and (not labels or label in labels) and (not contexts or ctx in contexts)]
    if not jobs:
        raise ValueError("The selection matches no framework, operation, context and pin")
    doctor_sha256 = hashlib.sha256(doctor.read_bytes()).hexdigest()
    claim_output(output, "operation_manifest.json", output / "operation_evidence",
                 {"sqlite_doctor_sha256": doctor_sha256, "pins": pins, "rebuild_classifier": CLASSIFIER,
                  "source_sha256": source_hashes()})
    rows, errors = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_group, job, output, doctor): job for job in jobs}
        for index, future in enumerate(as_completed(futures), 1):
            job = futures[future]
            try:
                group = future.result()
                rows.extend(group)
                print(f"{index}/{len(jobs)} {' / '.join(job)}: " + ", ".join(r["outcome"] for r in group), flush=True)
            except Exception as exc:
                errors.append({"job": job, "error": repr(exc), "traceback": traceback.format_exc()})
                print(f"ERROR {' / '.join(job)}: {exc}", flush=True)
    rows.sort(key=lambda r: (r["framework"], r["version_label"], r["path"], r["operation"], r["context"]))
    result = {"format_version": 1, "observed_at": datetime.now(timezone.utc).isoformat(), "pins": pins,
              "contexts": CONTEXTS, "requested_groups": len(jobs), "errors": errors,
              "selection": {"frameworks": frameworks, "operations": operations, "labels": labels, "contexts": contexts},
              "upstream_fixes": json.loads((ROOT / "sources/upstream_fixes.json").read_text()),
              "upstream_builds": json.loads((ROOT / "sources/upstream_builds.json").read_text()),
              "sqlite_doctor_sha256": doctor_sha256,
              "rebuild_classifier": CLASSIFIER, "rows": rows}
    (output / "operation_matrix.json").write_text(json.dumps(result, separators=(",", ":")) + "\n")
    from .matrix_report import write_report
    write_report(result, output / "operation_matrix.md")
    return result
