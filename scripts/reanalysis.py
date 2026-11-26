"""Re-derive the quantities touched by four analysis defects from retained evidence.

Nothing is fetched and no ORM runs. The original results are read, never written.
"""
import argparse
import gzip
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import oracle_validation, paper_numbers
from smp.matrix_spec import fixture
from smp.orm_matrix import checked_violations
from smp.orm_spec import orm_fixture
from smp.preservation import violations
from smp.realworld import tokens_without_comments
from smp.rebuild import CLASSIFIER, rebuild, rebuilt_tables, recorded_rebuild

REPLAY = "results/realworld-rerun-2026-11-02"
BREAKPOINT = "--> statement-breakpoint"
MATRICES = {
    "operation_matrix": "results/operation_matrix.json",
    "rails_fixes": "results/rails_fixes.json",
    "orm_matrix": "results/orm_matrix.json",
    "rerun_rails": "results/rerun-2026-11-01/rails-current/operation_matrix.json",
    "rerun_drizzle": "results/rerun-2026-11-01/drizzle/operation_matrix.json",
    "rails_base": "results/rails_base/operation_matrix.json",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_gzip(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def cell(experiment, row, population=None):
    key = {"experiment": experiment, "framework": row["framework"], "version_label": row["version_label"],
           "mode": row.get("mode", "default"), "path": row["path"], "operation": row["operation"],
           "context": row["context"]}
    if population:
        key["population"] = population
    return key


def matrix_trials(root):
    """Every retained matrix trial with its executed trace and, for the ORM matrix, its generated SQL."""
    for experiment, source in MATRICES.items():
        archives = {}
        for row in json.loads((root / source).read_text())["rows"]:
            if row["artifacts"] not in archives:
                archives[row["artifacts"]] = read_gzip(root / row["artifacts"])
            archive = archives[row["artifacts"]]
            for population, trial in row["trials"].items():
                if experiment == "orm_matrix":
                    trace = archive["trials"][row["path"] + "/" + population]["executed.sql"]
                    generated = archive["generation"]["migration.sql"]
                else:
                    trace, generated = archive["evidence"][population]["executed.sql"], None
                yield experiment, row, population, trial, trace, generated


def lint_cohort(row, runtime, planned):
    safe = row["trials"]["populated"]["outcome"] in ("preserved", "failed-loudly")
    return safe and (runtime is True or runtime is None and planned is True)


def rebuild_classification(root):
    families = {name: Counter() for name in MATRICES}
    changes, cohort = [], Counter()
    for experiment, row, population, trial, trace, generated in matrix_trials(root):
        counts = families[experiment]
        counts["trials"] += 1
        runtime = trial["rebuild"]
        corrected = {"rebuild": runtime if runtime is None else rebuild(trace)}
        if runtime is not None:
            counts["runtime_flags"] += 1
            if recorded_rebuild(trace) != runtime:
                raise ValueError(f"recorded rule does not reproduce {row['artifacts']}")
        if generated is not None:
            counts["planned_flags"] += 1
            if recorded_rebuild(generated) != trial["planned_rebuild"]:
                raise ValueError(f"recorded rule does not reproduce {row['artifacts']}")
            corrected["planned_rebuild"] = rebuild(generated)
        for field, value in corrected.items():
            if value != trial[field]:
                counts["changed_" + field] += 1
                changes.append({**cell(experiment, row, population), "field": field, "recorded": trial[field],
                                "corrected": value, "outcome": trial["outcome"],
                                "rebuilt_tables": rebuilt_tables(generated if field == "planned_rebuild" else trace)})
        if population == "populated":
            cohort["recorded"] += lint_cohort(row, runtime, trial.get("planned_rebuild"))
            cohort["corrected"] += lint_cohort(row, corrected["rebuild"], corrected.get("planned_rebuild"))
            cohort["membership_changed"] += (lint_cohort(row, runtime, trial.get("planned_rebuild"))
                                             != lint_cohort(row, corrected["rebuild"], corrected.get("planned_rebuild")))
    return {"format_version": 1, "classifier": CLASSIFIER,
            "recorded_rule": "any CREATE TABLE together with any DROP TABLE in the SQL",
            "corrected_rule": "a table is dropped after its rows were copied into a table created in the same SQL",
            "inputs": {source: sha256((root / source).read_bytes()) for source in MATRICES.values()},
            "families": {name: dict(sorted(counts.items())) for name, counts in families.items()},
            "safe_rebuilding_cells": dict(cohort), "changes": changes}


def content_reads(root):
    """Count content and view comparisons that the recorded checker passed without a readable digest."""
    families, masked = {}, []
    for experiment, source in MATRICES.items():
        counts = Counter()
        for row in json.loads((root / source).read_text())["rows"]:
            if experiment == "orm_matrix":
                spec = orm_fixture(row["framework"], row["operation"], row["context"])[0]
            else:
                spec = fixture(row["framework"], row["operation"], row["context"])[0]
            for population, trial in row["trials"].items():
                counts["trials"] += 1
                for section in ("content", "view_rows"):
                    for name, data in trial["before"][section].items():
                        counts[section + "_comparisons"] += 1
                        other = trial["after"][section].get(name, {})
                        if "digest" not in data and "digest" not in other:
                            counts[section + "_unread_on_both_sides"] += 1
                            masked.append({**cell(experiment, row, population), "section": section, "name": name})
                        elif "digest" not in data:
                            counts[section + "_unread_before"] += 1
                        elif "digest" not in other:
                            counts[section + "_unread_after"] += 1
                counts["violations_changed"] += checked_violations(
                    trial["before"], trial["after"], spec, trial["execution"]) != trial["violations"]
        families[experiment] = dict(sorted(counts.items()))
    controls = json.loads((root / "results/oracle_validation/controls.json").read_text())
    changed = []
    for row in controls["controls"]:
        found = violations(row["before"], row["after"], row["spec"], row["execution"])
        if found != row["violations"]:
            changed.append({"control": row["name"], "population": row["population"], "scope": row["scope"],
                            "expected_label": row["expected_label"], "recorded_confusion": row["confusion"],
                            "recorded_violations": row["violations"], "corrected_violations": found})
    return {"format_version": 1, "families": families, "masked_comparisons": masked,
            "oracle_controls": {"source": "results/oracle_validation/controls.json",
                                "sha256": sha256((root / "results/oracle_validation/controls.json").read_bytes()),
                                "trials": len(controls["controls"]),
                                "recorded_content_error_trials": controls["summary"]["content_error_trials"],
                                "recorded_summary": controls["summary"]["overall"],
                                "verdict_changes_on_recorded_observations": changed}}


def replay_documents(root, local):
    """Full evidence documents: the local copy when present, otherwise the published full artifacts."""
    aggregate = json.loads((root / REPLAY / "realworld.json").read_text())
    for row in aggregate["rows"]:
        ref = row["evidence"]
        path = local / Path(ref["file"]).name if local else None
        if path is not None and path.is_file():
            if sha256(path.read_bytes()) != ref["full_sha256"]:
                raise ValueError(f"local evidence differs from the recorded hash: {path.name}")
            yield row, read_gzip(path)
        elif ref["mode"] == "full":
            yield row, read_gzip(root / REPLAY / ref["file"])
        else:
            yield row, None


def key(sql):
    return tokens_without_comments(sql).strip()


def target_chunks(document):
    """The target migration as the migrator splits it, with the pinned statements each chunk covers.

    The file is laid out again from the catalogued statements at their byte
    offsets; the bytes between two statements are whitespace.
    """
    target = document["migration_file"]
    catalog = [entry for entry in document["source_statements"] if entry["source"]["file"] == target]
    data = bytearray(b" " * max(entry["source"]["byte_end"] for entry in catalog))
    for entry in catalog:
        data[entry["source"]["byte_start"]:entry["source"]["byte_end"]] = entry["sql"].encode()
    chunks, offset = [], 0
    for part in data.decode().split(BREAKPOINT):
        end = offset + len(part.encode())
        chunks.append({"text": " ".join(part.split()),
                       "sources": [entry["source"] for entry in catalog
                                   if entry["source"]["byte_start"] < end and entry["source"]["byte_end"] > offset]})
        offset = end + len(BREAKPOINT)
    return chunks


def target_sources(document):
    """Corrected source positions for the Drizzle path, by ordered occurrence in the target file."""
    chunks = target_chunks(document)
    section = document["paths"]["drizzle"]
    position, resolved = 0, []
    for item in section["submitted"]:
        if item["origin"] != "project":
            resolved.append(None)
            continue
        wanted = " ".join(item["sql"].split())
        index = next((i for i in range(position, len(chunks)) if chunks[i]["text"] == wanted), None)
        if index is None:
            index = next((i for i, chunk in enumerate(chunks) if chunk["text"] == wanted), None)
        if index is None:
            raise ValueError(f"statement absent from the target migration: {document['repo']} {document['migration_file']}")
        position = index + 1
        resolved.append(chunks[index]["sources"])
    pending = [(item["sql"], sources) for item, sources in zip(section["submitted"], resolved) if sources]
    current, traced = None, []
    for item in section["trace"]:
        if item["origin"] != "project":
            traced.append(None)
            continue
        ahead = next((i for i, (sql, _) in enumerate(pending) if sql.strip() == item["sql"].strip()), None)
        if ahead is not None:
            current = pending[ahead][1]
            del pending[:ahead + 1]
        if current is None:
            raise ValueError(f"trace entry without a submission: {document['repo']} {document['migration_file']}")
        traced.append(current)
    return resolved, traced


def statement_provenance(root, local):
    aggregate = json.loads((root / REPLAY / "realworld.json").read_text())
    full_rows = {}
    if local and (local / "realworld.json").is_file():
        full_rows = {(r["repo"], r["migration_file"]): r for r in json.loads((local / "realworld.json").read_text())["rows"]}
    corrections, totals, keywords, unavailable = [], Counter(), Counter(), []
    for row, document in replay_documents(root, local):
        ref = row["evidence"]
        totals["artifacts"] += 1
        if document is None:
            unavailable.append(ref["file"])
            continue
        section = document["paths"]["drizzle"]
        if section.get("not_executed"):
            totals["drizzle_not_executed"] += 1
            continue
        totals["drizzle_executed"] += 1
        target = document["migration_file"]
        submitted, traced = target_sources(document)
        items = []
        for name, entries, corrected in (("submitted", section["submitted"], submitted), ("trace", section["trace"], traced)):
            for index, (item, sources) in enumerate(zip(entries, corrected)):
                if sources is None:
                    continue
                totals[name + "_project_entries"] += 1
                if item["sources"] == sources:
                    continue
                outside = all(source["file"] != target for source in item["sources"])
                totals[name + ("_outside_target" if outside else "_other_occurrence")] += 1
                if name == "submitted":
                    keywords[key(item["sql"]).split(None, 1)[0].upper()] += 1
                items.append({"list": name, "index": index, "sha256": sha256(item["sql"].encode()),
                              "recorded": item["sources"], "corrected": sources})
        full = full_rows.get((row["repo"], row["migration_file"]))
        events = row["paths"]["drizzle"].get("execution", {}).get("events", [])
        if full is not None and any(isinstance(event, dict) for event in events):
            trace = iter(zip(section["trace"], traced))
            for index, (event, published) in enumerate(zip(full["paths"]["drizzle"]["execution"]["events"], events)):
                wanted = key(event).rstrip(";").lower()
                item, sources = next((pair for pair in trace if key(pair[0]["sql"]).rstrip(";").lower() == wanted))
                if isinstance(published, dict) and published["sources"] != sources:
                    totals["aggregate_events_corrected"] += 1
                    items.append({"list": "aggregate_events", "index": index, "sha256": published["sha256"],
                                  "recorded": published["sources"], "corrected": sources})
        if items:
            totals["migrations_corrected"] += 1
            corrections.append({"artifact": ref["file"], "artifact_sha256": ref["sha256"], "full_sha256": ref["full_sha256"],
                                "mode": ref["mode"], "repo": row["repo"], "migration_file": target,
                                "drizzle_outcome": row["paths"]["drizzle"]["outcome"], "items": items})
    return {"format_version": 1, "evidence_run": REPLAY,
            "aggregate_sha256": sha256((root / REPLAY / "realworld.json").read_bytes()),
            "rule": "each project statement submitted by the migrator is matched to the next equal statement of the "
                    "target migration, in file order; trace callbacks take the position of the submission they belong to",
            "summary": dict(sorted(totals.items())), "corrected_statement_keywords": dict(sorted(keywords.items())),
            "outcomes_of_corrected_migrations": dict(sorted(Counter(c["drizzle_outcome"] for c in corrections).items())),
            "artifacts_without_full_evidence": unavailable, "corrections": corrections}


def view_digests(root, local):
    totals, views, unavailable = Counter(), [], []
    for row, document in replay_documents(root, local):
        if document is None:
            unavailable.append(row["evidence"]["file"])
            continue
        totals["artifacts"] += 1
        for path, section in document["paths"].items():
            for boundary in ("before", "after"):
                if boundary not in section:
                    continue
                totals["snapshots"] += 1
                for entry in section[boundary]["sqlite_schema"]:
                    if entry["type"] == "view":
                        totals["view_entries"] += 1
                        views.append({"artifact": row["evidence"]["file"], "path": path, "boundary": boundary})
    findings = {source: sum(finding["kind"] in ("view_rows", "view_errors") for row in json.loads((root / source).read_text())["rows"]
                            for trial in row["paths"].values() for finding in trial.get("findings", []))
                for source in ("results/realworld.json", REPLAY + "/realworld.json")}
    return {"format_version": 1, "evidence_run": REPLAY, "summary": dict(sorted(totals.items())),
            "views": views, "recorded_view_findings": findings, "artifacts_without_full_evidence": unavailable}


def paper_macros(root, classification):
    recorded = paper_numbers.build_numbers(root, reclassified=None)["macros"]
    corrected = paper_numbers.build_numbers(root, reclassified=classification)["macros"]
    changed = {name: {"recorded": recorded[name]["value"], "corrected": entry["value"],
                      "definition": entry["definition"], "field": entry["field"]}
               for name, entry in corrected.items() if recorded[name]["value"] != entry["value"]}
    return {"format_version": 1, "macros": len(corrected), "unchanged": len(corrected) - len(changed), "changed": changed}


def oracle_rerun(output):
    result = oracle_validation.run_suite(output / "oracle_validation")
    return {"summary": result["summary"]["overall"], "by_scope": result["summary"]["by_scope"],
            "content_error_trials": result["summary"]["content_error_trials"]}


def report(results):
    provenance, classification = results["statement_provenance"], results["rebuild_classification"]
    reads, views, macros = results["content_reads"], results["view_digests"], results["paper_macros"]
    p = provenance["summary"]
    lines = ["# Re-analysis of retained evidence, 2026-11-21", "",
             "Generated by `scripts/reanalysis.py`; the protocol is `PROTOCOL_reanalysis.md` in the repository root. "
             "No framework was executed and no earlier result file was modified.", "",
             "## Paper quantities", "",
             f"{macros['unchanged']} of {macros['macros']} quantities are unchanged; {len(macros['changed'])} change.", ""]
    if macros["changed"]:
        lines += ["| Macro | Recorded | Corrected | Definition |", "|---|---:|---:|---|"]
        lines += [f"| `\\{name}` | {entry['recorded']} | {entry['corrected']} | {entry['definition']} |"
                  for name, entry in macros["changed"].items()]
    lines += ["", "## Statement positions in the replay evidence", "",
              f"{p.get('migrations_corrected', 0)} of {p['drizzle_executed']} migrations executed through the migrator carry "
              f"corrected positions: {p.get('submitted_outside_target', 0)} of {p['submitted_project_entries']} submitted project "
              f"statements and {p.get('trace_outside_target', 0)} of {p['trace_project_entries']} trace entries pointed to an earlier "
              f"migration of the same project, and {p.get('submitted_other_occurrence', 0)} submitted statements to another occurrence "
              f"inside the target file. {p.get('aggregate_events_corrected', 0)} event positions in the published aggregate change with them. "
              "First keywords of the corrected statements: "
              + ", ".join(f"{k} {v}" for k, v in provenance["corrected_statement_keywords"].items()) + ". "
              "Outcomes, findings and row values are not derived from these positions.", "",
              "## Rebuild classification", "",
              "| Results | Trials | Runtime flags | Planned flags | Runtime changed | Planned changed |", "|---|---:|---:|---:|---:|---:|"]
    for name, counts in classification["families"].items():
        lines.append(f"| {name} | {counts['trials']} | {counts.get('runtime_flags', 0)} | {counts.get('planned_flags', 0)} | "
                     f"{counts.get('changed_rebuild', 0)} | {counts.get('changed_planned_rebuild', 0)} |")
    cells = sorted({(c["framework"], c["operation"], c["context"]) for c in classification["changes"]})
    cohort = classification["safe_rebuilding_cells"]
    lines += ["", "The recorded rule reproduces every recorded flag. Changed cells: "
              + ("; ".join(f"{fw} {op} {ctx}" for fw, op, ctx in cells) or "none") + ". "
              f"Preserved or rolled-back rebuilding cells: {cohort['recorded']} recorded, {cohort['corrected']} corrected, "
              f"{cohort['membership_changed']} cells change membership.", "",
              "## Content and view reads", "",
              "| Results | Trials | Content comparisons | Unread on both sides | View comparisons | Unread on both sides |",
              "|---|---:|---:|---:|---:|---:|"]
    for name, counts in reads["families"].items():
        lines.append(f"| {name} | {counts['trials']} | {counts['content_comparisons']} | "
                     f"{counts.get('content_unread_on_both_sides', 0)} | {counts.get('view_rows_comparisons', 0)} | "
                     f"{counts.get('view_rows_unread_on_both_sides', 0)} |")
    recomputed = sum(counts["trials"] for counts in reads["families"].values())
    differing = sum(counts["violations_changed"] for counts in reads["families"].values())
    lines += ["", f"The corrected checker changed the violation lists for {differing} of {recomputed:,} trials."]
    oracle = reads["oracle_controls"]
    rerun = results.get("oracle_rerun")
    lines += ["", f"With the corrected checker, {len(oracle['verdict_changes_on_recorded_observations'])} of {oracle['trials']} recorded "
              "oracle control trials change verdict; all are the derived tables without an id column, whose recorded "
              f"observations hold read errors ({oracle['recorded_content_error_trials']} trials). "
              f"The recorded oracle summary is {json.dumps(oracle['recorded_summary'])}."]
    if rerun:
        lines += [f"Run again with the corrected checker (`oracle_validation/`), the same controls give {json.dumps(rerun['summary'])} "
                  f"with {rerun['content_error_trials']} content read errors."]
    v = views["summary"]
    lines += ["", "## View digests in the replays", "",
              f"{v.get('view_entries', 0)} view entries occur in {v.get('snapshots', 0)} snapshots of {v.get('artifacts', 0)} "
              "evidence documents. Recorded view findings: "
              + ", ".join(f"{count} in `{source}`" for source, count in views["recorded_view_findings"].items()) + ".", ""]
    return "\n".join(lines)


def analyse(root, local, output=None):
    classification = rebuild_classification(root)
    results = {"statement_provenance": statement_provenance(root, local),
               "rebuild_classification": classification, "content_reads": content_reads(root),
               "view_digests": view_digests(root, local), "paper_macros": paper_macros(root, classification)}
    if output is not None:
        results["oracle_rerun"] = oracle_rerun(output)
    return results


# What a check without the full local replay copy does not recompute.
NOT_RECOMPUTED = ["statement positions in redacted artifacts", "event positions of the replay aggregate",
                  "views in redacted artifacts"]


def published(items, unavailable):
    """The entries of a stored list that the fully published artifacts can reproduce."""
    return [item for item in items if item["artifact"] not in unavailable]


def differences(stored, results, local):
    """Names of the stored files that differ from a fresh derivation.

    Without the local replay copy, statement positions and views are compared for the fully published artifacts.
    """
    differing = [name for name in ("rebuild_classification", "content_reads") if results[name] != stored[name]]
    # Quantities added to the paper later change the totals, not the list of changed macros.
    if results["paper_macros"]["changed"] != stored["paper_macros"]["changed"]:
        differing.append("paper_macros")
    if local is not None:
        return differing + [name for name in ("statement_provenance", "view_digests") if results[name] != stored[name]]
    provenance, views = results["statement_provenance"], results["view_digests"]
    positions = lambda corrections: {c["artifact"]: [i for i in c["items"] if i["list"] != "aggregate_events"]
                                     for c in corrections}
    if positions(provenance["corrections"]) != positions(
            published(stored["statement_provenance"]["corrections"], provenance["artifacts_without_full_evidence"])):
        differing.append("statement_provenance")
    if (views["views"] != published(stored["view_digests"]["views"], views["artifacts_without_full_evidence"])
            or views["recorded_view_findings"] != stored["view_digests"]["recorded_view_findings"]):
        differing.append("view_digests")
    return differing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New directory under results/")
    parser.add_argument("--verify", type=Path, help="Recompute and compare with an existing re-analysis directory")
    parser.add_argument("--local", type=Path, default=ROOT / ".realworld-local/rerun-2026-11-02",
                        help="Full local replay evidence; without it only fully published artifacts are read")
    args = parser.parse_args()
    local = args.local if args.local.is_dir() else None
    if bool(args.output) == bool(args.verify):
        parser.error("give exactly one of --output and --verify")
    if args.verify:
        stored = {name: json.loads((args.verify / f"{name}.json").read_text()) for name in
                  ("statement_provenance", "rebuild_classification", "content_reads", "view_digests", "paper_macros")}
        results = analyse(ROOT, local)
        differing = differences(stored, results, local)
        with tempfile.TemporaryDirectory(dir=ROOT / "results") as folder:
            fresh = oracle_validation.run_suite(Path(folder) / "oracle")
        recorded = json.loads((args.verify / "oracle_validation/controls.json").read_text())
        if fresh["summary"] != recorded["summary"]:
            differing.append("oracle_validation")
        print(json.dumps({"verified": not differing, "differing": differing,
                          "replay_evidence": "full local copy" if local else "fully published artifacts only",
                          "not_recomputed": [] if local else NOT_RECOMPUTED}, indent=2))
        raise SystemExit(bool(differing))
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "results") or output.exists():
        parser.error("--output must be a new directory under results/")
    if local is None:
        parser.error("the full local replay evidence is required to write a re-analysis")
    output.mkdir(parents=True)
    results = analyse(ROOT, local, output)
    for name in ("statement_provenance", "rebuild_classification", "content_reads", "view_digests", "paper_macros"):
        write_json(output / f"{name}.json", results[name])
    (output / "README.md").write_text(report(results))
    print(json.dumps({"changed_macros": results["paper_macros"]["changed"],
                      "provenance": results["statement_provenance"]["summary"]}, indent=2))


if __name__ == "__main__":
    main()
