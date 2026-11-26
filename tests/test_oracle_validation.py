import copy
import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

import pytest

from scripts import oracle_validation as validation
from smp.preservation import classify, violations


@pytest.fixture(scope="module")
def trials(tmp_path_factory):
    folder = tmp_path_factory.mktemp("oracle-controls")
    return [validation.run_control(folder, control, populated)
            for control in validation.controls() for populated in (True, False)]


def trial(rows, name, population="populated"):
    return next(row for row in rows if row["name"] == name and row["population"] == population)


def test_complete_coverage_and_independent_ground_truth(trials):
    expected = {(op, ctx, population) for op in validation.ALL_OPERATIONS
                for ctx in validation.CONTEXTS for population in ("populated", "empty")}
    safe = [row for row in trials if row["kind"] == "intended_change"]
    assert {(row["operation"], row["context"], row["population"]) for row in safe} == expected
    assert all(row["confusion"] == "TN" for row in safe)
    assert all(row["ground_truth"]["verified"] and row["execution"]["success"] for row in trials)
    assert len({(row["name"], row["population"]) for row in trials}) == len(trials)


def test_fault_counts_and_empty_noops(trials):
    for kind, (_, data_only) in validation.FAULTS.items():
        populated = trial(trials, kind)
        empty = trial(trials, kind, "empty")
        assert populated["expected_label"] == "lossy"
        assert populated["confusion"] == ("FN" if kind in validation.LIMITATIONS else "TP")
        assert empty["empty_noop"] == data_only
        if data_only:
            assert empty["confusion"] == "TN"
            assert empty["ground_truth"]["affected_rows"] == 0
            assert empty["ground_truth"]["intended"] == empty["ground_truth"]["after"]
        else:
            assert empty["expected_label"] == "lossy"


def test_saved_verdicts_recompute_after_json_roundtrip(trials):
    for row in json.loads(json.dumps(trials)):
        found = violations(row["before"], row["after"], row["spec"], row["execution"])
        assert found == row["violations"]
        assert classify(row["execution"]["success"], found, row["before"], row["after"]) == row["oracle_verdict"]


def test_ground_truth_rejects_collateral_damage(trials):
    row = trial(trials, "delete_child")
    after = copy.deepcopy(row["ground_truth"]["after"])
    after["tables"]["parents"]["rows"].pop()
    with pytest.raises(AssertionError, match="collateral"):
        validation.verify_fault(row["ground_truth"]["intended"], after, "delete_child", True, 1)
    with pytest.raises(AssertionError):
        validation.verify_fault(row["ground_truth"]["intended"], row["ground_truth"]["after"], "delete_child", True, 0)


def test_safe_ground_truth_rejects_wrong_conversion(trials):
    row = trial(trials, "safe_change_type_C0")
    after = copy.deepcopy(row["ground_truth"]["after"])
    values = list(after["tables"]["parents"]["rows"][0])
    values[2] = 0
    after["tables"]["parents"]["rows"][0] = tuple(values)
    with closing(sqlite3.connect(":memory:")) as db:
        with pytest.raises(AssertionError, match="rows"):
            validation.verify_safe(row["ground_truth"]["before"], after, "change_type", db)


def test_rebuild_order_and_connection_enforcement(trials):
    for row in trials:
        if row["kind"] != "safe_rebuild":
            continue
        sql = row["executed_sql"]
        off, begin, commit, on = [sql.index(statement) for statement in
                                 ("PRAGMA foreign_keys=OFF", "BEGIN", "COMMIT", "PRAGMA foreign_keys=ON")]
        assert off < begin < commit < on
        assert row["confusion"] == "TN"
        assert row["execution"]["foreign_keys_after"] == 1
    assert trial(trials, "disable_enforcement")["violations"] == [{"kind": "fk_enforcement"}]
    dangling = trial(trials, "dangling_reference")
    assert dangling["execution"]["foreign_keys_after"] == 1
    assert {v["kind"] for v in dangling["violations"]} == {"content_digest", "foreign_key_check"}


def test_trigger_probe_and_heap_limitations(trials):
    for population in ("populated", "empty"):
        row = trial(trials, "change_trigger_body", population)
        assert {v["kind"] for v in row["violations"]} == {"changed_object", "trigger_behavior"}
        assert row["ground_truth"]["after"]["tables"]["audit"]["rows"] == []
    heap = trial(trials, "heap_overwrite")
    assert heap["confusion"] == "TP" and heap["scope"] == "derived"
    assert heap["violations"] == [{"kind": "content_digest", "table": "heap"}]
    assert trial(trials, "heap_overwrite", "empty")["confusion"] == "TN"
    assert trial(trials, "safe_heap")["confusion"] == "TN"
    assert trial(trials, "safe_heap_id")["after"]["content"]["heap"]["rows"] == [(1, "a"), (2, "b")]


def test_confusion_and_report_denominators(trials):
    summary = validation.summarize(trials)
    assert summary["overall"] == {"TP": 17, "FN": 2, "TN": 441, "FP": 0}
    assert summary["by_population"]["populated"] == {"TP": 11, "FN": 1, "TN": 218, "FP": 0}
    assert summary["by_population"]["empty"] == {"TP": 6, "FN": 1, "TN": 223, "FP": 0}
    assert summary["populated_intended_changes"]["trials"] == 207
    assert summary["empty_noops"] == 5
    assert summary["content_error_trials"] == 0
    report = validation.render_summary({"controls": trials, "summary": summary,
                                        "runtime": {"python": "test", "sqlite": "test"}})
    assert "**0/207**" in report
    for row in trials:
        if row["confusion"] in ("FP", "FN"):
            assert f"`{row['name']}` ({row['population']}): {row['explanation']}" in report


def test_outputs_stay_under_results_and_never_replace_a_result():
    with pytest.raises(ValueError, match="under results/"):
        validation.run_suite(validation.ROOT)
    with pytest.raises(ValueError, match="already holds a result"):
        validation.run_suite(validation.ROOT / "results/oracle_validation")


def test_recorded_controls_reproduce_except_the_unreadable_heap():
    recorded = json.loads((validation.ROOT / "results/oracle_validation/controls.json").read_text())
    changed = []
    for row in recorded["controls"]:
        found = violations(row["before"], row["after"], row["spec"], row["execution"])
        if found != row["violations"]:
            changed.append((row["name"], row["population"]))
    assert recorded["summary"]["content_error_trials"] == len(changed) == 4
    assert {name for name, _ in changed} == {"heap_overwrite", "safe_heap"}


def test_recorded_checker_reproduces_the_first_run():
    recorded = json.loads((validation.ROOT / "results/oracle_validation/controls.json").read_text())
    with tempfile.TemporaryDirectory(dir=validation.ROOT / "results") as folder:
        fresh = validation.run_suite(Path(folder) / "oracle", recorded_checker=True)
    verdicts = lambda result: {(row["name"], row["population"]): (row["expected_label"], row["oracle_verdict"],
                                                                   row["scope"], row["violations"])
                               for row in result["controls"]}
    assert fresh["summary"] == recorded["summary"] and fresh["summary"]["overall"]["TP"] == 16
    assert verdicts(fresh) == verdicts(recorded)
    report = validation.render_summary(fresh)
    assert "scripts/oracle_validation.py --recorded-checker --output" in report
    assert "Both content reads fail at ORDER BY id" in report and "never as preserved" not in report
    explanation = lambda name: next(row["explanation"] for row in fresh["controls"] if row["name"] == name and row["population"] == "populated")
    assert "cannot be read" in explanation("safe_heap") and "cannot be read" not in explanation("safe_heap_id")
    assert "--recorded-checker" not in validation.render_summary({**fresh, "checker": "corrected"}).split("## Reproduction")[1]
