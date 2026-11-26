import pytest

from smp.rebuild import rebuild, rebuilt_tables, recorded_rebuild

REPLACEMENT = """
CREATE TABLE `__new_parents` (`id` integer PRIMARY KEY, `value` text DEFAULT '9');
INSERT INTO `__new_parents`("id", "value") SELECT "id", "value" FROM `parents`;
DROP TABLE `parents`;
ALTER TABLE `__new_parents` RENAME TO `parents`;
"""
HOLDING = """
CREATE TEMPORARY TABLE "aparents" ("id" integer NOT NULL PRIMARY KEY, "value" text);
INSERT INTO "aparents" ("id","value") SELECT "id","value" FROM "parents";
DROP TABLE "parents";
CREATE TABLE "parents" ("id" integer NOT NULL PRIMARY KEY, "value" text DEFAULT '9');
INSERT INTO "parents" ("id","value") SELECT "id","value" FROM "aparents";
DROP TABLE "aparents";
"""
RENAMED_AWAY = """
ALTER TABLE parents RENAME TO parents_old;
CREATE TABLE parents(id INTEGER PRIMARY KEY, value TEXT);
INSERT INTO parents SELECT id, value FROM main.parents_old;
DROP TABLE parents_old;
"""


@pytest.mark.parametrize("sql", [REPLACEMENT, HOLDING, RENAMED_AWAY])
def test_rebuild_sequences_name_the_rebuilt_table(sql):
    assert rebuilt_tables(sql) == ["parents"]
    assert recorded_rebuild(sql)


@pytest.mark.parametrize("sql", [
    "CREATE TABLE audit(id); DROP TABLE old_queue;",
    'DROP TABLE "parents"; CREATE TABLE "renamed_parents" ("id" INTEGER PRIMARY KEY);',
    "CREATE TABLE copy AS SELECT * FROM parents; DROP TABLE unrelated;",
    "CREATE TABLE n(id); INSERT INTO n SELECT id FROM parents; DROP INDEX idx;",
])
def test_unrelated_create_and_drop_is_not_a_rebuild(sql):
    assert not rebuild(sql)


def test_failed_execution_counts_once_the_copied_table_is_dropped():
    statements = REPLACEMENT.strip().split("\n")
    assert not rebuild("\n".join(statements[:2]))
    assert rebuild("\n".join(statements[:3]))


def test_trigger_bodies_and_literals_are_not_statements():
    sql = """
    CREATE TRIGGER trg AFTER UPDATE ON parents BEGIN
      INSERT INTO audit SELECT NEW.id FROM parents; DELETE FROM audit WHERE id < 0;
    END;
    CREATE TABLE notes(id INTEGER, body TEXT DEFAULT 'DROP TABLE parents; -- kept');
    INSERT INTO notes SELECT id, 'x' FROM parents; -- DROP TABLE parents;
    """
    assert rebuilt_tables(sql) == []
    assert rebuilt_tables(sql + "DROP TABLE parents;") == ["parents"]
