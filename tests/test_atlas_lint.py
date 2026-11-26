from copy import deepcopy
import json

import pytest

from scripts import atlas_lint
from scripts.atlas_lint import (
    ROOT, LINTS, TXMODE, adapt_inputs, archive_cells, classify, cohort, digest, gzip_writer,
    load_evidence, load_jobs, lost_dependents, named_matches, read_jsonl, summary,
    supporting_files, totals, unavailable, verify_archives, write_json, write_record,
)
from scripts.relint import inputs


def report_run(diagnostics=(), error="", returncode=0):
    file = {"Name": "2_target.sql", "Text": 'DROP TABLE "children";'}
    if diagnostics:
        file["Reports"] = [{"Text": "destructive changes detected", "Diagnostics": list(diagnostics)}]
    if error:
        file["Error"] = error
    return dict(returncode=returncode, stderr="", stdout=json.dumps({
        "Files": [file], "Steps": [{"Name": "Analyze 2_target.sql", "Result": file}]}))


def test_cohorts_match_paper_and_exclude_partial_failures():
    jobs = load_jobs()
    assert len(jobs) == 479
    assert sum(cohort(row) == "silent" for _, row in jobs) == 215
    assert sum(cohort(row) == "safe_rebuild" for _, row in jobs) == 264
    row = deepcopy(next(r for _, r in jobs if cohort(r) == "safe_rebuild"))
    row["trials"]["populated"]["outcome"] = "loud-partial"
    assert cohort(row) is None
    row["trials"]["populated"]["outcome"] = "preserved"
    row.update(rebuild=None, planned_rebuild=True)
    assert cohort(row) == "safe_rebuild"
    row["rebuild"] = False
    assert cohort(row) is None
    row["path"] = "raw"
    assert cohort(row) is None


def test_reconstructed_bytes_and_context_match_relint_for_every_cell():
    missing = 0
    for source, row in load_jobs():
        trace, original = inputs(source, row)
        adapted = adapt_inputs(source, row)
        for variant, data in adapted.items():
            assert data["original"] == original[variant]
            assert data["available"] == (bool(trace) if "executed" in variant else True)
            assert data["available"] == row["detectors"]["lint"][variant]["available"]
            if variant.startswith("schema_and_"):
                assert data["original"] == data["schema"] + "\n" + data["target"]
            else:
                assert data["schema"] is None
                assert data["target"] == data["original"]
            missing += not data["available"]
    assert missing == 194


def test_diagnostic_failure_is_available_but_replay_failure_is_not():
    diagnostic = {"Code": "DS102", "Text": 'Dropping table "children"'}
    run = report_run([diagnostic], "destructive changes detected", 1)
    result = classify(run, [("table", "children")])
    assert result["available"] and result["flagged"] and result["names_lost_dependent"]
    report = json.loads(run["stdout"])
    report["Steps"].insert(0, {"Name": "Replay Migration Files", "Error": "no such table: parents"})
    run["stdout"] = json.dumps(report)
    result = classify(run, [("table", "children")])
    assert result["available"] is False
    assert result["flagged"] is None
    assert result["names_lost_dependent"] is None
    assert result["reason_category"] == "missing_table"
    assert result["diagnostics"] == [diagnostic]


@pytest.mark.parametrize("run", [
    dict(stdout="", stderr="Use atlas login", returncode=1),
    dict(stdout="not json", stderr="", returncode=0),
    dict(stdout="{}", stderr="", returncode=0),
    dict(stdout="[]", stderr="", returncode=0),
    dict(stdout="", stderr="", returncode=None, timed_out=True),
    report_run(error="skip crashed analyzer destructive: panic", returncode=1),
    report_run(returncode=1),
])
def test_errors_are_never_clean(run):
    result = classify(run)
    assert not result["available"]
    assert result["flagged"] is None


def test_clean_report_does_not_match_echoed_sql():
    result = classify(report_run(), [("table", "children")])
    assert result["available"]
    assert not result["flagged"]
    assert not result["names_lost_dependent"]


def test_crash_with_partial_diagnostic_is_unavailable():
    result = classify(report_run([{"Code": "DS102", "Text": 'Dropping table "children"'}],
                                 "destructive changes detected; skip crashed analyzer: panic", 1))
    assert not result["available"]


@pytest.mark.parametrize("text,expected", [
    ('Dropping table "children"', True),
    ('Dropping table `CHILDREN`', True),
    ("Table [children] may lose rows by cascade", True),
    ("Dropping table children_archive", False),
    ('Dropping table "parents"', False),
    ('Inspecting table "children"', False),
    ('Dropped table "parents"; source SQL mentions children', False),
])
def test_named_matching_requires_typed_exact_identifier_and_risk(text, expected):
    assert bool(named_matches([{"Text": text, "Code": "DS102"}], [("table", "children")])) == expected


def test_lost_dependent_targets_require_retained_violation_and_fk():
    row = {"trials": {"populated": {
        "violations": [{"kind": "row_count", "table": "children"},
                       {"kind": "missing_object", "object": "trigger:trg_external"},
                       {"kind": "view_errors", "details": ["parent_view: no such table"]}],
        "before": {"foreign_keys": {"children": [[0, 0, "parents", "parent_id", "id", "NO ACTION", "CASCADE"]]}}
    }}}
    assert lost_dependents(row) == [("table", "children"), ("trigger", "trg_external"), ("view", "parent_view")]
    row["trials"]["populated"]["before"]["foreign_keys"]["children"][0][6] = "RESTRICT"
    assert ("table", "children") not in lost_dependents(row)


def test_totals_keep_unavailable_separate_and_use_paper_denominators():
    flagged = dict(available=True, flagged=True, names_lost_dependent=True,
                   paper_available=True, transformed=False)
    missing = dict(unavailable("Missing trace", "missing_trace"), paper_available=False, transformed=False)
    failed = dict(unavailable("no such table", "missing_table"), paper_available=True, transformed=False)
    rows = [dict(cohort=group, outcome=status, lint={v: result for v in LINTS})
            for group, status, result in [("silent", "silent-loss", flagged),
                                           ("silent", "silent-loss", failed),
                                           ("safe_rebuild", "loud", flagged),
                                           ("safe_rebuild", "preserved", missing)]]
    counts = totals(rows)
    for variant in LINTS:
        silent = counts["silent"][variant]
        assert (silent["total"], silent["analyzed"], silent["flagged"], silent["unavailable"]) == (2, 1, 1, 1)
        safe = counts["safe_rebuild"][variant]
        assert (safe["total"], safe["paper_available"], safe["analyzed"], safe["loud_flagged"]) == (2, 1, 1, 1)
        assert safe["clean"] == 0


def test_control_artifacts_validate_actual_report_format():
    supporting = supporting_files(ROOT / "results/atlas_lint")
    positive = classify(json.loads(supporting["setup/positive/lint.json"]))
    negative = classify(json.loads(supporting["setup/negative/lint.json"]))
    assert positive["available"] and positive["flagged"]
    assert negative["available"] and not negative["flagged"]


def test_failed_transaction_retry_preserves_sql_and_both_decisions(monkeypatch, tmp_path):
    job = next(job for job in load_jobs() if job[1]["framework"] == "drizzle")
    source, row = job
    adapted = adapt_inputs(source, row)
    calls = []

    def fake_attempt(directory, schema, target, timeout, dependents):
        calls.append((directory, schema, target))
        directory.mkdir(parents=True)
        (directory / "2_target.sql").write_text(target)
        if schema is not None:
            (directory / "1_schema.sql").write_text(schema)
        write_json(directory / "hash.json", {"returncode": 0})
        write_json(directory / "lint.json", dict(stdout="", returncode=1,
                   stderr="cannot VACUUM from within a transaction"))
        return unavailable("cannot VACUUM from within a transaction", "transaction")

    monkeypatch.setattr(atlas_lint, "attempt", fake_attempt)
    result, sql, raw = atlas_lint.run_cell(job, tmp_path, 60)
    assert not list(tmp_path.iterdir())
    archived = archive_cells(tmp_path, [(result, sql, raw)])
    assert archived == [result]
    saved_sql = load_evidence(tmp_path / "inputs.jsonl.gz")
    saved_raw = load_evidence(tmp_path / "diagnostics.jsonl.gz")
    assert len(calls) == 8
    for name in LINTS:
        decision = result["lint"][name]
        assert decision["attempts"] == ["original", "txmode_none"]
        assert decision["flagged"] is None
        assert decision["original_decision"]["flagged"] is None
        pair = [call for call in calls if call[0].parent.name == name]
        assert pair[0][1] == pair[1][1] == adapted[name]["schema"]
        assert pair[0][2] == adapted[name]["target"]
        assert pair[1][2] == TXMODE + pair[0][2]
        saved = saved_sql[result["cell_id"], name]["files"]
        assert saved["input.sql"] == adapted[name]["original"]
        assert saved["original/2_target.sql"] == adapted[name]["target"]
        assert saved["txmode_none/2_target.sql"] == TXMODE + adapted[name]["target"]
        assert json.loads(saved_raw[result["cell_id"], name]["files"]["decision.json"]) == decision


def test_jsonl_round_trip_preserves_bytes_and_is_reproducible(tmp_path):
    records = [dict(key=["cell"], cell_id="cell", input="executed",
                    files={"input.sql": "-- café\r\nSELECT 'λ';\n", "atlas.sum": "h1:abc\n"})]
    for name in ("first.gz", "second.gz"):
        with gzip_writer(tmp_path / name) as stream:
            for record in records:
                write_record(stream, record)
    assert list(read_jsonl(tmp_path / "first.gz")) == records
    assert (tmp_path / "first.gz").read_bytes() == (tmp_path / "second.gz").read_bytes()
    assert load_evidence(tmp_path / "first.gz")["cell", "executed"] == records[0]
    with pytest.raises(FileExistsError):
        with gzip_writer(tmp_path / "first.gz"):
            pass


def test_duplicate_archive_keys_are_rejected(tmp_path):
    record = dict(key=["cell"], cell_id="cell", input="executed", files={})
    with gzip_writer(tmp_path / "duplicate.gz") as stream:
        write_record(stream, record)
        write_record(stream, record)
    with pytest.raises(ValueError, match="Duplicate archive key"):
        load_evidence(tmp_path / "duplicate.gz")


def test_temporary_cell_directory_is_removed_on_failure(monkeypatch, tmp_path):
    def fail(job, output, timeout):
        (output / "input.sql").write_text("SELECT 1;")
        raise RuntimeError("interrupted")

    monkeypatch.setattr(atlas_lint, "run_cell_files", fail)
    with pytest.raises(RuntimeError, match="interrupted"):
        atlas_lint.run_cell(None, tmp_path, 60)
    assert not list(tmp_path.iterdir())


def test_retained_run_is_complete_and_matches_raw_reports():
    output = ROOT / "results/atlas_lint"
    report = json.loads((output / "report.json").read_text())
    assert summary(report) == (output / "summary.md").read_text()
    assert len(report["rows"]) == 479
    assert len({tuple(row["key"]) for row in report["rows"]}) == 479
    assert report["totals"] == totals(report["rows"])
    for name in LINTS:
        assert report["totals"]["silent"][name]["total"] == 215
        safe = report["totals"]["safe_rebuild"][name]
        assert safe["total"] == 264
        assert safe["paper_available"] == (204 if "executed" in name else 264)
    for path, expected in report["source_sha256"].items():
        assert digest((ROOT / path).read_bytes()) == expected
    supporting = supporting_files(output)
    if report.get("execution_script_archive"):
        script = supporting[report["execution_script"].removeprefix("results/atlas_lint/")].encode()
    else:
        script = (ROOT / report.get("execution_script", "scripts/atlas_lint.py")).read_bytes()
    assert digest(script) == report["script_sha256"]
    sql, raw = verify_archives(output, report)
    assert len(sql) == len(raw) == 1916
    for row in report["rows"]:
        assert digest((ROOT / row["archive"]).read_bytes()) == row["archive_sha256"]
        for name, decision in row["lint"].items():
            key = row["cell_id"], name
            assert digest(sql[key]["files"]["input.sql"].encode()) == decision["input_sha256"]
            assert json.loads(raw[key]["files"]["decision.json"]) == decision
            if not decision["attempts"]:
                assert decision["reason_category"] == "missing_trace"
                continue
            attempt = decision["attempts"][-1]
            command = json.loads(raw[key]["files"][f"{attempt}/lint.json"])
            reclassified = classify(command, row["lost_dependents"])
            for field, value in reclassified.items():
                assert decision[field] == value, (row["key"], name, field)
