import json
from pathlib import Path

import pytest

from smp import pilot, operation_matrix
from scripts import build_rails_merge


def test_doctor_selection_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    path_binary = tmp_path / "sqlite-doctor"
    path_binary.write_text("#!/bin/sh\nexit 0\n")
    path_binary.chmod(0o755)
    monkeypatch.delenv("SMP_DOCTOR", raising=False)
    assert pilot.resolve_doctor() == path_binary
    env_binary = tmp_path / "environment-doctor"
    monkeypatch.setenv("SMP_DOCTOR", str(env_binary))
    assert pilot.resolve_doctor() == env_binary
    explicit = tmp_path / "explicit-doctor"
    assert pilot.resolve_doctor(explicit) == explicit


def test_missing_doctor_fails_matrix_before_creating_output(tmp_path, monkeypatch):
    monkeypatch.setattr(operation_matrix, "ROOT", tmp_path)
    output = tmp_path / "matrix"
    with pytest.raises(FileNotFoundError, match="Supply --doctor, set SMP_DOCTOR"):
        operation_matrix.run_matrix(output, tmp_path / "missing")
    assert not output.exists()
    result = pilot.lint(tmp_path / "missing", "SELECT 1;", tmp_path / "input.sql")
    assert result["available"] is False
    assert result["detected"] is None


def test_original_upstream_selection(tmp_path, monkeypatch):
    root = pilot.ROOT
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    for name in ("versions.json", "cases", "sources"):
        (tmp_path / name).symlink_to(root / name)
    seen = []
    monkeypatch.setattr(pilot, "generate", lambda *args, **kwargs: tmp_path)
    labels = ["rails-pr57128", "drizzle-pr5784", "drizzle-pr5074", "drizzle-pr5784+5074"]
    expected = json.loads((root / "results/upstream_fixes.json").read_text())
    recorded = {(r["case"], r["path"], r["version_label"]): r for r in expected["runs"]}
    def run(case, path, label, *args):
        seen.append((case.name, path, label))
        return recorded[case.name, path, label]
    monkeypatch.setattr(pilot, "run_case", run)
    result = pilot.run_pilot(tmp_path / "output", tmp_path / "missing", upstream=True, labels=labels)
    assert set(seen) == set(recorded)
    assert len(seen) == 61
    assert set(result["pins"]["rails"]) == {"rails-pr57128"}
    assert json.loads((tmp_path / "output/upstream_fixes.json").read_text())["runs"] == expected["runs"]
    report = (tmp_path / "output/upstream_fixes.md").read_text()
    for label in labels:
        assert f"| {label} |" in report
    assert "rails-pr56811" not in report.split("## Detector comparison")[0]


def test_relocate_rails_lock_preserves_every_resolution(tmp_path, monkeypatch):
    root = build_rails_merge.ROOT
    monkeypatch.setattr(build_rails_merge, "ROOT", tmp_path)
    (tmp_path / "sources").symlink_to(root / "sources")
    for label in ("rails-pr57128+56811", "rails-pr58709+56811"):
        lock = tmp_path / "runners/rails" / label / "Gemfile.lock"
        lock.parent.mkdir(parents=True)
        original = (root / "runners/rails" / label / "Gemfile.lock").read_text()
        lock.write_text(original)
        destination = tmp_path / "relocated" / (label + ".git")
        build_rails_merge.relocate_lockfile(label, destination)
        after = lock.read_text()
        assert after.splitlines()[1] == f"  remote: {destination}"
        assert original.splitlines()[2:] == after.splitlines()[2:]
        build_rails_merge.relocate_lockfile(label, destination)
        assert lock.read_text() == after


def test_original_operation_selection_is_recorded(tmp_path, monkeypatch):
    import sys
    from smp import matrix_report
    root = operation_matrix.ROOT
    monkeypatch.setattr(operation_matrix, "ROOT", tmp_path)
    for name in ("versions.json", "sources"):
        (tmp_path / name).symlink_to(root / name)
    def group(job, *args):
        framework, operation, context, label = job
        paths = ("rails",) if framework == "rails" else ("drizzle", "raw", "raw-tx")
        return [dict(framework=framework, operation=operation, context=context,
                     version_label=label, path=path, outcome="preserved") for path in paths]
    monkeypatch.setattr(operation_matrix, "run_group", group)
    from types import SimpleNamespace
    monkeypatch.setattr(operation_matrix.subprocess, "run", lambda *args, **kwargs:
                        SimpleNamespace(returncode=0, stdout='{"findings": []}'))
    monkeypatch.setattr(matrix_report, "write_report", lambda *args: None)
    labels = ["before", "current", "rails-pr57128", "drizzle-pr5784", "drizzle-pr5074", "drizzle-pr5784+5074"]
    result = operation_matrix.run_matrix(tmp_path / "output", Path(sys.executable), labels=labels)
    expected = json.loads((root / "results/operation_matrix.json").read_text())
    def keys(rows):
        return {(r["framework"], r["operation"], r["context"], r["version_label"], r["path"]) for r in rows}
    assert keys(result["rows"]) == keys(expected["rows"])
    assert len(result["rows"]) == 2457
    assert result["selection"]["labels"] == labels


@pytest.mark.parametrize("kit_one", [False, True])
def test_pilot_validator_accepts_both_kit_layouts(tmp_path, kit_one):
    import shutil
    import subprocess
    import sys
    from smp.report import gate_results
    root = pilot.ROOT
    original = json.loads((root / "results/pilot.json").read_text())
    run = next(r for r in original["runs"] if r["path"] == "drizzle")
    artifacts = tmp_path / "artifacts"
    shutil.copytree(root / run["artifacts"], artifacts)
    if kit_one:
        old = artifacts / "generated_history/0001_after.sql"
        new = artifacts / "generated_history/20261103000000_after/migration.sql"
        new.parent.mkdir()
        old.rename(new)
    run["artifacts"] = str(artifacts)
    (artifacts / "result.json").write_text(json.dumps(run))
    result = dict(runs=[run], gates=gate_results([run]))
    path = tmp_path / "pilot.json"
    path.write_text(json.dumps(result))
    completed = subprocess.run([sys.executable, str(root / "scripts/validate_results.py"), str(path)],
                               capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["runs_validated"] == 1


def test_broken_executable_fails_matrix_before_creating_output(tmp_path, monkeypatch):
    monkeypatch.setattr(operation_matrix, "ROOT", tmp_path)
    broken = tmp_path / "broken-doctor"
    broken.write_text("#!/bin/sh\necho not-json\n")
    broken.chmod(0o755)
    with pytest.raises(ValueError, match="sqlite-doctor could not run"):
        operation_matrix.run_matrix(tmp_path / "output", broken)
    assert not (tmp_path / "output").exists()


def test_pilot_validator_accepts_an_unavailable_linter(tmp_path):
    import shutil
    import subprocess
    import sys
    from smp.report import gate_results
    root = pilot.ROOT
    original = json.loads((root / "results/pilot.json").read_text())
    run = next(r for r in original["runs"] if r["path"] == "rails")
    artifacts = tmp_path / "artifacts"
    shutil.copytree(root / run["artifacts"], artifacts)
    run["artifacts"] = str(artifacts)
    unavailable = pilot.lint(tmp_path / "missing", "SELECT 1;", tmp_path / "input.sql")
    assert unavailable["output"] is None
    run["detectors"]["lint"] = {name: {"available": False, "detected": None, "error": "[Errno 2] No such file"}
                                for name in run["detectors"]["lint"]}
    (artifacts / "result.json").write_text(json.dumps(run))
    path = tmp_path / "pilot.json"
    gates = gate_results([run])
    assert gates["G2"]["lint_available_for_all_inputs"] is False
    path.write_text(json.dumps(dict(runs=[run], gates=gates)))
    completed = subprocess.run([sys.executable, str(root / "scripts/validate_results.py"), str(path)],
                               capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["runs_validated"] == 1


def matrix_root(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from smp import matrix_report
    root = operation_matrix.ROOT
    monkeypatch.setattr(operation_matrix, "ROOT", tmp_path)
    for name in ("versions.json", "sources"):
        (tmp_path / name).symlink_to(root / name)
    def group(job, *args):
        framework, operation, context, label = job
        return [dict(framework=framework, operation=operation, context=context,
                     version_label=label, path="rails", outcome="preserved")]
    monkeypatch.setattr(operation_matrix, "run_group", group)
    monkeypatch.setattr(operation_matrix.subprocess, "run", lambda *args, **kwargs:
                        SimpleNamespace(returncode=0, stdout='{"findings": []}'))
    monkeypatch.setattr(matrix_report, "write_report", lambda *args: None)


@pytest.mark.parametrize("selection", [dict(labels=["curent"]), dict(frameworks=["rail"]),
                                       dict(operations=["add_colum"]), dict(contexts=["C9"]),
                                       dict(frameworks=["rails"], operations=["drop_unique"])])
def test_matrix_rejects_a_selection_that_runs_nothing(tmp_path, monkeypatch, selection):
    import sys
    matrix_root(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="Unknown|matches no"):
        operation_matrix.run_matrix(tmp_path / "output", Path(sys.executable), **selection)
    assert not (tmp_path / "output").exists()


def test_matrix_resume_requires_the_same_linter_and_a_manifest(tmp_path, monkeypatch):
    import sys
    matrix_root(tmp_path, monkeypatch)
    doctor = Path(sys.executable)
    selection = dict(frameworks=["rails"], operations=["add_column"], contexts=["C0"], labels=["current"])
    first = operation_matrix.run_matrix(tmp_path / "output", doctor, **selection)
    again = operation_matrix.run_matrix(tmp_path / "output", doctor, **selection)
    assert first["sqlite_doctor_sha256"] == again["sqlite_doctor_sha256"]
    other = tmp_path / "other-doctor"
    other.write_text("#!/bin/sh\necho '{}'\n")
    other.chmod(0o755)
    with pytest.raises(ValueError, match="different linter"):
        operation_matrix.run_matrix(tmp_path / "output", other, **selection)
    historical = tmp_path / "historical/operation_evidence"
    historical.mkdir(parents=True)
    (historical / "cell.json.gz").write_bytes(b"")
    with pytest.raises(ValueError, match="without a run manifest"):
        operation_matrix.run_matrix(tmp_path / "historical", doctor, **selection)


def test_generation_scratch_is_separate_per_output(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from smp import generate as generator
    from smp.environment import scratch_scope
    root = pilot.ROOT
    monkeypatch.setattr(generator, "ROOT", tmp_path)
    (tmp_path / "versions.json").write_bytes((root / "versions.json").read_bytes())
    runtime = tmp_path / "runners/drizzle/current"
    for package, version in json.loads((root / "versions.json").read_text())["drizzle"]["current"].items():
        (runtime / "node_modules" / package).mkdir(parents=True)
        (runtime / "node_modules" / package / "package.json").write_text(json.dumps({"version": version}))
    case = tmp_path / "case"
    case.mkdir()
    (case / "case.json").write_text(json.dumps({"id": "shared_case", "before": "before.ts", "after": "after.ts"}))
    (case / "before.ts").write_text("// before")
    (case / "after.ts").write_text("// after")
    def kit(command, cwd, **kwargs):
        config = Path(next(a for a in command if a.startswith("--config=")).split("=", 1)[1])
        name = next(a for a in command if a.startswith("--name=")).split("=", 1)[1]
        history = cwd / json.loads(config.read_text())["out"]
        (history / "meta").mkdir(parents=True, exist_ok=True)
        journal = history / "meta/_journal.json"
        entries = json.loads(journal.read_text())["entries"] if journal.exists() else []
        tag = f"{len(entries):04d}_{name}"
        (history / f"{tag}.sql").write_text("SELECT 1;")
        journal.write_text(json.dumps({"entries": entries + [{"tag": tag}]}))
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(generator.subprocess, "run", kit)
    assert scratch_scope(tmp_path / "a") != scratch_scope(tmp_path / "b")
    assert scratch_scope(tmp_path / "a") == scratch_scope(tmp_path / "a/../a")
    first = generator.generate(case, "current", scope=scratch_scope(tmp_path / "a"))
    second = generator.generate(case, "current", scope=scratch_scope(tmp_path / "b"))
    assert first != second and first.is_relative_to(runtime) and second.is_relative_to(runtime)
    assert (first / "upgrade/0001_after.sql").exists() and (second / "upgrade/0001_after.sql").exists()


@pytest.mark.parametrize("command,aggregate", [("pilot", "pilot.json"), ("upstream-fixes", "upstream_fixes.json"),
                                               ("rails-fixes", "rails_fixes.json"), ("rails-atomicity", "rails_atomicity.json"),
                                               ("realworld", "realworld.json")])
def test_commands_never_replace_a_retained_aggregate(monkeypatch, command, aggregate):
    import io
    import sys
    from smp import cli
    errors = io.StringIO()
    monkeypatch.setattr(sys, "stderr", errors)
    retained = pilot.ROOT / "results"
    before = (retained / aggregate).read_bytes()
    extra = ["--repo", "owner/project", "--migration", "migrations/0001.sql"] if command == "realworld" else []
    for arguments in ([command, *extra], [command, *extra, "--output", str(retained)]):
        monkeypatch.setattr(sys, "argv", ["smp", *arguments])
        with pytest.raises(SystemExit) as stopped:
            cli.main()
        assert stopped.value.code == 2
    assert "already holds" in errors.getvalue()
    assert (retained / aggregate).read_bytes() == before
