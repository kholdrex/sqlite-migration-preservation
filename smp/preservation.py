"""Value and behavior observations, opt-in alongside the original pilot checks."""
import hashlib
import json
import sqlite3
from contextlib import closing

from .checks import canonical_sql, identifier, snapshot


def digest(rows):
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(",", ":"),
                                     default=lambda value: {"blob": value.hex()}).encode()).hexdigest()


RUNNER_TABLES = ("sqlite_", "__drizzle", "schema_migrations", "ar_internal_metadata")


def observe(database, spec, after=False, bookkeeping=lambda name: name.startswith(RUNNER_TABLES), recorded_checker=False):
    """bookkeeping selects the runner's own tables, which are left out of the application-state digest.

    recorded_checker reads content as the matrix runs did: every table is ordered by id.
    """
    rename = spec.get("table_rename", {}) if after else {}
    tables = [rename.get(t, t) for t in spec["tables"]]
    result = snapshot(database, tables)
    result["content"] = {}
    result["view_rows"] = {}
    result["trigger_probes"] = {}
    with closing(sqlite3.connect(database)) as db:
        for table, columns in spec["preserve"].items():
            actual = rename.get(table, table)
            projection = []
            for column in columns:
                target = spec.get("column_rename", {}).get(column, column) if after and table == "parents" else column
                expression = identifier(target)
                if table == "parents" and column == "value" and spec["operation"] == "change_type":
                    expression = f"CAST({expression} AS TEXT)"
                projection.append(expression)
            try:
                # Stable integer primary keys define order; adding/dropping fields does not change the projection.
                # A table without an id column is ordered by its projected rows.
                keyed = recorded_checker or any(row[1] == "id" for row in db.execute(f"PRAGMA table_info({identifier(actual)})"))
                order = "id" if keyed else ",".join(str(i) for i in range(1, len(projection) + 1))
                rows = db.execute(f"SELECT {','.join(projection)} FROM {identifier(actual)} ORDER BY {order}").fetchall()
                result["content"][table] = {"columns": columns, "digest": digest(rows), "rows": rows}
            except sqlite3.Error as exc:
                result["content"][table] = {"error": str(exc)}
        for name in spec.get("views", []):
            try:
                rows = db.execute(f"SELECT * FROM {identifier(name)} ORDER BY 1").fetchall()
                result["view_rows"][name] = {"digest": digest(rows), "rows": rows}
            except sqlite3.Error as exc:
                result["view_rows"][name] = {"error": str(exc)}
        # Capture persisted application state before reversible behavioral probes.
        state = []
        for kind, name, sql in db.execute("SELECT type,name,sql FROM sqlite_schema WHERE sql IS NOT NULL ORDER BY type,name"):
            if bookkeeping(name):
                continue
            rows = db.execute(f"SELECT * FROM {identifier(name)} ORDER BY rowid").fetchall() if kind == "table" else None
            state.append([kind, name, canonical_sql(sql), rows])
        result["state_digest"] = digest(state)
        for name in spec.get("triggers", []):
            db.execute("SAVEPOINT preservation_probe")
            try:
                parent = rename.get("parents", "parents")
                # Also exercise triggers in the empty trial, without persisting probe fixtures.
                db.execute("INSERT OR IGNORE INTO tenants(id,payload) VALUES(1,'probe')")
                value_column = "renamed_value" if after and spec["operation"] == "rename_column" else "value"
                if after and spec["operation"] in ("remove_column", "drop_column"):
                    db.execute(f"INSERT OR IGNORE INTO {identifier(parent)}(id,payload) VALUES(999,'probe')")
                else:
                    db.execute(f"INSERT OR IGNORE INTO {identifier(parent)}(id,payload,{identifier(value_column)}) VALUES(999,'probe','77')")
                baseline = db.execute("SELECT count(*) FROM audit").fetchone()[0]
                db.execute(f"UPDATE {identifier(parent)} SET payload='probe-updated' WHERE id=999")
                rows = db.execute("SELECT parent_id,message FROM audit ORDER BY id").fetchall()[baseline:]
                result["trigger_probes"][name] = {"rows": rows, "fires": rows == [(999, "probe-updated")]}
            except sqlite3.Error as exc:
                result["trigger_probes"][name] = {"error": str(exc), "fires": False}
            finally:
                db.execute("ROLLBACK TO preservation_probe")
                db.execute("RELEASE preservation_probe")
    return result


def expected_present(after, expected):
    from .checks import intended_change
    kind = expected["kind"]
    if kind == "all":
        return all(expected_present(after, item) for item in expected["items"])
    if kind == "absent_column":
        return expected["table"] in after["columns"] and all(c["name"] != expected["name"] for c in after["columns"][expected["table"]])
    if kind == "absent_object":
        return expected["object"] not in after["objects"]
    if kind == "absent_fk":
        return not any(row[3] == expected["column"] for row in after["foreign_keys"].get(expected["table"], []))
    if kind == "table":
        return expected["name"] in after["counts"] and expected["old"] not in after["counts"]
    if kind in ("check", "unique"):
        return after["intended_probe"] == expected["present"]
    return intended_change(after, expected)


def probe_constraint(database, spec, result):
    expected = spec["expected"]
    if expected["kind"] not in ("check", "unique"):
        return
    with closing(sqlite3.connect(database)) as db:
        db.execute("SAVEPOINT intended_probe")
        try:
            db.execute("INSERT INTO parents(id,payload,value) VALUES(991,'probe','-1')")
            if expected["kind"] == "unique":
                db.execute("INSERT INTO parents(id,payload,value) VALUES(992,'other','-1')")
            result["intended_probe"] = False
        except sqlite3.IntegrityError:
            result["intended_probe"] = True
        finally:
            db.execute("ROLLBACK TO intended_probe")
            db.execute("RELEASE intended_probe")


def violations(before, after, spec, execution, recorded_checker=False):
    """recorded_checker compares as the matrix runs did: two unreadable observations count as equal."""
    found = []
    unread = lambda data: "digest" not in data and not recorded_checker
    rename = spec.get("table_rename", {})
    for table, count in before["counts"].items():
        if after["counts"].get(rename.get(table, table)) != count:
            found.append({"kind": "row_count", "table": table})
    # A table whose content could not be read before the migration counts as a content violation.
    for table, data in before["content"].items():
        if unread(data) or data.get("digest") != after["content"].get(table, {}).get("digest"):
            found.append({"kind": "content_digest", "table": table})
    for key, obj in before["objects"].items():
        if key in spec.get("removed_objects", []):
            continue
        current = after["objects"].get(key)
        if current is None:
            found.append({"kind": "missing_object", "object": key})
        else:
            tokens = [rename.get(t, t) for t in canonical_sql(obj["sql"])]
            if tokens != canonical_sql(current["sql"]):
                found.append({"kind": "changed_object", "object": key})
    for table, foreign_keys in before["foreign_keys"].items():
        current = after["foreign_keys"].get(rename.get(table, table), [])
        for foreign_key in foreign_keys:
            if table == "parents" and foreign_key[3] == "tenant_id" and spec["operation"] in ("remove_foreign_key", "drop_foreign_key"):
                continue
            definition = [rename.get(foreign_key[2], foreign_key[2]), *foreign_key[3:]]
            if not any(row[2:] == definition for row in current):
                found.append({"kind": "foreign_key_definition", "table": table, "definition": definition})
    for name, data in before["view_rows"].items():
        if unread(data) or data.get("digest") != after["view_rows"].get(name, {}).get("digest"):
            found.append({"kind": "view_rows", "object": name})
    for name, data in before["trigger_probes"].items():
        if not after["trigger_probes"].get(name, {}).get("fires") or data != after["trigger_probes"].get(name):
            found.append({"kind": "trigger_behavior", "object": name})
    for key, valid in [("foreign_key_check", []), ("integrity_check", ["ok"]), ("errors", []), ("view_errors", [])]:
        if after[key] != valid:
            found.append({"kind": key, "details": after[key]})
    if execution.get("foreign_keys_after") != 1:
        found.append({"kind": "fk_enforcement"})
    if not expected_present(after, spec["expected"]):
        found.append({"kind": "intended_change_missing"})
    return found


def classify(success, findings, before, after):
    if success:
        return "silent-loss" if findings else "preserved"
    return "failed-loudly" if before["state_digest"] == after["state_digest"] else "failed-loudly-partial"
