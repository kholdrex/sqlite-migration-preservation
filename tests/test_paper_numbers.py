"""Paper regressions and safeguards for denominators and manual adjudications."""
from copy import deepcopy
import hashlib
import json
import re

import pytest

from scripts.paper_numbers import (
    ROOT, LINTS, Numbers, REAL_DATA_LOSS_INCIDENTS, build_numbers, current_detail_numbers,
    fk_action_changed, realworld_outcome, specific_lint_finding, summarize_cells,
    kappa, token, tracker_numbers, tracker_sample_numbers, write_numbers,
)


@pytest.fixture(scope="module")
def report():
    return build_numbers()


@pytest.mark.parametrize("macro,expected", [
    ("nSilentRailsCurrent", 48), ("nCellsRailsCurrent", 144),
    ("nSilentDrizzleCurrent", 36), ("nCellsDrizzleCurrent", 135),
    ("nExecutionsOperationMatrix", 4914), ("nRealworldQualifyingRebuilds", 20),
    ("nTrackerRelevant", 167), ("nTrackerInputs", 656),
    ("nExecutionsPilot", 100), ("nExecutionsUpstreamFixes", 122),
    ("nExecutionsRailsFixes", 1208), ("nExecutionsRailsAtomicity", 48),
    ("nExecutionsOrmMatrix", 5292), ("nExecutionsRealworld", 210),
    ("nRerunRailsDifferences", 0), ("nRerunDrizzleDifferences", 0),
    ("nRcDrizzleSilentLoss", 40), ("nRcDrizzleCells", 126), ("nRcDrizzleExcluded", 9),
    ("nRcDrizzleBaselineSilentLoss", 36), ("nRcDrizzleBaselineCells", 126),
    ("nRealworldQualifyingSilentToPreserved", 11), ("nRealworldQualifyingSilentToSilent", 4),
    ("nCurrentOverallLoudPartialView", 25), ("nCurrentOverallLoudPartialRestrict", 14),
    ("nCurrentOverallLintFalseAlarmLoudExecuted", 14), ("nTrackerTotalRealDataLossIncidentsSilent", 5),
    ("nKitPairsStableAutocommitChildren", 0), ("nKitPairsRcAutocommitChildren", 3),
    ("nRelintCurrentOverallLintSpecificSchemaAndExecuted", 164),
    ("nRelintCurrentOverallAvailableLintSchemaAndExecuted", 178),
    ("nRelintCurrentOverallLintRuleFalseAlarmSchemaAndExecuted", 25),
    ("nCurrentOverallLintSpecificSchemaAndExecuted", 29),
    ("nRealworldQualifyingDistinctMigrationHashes", 16),
    ("nRealworldQualifyingDrizzleRowOrFkValueLossDistinctMigrationHashes", 11),
    ("nRealworldQualifyingDrizzleLoudDistinctMigrationHashes", 5),
    ("nRealworldPriorityRepos", 14), ("nRealworldReplayedDeclaredCaret", 67),
    ("nRealworldReplayedDeclaredExact", 2), ("nRealworldReplayedVersionFallback", 1),
    ("nTrackerSampleReports", 60), ("nTrackerSampleCorpusRelevant", 40), ("nTrackerSampleBothRelevant", 34),
    ("nTrackerSampleRelevantAgree", 53), ("nTrackerSampleRelevantKappa", "0.75"),
    ("nTrackerSampleSilentCorpus", 14), ("nTrackerSampleSilentAuthor", 22),
])
def test_known_values(report, macro, expected):
    assert report["macros"][macro]["value"] == expected


def test_all_cell_outcomes_partition_the_denominator(report):
    values = {k: v["value"] for k, v in report["macros"].items()}
    for name in values:
        if not name.endswith("DetectorSilentDenominator"):
            continue
        prefix = name.removesuffix("DetectorSilentDenominator")
        for population in ("", "Empty"):
            assert sum(values[prefix + population + status] for status in
                       ("Preserved", "SilentLoss", "Loud", "LoudPartial")) == values[prefix + "Cells"]
        assert values[name] == values[prefix + "SilentLoss"]
        assert values[prefix + "DetectedPopulatedInvariants"] == values[name]


def test_atomicity_failures_exclude_no_transaction_controls(report):
    values = {k: v["value"] for k, v in report["macros"].items()}
    assert values["nAtomicityRailsCurrentTransactionalFailures"] == 0
    assert values["nAtomicityRailsCurrentNoTransactionPartiallyCommitted"] == 4
    assert values["nAtomicityRailsPrFiveSevenOneTwoEightTransactionalFailures"] == 4
    assert values["nAtomicityRailsPrFiveSevenOneTwoEightPlusFiveSixEightOneOneTransactionalFailures"] == 4
    assert values["nAtomicityRailsPrFiveEightSevenZeroNinePlusFiveSixEightOneOneTransactionalFailures"] == 0


def test_realworld_adjudication_and_loss_categories(report):
    values = {k: v["value"] for k, v in report["macros"].items()}
    for path, raw, adjusted in (("Drizzle", 20, 19), ("Raw", 13, 12), ("RawTx", 24, 23)):
        prefix = "nRealworldAll" + path
        assert values[prefix + "RawSilentLoss"] == raw
        assert values[prefix + "SilentLoss"] == adjusted
        assert values[prefix + "AdjudicatedExclusions"] == 1
        assert values[prefix + "RowOrFkValueLoss"] + values[prefix + "ImplicitObjectOnly"] + values[prefix + "OtherLossOnly"] == adjusted
        assert values[prefix + "ImplicitObjectLoss"] == values[prefix + "ImplicitObjectOnly"] + values[prefix + "BothRowAndImplicitLoss"]
    assert values["nRealworldQualifyingDistinctMigrationHashes"] == 16


def test_superseded_index_does_not_exclude_unrelated_losses():
    row = {"repo": "saltbo/zpan", "migration_file": "migrations/0054_lively_nuke.sql"}
    trial = {"outcome": "silent-loss", "findings": [
        {"kind": "implicit_object_loss", "object": "index:activity_events_org_id_idx"}]}
    original = deepcopy(trial)
    assert realworld_outcome(row, trial) == ("preserved", [])
    assert trial == original
    trial["findings"].append({"kind": "row_count"})
    assert realworld_outcome(row, trial) == ("silent-loss", [{"kind": "row_count"}])
    assert realworld_outcome({**row, "repo": "another/repo"}, original)[0] == "silent-loss"


def test_tracker_incidents_are_explicit_not_production_flag(report):
    labels = [json.loads(line) for line in (ROOT / "results/tracker_labels.jsonl").read_text().splitlines()]
    for row in labels:
        row["production_impact"] = False
    book = Numbers()
    tracker_numbers(book, labels)
    assert book.macros["nTrackerRealDataLossIncidents"]["value"] == 6
    assert report["adjudications"]["real_data_loss_incidents"] == list(REAL_DATA_LOSS_INCIDENTS)
    assert book.macros["nTrackerDrizzleRealDataLossIncidents"]["value"] == 4


def test_unavailable_lint_is_not_a_negative_result():
    row = {"trials": {pop: {"outcome": "silent-loss", "violations": [{"kind": "missing_object"}],
                           "execution": {"success": True}} for pop in ("populated", "empty")},
           "detectors": {"lint": {k: {"available": False, "detected": True} for k in
                         ("executed", "migration_only", "schema_and_executed", "schema_and_migration")}}}
    book = Numbers()
    summarize_cells(book, "Test", [row], "fixture", "rows")
    assert book.macros["nTestAvailableLintExecuted"]["value"] == 0
    assert book.macros["nTestDetectedLintExecuted"]["value"] == 0
    assert book.macros["nTestDetectedEmptyInvariants"]["value"] == 1
    assert book.macros["nTestDetectedEmptyExecutionErrors"]["value"] == 0


def test_fk_action_change_is_distinct_from_missing_fk():
    row = {"trials": {"populated": {
        "violations": [{"kind": "foreign_key_definition", "table": "parents",
                        "definition": ["tenants", "ancestor_id", "id", "NO ACTION", "CASCADE", "NONE"]}],
        "after": {"foreign_keys": {"parents": []}},
    }}}
    assert not fk_action_changed(row)
    row["trials"]["populated"]["after"]["foreign_keys"]["parents"] = [
        [0, 0, "tenants", "ancestor_id", "id", "NO ACTION", "NO ACTION", "NONE"]]
    assert fk_action_changed(row)


def test_outputs_are_reproducible_and_all_macros_have_provenance(report, tmp_path):
    write_numbers(report, tmp_path)
    for suffix in ("json", "tex", "md"):
        assert (tmp_path / f"numbers.{suffix}").read_bytes() == (ROOT / "paper" / f"numbers.{suffix}").read_bytes()
    tex = (tmp_path / "numbers.tex").read_text()
    names = re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", tex)
    assert set(names) == set(report["macros"])
    assert len(names) == len(set(names))
    for entry in report["macros"].values():
        assert entry["field"] and entry["definition"]
        assert all((ROOT / source).is_file() for source in entry["source"].split("; "))


def test_figure_manifest_matches_number_sources(report):
    manifest = json.loads((ROOT / "paper/figures/manifest.json").read_text())
    for path, digest in manifest["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
        assert report["source_sha256"][path] == digest
    for panel in manifest["grid"]:
        if panel["label"] in ("Rails", "Drizzle", "Django"):
            assert panel["outcomes"]["silent-loss"] == report["macros"]["nSilent" + panel["label"] + "Current"]["value"]
    assert [p["label"] for p in manifest["grid"]] == ["Rails", "Drizzle", "Django", "Alembic (auto)", "Prisma 7.10.0"]
    assert all(p["pin"] != "prisma-latest-tag" for p in manifest["grid"])
    prisma = manifest["grid"][-1]
    assert prisma["outcomes"]["unsupported"] == 18
    assert sum(prisma["outcomes"].values()) - 18 == report["macros"]["nCellsPrismaCurrent"]["value"]
    for bar in manifest["fixes"]:
        if bar["pin"] == "current":
            assert bar["silent_loss"] == report["macros"]["nSilent" + bar["framework"].capitalize() + "Current"]["value"]
        if bar["framework"] == "drizzle":
            assert bar["atomicity_failures"] is None


def test_tracker_total_aliases_and_category_totals(report):
    values = {k: v["value"] for k, v in report["macros"].items()}
    for suffix, expected in (("Inputs", 656), ("Relevant", 167), ("Silent", 43), ("RealDataLossIncidents", 6)):
        assert values["nTrackerTotal" + suffix] == values["nTracker" + suffix] == expected
    for category in ("Consequence", "Mechanism"):
        for silent, total in (("", 167), ("Silent", 43)):
            prefix = "nTrackerTotal" + silent + category
            counts = {k: v for k, v in values.items() if k.startswith(prefix)}
            assert sum(counts.values()) == total
            for name, value in counts.items():
                assert value == values[name.replace("nTrackerTotal", "nTracker", 1)]


@pytest.mark.parametrize("fw,row_loss,objects,operations,loss_operations", [
    ("Rails", 36, 12, 16, 12), ("Drizzle", 22, 14, 15, 8),
    ("Django", 0, 24, 20, 12), ("Alembic", 42, 28, 20, 14),
    ("Prisma", 17, 20, 18, 12), ("Overall", 117, 98, 89, 58),
])
def test_current_loss_types_and_operations(report, fw, row_loss, objects, operations, loss_operations):
    values = {k: v["value"] for k, v in report["macros"].items()}
    prefix = "nCurrent" + fw
    assert values[prefix + "SilentRowOrValue"] == row_loss
    assert values[prefix + "SilentObjectOnly"] == objects
    assert values[prefix + "SilentOther"] == 0
    assert row_loss + objects == values[prefix + "SilentLoss"]
    assert values[prefix + "OperationsEvaluated"] == operations
    assert values[prefix + "OperationsWithSilentLoss"] == loss_operations


def test_lint_specificity_and_false_alarm_totals(report):
    values = {k: v["value"] for k, v in report["macros"].items()}
    frameworks = ("Rails", "Drizzle", "Django", "Alembic", "Prisma")
    for lint in LINTS:
        variant = token(lint)
        for fw in (*frameworks, "Overall"):
            prefix = "nCurrent" + fw
            assert sum(values[prefix + "Lint" + category + variant] for category in
                       ("Specific", "GenericOnly", "Unmatched")) == values[prefix + "DetectedLint" + variant]
            assert values[prefix + "LintFalseAlarm" + variant] <= values[prefix + "LintFalseAlarmEligible" + variant]
        for category in ("Specific", "GenericOnly", "Unmatched", "FalseAlarm", "FalseAlarmEligible"):
            assert values["nCurrentOverallLint" + category + variant] == sum(
                values["nCurrent" + fw + "Lint" + category + variant] for fw in frameworks)
    assert values["nCurrentRailsLintFalseAlarmExecuted"] == 60
    assert values["nCurrentDrizzleLintFalseAlarmExecuted"] == 32
    assert values["nCurrentOverallLintSpecificSchemaAndExecuted"] == 29
    assert values["nCurrentOverallLintGenericOnlySchemaAndExecuted"] == 55
    assert values["nCurrentOverallLintSpecificSchemaAndMigration"] == 14
    assert values["nCurrentPrismaLintFalseAlarmEligibleExecuted"] == 0
    assert values["nCurrentPrismaLintFalseAlarmEligibleMigrationOnly"] == 60


def test_specific_lint_requires_matching_object_and_mechanism():
    row = {"trials": {"populated": {
        "violations": [{"kind": "row_count", "table": "children"},
                       {"kind": "missing_object", "object": "trigger:trg_external"}],
        "before": {"counts": {"children": 3}, "foreign_keys": {
            "children": [[0, 0, "parents", "parent_id", "id", "NO ACTION", "CASCADE", "NONE"]]}},
        "after": {"counts": {"children": 0}},
    }}}
    cascade = {"code": "SQLD001", "detail": "Dependent table `children` references rebuilt table `parents` with ON DELETE CASCADE"}
    trigger = {"code": "SQLD003", "detail": "The trigger `trg_external` created on line 5 is destroyed"}
    assert specific_lint_finding(row, cascade)
    assert specific_lint_finding(row, trigger)
    assert not specific_lint_finding(row, {**cascade, "code": "SQLD002"})
    assert not specific_lint_finding(row, {**cascade, "detail": cascade["detail"].replace("children", "other_children")})
    assert not specific_lint_finding(row, {**trigger, "detail": trigger["detail"].replace("trg_external", "unrelated")})
    assert not specific_lint_finding(row, {**trigger, "detail": trigger["detail"].replace("trigger", "index")})
    row["trials"]["populated"]["before"]["foreign_keys"]["children"][0][6] = "SET NULL"
    assert not specific_lint_finding(row, cascade)


def test_false_alarm_scope_and_cell_counting():
    warning = {"code": "SQLD002"}
    row = {"framework": "rails", "operation": "change_type", "rebuild": True,
           "trials": {"populated": {"outcome": "preserved", "violations": []}},
           "detectors": {"lint": {variant: {"available": True, "output": {"findings": [warning, warning]}}
                                  for variant in LINTS}}}
    loud, partial, no_rebuild, unavailable, planned, native = [deepcopy(row) for _ in range(6)]
    loud["trials"]["populated"]["outcome"] = "failed-loudly"
    partial["trials"]["populated"]["outcome"] = "failed-loudly-partial"
    no_rebuild["rebuild"] = False
    for lint in unavailable["detectors"]["lint"].values():
        lint["available"] = False
    planned.update(rebuild=None, planned_rebuild=True)
    native.update(rebuild=False, planned_rebuild=True)  # A known runtime result takes priority.
    book = Numbers()
    current_detail_numbers(book, "Test", [row, loud, partial, no_rebuild, unavailable, planned, native], "fixture", "rows")
    assert book.macros["nTestLintFalseAlarmExecuted"]["value"] == 3
    assert book.macros["nTestLintFalseAlarmEligibleExecuted"]["value"] == 3


def test_rebuild_reclassification_is_the_only_difference_from_recorded_flags(report):
    recorded = build_numbers(reclassified=None)["macros"]
    changed = {name: (recorded[name]["value"], entry["value"]) for name, entry in report["macros"].items()
               if recorded[name]["value"] != entry["value"]}
    stored = json.loads((ROOT / "results/reanalysis-2026-11-21/paper_macros.json").read_text())["changed"]
    assert changed == {name: (entry["recorded"], entry["corrected"]) for name, entry in stored.items()}
    assert all(name.endswith("RebuildingCells") for name in changed)


def test_reclassification_rejects_cells_absent_from_the_results():
    from scripts.paper_numbers import load_results, reclassify
    change = {"experiment": "orm_matrix", "framework": "prisma", "version_label": "absent", "mode": "default",
              "path": "raw", "operation": "rename_table", "context": "C0", "population": "populated",
              "field": "rebuild", "corrected": False}
    with pytest.raises(ValueError, match="absent from the results"):
        reclassify(load_results(), {"changes": [change]})


def test_replay_version_declarations_partition_the_replays(report):
    values = {k: v["value"] for k, v in report["macros"].items()}
    assert (values["nRealworldReplayedDeclaredCaret"] + values["nRealworldReplayedDeclaredExact"]
            + values["nRealworldReplayedVersionFallback"]) == values["nRealworldMigrationsReplayed"]
    from scripts.paper_numbers import declared_version
    assert declared_version({"declared": "^0.44.2", "resolved": "0.44.2", "fallback": False}) == "Caret"
    assert declared_version({"declared": "0.45.2", "resolved": "0.45.2", "fallback": False}) == "Exact"
    assert declared_version({"declared": None, "resolved": "0.45.4", "fallback": True}) == "Fallback"
    for other in ({"declared": "^0.44.2", "resolved": "0.44.7", "fallback": False},
                  {"declared": "~0.44.2", "resolved": "0.44.2", "fallback": False}):
        with pytest.raises(ValueError, match="neither"):
            declared_version(other)


def test_kappa_is_one_for_identical_labels_and_zero_at_chance():
    assert kappa([True, False, True], [True, False, True]) == 1
    assert kappa([True, True, False, False], [True, False, True, False]) == 0


def test_sample_rejects_reports_outside_the_corpus():
    labels = [{"id": "a#1", "relevant": True}]
    with pytest.raises(ValueError, match="unknown tracker IDs"):
        tracker_sample_numbers(Numbers(), labels, [{"id": "a#2", "relevant": True}])


def test_tracker_sample_is_the_seeded_stratified_draw():
    import random
    read = lambda name: [json.loads(line) for line in (ROOT / "results" / name).read_text().splitlines() if line.strip()]
    labels, sample = read("tracker_labels.jsonl"), read("tracker_sample_labels.jsonl")
    generator = random.Random(20261102)
    drawn = generator.sample(sorted(r["id"] for r in labels if r["relevant"]), 40)
    drawn += generator.sample(sorted(r["id"] for r in labels if not r["relevant"]), 20)
    assert sorted(drawn) == sorted(r["id"] for r in sample)
