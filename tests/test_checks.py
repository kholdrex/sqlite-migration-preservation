import sqlite3

import pytest

from smp.checks import check_invariants, create_database, snapshot, statements

SCHEMA = """
CREATE TABLE parents(id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE children(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id) ON DELETE CASCADE);
CREATE INDEX idx_name ON parents(name);
"""
SEED = "INSERT INTO parents VALUES(1, 'a'); INSERT INTO children VALUES(1, 1);"
EXPECTED = {"kind": "column", "table": "parents", "name": "note"}


def make_db(tmp_path):
    path = tmp_path / "test.db"
    create_database(path, SCHEMA, SEED, True)
    return path, snapshot(path, ["parents", "children"])


def test_cascade_loss_despite_success_and_clean_sqlite_checks(tmp_path):
    path, before = make_db(tmp_path)
    with sqlite3.connect(path, isolation_level=None) as db:
        db.executescript("""
        PRAGMA foreign_keys=ON;
        BEGIN;
        PRAGMA foreign_keys=OFF;
        CREATE TABLE replacement(id INTEGER PRIMARY KEY, name TEXT, note TEXT);
        INSERT INTO replacement(id,name) SELECT id,name FROM parents;
        DROP TABLE parents;
        ALTER TABLE replacement RENAME TO parents;
        CREATE INDEX idx_name ON parents(name);
        COMMIT;
        """)
    after = snapshot(path, ["parents", "children"])
    assert after["foreign_key_check"] == []
    assert after["integrity_check"] == ["ok"]
    assert check_invariants(before, after, EXPECTED) == [
        {"kind": "row_count", "table": "children", "before": 1, "after": 0}]


def test_lost_index(tmp_path):
    path, before = make_db(tmp_path)
    with sqlite3.connect(path) as db:
        db.executescript("DROP INDEX idx_name; ALTER TABLE parents ADD COLUMN note TEXT;")
    assert check_invariants(before, snapshot(path, ["parents", "children"]), EXPECTED) == [
        {"kind": "missing_object", "object": "index:idx_name"}]


def test_safe_change(tmp_path):
    path, before = make_db(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("ALTER TABLE parents ADD COLUMN note TEXT")
    assert check_invariants(before, snapshot(path, ["parents", "children"]), EXPECTED) == []


def test_missing_implicit_unique_index(tmp_path):
    path = tmp_path / "unique.db"
    create_database(path, "CREATE TABLE parents(id INTEGER PRIMARY KEY, name TEXT UNIQUE);",
                    "INSERT INTO parents VALUES(1, 'a');", True)
    before = snapshot(path, ["parents"])
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE replacement(id INTEGER PRIMARY KEY, name TEXT, note TEXT);
        INSERT INTO replacement(id,name) SELECT id,name FROM parents;
        DROP TABLE parents;
        ALTER TABLE replacement RENAME TO parents;
        """)
    assert check_invariants(before, snapshot(path, ["parents"]), EXPECTED) == [
        {"kind": "missing_object", "object": "index:sqlite_autoindex_parents_1"}]


def test_lost_trigger_and_changed_view_definition(tmp_path):
    path, _ = make_db(tmp_path)
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TRIGGER name_guard BEFORE UPDATE ON parents BEGIN SELECT RAISE(ABORT, 'blocked'); END;
        CREATE VIEW parent_names AS SELECT name FROM parents;
        """)
    before = snapshot(path, ["parents", "children"])
    with sqlite3.connect(path) as db:
        db.executescript("""
        DROP TRIGGER name_guard;
        DROP VIEW parent_names;
        CREATE VIEW parent_names AS SELECT id FROM parents;
        ALTER TABLE parents ADD COLUMN note TEXT;
        """)
    violations = check_invariants(before, snapshot(path, ["parents", "children"]), EXPECTED)
    assert {(v["kind"], v["object"]) for v in violations} == {
        ("missing_object", "trigger:name_guard"), ("changed_object", "view:parent_names")}


def test_foreign_key_violation_and_missing_intended_change(tmp_path):
    path, before = make_db(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE children SET parent_id=999")
    violations = check_invariants(before, snapshot(path, ["parents", "children"]), EXPECTED)
    assert {v["kind"] for v in violations} == {"foreign_key_check", "intended_change_missing"}


def test_index_formatting_is_not_a_definition_change(tmp_path):
    path, before = make_db(tmp_path)
    with sqlite3.connect(path) as db:
        db.executescript('DROP INDEX idx_name; CREATE INDEX "idx_name" ON "parents" ("name"); ALTER TABLE parents ADD COLUMN note TEXT;')
    assert check_invariants(before, snapshot(path, ["parents", "children"]), EXPECTED) == []


def test_statement_split_preserves_triggers_and_semicolon_literals():
    sql = "CREATE TABLE a(x); CREATE TRIGGER t AFTER INSERT ON a BEGIN SELECT 'a;b'; SELECT 1; END; INSERT INTO a VALUES (';');"
    parts = list(statements(sql))
    assert len(parts) == 3
    with sqlite3.connect(":memory:") as db:
        for statement in parts:
            db.execute(statement)
        assert db.execute("SELECT x FROM a").fetchall() == [(";",)]


@pytest.mark.parametrize("tail", ["-- end of file", "-- end of file\n", "/* done */", "\n-- a\n/* b */ -- c"])
def test_statement_split_ignores_a_trailing_comment(tail):
    assert list(statements("SELECT 1; " + tail)) == ["SELECT 1;"]
    assert list(statements("SELECT 1 " + tail)) == [("SELECT 1 " + tail).strip()]


@pytest.mark.parametrize("sql", ["SELECT 1; /* open", "CREATE TRIGGER t AFTER INSERT ON p BEGIN SELECT 1; -- unfinished",
                                 "SELECT 'unterminated -- not a comment"])
def test_statement_split_still_rejects_incomplete_sql(sql):
    with pytest.raises(ValueError, match="Incomplete"):
        list(statements(sql))
