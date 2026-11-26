"""Independent failure-state checks for the atomicity observer and classifier."""
import sqlite3

import pytest

from smp.rails_atomicity import assess, observe


@pytest.fixture
def starting_state(tmp_path):
    database = tmp_path / "atomicity.db"
    with sqlite3.connect(database) as db:
        db.executescript("""
            CREATE TABLE parents(id INTEGER PRIMARY KEY, payload TEXT NOT NULL, value TEXT DEFAULT '5');
            CREATE TABLE children(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id), payload TEXT);
            CREATE TABLE markers(id INTEGER PRIMARY KEY, note TEXT NOT NULL);
            CREATE TABLE schema_migrations(version TEXT PRIMARY KEY);
            INSERT INTO parents VALUES(1,'original parent','11');
            INSERT INTO children VALUES(1,1,'original child');
            INSERT INTO markers VALUES(1,'original marker');
            INSERT INTO schema_migrations VALUES('123');
        """)
    return database, observe(database)


def test_rollback_restores_rows_and_schema(starting_state):
    database, before = starting_state
    with sqlite3.connect(database) as db:
        db.execute("BEGIN")
        db.execute("UPDATE markers SET note='written before rebuild'")
        db.execute("ALTER TABLE markers ADD COLUMN stage_note TEXT")
        db.execute("DELETE FROM children")
        db.rollback()
    result = assess(before, observe(database))
    assert result["classification"] == "fully rolled back"
    assert result["schema_migrations_unchanged"]
    assert not any(result["surviving_changes"].values())


@pytest.mark.parametrize("sql,change", [
    ("UPDATE markers SET note='written before rebuild'", "precursor_data"),
    ("ALTER TABLE markers ADD COLUMN stage_note TEXT", "precursor_schema"),
])
def test_committed_precursor_is_partial_without_row_loss(starting_state, sql, change):
    database, before = starting_state
    with sqlite3.connect(database) as db:
        db.execute(sql)
    result = assess(before, observe(database))
    assert result["classification"] == "partially committed"
    assert result["surviving_changes"][change]
    assert result["data_loss"] == []


@pytest.mark.parametrize("sql", ["DELETE FROM children", "UPDATE children SET payload='corrupted'"])
def test_missing_or_changed_child_takes_precedence_over_partial_commit(starting_state, sql):
    database, before = starting_state
    with sqlite3.connect(database) as db:
        db.execute("UPDATE markers SET note='written before rebuild'")
        db.execute(sql)
    result = assess(before, observe(database))
    assert result["classification"] == "data loss"
    assert result["surviving_changes"]["precursor_data"]
    assert result["data_loss"][0]["table"] == "children"


def test_changed_migration_version_prevents_full_rollback_classification(starting_state):
    database, before = starting_state
    with sqlite3.connect(database) as db:
        db.execute("INSERT INTO schema_migrations VALUES('456')")
    result = assess(before, observe(database))
    assert result["classification"] == "partially committed"
    assert not result["schema_migrations_unchanged"]
