"""Validators on damaged and undamaged results, with and without -O."""
import copy
import json
import shutil
import subprocess
import sys

import pytest

from smp.checks import ValidationError, require
from smp.environment import ROOT
from smp.report import gate_results


def test_require_survives_optimization():
    code = ("from smp.checks import require\n"
            "try:\n    require(1 == 2, 'damaged')\nexcept AssertionError as exc:\n    raise SystemExit(str(exc))\n")
    completed = subprocess.run([sys.executable, "-O", "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 1 and "damaged" in completed.stderr
    with pytest.raises(ValidationError):
        require(False, "damaged")


@pytest.mark.parametrize("flags", [[], ["-O"]])
def test_pilot_validator_rejects_a_changed_violation(tmp_path, flags):
    original = json.loads((ROOT / "results/pilot.json").read_text())
    run = next(r for r in original["runs"] if r["path"] == "rails" and r["trials"]["populated"]["violations"])
    artifacts = tmp_path / "artifacts"
    shutil.copytree(ROOT / run["artifacts"], artifacts)
    run["artifacts"] = str(artifacts)
    path = tmp_path / "pilot.json"

    def validate(changed):
        (artifacts / "result.json").write_text(json.dumps(changed))
        path.write_text(json.dumps(dict(runs=[changed], gates=gate_results([changed]))))
        return subprocess.run([sys.executable, *flags, str(ROOT / "scripts/validate_results.py"), str(path)],
                              capture_output=True, text=True)

    unchanged = validate(run)
    assert unchanged.returncode == 0 and json.loads(unchanged.stdout)["runs_validated"] == 1
    damaged = copy.deepcopy(run)
    damaged["trials"]["populated"]["violations"] = []
    damaged["detectors"]["populated_invariants"]["detected"] = False
    completed = validate(damaged)
    assert completed.returncode != 0 and "ValidationError" in completed.stderr
    assert "runs_validated" not in completed.stdout


@pytest.mark.parametrize("script", ["validate_operation_matrix.py", "validate_orm_matrix.py", "validate_results.py",
                                    "validate_rails_fixes.py", "validate_rails_atomicity.py", "oracle_validation.py"])
def test_no_validation_depends_on_assert_statements(script):
    import ast
    sources = [ROOT / "scripts" / script, ROOT / "smp/rails_atomicity.py", ROOT / "smp/operation_matrix.py",
               ROOT / "smp/orm_matrix.py"]
    for source in sources:
        tree = ast.parse(source.read_text())
        assert not [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)], source.name


def test_matrix_validators_reject_an_empty_selection():
    from scripts.validate_operation_matrix import validate as validate_operations
    from scripts.validate_orm_matrix import validate as validate_orms
    pins = json.loads((ROOT / "versions.json").read_text())
    empty = {"rows": [], "errors": [], "pins": pins, "selection": {"labels": ["curent"]}}
    with pytest.raises(ValidationError, match="No rows"):
        validate_operations(empty)
    with pytest.raises(ValidationError, match="No rows"):
        validate_operations(empty, complete=False)
    with pytest.raises(ValidationError, match="No rows"):
        validate_orms({"rows": [], "errors": [], "unsupported": []}, complete=False)


def test_release_candidate_repeat_validates_with_its_inline_unique_schemas():
    from scripts.validate_operation_matrix import inline_unique_on_value, validate, validate_generation
    from smp.matrix_spec import fixture
    directory = ROOT / "results/rerun-2026-11-01/drizzle"
    summary = validate(json.loads((directory / "operation_matrix.json").read_text()), complete=False)
    assert summary["pairs_validated"] == 810 and summary["starting_schemas_with_inline_unique"] == 9
    archive = directory / "operation_evidence/matrix_drizzle_drop_unique_C0--v1-rc5--generation.json.gz"
    with pytest.raises(ValidationError):
        validate_generation(archive, fixture("drizzle", "drop_unique", "C0")[1])
    table = "CREATE TABLE parents(id INTEGER PRIMARY KEY, payload TEXT{}, value TEXT{});"
    assert inline_unique_on_value(table.format("", " UNIQUE")) == "sqlite_autoindex_parents_1"
    assert inline_unique_on_value(table.format(" UNIQUE", "")) is None


def test_reanalysis_check_without_the_local_copy_compares_published_artifacts():
    from scripts import reanalysis
    directory = ROOT / "results/reanalysis-2026-11-21"
    stored = {name: json.loads((directory / f"{name}.json").read_text()) for name in
              ("statement_provenance", "rebuild_classification", "content_reads", "view_digests", "paper_macros")}
    results = reanalysis.analyse(ROOT, None)
    assert reanalysis.differences(stored, results, None) == []
    full = next(c for c in stored["statement_provenance"]["corrections"] if c["mode"] == "full")
    changed = copy.deepcopy(stored)
    changed["view_digests"]["views"].append({"artifact": full["artifact"], "path": "drizzle", "boundary": "after"})
    assert reanalysis.differences(changed, results, None) == ["view_digests"]
    changed = copy.deepcopy(stored)
    changed["view_digests"]["recorded_view_findings"]["results/realworld.json"] = 1
    assert reanalysis.differences(changed, results, None) == ["view_digests"]
    changed = copy.deepcopy(stored)
    next(c for c in changed["statement_provenance"]["corrections"] if c["artifact"] == full["artifact"])["items"].pop(0)
    assert reanalysis.differences(changed, results, None) == ["statement_provenance"]


def test_replay_validator_compares_row_counts_with_the_snapshots():
    from scripts.validate_realworld import validate
    from smp.realworld import summary
    directory = ROOT / "results/realworld-rerun-2026-11-02"
    result = json.loads((directory / "realworld.json").read_text())
    assert validate(result, directory) == []
    row = next(r for r in result["rows"] if r["status"] != "unreplayable"
               and any(f["kind"] == "row_count" for f in r["paths"]["drizzle"]["findings"]))
    row["paths"]["drizzle"].update(outcome="preserved", findings=[])
    result["summary"] = summary(result["rows"])
    assert any("row-count findings differ from the snapshot" in error for error in validate(result, directory))


def test_relint_refuses_an_existing_output_and_a_missing_binary(tmp_path):
    existing = tmp_path / "relint.json"
    existing.write_text("{}")
    for arguments in (["--doctor", sys.executable, "--output", str(existing)],
                      ["--doctor", str(tmp_path / "absent"), "--verify"]):
        completed = subprocess.run([sys.executable, str(ROOT / "scripts/relint.py"), "--commit", "0" * 40, *arguments],
                                   capture_output=True, text=True)
        assert completed.returncode == 2
    assert existing.read_text() == "{}"
