"""Rendering of the Markdown reports."""
import json
import re

import pytest

from smp import matrix_report, orm_report, rails_atomicity, rails_base, rails_fixes, report, upstream_report
from smp.environment import ROOT


def load(name):
    return json.loads((ROOT / "results" / name).read_text())


def toggle_populated_violation(run):
    trial = run["trials"]["populated"]
    trial["violations"] = [] if trial["violations"] else [{"kind": "missing_object", "object": "index:idx"}]


def pilot(tmp_path, change):
    result = load("pilot.json")
    if change:
        toggle_populated_violation(result["runs"][0])
    report.write_report(result, tmp_path / "report.md")
    return "Population is essential to exposing the nine framework cascade-loss runs"


def upstream(tmp_path, change):
    result = load("upstream_fixes.json")
    if change:
        toggle_populated_violation(result["runs"][0])
    upstream_report.write_upstream_report(result, tmp_path / "report.md")
    return "Each individual fix prevents its framework's measured cascade losses"


def fixes(tmp_path, change):
    result = load("rails_fixes.json")
    if change:
        row = next(r for r in result["rows"] if r["version_label"] == "rails-pr58709+56811")
        row["outcome"] = row["trials"]["populated"]["outcome"] = "silent-loss"
        row["trials"]["populated"]["violations"] = [{"kind": "row_count", "table": "children"}]
    rails_fixes.write_report(result, tmp_path / "report.md")
    return "Both combined pins have **no silent-loss cells in this matrix**"


def orms(tmp_path, change):
    result = load("orm_matrix.json")
    if change:
        row = next(r for r in result["rows"] if r["path"] == "django" and r["outcome"] == "preserved")
        row["outcome"] = row["trials"]["populated"]["outcome"] = "silent-loss"
        row["trials"]["populated"]["violations"] = [{"kind": "row_count", "table": "children"}]
    orm_report.write_report(result, tmp_path / "report.md")
    return "Its transaction protects the original table when the C7 view blocks a rebuild"


def bases(tmp_path, change):
    result = load("rails_base/comparison.json")
    if change:
        cell = result["comparisons"][0]["cells"][0]
        cell["head"] = {"outcome": "silent-loss", "codes": ["R"], "rebuild": True}
        result["comparisons"][0]["counts"]["populated"]["head"]["silent-loss"] = 13
    rails_base.write_summary(result, tmp_path)
    (tmp_path / "summary.md").rename(tmp_path / "report.md")
    return "Each base loses preservation in 48/144 populated cells"


@pytest.mark.parametrize("render", [pilot, upstream, fixes, orms, bases])
def test_interpretation_is_printed_only_for_the_outcomes_it_describes(tmp_path, render):
    claim = render(tmp_path, change=False)
    recorded = (tmp_path / "report.md").read_text()
    assert claim in recorded and report.OMITTED not in recorded
    render(tmp_path, change=True)
    changed = (tmp_path / "report.md").read_text()
    assert claim not in changed and report.OMITTED in changed
    assert [line for line in changed.splitlines() if line.startswith("|")] != \
           [line for line in recorded.splitlines() if line.startswith("|")]


def test_atomicity_findings_follow_the_classifications():
    result = load("rails_atomicity.json")
    claim = "persist both the precursor and the completed parent rebuild"
    assert claim in "\n".join(rails_atomicity.report_lines(result))
    row = next(r for r in result["rows"] if r["version_label"] == "rails-pr57128" and r["scenario"]["transactional"])
    row["assessment"]["classification"] = "fully rolled back"
    changed = "\n".join(rails_atomicity.report_lines(result))
    assert claim not in changed and report.OMITTED in changed
    assert "| rails-pr57128 | fully rolled back |" in changed


@pytest.mark.parametrize("render", [pilot, upstream, fixes, orms, bases])
def test_reproduction_commands_preserve_retained_results(tmp_path, render):
    render(tmp_path, change=False)
    text = (tmp_path / "report.md").read_text()
    assert not re.search(r"--output results(?![/\w])", text)
    assert "scripts/build_rails_base.py\n" not in text


def test_matrix_report_points_to_a_new_output_directory(tmp_path):
    result = load("rerun-2026-11-01/rails-current/operation_matrix.json")
    matrix_report.write_report(result, tmp_path / "report.md")
    text = (tmp_path / "report.md").read_text()
    assert not re.search(r"--output results(?![/\w])", text)


def test_base_control_never_writes_into_the_retained_run(tmp_path):
    from scripts import build_rails_base
    retained = ROOT / "results/rails_base"
    for start in (rails_base.run, build_rails_base.build):
        with pytest.raises(ValueError, match="directory of its own"):
            start(retained)
    with pytest.raises(ValueError, match="under results/rails_base"):
        rails_base.run(tmp_path)


def test_replay_comparison_counts_come_from_the_compared_results():
    from scripts.finalize_realworld_rerun import report as render
    directory = ROOT / "results/realworld-rerun-2026-11-02"
    original, rerun = load("realworld.json"), json.loads((directory / "realworld.json").read_text())
    comparison = json.loads((directory / "comparison.json").read_text())
    text = render(comparison, rerun, rerun["evidence_validation"])
    assert "silent-loss counts are 19 Drizzle, 12 raw and 23 raw-tx (unadjudicated: 20, 13 and 24)" in text
    assert "11 change from Drizzle silent loss to raw preservation and 4 remain silent loss" in text
    comparison["paper_counts"]["quantities"]["nRealworldAllDrizzleSilentLoss"]["rerun"] = 18
    assert "silent-loss counts are 18 Drizzle" in render(comparison, rerun, rerun["evidence_validation"])


def test_atlas_summary_denominators_follow_the_report():
    from scripts.atlas_lint import summary
    recorded = json.loads((ROOT / "results/atlas_lint/report.json").read_text())
    assert summary(recorded) == (ROOT / "results/atlas_lint/summary.md").read_text()
    recorded["totals"]["silent"]["executed"]["paper_available"] = 177
    recorded["deviations"] = ["The image was pulled twice."]
    changed = summary(recorded)
    assert "177 silent / 204 safe cells for executed inputs" in changed
    assert "The image was pulled twice. On the pinned image" in changed
