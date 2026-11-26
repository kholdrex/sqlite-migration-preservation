"""Lint the retained inputs of the latest-pin cells again with another sqlite-doctor build.

The four lint inputs per cell are rebuilt from the evidence archives. With --verify,
the rebuilt inputs are linted with the recorded binary and must reproduce every
recorded lint result before a new build is trusted on them.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smp.checks import statements
from smp.pilot import lint
from smp.runners import TRANSACTION

SOURCES = ("operation_matrix", "orm_matrix")
UNTRACED = "CLI exposes no runtime SQL trace"


def selected(row):
    """The latest executable native pins, as in the paper's Current selection."""
    return row["path"] not in ("raw", "raw-tx") and (
        row["version_label"] in ("current", "django-current", "prisma-stable")
        or (row["framework"] == "alembic" and row.get("mode") == "auto"))


def key(source, row):
    return [source, row["framework"], row["version_label"], row.get("mode", "default"),
            row["path"], row["operation"], row["context"]]


def inputs(source, row):
    archive = json.loads(gzip.decompress((ROOT / row["artifacts"]).read_bytes()))
    schema = archive["schema"]
    if source == "operation_matrix":
        trace = archive["evidence"]["populated"]["executed.sql"]
        migration = archive["evidence"]["populated"]["migration.sql"]
    else:
        trace = archive["trials"][row["path"] + "/populated"]["executed.sql"]
        migration = archive["generation"]["migration.sql"]
        if row["framework"] == "django":
            migration = "\n".join(s for s in statements(migration) if not TRANSACTION.match(s))
    return trace, {"migration_only": migration, "schema_and_migration": schema + "\n" + migration,
                   "executed": trace, "schema_and_executed": schema + "\n" + trace}


def relint(doctor, work, job):
    index, source, row = job
    trace, variants = inputs(source, row)
    result = {}
    for name, sql in variants.items():
        if "executed" in name and not trace:
            result[name] = {"available": False, "reason": UNTRACED}
        else:
            result[name] = lint(doctor, sql, work / f"{index}_{name}.sql")
            (work / f"{index}_{name}.sql").unlink()
    return {"key": key(source, row), "lint": result}


def comparable(lint_result):
    """Lint results without the input file path, which differs between runs."""
    output = lint_result.get("output")
    if output is not None:
        output = {k: v for k, v in output.items() if k != "source"}
    return {"available": lint_result.get("available"), "detected": lint_result.get("detected"), "output": output}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doctor", type=Path, required=True)
    parser.add_argument("--commit", required=True, help="sqlite-doctor commit the binary was built from")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true", help="require identical results to the recorded run")
    args = parser.parse_args()
    if not args.verify and args.output is None:
        parser.error("give --output or --verify")
    if args.output is not None and args.output.exists():
        parser.error(f"{args.output} already exists; choose a new file")
    if not args.doctor.is_file() or not os.access(args.doctor, os.X_OK):
        parser.error(f"{args.doctor} is not an executable file")
    jobs = []
    for source in SOURCES:
        for row in json.loads((ROOT / f"results/{source}.json").read_text())["rows"]:
            if selected(row):
                jobs.append((len(jobs), source, row))
    work = ROOT / ".cache/relint"
    work.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(lambda job: relint(args.doctor, work, job), jobs))
    if args.verify:
        mismatches = [(job[1], key(job[1], job[2]), name) for job, row in zip(jobs, rows)
                      for name in row["lint"]
                      if comparable(row["lint"][name]) != comparable(job[2]["detectors"]["lint"][name])]
        linted = sum(result.get("reason") != UNTRACED for row in rows for result in row["lint"].values())
        print(f"{len(rows)} cells, {len(rows) * 4} lint inputs ({linted} linted, {len(rows) * 4 - linted} without a "
              f"runtime trace), {len(mismatches)} mismatches")
        for mismatch in mismatches[:10]:
            print(" ", mismatch)
        sys.exit(1 if mismatches else 0)
    output = {"format_version": 1, "sqlite_doctor_commit": args.commit,
              "sqlite_doctor_sha256": hashlib.sha256(args.doctor.read_bytes()).hexdigest(),
              "selection": "latest executable native pins (paper Current selection)",
              "sources": [f"results/{s}.json" for s in SOURCES], "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(json.dumps(output, separators=(",", ":")) + "\n")
    print(f"Wrote {len(rows)} cells to {args.output}")


if __name__ == "__main__":
    main()
