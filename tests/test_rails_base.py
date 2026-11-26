import pytest

from scripts.build_rails_base import base_pins
from smp import environment
from smp.matrix_spec import CONTEXTS, RAILS
from smp.rails_atomicity import scenarios
from smp.rails_base import atomicity_index, matrix_index, runtime_differences, transition, validate_execution


def test_base_pins_deduplicate_full_commits():
    commit = "a" * 40
    pin = {"commit": commit, "base_for": ["rails-pr1", "rails-pr2"]}
    fixes = {"rails-pr1": {"base_commit": commit}, "rails-pr2": {"base_commit": commit},
             "rails-base-" + commit[:12]: pin}
    assert base_pins(fixes) == {"rails-base-" + commit[:12]: pin}
    pin["base_for"] = ["rails-pr1"]
    with pytest.raises(ValueError, match="Inconsistent base"):
        base_pins(fixes)


def test_matrix_coverage_rejects_missing_duplicate_and_wrong_path():
    rows = [{"version_label": "base", "operation": op, "context": ctx, "framework": "rails", "path": "rails"}
            for op in RAILS for ctx in CONTEXTS]
    assert len(matrix_index(rows, ["base"])) == 144
    for invalid in (rows[:-1], rows + [rows[0]], [{**rows[0], "path": "raw"}] + rows[1:]):
        with pytest.raises(ValueError, match="Missing or duplicate"):
            matrix_index(invalid, ["base"])


def test_atomicity_coverage_rejects_missing_duplicate():
    rows = [{"version_label": "base", "scenario": spec} for spec in scenarios()]
    assert len(atomicity_index(rows, ["base"])) == 8
    for invalid in (rows[:-1], rows + [rows[0]]):
        with pytest.raises(ValueError, match="Missing or duplicate"):
            atomicity_index(invalid, ["base"])


@pytest.mark.parametrize("before,after,expected", [
    ("silent-loss", "preserved", "fixed silent loss"),
    ("silent-loss", "failed-loudly", "changed"),
    ("preserved", "failed-loudly-partial", "regression"),
    ("silent-loss", "silent-loss", "residual silent loss"),
    ("preserved", "preserved", "unchanged"),
])
def test_transitions_do_not_count_loud_failure_as_fixed(before, after, expected):
    assert transition({"outcome": before}, {"outcome": after}) == expected


def test_runtime_validation_rejects_wrong_ruby_revision_hash():
    pin = {"commit": "a" * 40, "version": "8.2.0.alpha", "adapter_sha256": "b" * 64}
    execution = {"ruby": "3.4.3", "activerecord": "8.2.0.alpha", "sqlite3_gem": "2.9.6",
                 "activerecord_revision": pin["commit"], "adapter_sha256": pin["adapter_sha256"],
                 "foreign_keys_before": 1, "foreign_keys_after": 1}
    validate_execution(execution, pin)
    for key in ("ruby", "activerecord_revision", "adapter_sha256", "foreign_keys_after"):
        with pytest.raises(ValueError):
            validate_execution({**execution, key: "wrong"}, pin)


def test_dependency_diff_includes_missing_and_changed_gems():
    assert runtime_differences({"same": "1", "changed": "1", "removed": "1"},
                               {"same": "1", "changed": "2", "added": "3"}) == {
        "changed": {"base": "1", "head": "2"}, "removed": {"base": "1", "head": None},
        "added": {"base": None, "head": "3"}}


def test_isolated_runtime_redirects_all_writable_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(environment, "ROOT", tmp_path)
    monkeypatch.setenv("SMP_RUNTIME_ROOT", "results/rails_base/runtime")
    runtime = tmp_path / "results/rails_base/runtime"
    env = environment.local_env()
    for key in ("BUNDLE_PATH", "BUNDLE_APP_CONFIG", "BUNDLE_USER_HOME", "TMPDIR", "PIP_CACHE_DIR",
                "npm_config_cache", "npm_config_devdir"):
        assert environment.Path(env[key]).is_relative_to(runtime)
    monkeypatch.setenv("SMP_RUNTIME_ROOT", "../outside")
    with pytest.raises(ValueError, match="inside the repository"):
        environment.local_env()


def test_runtime_rejects_symlink_escape(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    root.mkdir()
    (root / "shared").symlink_to(tmp_path, target_is_directory=True)
    monkeypatch.setattr(environment, "ROOT", root)
    monkeypatch.setenv("SMP_RUNTIME_ROOT", "shared/new-runtime")
    with pytest.raises(ValueError, match="inside the repository"):
        environment.local_env()


def test_comparison_keeps_populations_and_atomicity_separate(monkeypatch):
    from smp import rails_base
    monkeypatch.setattr(rails_base, "RAILS", {"change_default": ""})
    monkeypatch.setattr(rails_base, "CONTEXTS", {"C1": "cascade"})
    def row(label, populated, empty):
        return {"version_label": label, "operation": "change_default", "context": "C1",
                "framework": "rails", "path": "rails", "artifacts": label + ".json.gz",
                "trials": {population: {"outcome": outcome, "violations": [], "rebuild": True}
                           for population, outcome in (("populated", populated), ("empty", empty))}}
    def probes(label, outcome):
        return [{"version_label": label, "scenario": spec, "assessment": {"classification": outcome},
                 "after_rebuild": {"children": []}, "after": {"rows": {"children": [1, 2, 3]}},
                 "artifacts": label + spec["id"]} for spec in scenarios()]
    result = rails_base.compare([row("base", "silent-loss", "preserved")],
                                [row("head", "preserved", "silent-loss")],
                                probes("base", "fully rolled back"), probes("head", "partially committed"),
                                [("base", "head")])[0]
    assert result["transitions"]["populated"] == {"fixed silent loss": 1}
    assert result["transitions"]["empty"] == {"regression": 1}
    assert len(result["atomicity"]) == 8
    assert result["atomicity"][0]["base"]["assessment"]["classification"] == "fully rolled back"
    assert result["atomicity"][0]["head"]["assessment"]["classification"] == "partially committed"


def test_runtime_consistency_checks_empty_and_atomicity_dependencies():
    from smp.rails_base import validate_runtime_consistency
    execution = {"ruby": "3.4.3", "sqlite": "3.53.2", "gems": {"bundler": "2.6.7"}}
    row = {"version_label": "base", "trials": {"populated": {"execution": execution},
                                               "empty": {"execution": execution}}}
    probe = {"version_label": "base", "execution": execution}
    assert validate_runtime_consistency([row], [probe], ["base"])["base"]["bundler"] == "2.6.7"
    with pytest.raises(ValueError, match="changed between trials"):
        validate_runtime_consistency([row], [{**probe, "execution": {**execution, "gems": {}}}], ["base"])
    row["trials"]["empty"]["execution"] = {**execution, "sqlite": "other"}
    with pytest.raises(ValueError, match="changed between trials"):
        validate_runtime_consistency([row], [probe], ["base"])


def test_matrix_validation_accepts_json_arrays_and_rejects_changed_archive(monkeypatch):
    import json
    from smp import rails_base
    trial = {"execution": {"success": True}, "before": {"rows": [(1, "value")]}, "after": {},
             "violations": [], "outcome": "preserved"}
    row = {"artifacts": "unused", "trials": {"populated": trial, "empty": trial}}
    saved = {"row": json.loads(json.dumps(row)), "spec": {}}
    monkeypatch.setattr(rails_base, "matrix_index", lambda rows, labels: {("base", "operation", "C0"): row})
    monkeypatch.setattr(rails_base, "read_gzip", lambda path: saved)
    monkeypatch.setattr(rails_base, "validate_execution", lambda execution, pin: None)
    monkeypatch.setattr(rails_base, "violations", lambda *args: [])
    monkeypatch.setattr(rails_base, "classify", lambda *args: "preserved")
    rails_base.validate_matrix([row], {"base": {}})
    saved["row"]["trials"]["populated"]["before"]["rows"] = [[2, "changed"]]
    with pytest.raises(ValueError, match="archive differs"):
        rails_base.validate_matrix([row], {"base": {}})
