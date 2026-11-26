import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.paper_numbers import LINTS, outcome
from scripts.relint import inputs, key, selected

IMAGE = "arigaio/atlas@sha256:dc27586a3d1097ff47e90124f13cbed884a27026c374a82e523699645a6d5d57"
SOURCES = ("operation_matrix", "rails_fixes", "orm_matrix")
OUTPUT = ROOT / "results/atlas_lint"
TXMODE = "-- atlas:txmode none\n\n"
RISK = re.compile(r"drop|delet|loss|lost|remov|cascade|null|chang|modif|renam|break", re.I)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


@contextmanager
def gzip_writer(path):
    with path.open("xb") as file:
        with gzip.GzipFile(filename="", mode="wb", fileobj=file, mtime=0) as compressed:
            yield compressed


def write_record(stream, record):
    stream.write((json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode())


def read_jsonl(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def load_evidence(path):
    records = {}
    for record in read_jsonl(path):
        key = record["cell_id"], record["input"]
        if key in records:
            raise ValueError(f"Duplicate archive key: {key}")
        if record["cell_id"] != "--".join(record["key"]) or record["input"] not in LINTS:
            raise ValueError(f"Invalid archive key: {key}")
        records[key] = record
    return records


def supporting_files(output):
    return json.loads(gzip.decompress((output / "supporting.json.gz").read_bytes()))


def directory_files(directory):
    return {p.relative_to(directory).as_posix(): p.read_bytes().decode("utf-8")
            for p in sorted(directory.rglob("*")) if p.is_file()}


def pack_cell(directory, row):
    if json.loads((directory / "cell.json").read_text()) != row:
        raise ValueError(f"Cell metadata differs: {row['cell_id']}")
    inputs, diagnostics = [], []
    for name in LINTS:
        sql, raw = {}, {}
        for path, content in directory_files(directory / name).items():
            if path.endswith(".json"):
                raw[path] = content
            elif path.endswith(".sql") or path.endswith("atlas.sum"):
                sql[path] = content
            else:
                raise ValueError(f"Unexpected evidence file: {path}")
        if json.loads(raw["decision.json"]) != row["lint"][name]:
            raise ValueError(f"Input decision differs: {row['cell_id']} {name}")
        header = dict(key=row["key"], cell_id=row["cell_id"], input=name)
        inputs.append(dict(header, files=sql))
        diagnostics.append(dict(header, files=raw))
    return inputs, diagnostics


def archive_cells(output, cells):
    rows = []
    with gzip_writer(output / "inputs.jsonl.gz") as sql, gzip_writer(output / "diagnostics.jsonl.gz") as raw:
        for row, inputs, diagnostics in cells:
            for record in inputs:
                write_record(sql, record)
            for record in diagnostics:
                write_record(raw, record)
            rows.append(row)
            if len(rows) % 20 == 0 or len(rows) == 479:
                print(f"Archived {len(rows)} cells", flush=True)
    return sorted(rows, key=lambda row: row["key"])


def storage_manifest(output, report):
    return {name: dict(sha256=digest((output / name).read_bytes()),
                       records=len(report["rows"]) * len(LINTS))
            for name in ("inputs.jsonl.gz", "diagnostics.jsonl.gz")}


def verify_archives(output, report):
    for name, metadata in report["evidence"].items():
        if digest((output / name).read_bytes()) != metadata["sha256"]:
            raise ValueError(f"Archive checksum differs: {name}")
    sql = load_evidence(output / "inputs.jsonl.gz")
    raw = load_evidence(output / "diagnostics.jsonl.gz")
    expected = {(row["cell_id"], name) for row in report["rows"] for name in LINTS}
    if set(sql) != expected or set(raw) != expected:
        raise ValueError("Archive keys differ from the report")
    for row in report["rows"]:
        for name, decision in row["lint"].items():
            key = row["cell_id"], name
            if sql[key]["key"] != row["key"] or raw[key]["key"] != row["key"]:
                raise ValueError(f"Cell key differs: {key}")
            if digest(sql[key]["files"]["input.sql"].encode()) != decision["input_sha256"]:
                raise ValueError(f"Input checksum differs: {key}")
            files = raw[key]["files"]
            if json.loads(files["decision.json"]) != decision:
                raise ValueError(f"Decision differs: {key}")
            for index, attempt in enumerate(decision["attempts"]):
                hashed = json.loads(files[f"{attempt}/hash.json"])
                if hashed["returncode"] != 0:
                    actual = unavailable(hashed["stderr"] or "Migration hash failed", "hash_error")
                else:
                    actual = classify(json.loads(files[f"{attempt}/lint.json"]), row["lost_dependents"])
                saved = decision["original_decision"] if index == 0 and len(decision["attempts"]) > 1 else decision
                if any(saved.get(field) != value for field, value in actual.items()):
                    raise ValueError(f"Raw classification differs: {key} {attempt}")
    if totals(report["rows"]) != report["totals"]:
        raise ValueError("Overall totals differ")
    for framework, counts in report["by_framework"].items():
        if totals([r for r in report["rows"] if r["framework"] == framework]) != counts:
            raise ValueError(f"Framework totals differ: {framework}")
    return sql, raw


def cohort(row):
    if not selected(row):
        return None
    status = outcome(row)
    if status == "silent-loss":
        return "silent"
    if status in ("preserved", "loud") and (
            row["rebuild"] is True or row["rebuild"] is None and row.get("planned_rebuild") is True):
        return "safe_rebuild"
    return None


def load_jobs():
    jobs = []
    for source in SOURCES:
        for row in json.loads((ROOT / f"results/{source}.json").read_text())["rows"]:
            if cohort(row):
                jobs.append((source, row))
    return jobs


def adapt_inputs(source, row):
    trace, variants = inputs(source, row)
    schema = json.loads(gzip.decompress((ROOT / row["artifacts"]).read_bytes()))["schema"]
    result = {}
    for name, sql in variants.items():
        context = name.startswith("schema_and_")
        target = variants["executed" if "executed" in name else "migration_only"]
        if context and sql != schema + "\n" + target:
            raise ValueError("Reconstructed schema boundary differs from relint")
        result[name] = dict(original=sql, schema=schema if context else None,
                            target=target, available=bool(trace) if "executed" in name else True)
    return result


def lost_dependents(row):
    trial = row["trials"]["populated"]
    dependents = set()
    for violation in trial["violations"]:
        kind = violation["kind"]
        if kind in ("missing_object", "changed_object"):
            obj = violation.get("object", "")
            if ":" in obj:
                obj_kind, name = obj.split(":", 1)
                if obj_kind in ("trigger", "index", "view"):
                    dependents.add((obj_kind, name))
        elif kind in ("trigger_behavior", "view_rows") and violation.get("object"):
            dependents.add(("trigger" if kind == "trigger_behavior" else "view", violation["object"]))
        elif kind == "view_errors":
            for detail in violation.get("details", []):
                dependents.add(("view", detail.split(":", 1)[0]))
        elif kind in ("row_count", "content_digest"):
            table = violation.get("table")
            if any(fk[2] == "parents" and fk[6] in ("CASCADE", "SET NULL", "SET DEFAULT")
                   for fk in trial["before"]["foreign_keys"].get(table, [])):
                dependents.add(("table", table))
    return sorted(dependents)


def named_matches(diagnostics, dependents):
    matches = []
    for diagnostic in diagnostics:
        message = diagnostic["Text"]
        if not RISK.search(message):
            continue
        for kind, name in dependents:
            escaped = re.escape(name)
            identifier = rf'(?:"{escaped}"|`{escaped}`|\[{escaped}\]|\'{escaped}\'|{escaped}(?![\w$]))'
            if re.search(rf"\b{kind}\s+{identifier}", message, re.I):
                matches.append(dict(code=diagnostic.get("Code"), message=message,
                                    dependent=f"{kind}:{name}"))
    return matches


def unavailable(reason, category, diagnostics=()):
    return dict(available=False, flagged=None, names_lost_dependent=None,
                reason=reason, reason_category=category, diagnostics=list(diagnostics), matches=[])


def error_category(reason):
    lower = reason.lower()
    for needle, category in (("no such table", "missing_table"), ("already exists", "existing_object"),
                             ("transaction", "transaction"), ("syntax", "syntax"),
                             ("parse", "parse"), ("foreign key", "foreign_key"),
                             ("no such column", "missing_column"), ("login", "authentication"),
                             ("timed out", "timeout")):
        if needle in lower:
            return category
    return "analysis_error"


def classify(run, dependents=()):
    if run.get("timed_out"):
        return unavailable("Atlas command timed out", "timeout")
    try:
        report = json.loads(run["stdout"])
    except (ValueError, TypeError):
        reason = run["stderr"].strip() or run["stdout"].strip() or "No JSON report"
        return unavailable(reason, error_category(reason))
    if not isinstance(report, dict):
        return unavailable("Expected a JSON summary object", "invalid_report")
    files, steps = report.get("Files", []), report.get("Steps", [])
    if not isinstance(files, list) or not isinstance(steps, list):
        return unavailable("Malformed report lists", "invalid_report")
    target = [f for f in files if isinstance(f, dict) and f.get("Name") == "2_target.sql"]
    diagnostics = [d for f in target for r in f.get("Reports", []) for d in r.get("Diagnostics", [])]
    if any(not isinstance(d, dict) or not isinstance(d.get("Text"), str) or not d.get("Code")
           for d in diagnostics):
        return unavailable("Malformed analyzer diagnostics", "invalid_report")
    errors = [s["Error"] for s in steps if s.get("Error")]
    if errors:
        reason = "; ".join(errors)
        return unavailable(reason, error_category(reason), diagnostics)
    if len(target) != 1 or not any(s.get("Name") == "Analyze 2_target.sql" for s in steps):
        reason = "; ".join(f["Error"] for f in files if f.get("Error")) or "Target analysis did not complete"
        return unavailable(reason, error_category(reason), diagnostics)
    for file in files:
        error = file.get("Error", "")
        titles = {r.get("Text") for r in file.get("Reports", []) if r.get("Diagnostics")}
        if error and any(part not in titles for part in error.split("; ")):
            return unavailable(error, "analyzer_error", diagnostics)
    if run["returncode"] not in (0, 1) or run["returncode"] and not diagnostics:
        return unavailable(run["stderr"].strip() or "Unexplained nonzero exit", "command_error", diagnostics)
    matches = named_matches(diagnostics, dependents)
    return dict(available=True, flagged=bool(diagnostics), names_lost_dependent=bool(matches),
                diagnostics=diagnostics, matches=matches)


def command(args, timeout):
    start = time.monotonic()
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        result = dict(command=args, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
    except subprocess.TimeoutExpired as exc:
        decode = lambda value: value.decode(errors="replace") if isinstance(value, bytes) else value or ""
        result = dict(command=args, returncode=None, stdout=decode(exc.stdout),
                      stderr=decode(exc.stderr), timed_out=True)
    result["elapsed_seconds"] = round(time.monotonic() - start, 4)
    return result


def atlas(directory, args, timeout, readonly=False):
    name = "smp-atlas-" + uuid.uuid4().hex
    cmd = ["docker", "run", "--rm", "--name", name, "--network", "none",
           "-v", f"{directory.resolve()}:/work" + (":ro" if readonly else ""), IMAGE] + args
    result = command(cmd, timeout)
    if result.get("timed_out"):
        result["cleanup"] = command(["docker", "rm", "-f", name], 20)
    return result


def attempt(directory, schema, target, timeout, dependents):
    directory.mkdir(parents=True, exist_ok=True)
    if schema is not None:
        (directory / "1_schema.sql").write_text(schema)
    (directory / "2_target.sql").write_text(target)
    hashed = atlas(directory, ["migrate", "hash", "--dir", "file:///work"], timeout)
    write_json(directory / "hash.json", hashed)
    if hashed["returncode"] != 0:
        return unavailable(hashed["stderr"] or "Migration hash failed", "hash_error")
    run = atlas(directory, ["migrate", "lint", "--dir", "file:///work", "--dev-url",
                            "sqlite://file?mode=memory", "--latest", "1", "--format", "{{ json . }}"],
                timeout, readonly=True)
    write_json(directory / "lint.json", run)
    return classify(run, dependents)


def run_cell(job, output, timeout):
    with TemporaryDirectory(prefix=".atlas-", dir=output) as temporary:
        row = run_cell_files(job, Path(temporary), timeout)
        inputs, diagnostics = pack_cell(Path(temporary) / "cells" / row["cell_id"], row)
        return row, inputs, diagnostics


def run_cell_files(job, output, timeout):
    source, row = job
    cell_key = key(source, row)
    cell_id = "--".join(cell_key)
    directory = output / "cells" / cell_id
    directory.mkdir(parents=True, exist_ok=True)
    dependents = lost_dependents(row)
    result = dict(key=cell_key, cell_id=cell_id, framework=row["framework"], outcome=outcome(row),
                  cohort=cohort(row), archive=row["artifacts"],
                  archive_sha256=digest((ROOT / row["artifacts"]).read_bytes()),
                  lost_dependents=dependents, lint={})
    for name, data in adapt_inputs(source, row).items():
        path = directory / name
        path.mkdir(exist_ok=True)
        (path / "input.sql").write_text(data["original"])
        if not data["available"]:
            decision = unavailable("CLI exposes no runtime SQL trace", "missing_trace")
            attempts = []
        else:
            decision = attempt(path / "original", data["schema"], data["target"], timeout, dependents)
            attempts = ["original"]
            if not decision["available"] and (
                    decision["reason_category"] == "transaction" or
                    re.search(r"\b(BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RELEASE)\b", data["target"], re.I)):
                original_decision = decision
                decision = attempt(path / "txmode_none", data["schema"], TXMODE + data["target"],
                                   timeout, dependents)
                decision["original_decision"] = original_decision
                attempts.append("txmode_none")
        decision.update(input_sha256=digest(data["original"].encode()),
                        paper_available=row["detectors"]["lint"][name]["available"],
                        attempts=attempts, transformed=decision["available"] and len(attempts) > 1)
        write_json(path / "decision.json", decision)
        result["lint"][name] = decision
    write_json(directory / "cell.json", result)
    return result


def totals(rows):
    result = {}
    for group in ("silent", "safe_rebuild"):
        cells = [r for r in rows if r["cohort"] == group]
        result[group] = {}
        for name in LINTS:
            available = [r for r in cells if r["lint"][name]["available"]]
            result[group][name] = dict(
                total=len(cells), paper_available=sum(r["lint"][name]["paper_available"] for r in cells),
                analyzed=len(available), unavailable=len(cells) - len(available),
                clean=sum(not r["lint"][name]["flagged"] for r in available),
                flagged=sum(r["lint"][name]["flagged"] for r in available),
                names_lost_dependent=sum(r["lint"][name]["names_lost_dependent"] for r in available),
                loud_flagged=sum(r["outcome"] == "loud" and r["lint"][name]["flagged"] for r in available),
                transformed=sum(r["lint"][name]["transformed"] for r in available),
                reasons=dict(Counter(r["lint"][name]["reason_category"] for r in cells
                                     if not r["lint"][name]["available"])))
    return result


def ratio(numerator, denominator):
    return f"{numerator}/{denominator}" if denominator else "N/A (0 analyzed)"


def summary(report):
    lines = ["# Atlas RQ2 baseline", "", f"Image: `{IMAGE}`.", "",
             report["version"]["stdout"].splitlines()[0], "",
             f"{len(report['rows'])} cells; {len(report['rows']) * 4} input slots. "
             "Counts are per populated cell and input. Unavailable inputs are not clean.", "",
             "The starting schema is prior migration history for schema-context inputs; "
             "only the target file is analyzed. No schema is added to context-free inputs.", ""]
    for title, data in [("Overall", report["totals"])] + list(report["by_framework"].items()):
        lines += [f"## {title}", "", "Silent loss:", "",
                  "| Input | Flagged / paper denominator | Flagged / all | Names dependent / all | Analyzed | Clean | Unavailable | Flagged / analyzed |",
                  "| --- | --- | --- | --- | ---: | ---: | ---: | --- |"]
        for name in LINTS:
            t = data["silent"][name]
            lines.append(f"| {name} | {ratio(t['flagged'], t['paper_available'])} | "
                         f"{ratio(t['flagged'], t['total'])} | "
                         f"{ratio(t['names_lost_dependent'], t['total'])} | {t['analyzed']} | "
                         f"{t['clean']} | {t['unavailable']} | {ratio(t['flagged'], t['analyzed'])} |")
        lines += ["", "Preserved or rolled-back rebuilding cells:", "",
                  "| Input | Flags / paper denominator | Flags / all rebuilds | Flags / analyzed | Clean | Unavailable | Loud flags |",
                  "| --- | --- | --- | --- | ---: | ---: | ---: |"]
        for name in LINTS:
            t = data["safe_rebuild"][name]
            lines.append(f"| {name} | {ratio(t['flagged'], t['paper_available'])} | "
                         f"{ratio(t['flagged'], t['total'])} | {ratio(t['flagged'], t['analyzed'])} | "
                         f"{t['clean']} | {t['unavailable']} | {t['loud_flagged']} |")
        lines.append("")
    lines += ["## Unavailability", "", "| Cohort | Input | Reason | Cells |", "| --- | --- | --- | ---: |"]
    for group in ("silent", "safe_rebuild"):
        for name in LINTS:
            t = report["totals"][group][name]
            for reason, count in sorted(t["reasons"].items()):
                lines.append(f"| {group} | {name} | {reason} | {count} |")
    codes = Counter(d["Code"] for row in report["rows"] for result in row["lint"].values()
                    if result["available"] for d in result["diagnostics"])
    available = {group: {name: t["paper_available"] for name, t in report["totals"][group].items()}
                 for group in ("silent", "safe_rebuild")}
    cohorts = {group: report["totals"][group]["migration_only"]["total"] for group in ("silent", "safe_rebuild")}
    lines += ["", "Diagnostics on analyzed inputs: " + ", ".join(
        f"{code}: {count}" for code, count in sorted(codes.items())) + ".", "",
        "The paper's available-input denominators are "
        f"{available['silent']['migration_only']} silent / {available['safe_rebuild']['migration_only']} safe cells for "
        f"migration inputs and {available['silent']['executed']} silent / {available['safe_rebuild']['executed']} safe "
        f"cells for executed inputs. The full cohorts remain {cohorts['silent']} and {cohorts['safe_rebuild']}. "
        "Atlas failures remain in both relevant cohort totals; "
        "only the conditional analyzed denominator excludes them.", "",
        "`analysis_error` includes unbound query parameters in retained Rails traces and "
        "other replay errors. Exact error messages, including statement text, are retained "
        "in each input's `diagnostics.jsonl.gz` record."]
    decisions = [d for row in report["rows"] for d in row["lint"].values()]
    retried = sum(len(d["attempts"]) > 1 for d in decisions)
    lines += ["", "## Limitations", "",
              " ".join(report.get("deviations", []) + [
                  "On the pinned image the table-drop control was flagged and the added-table control was not.",
                  f"{retried} inputs were retried with the transaction directive; "
                  f"{sum(d['transformed'] for d in decisions)} of them could then be analysed."]), "",
              "The image identifies itself as a canary Community build. Its exact digest and platform are "
              "retained; the results do not characterize licensed Atlas Pro or other releases. "
              "The current Community documentation lists lint as unavailable, whereas the retained "
              "image demonstrably runs it. [Edition documentation](https://atlasgo.io/community-edition).", "",
              "Atlas must replay SQL on an empty dev database. Context-free failures therefore measure "
              "input compatibility, not absence of migration risk. The schema-only dev database has no "
              "application rows. Repeated callback trace statements and incomplete rolled-back traces "
              "are preserved; replay failures remain unavailable. The transaction directive is the only retry. "
              "[Lint workflow](https://atlasgo.io/versioned/lint), "
              "[transaction directive](https://atlasgo.io/lint/analyzers).", "",
              "A general diagnostic counts as flagged even if it concerns an intended column drop or "
              "rename. Only diagnostic messages matching an observed dependent count as naming the loss. "
              "False alarms use the paper's preservation endpoint, not a claim that the warning is wrong "
              "about every possible deployment risk. Rates over analyzed inputs have selection bias; "
              "counts over full denominators are observed flags, not estimates for unavailable inputs.", "",
              "## Reproduction and evidence", "", "```sh",
              ".venv/bin/python -B scripts/atlas_lint.py --output results/atlas_lint/reproduction", "```", "",
              "The runner pulls only the pinned digest if absent, repeats both controls, hashes retained "
              "sources, and writes raw command output and decisions in `diagnostics.jsonl.gz` and `inputs.jsonl.gz`. "
              "`report.json` contains all decisions, source/archive hashes, image inspection, tool version, "
              "protocol/script hashes, totals, and framework breakdowns. Existing sources are checked "
              "again after the run. `supporting.json.gz` holds the files of the two controls; in the retained run it also "
              "holds the image discovery.", ""]
    return "\n".join(lines)


def controls(output, timeout):
    with TemporaryDirectory(prefix=".atlas-controls-", dir=output) as temporary:
        results = control_files(Path(temporary), timeout)
        with gzip_writer(output / "supporting.json.gz") as stream:
            write_record(stream, directory_files(Path(temporary)))
    return results


def control_files(output, timeout):
    results = {}
    for name, sql in (("positive", "DROP TABLE users;\n"),
                      ("negative", "CREATE TABLE posts(id INTEGER PRIMARY KEY);\n")):
        results[name] = attempt(output / "controls" / name,
                                "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);\n",
                                sql, timeout, ())
    write_json(output / "controls.json", results)
    if not (results["positive"]["available"] and results["positive"]["flagged"] and
            results["negative"]["available"] and not results["negative"]["flagged"]):
        raise RuntimeError("Atlas controls failed; inspect controls.json")
    return results


def main():
    parser = argparse.ArgumentParser(description="Run pinned Docker Atlas on the current-pin RQ2 cohorts")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--summarize", action="store_true", help="Verify compressed evidence and regenerate the summary")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(OUTPUT.resolve()) or output == ROOT:
        parser.error("Output must be inside results/atlas_lint")
    if args.workers < 1 or args.timeout < 1:
        parser.error("Workers and timeout must be positive")
    if args.summarize:
        report = json.loads((output / "report.json").read_text())
        verify_archives(output, report)
        (output / "summary.md").write_text(summary(report))
        print("Verified compressed evidence and regenerated summary")
        return
    if any((output / name).exists() for name in
           ("report.json", "cells", "inputs.jsonl.gz", "diagnostics.jsonl.gz", "supporting.json.gz")):
        parser.error("Use a new output directory to preserve earlier evidence")
    output.mkdir(parents=True, exist_ok=True)
    inspected = command(["docker", "image", "inspect", IMAGE], args.timeout)
    if inspected["returncode"]:
        pulled = command(["docker", "pull", IMAGE], 300)
        write_json(output / "pull.json", pulled)
        if pulled["returncode"]:
            raise RuntimeError("Cannot pull pinned Atlas image")
        inspected = command(["docker", "image", "inspect", IMAGE], args.timeout)
    write_json(output / "image-inspect.json", inspected)
    if inspected["returncode"]:
        raise RuntimeError("Cannot inspect pinned Atlas image")
    version = command(["docker", "run", "--rm", "--network", "none", IMAGE, "version"], args.timeout)
    source_paths = [f"results/{source}.json" for source in SOURCES]
    hashes = {p: digest((ROOT / p).read_bytes()) for p in source_paths}
    report = dict(format_version=2, started_at=datetime.now(timezone.utc).isoformat(), image=IMAGE, deviations=[],
                  image_tag="arigaio/atlas:latest-community", version=version,
                  image_inspect=json.loads(inspected["stdout"]), source_sha256=hashes,
                  protocol_sha256=digest((ROOT / "PROTOCOL_atlas_lint.md").read_bytes()),
                  script_sha256=digest(Path(__file__).read_bytes()),
                  controls=controls(output, args.timeout))
    jobs = load_jobs()
    silent = sum(cohort(row) == "silent" for _, row in jobs)
    if len(jobs) != 479 or silent != 215:
        raise ValueError(f"Expected 479 cells with 215 silent-loss cells in {', '.join(SOURCES)}; "
                         f"found {len(jobs)} with {silent}")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = [pool.submit(run_cell, job, output, args.timeout) for job in jobs]
        rows = archive_cells(output, (future.result() for future in as_completed(pending)))
    report.update(rows=rows, totals=totals(rows),
                  by_framework={fw: totals([r for r in rows if r["framework"] == fw])
                                for fw in sorted({r["framework"] for r in rows})},
                  finished_at=datetime.now(timezone.utc).isoformat())
    if hashes != {p: digest((ROOT / p).read_bytes()) for p in source_paths}:
        raise RuntimeError("Existing source results changed during execution")
    report["source_hashes_unchanged"] = True
    report["evidence"] = storage_manifest(output, report)
    verify_archives(output, report)
    write_json(output / "report.json", report)
    (output / "summary.md").write_text(summary(report))
    print(f"Wrote {len(rows)} cells to {output}")


if __name__ == "__main__":
    main()
