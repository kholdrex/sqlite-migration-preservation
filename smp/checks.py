import re
import sqlite3
from pathlib import Path


class ValidationError(AssertionError):
    """A retained result or a runner precondition failed a check."""


def require(condition, message="check failed"):
    """Check a result explicitly; unlike an assert statement this survives python -O."""
    if not condition:
        raise ValidationError(message)


def identifier(name):
    return '"' + name.replace('"', '""') + '"'


def tokens_without_comments(sql):
    # Tokenizer preserves strings: comment markers within strings are not comments.
    return re.sub(r"('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`[^`]*`)|--[^\n]*|/\*[\s\S]*?\*/",
                  lambda m: m[1] or ' ', sql)


def statements(sql):
    """Split SQL with SQLite's parser, preserving trigger bodies and literals."""
    pending = ""
    for char in sql:
        pending += char
        if char == ";" and sqlite3.complete_statement(pending):
            if pending.strip():
                yield pending.strip()
            pending = ""
    # A tail of comments is not a statement; the newline keeps the added semicolon out of a line comment.
    if tokens_without_comments(pending).strip():
        if not sqlite3.complete_statement(pending + "\n;"):
            raise ValueError("Incomplete SQL statement")
        yield pending.strip()


def canonical_sql(sql):
    """Normalize formatting and identifier quotes without changing literals."""
    tokens = re.findall(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`[^`]*`|\[[^]]*\]|[\w]+|[^\s]", sql or "")
    return [t if t.startswith("'") else t.strip('"`[]').lower() for t in tokens if t != ";"]


def snapshot(database, tables):
    with sqlite3.connect(database) as db:
        objects = {f"{kind}:{name}": {"type": kind, "name": name, "table": table, "sql": sql}
                   for kind, name, table, sql in db.execute(
                       "SELECT type, name, tbl_name, sql FROM sqlite_schema "
                       "WHERE type IN ('index','trigger','view') ORDER BY type,name")}
        counts, columns, foreign_keys, errors = {}, {}, {}, []
        for table in tables:
            try:
                counts[table] = db.execute(f"SELECT count(*) FROM {identifier(table)}").fetchone()[0]
                columns[table] = [dict(zip(("cid", "name", "type", "notnull", "default", "pk"), row))
                                  for row in db.execute(f"PRAGMA table_info({identifier(table)})")]
                foreign_keys[table] = [list(row) for row in db.execute(f"PRAGMA foreign_key_list({identifier(table)})")]
            except sqlite3.Error as exc:
                errors.append(f"{table}: {exc}")
        view_errors = []
        for obj in objects.values():
            if obj["type"] == "view":
                try:
                    db.execute(f"SELECT * FROM {identifier(obj['name'])} LIMIT 0")
                except sqlite3.Error as exc:
                    view_errors.append(f"{obj['name']}: {exc}")
        try:
            fk_check = [list(row) for row in db.execute("PRAGMA foreign_key_check")]
        except sqlite3.Error as exc:
            fk_check = [[str(exc)]]
        return {"counts": counts, "columns": columns, "foreign_keys": foreign_keys,
                "objects": objects, "foreign_key_check": fk_check,
                "integrity_check": [row[0] for row in db.execute("PRAGMA integrity_check")],
                "errors": errors, "view_errors": view_errors,
                "observer_sqlite": sqlite3.sqlite_version}


def intended_change(after, expected):
    kind = expected["kind"]
    if kind == "column":
        column = next((c for c in after["columns"].get(expected["table"], [])
                       if c["name"] == expected["name"]), None)
        return column is not None and all(column.get(k) == v for k, v in expected.get("attributes", {}).items())
    if kind == "foreign_key":
        return any(row[2] == expected["target"] and row[3] == expected["column"]
                   for row in after["foreign_keys"].get(expected["table"], []))
    if kind == "index":
        obj = after["objects"].get(f"index:{expected['name']}")
        return obj is not None and canonical_sql(obj["sql"]) == canonical_sql(expected["sql"])
    raise ValueError(f"Unknown intended change: {kind}")


def check_invariants(before, after, expected):
    violations = []
    for table, count in before["counts"].items():
        if after["counts"].get(table) != count:
            violations.append({"kind": "row_count", "table": table, "before": count,
                               "after": after["counts"].get(table)})
    for key, obj in before["objects"].items():
        current = after["objects"].get(key)
        if current is None:
            violations.append({"kind": "missing_object", "object": key})
        elif canonical_sql(current["sql"]) != canonical_sql(obj["sql"]):
            violations.append({"kind": "changed_object", "object": key,
                               "before": obj["sql"], "after": current["sql"]})
    for key, valid in [("foreign_key_check", []), ("integrity_check", ["ok"]),
                       ("errors", []), ("view_errors", [])]:
        if after[key] != valid:
            violations.append({"kind": key, "details": after[key]})
    if not intended_change(after, expected):
        violations.append({"kind": "intended_change_missing", "expected": expected})
    return violations


def create_database(path, schema, seed, populated):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    with sqlite3.connect(path, isolation_level=None) as db:
        db.execute("PRAGMA foreign_keys=ON")
        for statement in statements(schema):
            db.execute(statement)
        if populated:
            for statement in statements(seed):
                db.execute(statement)
