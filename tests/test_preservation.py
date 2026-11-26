import sqlite3

import pytest

from smp.checks import create_database
from smp.matrix_spec import fixture, materialize
from smp.preservation import classify, expected_present, observe, probe_constraint, violations


def database(tmp_path, operation="add_column", context="C0"):
    spec, _, _ = fixture("rails", operation, context)
    # Define the test schema separately so the checker and fixture generator cannot share the same SQL error.
    value = "value TEXT"
    constraint = ", CONSTRAINT positive_value CHECK (CAST(value AS INTEGER) > 0)" if operation == "remove_check_constraint" else ""
    ancestor = ", ancestor_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE" if context == "C8" else ""
    schema = f"""
        CREATE TABLE tenants(id INTEGER PRIMARY KEY, payload TEXT);
        CREATE TABLE parents(id INTEGER PRIMARY KEY,payload TEXT,{value},tenant_id INTEGER{ancestor}{constraint});
        CREATE INDEX idx_declared ON parents(payload);
    """
    if operation == "remove_index":
        schema += "CREATE INDEX idx_operation ON parents(value);"
    if context in ("C1", "C2"):
        action = "CASCADE" if context == "C1" else "SET NULL"
        schema += f"CREATE TABLE children(id INTEGER PRIMARY KEY,parent_id INTEGER REFERENCES parents(id) ON DELETE {action},payload TEXT);"
    if context == "C5":
        schema += """
            CREATE TABLE audit(id INTEGER PRIMARY KEY,parent_id INTEGER,message TEXT);
            CREATE TRIGGER trg_external AFTER UPDATE OF payload ON parents
            BEGIN INSERT INTO audit(parent_id,message) VALUES(NEW.id,NEW.payload); END;
        """
    if context == "C7":
        schema += "CREATE VIEW parent_view AS SELECT id,payload FROM parents;"
    seed = "INSERT INTO tenants VALUES(1,'a'),(2,'b');"
    seed += "INSERT INTO parents(id,payload,value,tenant_id) VALUES(1,'alpha','11',1),(2,'beta','22',2);"
    if context == "C8":
        seed += "UPDATE parents SET ancestor_id=tenant_id;"
    if context in ("C1", "C2"):
        seed += "INSERT INTO children VALUES(1,1,'child');"
    path = tmp_path / "tiny.db"
    create_database(path, schema, seed, True)
    before = observe(path, spec)
    probe_constraint(path, spec, before)
    return path, spec, before


def changes(path, spec, before, sql, enforcement=1, after=True):
    with sqlite3.connect(path) as db:
        db.executescript(sql)
    observed = observe(path, spec, after=after)
    probe_constraint(path, spec, observed)
    found = violations(before, observed, spec, {"foreign_keys_after": enforcement})
    return observed, {v["kind"] for v in found}


def test_same_count_set_null_changes_digest(tmp_path):
    path, spec, before = database(tmp_path, context="C2")
    after, kinds = changes(path, spec, before, "UPDATE children SET parent_id=NULL; ALTER TABLE parents ADD COLUMN note TEXT;")
    assert after["counts"] == before["counts"]
    assert kinds == {"content_digest"}


def test_overwritten_value_and_stable_key_order(tmp_path):
    path, spec, before = database(tmp_path)
    after, kinds = changes(path, spec, before, "UPDATE parents SET value='9'; ALTER TABLE parents ADD COLUMN note TEXT;")
    assert kinds == {"content_digest"}
    assert after["content"]["parents"]["rows"][0][0] == 1


def test_view_same_definition_different_rows(tmp_path):
    path, spec, before = database(tmp_path, context="C7")
    _, kinds = changes(path, spec, before, "UPDATE parents SET payload='changed'; ALTER TABLE parents ADD COLUMN note TEXT;")
    assert kinds == {"content_digest", "view_rows"}


def test_broken_view_compilation(tmp_path):
    path, spec, before = database(tmp_path, context="C7")
    _, kinds = changes(path, spec, before, "DROP VIEW parent_view; CREATE VIEW parent_view AS SELECT missing FROM parents; ALTER TABLE parents ADD COLUMN note TEXT;")
    assert kinds == {"changed_object", "view_rows", "view_errors"}


def test_trigger_exists_but_does_not_fire_and_probe_rolls_back(tmp_path):
    path, spec, before = database(tmp_path, context="C5")
    assert before["trigger_probes"]["trg_external"]["fires"]
    assert before["counts"]["audit"] == 0
    after, kinds = changes(path, spec, before, """
        DROP TRIGGER trg_external;
        CREATE TRIGGER trg_external AFTER UPDATE OF payload ON parents WHEN 0
        BEGIN INSERT INTO audit(parent_id,message) VALUES(NEW.id,NEW.payload); END;
        ALTER TABLE parents ADD COLUMN note TEXT;
    """)
    assert "trigger:trg_external" in after["objects"]
    assert kinds == {"changed_object", "trigger_behavior"}
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM audit").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM parents").fetchone()[0] == 2


def test_missing_trigger(tmp_path):
    path, spec, before = database(tmp_path, context="C5")
    _, kinds = changes(path, spec, before, "DROP TRIGGER trg_external; ALTER TABLE parents ADD COLUMN note TEXT;")
    assert kinds == {"missing_object", "trigger_behavior"}


def test_fk_connection_state_and_check_are_independent(tmp_path):
    path, spec, before = database(tmp_path, context="C1")
    _, kinds = changes(path, spec, before, "UPDATE children SET parent_id=999; ALTER TABLE parents ADD COLUMN note TEXT;", enforcement=0)
    assert kinds == {"content_digest", "foreign_key_check", "fk_enforcement"}


def test_missing_intended_change(tmp_path):
    path, spec, before = database(tmp_path)
    _, kinds = changes(path, spec, before, "SELECT 1")
    assert kinds == {"intended_change_missing"}


@pytest.mark.parametrize("operation,sql", [
    ("remove_column", "ALTER TABLE parents DROP COLUMN value"),
    ("rename_column", "ALTER TABLE parents RENAME COLUMN value TO renamed_value"),
    ("rename_table", "ALTER TABLE parents RENAME TO renamed_parents"),
    ("remove_index", "DROP INDEX idx_operation"),
])
def test_intentional_changes_are_not_losses(tmp_path, operation, sql):
    path, spec, before = database(tmp_path, operation)
    _, kinds = changes(path, spec, before, sql)
    assert kinds == set()


def test_type_conversion_preserves_normalized_values(tmp_path):
    path, spec, before = database(tmp_path, "change_type")
    _, kinds = changes(path, spec, before, """
        CREATE TABLE replacement(id INTEGER PRIMARY KEY,payload TEXT,value INTEGER,tenant_id INTEGER);
        INSERT INTO replacement SELECT * FROM parents;
        DROP TABLE parents;
        ALTER TABLE replacement RENAME TO parents;
        CREATE INDEX idx_declared ON parents(payload);
    """)
    assert kinds == set()


def test_error_classification_detects_committed_schema_and_data(tmp_path):
    path, spec, before = database(tmp_path)
    after, kinds = changes(path, spec, before, "BEGIN; UPDATE parents SET payload='lost'; ROLLBACK;")
    assert classify(False, kinds, before, after) == "failed-loudly"
    after, kinds = changes(path, spec, before, "CREATE TABLE leftover(id INTEGER PRIMARY KEY);")
    assert classify(False, kinds, before, after) == "failed-loudly-partial"
    assert classify(True, kinds, before, after) == "silent-loss"
    assert classify(True, [], before, before) == "preserved"


@pytest.mark.parametrize("operation,present", [("add_check_constraint", False), ("remove_check_constraint", True)])
def test_check_constraint_probe(tmp_path, operation, present):
    path, spec, before = database(tmp_path, operation)
    assert before["intended_probe"] == present
    assert not expected_present(before, spec["expected"])
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM parents").fetchone()[0] == 2


@pytest.mark.parametrize("operation,present", [("add_unique", False), ("drop_unique", True)])
def test_unique_constraint_probe(tmp_path, operation, present):
    spec, schema, seed = fixture("drizzle", operation, "C0")
    path = tmp_path / "tiny.db"
    create_database(path, schema, seed, True)
    before = observe(path, spec)
    probe_constraint(path, spec, before)
    assert before["intended_probe"] == present
    assert not expected_present(before, spec["expected"])


def test_deterministic_generator(tmp_path):
    first, _ = materialize(tmp_path / "a", "drizzle", "rename_table", "C4")
    second, _ = materialize(tmp_path / "b", "drizzle", "rename_table", "C4")
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {p.name: p.read_bytes() for p in second.iterdir()}


def test_missing_fk_definition_is_detected_without_orphans(tmp_path):
    path, spec, before = database(tmp_path, context="C8")
    _, kinds = changes(path, spec, before, """
        CREATE TABLE replacement(id INTEGER PRIMARY KEY,payload TEXT,value TEXT,tenant_id INTEGER,ancestor_id INTEGER,note TEXT);
        INSERT INTO replacement(id,payload,value,tenant_id,ancestor_id) SELECT * FROM parents;
        DROP TABLE parents;
        ALTER TABLE replacement RENAME TO parents;
        CREATE INDEX idx_declared ON parents(payload);
    """)
    assert kinds == {"foreign_key_definition"}


def test_empty_trigger_probe_and_safe_view(tmp_path):
    for context in ("C5", "C7"):
        spec, schema, seed = fixture("rails", "add_column", context)
        path = tmp_path / f"{context}.db"
        create_database(path, schema, seed, False)
        before = observe(path, spec)
        _, kinds = changes(path, spec, before, "ALTER TABLE parents ADD COLUMN note TEXT;")
        assert kinds == set()
        assert all(count == 0 for count in before["counts"].values())


@pytest.mark.parametrize("context", ["C1", "C5", "C7"])
def test_table_rename_maps_dependent_objects_and_foreign_keys(tmp_path, context):
    path, spec, before = database(tmp_path, "rename_table", context)
    _, kinds = changes(path, spec, before, "ALTER TABLE parents RENAME TO renamed_parents;")
    assert kinds == set()


def test_partial_commit_detects_value_only_damage(tmp_path):
    path, spec, before = database(tmp_path)
    after, kinds = changes(path, spec, before, "UPDATE parents SET value='lost' WHERE id=1;")
    assert before["counts"] == after["counts"]
    assert classify(False, kinds, before, after) == "failed-loudly-partial"


def test_digest_is_independent_of_insertion_order_and_preserves_blobs(tmp_path):
    path, spec, before = database(tmp_path)
    after, kinds = changes(path, spec, before, """
        DELETE FROM parents;
        INSERT INTO parents(id,payload,value,tenant_id) VALUES(2,'beta','22',2),(1,'alpha','11',1);
        ALTER TABLE parents ADD COLUMN note TEXT;
    """)
    assert not kinds
    assert before["content"]["parents"]["digest"] == after["content"]["parents"]["digest"]
    _, kinds = changes(path, spec, before, "UPDATE parents SET payload=x'0011' WHERE id=1;")
    assert kinds == {"content_digest"}


def test_table_without_id_is_compared_by_full_rows(tmp_path):
    path, spec, _ = database(tmp_path)
    with sqlite3.connect(path) as db:
        db.executescript("CREATE TABLE heap(payload TEXT); INSERT INTO heap VALUES('b'),('a');")
    spec["tables"].append("heap")
    spec["preserve"]["heap"] = ["payload"]
    before = observe(path, spec)
    probe_constraint(path, spec, before)
    assert before["content"]["heap"]["rows"] == [("a",), ("b",)]
    _, kinds = changes(path, spec, before, "UPDATE heap SET payload='changed' WHERE rowid=1; ALTER TABLE parents ADD COLUMN note TEXT;")
    assert kinds == {"content_digest"}


def test_unreadable_content_is_never_preserved(tmp_path):
    path, spec, before = database(tmp_path, context="C7")
    after, _ = changes(path, spec, before, "ALTER TABLE parents ADD COLUMN note TEXT;")
    assert violations(before, after, spec, {"foreign_keys_after": 1}) == []
    for section, name, kind in (("content", "parents", "content_digest"), ("view_rows", "parent_view", "view_rows")):
        unread_before = {**before, section: {**before[section], name: {"error": "no such column: id"}}}
        unread_after = {**after, section: {**after[section], name: {"error": "no such column: id"}}}
        found = violations(unread_before, unread_after, spec, {"foreign_keys_after": 1})
        assert kind in {v["kind"] for v in found}
