import argparse
import copy
import hashlib
import json
import platform
import re
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from smp.checks import create_database, identifier, require
from smp.matrix_spec import CONTEXTS, DRIZZLE, RAILS, fixture
from smp.orm_spec import OPERATIONS
from smp.preservation import classify, observe, probe_constraint, violations

ALL_OPERATIONS = tuple(dict.fromkeys((*RAILS, *DRIZZLE, *OPERATIONS)))
FAULTS = {
    "delete_child": ("C1", True),
    "null_fk": ("C2", True),
    "overwrite_value": ("C0", True),
    "drop_trigger": ("C5", False),
    "drop_index": ("C6", False),
    "change_fk_action": ("C1", False),
    "drop_view": ("C7", False),
    "disable_enforcement": ("C0", False),
    "dangling_reference": ("C1", True),
    "change_trigger_body": ("C5", False),
    "unintended_default": ("C0", False),
    "heap_overwrite": ("C0", True),
}
LIMITATIONS = {"unintended_default"}
DERIVED = {"heap_overwrite"}


def controls(recorded_checker=False):
    for operation in ALL_OPERATIONS:
        for context in CONTEXTS:
            yield {"name": f"safe_{operation}_{context}", "operation": operation,
                   "context": context, "kind": "intended_change", "scope": "matrix"}
    for context in CONTEXTS:
        yield {"name": f"safe_rebuild_{context}", "operation": "add_column",
               "context": context, "kind": "safe_rebuild", "scope": "matrix"}
    for fault, (context, _) in FAULTS.items():
        yield {"name": fault, "operation": "add_column", "context": context,
               "kind": fault, "scope": "limitation" if fault in LIMITATIONS or (recorded_checker and fault in DERIVED)
               else "derived" if fault in DERIVED else "matrix"}
    for kind in ("safe_heap", "safe_heap_id"):
        yield {"name": kind, "operation": "add_column", "context": "C0",
               "kind": kind, "scope": "derived"}


def direct_state(db):
    schema = list(db.execute("SELECT type,name,tbl_name,sql FROM sqlite_schema "
                             "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"))
    tables = {}
    for kind, name, _, _ in schema:
        if kind == "table":
            columns = list(db.execute(f"PRAGMA table_info({identifier(name)})"))
            tables[name] = {
                "columns": columns,
                "rows": list(db.execute(f"SELECT * FROM {identifier(name)} ORDER BY rowid")),
                "foreign_keys": list(db.execute(f"PRAGMA foreign_key_list({identifier(name)})")),
            }
    return {"schema": schema, "tables": tables,
            "foreign_keys": db.execute("PRAGMA foreign_keys").fetchone()[0]}


def rebuild(db, table, declaration):
    require(not db.in_transaction)
    db.execute("PRAGMA foreign_keys=OFF")
    require(db.execute("PRAGMA foreign_keys").fetchone()[0] == 0)
    db.execute("BEGIN")
    try:
        objects = list(db.execute("SELECT type,name,sql FROM sqlite_schema "
                                  "WHERE sql IS NOT NULL AND "
                                  "((tbl_name=? AND type IN ('index','trigger')) OR type='view') "
                                  "ORDER BY type,name", (table,)))
        for kind, name, _ in objects:
            if kind == "view":
                db.execute(f"DROP VIEW {identifier(name)}")
        replacement = "replacement_" + table
        db.execute(f"CREATE TABLE {identifier(replacement)}({declaration})")
        old = {row[1] for row in db.execute(f"PRAGMA table_info({identifier(table)})")}
        columns = [row[1] for row in db.execute(f"PRAGMA table_info({identifier(replacement)})") if row[1] in old]
        projection = ",".join(map(identifier, columns))
        db.execute(f"INSERT INTO {identifier(replacement)}({projection}) "
                   f"SELECT {projection} FROM {identifier(table)}")
        db.execute(f"DROP TABLE {identifier(table)}")
        db.execute(f"ALTER TABLE {identifier(replacement)} RENAME TO {identifier(table)}")
        for _, _, sql in objects:
            db.execute(sql)
        require(not db.execute("PRAGMA foreign_key_check").fetchall())
        require(db.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    finally:
        db.execute("PRAGMA foreign_keys=ON")
    require(db.execute("PRAGMA foreign_keys").fetchone()[0] == 1)


def table_declaration(db, table):
    sql = db.execute("SELECT sql FROM sqlite_schema WHERE type='table' AND name=?", (table,)).fetchone()[0]
    return sql[sql.index("(") + 1:sql.rindex(")")]


def migrate(db, operation, force_rebuild=False):
    native = {
        "add_column": "ALTER TABLE parents ADD COLUMN note TEXT",
        "remove_column": "ALTER TABLE parents DROP COLUMN value",
        "drop_column": "ALTER TABLE parents DROP COLUMN value",
        "rename_column": "ALTER TABLE parents RENAME COLUMN value TO renamed_value",
        "rename_table": "ALTER TABLE parents RENAME TO renamed_parents",
        "add_index": "CREATE INDEX idx_operation ON parents(value)",
        "remove_index": "DROP INDEX idx_operation",
        "drop_index": "DROP INDEX idx_operation",
        "add_unique": "CREATE UNIQUE INDEX parents_value_unique ON parents(value)",
        "drop_unique": "DROP INDEX parents_value_unique",
        "add_reference": "ALTER TABLE parents ADD COLUMN owner_id INTEGER REFERENCES tenants(id)",
    }
    if operation in native and not force_rebuild:
        db.execute(native[operation])
        return
    if operation == "add_timestamps":
        for name in ("created_at", "updated_at"):
            db.execute(f"ALTER TABLE parents ADD COLUMN {name} DATETIME")
        return
    declaration = table_declaration(db, "parents")
    replacements = {
        "change_type": ("value TEXT", "value INTEGER"),
        "set_not_null": ("value TEXT", "value TEXT NOT NULL"),
        "drop_not_null": ("value TEXT NOT NULL", "value TEXT"),
        "change_default": ("DEFAULT '5'", "DEFAULT '9'"),
        "set_default": ("value TEXT", "value TEXT DEFAULT '9'"),
        "drop_default": (" DEFAULT '5'", ""),
        "remove_foreign_key": (", CONSTRAINT fk_tenant FOREIGN KEY(tenant_id) REFERENCES tenants(id)", ""),
        "drop_foreign_key": (", CONSTRAINT fk_tenant FOREIGN KEY(tenant_id) REFERENCES tenants(id)", ""),
        "remove_check_constraint": (", CONSTRAINT positive_value CHECK (CAST(value AS INTEGER) > 0)", ""),
    }
    additions = {
        "add_column": ", note TEXT",
        "add_foreign_key": ", CONSTRAINT fk_tenant FOREIGN KEY(tenant_id) REFERENCES tenants(id)",
        "add_check_constraint": ", CONSTRAINT positive_value CHECK (CAST(value AS INTEGER) > 0)",
    }
    if operation in replacements:
        old, new = replacements[operation]
        require(old in declaration)
        declaration = declaration.replace(old, new)
    else:
        declaration += additions[operation]
    rebuild(db, "parents", declaration)


def sql_shape(sql):
    return re.sub(r'\s+', '', sql.replace('"', '')).rstrip(';')


def verify_safe(before, after, operation, db):
    expected = copy.deepcopy(before)
    parents = expected["tables"]["parents"]
    columns = [list(row) for row in parents["columns"]]
    rows = [list(row) for row in parents["rows"]]
    value_index = next(i for i, column in enumerate(columns) if column[1] == "value")
    if operation in ("remove_column", "drop_column"):
        columns.pop(value_index)
        for row in rows:
            row.pop(value_index)
    elif operation == "rename_column":
        columns[value_index][1] = "renamed_value"
    elif operation == "change_type":
        columns[value_index][2] = "INTEGER"
        for row in rows:
            row[value_index] = int(row[value_index])
    elif operation in ("set_not_null", "drop_not_null"):
        columns[value_index][3] = int(operation == "set_not_null")
    elif operation in ("change_default", "set_default", "drop_default"):
        columns[value_index][4] = None if operation == "drop_default" else "'9'"
    added = {"add_column": [("note", "TEXT")], "add_reference": [("owner_id", "INTEGER")],
             "add_timestamps": [("created_at", "DATETIME"), ("updated_at", "DATETIME")]}.get(operation, [])
    for name, kind in added:
        columns.append([len(columns), name, kind, 0, None, 0])
        for row in rows:
            row.append(None)
    for i, column in enumerate(columns):
        column[0] = i
    parents["columns"], parents["rows"] = list(map(tuple, columns)), list(map(tuple, rows))
    fks = [row[2:] for row in parents["foreign_keys"]]
    if operation in ("remove_foreign_key", "drop_foreign_key"):
        fks = [row for row in fks if row[1] != "tenant_id"]
    if operation in ("add_foreign_key", "add_reference"):
        fks.append(("tenants", "owner_id" if operation == "add_reference" else "tenant_id",
                    "id", "NO ACTION", "NO ACTION", "NONE"))
    parents["foreign_keys"] = [(i, 0, *row) for i, row in enumerate(fks)]
    if operation == "rename_table":
        expected["tables"]["renamed_parents"] = expected["tables"].pop("parents")
        for table in expected["tables"].values():
            table["foreign_keys"] = [(*row[:2], "renamed_parents" if row[2] == "parents" else row[2], *row[3:])
                                      for row in table["foreign_keys"]]
    require(expected["tables"].keys() == after["tables"].keys())
    for name, table in expected["tables"].items():
        actual = after["tables"][name]
        require(table["columns"] == actual["columns"], (operation, name, "columns"))
        require(table["rows"] == actual["rows"], (operation, name, "rows"))
        require(sorted(row[2:] for row in table["foreign_keys"]) == sorted(row[2:] for row in actual["foreign_keys"]))
    objects = {row[1]: row for row in before["schema"] if row[0] != "table"}
    if operation in ("remove_index", "drop_index", "drop_unique"):
        del objects["parents_value_unique" if operation == "drop_unique" else "idx_operation"]
    if operation in ("add_index", "add_unique"):
        name = "idx_operation" if operation == "add_index" else "parents_value_unique"
        unique = "UNIQUE " if operation == "add_unique" else ""
        objects[name] = ("index", name, "parents", f"CREATE {unique}INDEX {name} ON parents(value)")
    actual_objects = {row[1]: row for row in after["schema"] if row[0] != "table"}
    require(objects.keys() == actual_objects.keys())
    for name, (kind, _, table, sql) in objects.items():
        if operation == "rename_table":
            table = "renamed_parents" if table == "parents" else table
            sql = re.sub(r'\bparents\b', 'renamed_parents', sql)
        actual = actual_objects[name]
        require((kind, table, sql_shape(sql)) == (actual[0], actual[2], sql_shape(actual[3])))
    if operation in ("add_check_constraint", "remove_check_constraint", "add_unique", "drop_unique"):
        db.execute("SAVEPOINT truth_constraint")
        rejected = False
        try:
            db.execute("INSERT INTO parents(id,value) VALUES(901,'-2')")
            if "unique" in operation:
                db.execute("INSERT INTO parents(id,value) VALUES(902,'-2')")
        except sqlite3.IntegrityError:
            rejected = True
        finally:
            db.execute("ROLLBACK TO truth_constraint")
            db.execute("RELEASE truth_constraint")
        require(rejected == operation.startswith("add"))
    require(after["foreign_keys"] == 1)
    require(not db.execute("PRAGMA foreign_key_check").fetchall())
    require(db.execute("PRAGMA integrity_check").fetchall() == [("ok",)])


def inject(db, kind):
    sql = {
        "delete_child": "DELETE FROM children WHERE id=1",
        "null_fk": "UPDATE children SET parent_id=NULL WHERE id=1",
        "overwrite_value": "UPDATE parents SET value='changed' WHERE id=1",
        "drop_trigger": "DROP TRIGGER trg_external",
        "drop_index": "DROP INDEX idx_external",
        "drop_view": "DROP VIEW parent_view",
        "disable_enforcement": "PRAGMA foreign_keys=OFF",
        "heap_overwrite": "UPDATE heap SET payload='changed' WHERE rowid=1",
    }
    if kind in sql:
        return db.execute(sql[kind]).rowcount
    if kind == "change_fk_action":
        rebuild(db, "children", table_declaration(db, "children").replace("CASCADE", "SET NULL"))
    elif kind == "unintended_default":
        rebuild(db, "parents", table_declaration(db, "parents").replace("payload TEXT", "payload TEXT DEFAULT 'unexpected'"))
    elif kind == "dangling_reference":
        db.execute("PRAGMA foreign_keys=OFF")
        affected = db.execute("UPDATE children SET parent_id=404 WHERE id=1").rowcount
        db.execute("PRAGMA foreign_keys=ON")
        return affected
    elif kind == "change_trigger_body":
        db.execute("DROP TRIGGER trg_external")
        db.execute("CREATE TRIGGER trg_external AFTER UPDATE OF payload ON parents "
                   "BEGIN INSERT INTO audit(parent_id,message) VALUES(NEW.id,'wrong'); END")
    return None


def verify_fault(before, after, kind, populated, affected):
    expected = copy.deepcopy(before)
    if kind in ("delete_child", "null_fk", "overwrite_value", "dangling_reference", "heap_overwrite"):
        require(affected == int(populated))
        if populated:
            table = "heap" if kind == "heap_overwrite" else "parents" if kind == "overwrite_value" else "children"
            rows = expected["tables"][table]["rows"]
            if kind == "delete_child":
                rows.pop(0)
            else:
                index = 0 if kind == "heap_overwrite" else 2 if kind == "overwrite_value" else 1
                value = None if kind == "null_fk" else 404 if kind == "dangling_reference" else "changed"
                row = list(rows[0])
                row[index] = value
                rows[0] = tuple(row)
    elif kind == "disable_enforcement":
        expected["foreign_keys"] = 0
    elif kind in ("drop_trigger", "drop_index", "drop_view", "change_trigger_body"):
        name = {"drop_trigger": "trg_external", "drop_index": "idx_external", "drop_view": "parent_view",
                "change_trigger_body": "trg_external"}[kind]
        expected["schema"] = [row for row in expected["schema"] if row[1] != name]
        if kind == "change_trigger_body":
            changed = next(row for row in after["schema"] if row[1] == name)
            require("'wrong'" in changed[3])
            expected["schema"].append(changed)
            expected["schema"].sort(key=lambda row: row[:2])
    elif kind in ("change_fk_action", "unintended_default"):
        name = "children" if kind == "change_fk_action" else "parents"
        if kind == "change_fk_action":
            fks = expected["tables"][name]["foreign_keys"]
            require(len(fks) == 1 and fks[0][6] == "CASCADE")
            fks[0] = (*fks[0][:6], "SET NULL", fks[0][7])
            old, new = "CASCADE", "SET NULL"
        else:
            columns = expected["tables"][name]["columns"]
            column = columns[1]
            require(column[1] == "payload" and column[4] is None)
            columns[1] = (*column[:4], "'unexpected'", column[5])
            old, new = "payload TEXT", "payload TEXT DEFAULT 'unexpected'"
        expected["schema"] = [(kind_, name_, table, sql.replace(old, new) if kind_ == "table" and name_ == name else sql)
                              for kind_, name_, table, sql in expected["schema"]]
    expected["schema"] = [(*row[:3], sql_shape(row[3])) for row in expected["schema"]]
    actual = copy.deepcopy(after)
    actual["schema"] = [(*row[:3], sql_shape(row[3])) for row in actual["schema"]]
    require(expected == actual, (kind, "unexpected collateral change"))


def run_control(folder, control, populated, recorded_checker=False):
    spec, schema, seed = fixture("raw", control["operation"], control["context"])
    kind = control["kind"]
    if kind in ("safe_heap", "safe_heap_id", "heap_overwrite"):
        with_id = kind == "safe_heap_id"
        schema += "CREATE TABLE heap(" + ("id INTEGER," if with_id else "") + "payload TEXT);\n"
        seed += "INSERT INTO heap VALUES" + ("(2,'b'),(1,'a');" if with_id else "('a'),('b');")
        spec["tables"].append("heap")
        spec["preserve"]["heap"] = ["id", "payload"] if with_id else ["payload"]
    population = "populated" if populated else "empty"
    path = Path(folder) / f"{control['name']}_{population}.db"
    create_database(path, schema, seed, populated)
    before = observe(path, spec, recorded_checker=recorded_checker)
    probe_constraint(path, spec, before)
    trace = []
    with closing(sqlite3.connect(path, isolation_level=None)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        original = direct_state(db)
        db.set_trace_callback(trace.append)
        migrate(db, control["operation"], force_rebuild=kind == "safe_rebuild")
        db.set_trace_callback(None)
        intended = direct_state(db)
        verify_safe(original, intended, control["operation"], db)
        db.set_trace_callback(trace.append)
        affected = inject(db, kind) if kind in FAULTS else None
        db.set_trace_callback(None)
        final = direct_state(db)
        if kind in FAULTS:
            verify_fault(intended, final, kind, populated, affected)
        else:
            require(final == intended)
        execution = {"success": True, "foreign_keys_before": original["foreign_keys"],
                     "foreign_keys_after": final["foreign_keys"], "sqlite": sqlite3.sqlite_version}
    after = observe(path, spec, after=True, recorded_checker=recorded_checker)
    probe_constraint(path, spec, after)
    found = violations(before, after, spec, execution, recorded_checker)
    verdict = classify(True, found, before, after)
    loss = kind in FAULTS and (populated or not FAULTS[kind][1])
    positive = verdict == "silent-loss"
    cell = ("TP" if positive else "FN") if loss else ("FP" if positive else "TN")
    row = {**control, "population": population, "expected_label": "lossy" if loss else "safe",
           "oracle_verdict": verdict, "confusion": cell, "violations": found,
           "empty_noop": kind in FAULTS and FAULTS[kind][1] and not populated,
           "ground_truth": {"verified": True, "affected_rows": affected, "before": original,
                            "intended": intended, "after": final},
           "spec": spec, "schema": schema, "seed": seed, "executed_sql": trace,
           "execution": execution, "before": before, "after": after}
    row["explanation"] = explain(row, recorded_checker)
    return row


def explain(row, recorded_checker=False):
    if row["confusion"] == "FN":
        if row["kind"] == "heap_overwrite" and recorded_checker:
            return "The table has no id column. Both content reads fail at ORDER BY id, the two missing digests compare equal, and the row count is unchanged."
        if row["kind"] == "unintended_default":
            return "Existing payload default changed. Table SQL/defaults outside the declared target are not compared on success; state_digest is used only for failed executions."
        return "Unexpected missed seeded fault; inspect the retained ground truth and observations."
    if row["confusion"] == "FP":
        return "Independent full-row, column, FK, object, and constraint checks verified the intended transformation; inspect the reported invariant mismatch."
    if row["empty_noop"]:
        return "The empty fixture has no target row; zero rows changed, so this is a safe negative trial."
    if row["kind"] in ("safe_heap", "safe_heap_id"):
        if recorded_checker and row["kind"] == "safe_heap":
            return "Derived fixture without a primary key; a table without an id column cannot be read, so the safe verdict does not show that its rows were compared."
        return "Derived fixture without a primary key; rows are compared as a multiset when there is no id column."
    return "Verified seeded fault detected." if row["confusion"] == "TP" else "Verified intended transformation preserved."


def confusion(rows):
    return {cell: sum(row["confusion"] == cell for row in rows) for cell in ("TP", "FN", "TN", "FP")}


def summarize(rows):
    result = {"overall": confusion(rows)}
    for field in ("population", "kind", "scope"):
        result["by_" + field] = {value: confusion([row for row in rows if row[field] == value])
                                 for value in sorted({row[field] for row in rows})}
    safe = [row for row in rows if row["population"] == "populated" and row["kind"] == "intended_change"]
    result["populated_intended_changes"] = {"trials": len(safe), "false_alarms": sum(row["confusion"] == "FP" for row in safe),
        "by_operation": {op: confusion([row for row in safe if row["operation"] == op]) for op in ALL_OPERATIONS}}
    result["empty_noops"] = sum(row["empty_noop"] for row in rows)
    result["content_error_trials"] = sum(any("error" in data for data in row["after"]["content"].values()) for row in rows)
    return result


def render_summary(result):
    rows, summary = result["controls"], result["summary"]
    recorded = result.get("checker") == "recorded"
    counts = summary["overall"]
    positive, negative = counts["TP"] + counts["FN"], counts["TN"] + counts["FP"]
    lines = ["# Oracle validation results", "", f"Python {result['runtime']['python']}; SQLite {result['runtime']['sqlite']}. "
             + ("Checker of the matrix runs (`--recorded-checker`)." if recorded else "Corrected checker."), "",
             f"{len(rows)} successful raw sqlite3 executions: {len(rows) // 2} controls, each populated and empty. "
             f"{len(ALL_OPERATIONS)} operation names × {len(CONTEXTS)} contexts, plus safe rebuilds and fault/scope controls.", "",
             f"TP {counts['TP']}/{positive} lossy trials; FN {counts['FN']}/{positive}; "
             f"TN {counts['TN']}/{negative} safe trials; FP {counts['FP']}/{negative}.", "",
             "| Population | TP | FN | TN | FP |", "|---|---:|---:|---:|---:|"]
    for population, cells in summary["by_population"].items():
        lines.append(f"| {population} | " + " | ".join(str(cells[k]) for k in counts) + " |")
    lines += ["", "| Control / violation kind | TP | FN | TN | FP |", "|---|---:|---:|---:|---:|"]
    for kind, cells in summary["by_kind"].items():
        lines.append(f"| {kind} | " + " | ".join(str(cells[k]) for k in counts) + " |")
    lines += ["", "| Scope | TP | FN | TN | FP |", "|---|---:|---:|---:|---:|"]
    for scope, cells in summary["by_scope"].items():
        lines.append(f"| {scope} | " + " | ".join(str(cells[k]) for k in counts) + " |")
    safe = summary["populated_intended_changes"]
    lines += ["", f"Populated intended-change false alarms: **{safe['false_alarms']}/{safe['trials']}**. "
              "Each operation below has all nine contexts; aliases remain separate operation names.", "",
              "| Operation | Populated false alarms / safe trials |", "|---|---:|"]
    for op, cells in safe["by_operation"].items():
        lines.append(f"| {op} | {cells['FP']} / {cells['FP'] + cells['TN']} |")
    lines += ["", f"Empty mutation no-ops: {summary['empty_noops']}; included as TN, not FN. "
              "Each injected fault is one trial even when multiple invariants fire.", "", "## Every FP and FN", ""]
    errors = [row for row in rows if row["confusion"] in ("FN", "FP")]
    lines += [f"- {row['confusion']}: `{row['name']}` ({row['population']}): {row['explanation']}" for row in errors]
    if not any(row["confusion"] == "FP" for row in errors):
        lines.append("- No false positives.")
    lines += ["", "## Scope and open problems", "",
              f"Content observation errors occur in {summary['content_error_trials']}/{len(rows)} trials. "
              + ("This checker orders every table by id, so a table without an id column cannot be read, and it does "
                 "not report a failed read as a finding. The safe controls on such tables therefore do not show "
                 "that their rows were compared. " if recorded else
                 "A table without an id column is ordered by its projected rows, so the heap controls compare "
                 "row multisets; a content read that fails is reported as a content violation, never as preserved. ")
              + "A heap with unique id values can be ordered, but uniqueness is not verified by the observer.", "",
              "Changed trigger SQL is detected, including on an empty database. The limitation controls cover "
              "column defaults outside the declared target, which are not compared on success. Trigger probes "
              "cover one payload update, not all behavior. Integrity corruption, arbitrary type conversions, "
              "dependent-column renames, and framework-specific migration execution are outside these controls.", "",
              "These are deterministic seeded controls, not estimates of real-world error prevalence. "
              "The operation union shares fixture SQL across frameworks and does not multiply equivalent "
              "raw controls by framework name. Main counts include limitations; scope-specific counts are "
              "retained in controls.json.", "", "## Reproduction", "",
              f"Run `.venv/bin/python scripts/oracle_validation.py{' --recorded-checker' if recorded else ''} "
              "--output results/<new directory>` from the "
              "repository root; an existing result is never overwritten. The tests are "
              "`tests/test_oracle_validation.py`, `tests/test_preservation.py`, `tests/test_checks.py` and "
              "`tests/test_orm_checks.py`.", "",
              "The rebuild implementation follows SQLite's "
              "[generalized ALTER TABLE procedure](https://www.sqlite.org/lang_altertable.html#otheralter). "
              "Views are saved and dropped before replacing their referenced table, then recreated before validation.", "",
              "See results/oracle_validation/expected_state.md for the code-derived contract, and controls.json for source hashes, "
              "full observations, direct ground truth, executed SQL, per-control verdicts, and grouped counts.", ""]
    return "\n".join(lines)


def run_suite(output, recorded_checker=False):
    """recorded_checker runs the checker as it was when the matrix results were produced."""
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / "results"):
        raise ValueError("Outputs must remain under results/")
    if (output / "controls.json").exists():
        raise ValueError(f"{output} already holds a result; select a new directory")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="databases-", dir=output) as folder:
        rows = [run_control(folder, control, populated, recorded_checker)
                for control in controls(recorded_checker) for populated in (True, False)]
    sources = ["smp/checks.py", "smp/preservation.py", "smp/matrix_spec.py", "smp/orm_spec.py",
               "scripts/oracle_validation.py", "tests/test_oracle_validation.py", "PROTOCOL_oracle_validation.md",
               "results/oracle_validation/expected_state.md"]
    result = {"format_version": 1, "checker": "recorded" if recorded_checker else "corrected", "runtime": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version},
              "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources},
              "summary": summarize(rows), "controls": rows}
    (output / "controls.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / "summary.md").write_text(render_summary(result))
    return result


def main():
    parser = argparse.ArgumentParser(description="Validate preservation decisions against raw SQLite controls.")
    parser.add_argument("--output", type=Path, required=True, help="New directory under results/")
    parser.add_argument("--recorded-checker", action="store_true",
                        help="Use the checker of the matrix runs (results/oracle_validation) instead of the corrected one")
    args = parser.parse_args()
    result = run_suite(args.output, args.recorded_checker)
    print(json.dumps({"executions": len(result["controls"]), **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
