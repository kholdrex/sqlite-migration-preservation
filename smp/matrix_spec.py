"""Compact operation/context product; fixtures are materialized only in the run cache."""
import json
from pathlib import Path

CONTEXTS = {
    "C0": "none", "C1": "child ON DELETE CASCADE", "C2": "child ON DELETE SET NULL",
    "C3": "child ON DELETE RESTRICT", "C4": "two-level cascade", "C5": "external parent trigger",
    "C6": "external parent index", "C7": "parent view", "C8": "parent is a cascading child",
}
RAILS = {
    "add_column": "add_column :parents, :note, :text",
    "add_index": "add_index :parents, :value, name: 'idx_operation'",
    "remove_column": "remove_column :parents, :value",
    "rename_column": "rename_column :parents, :value, :renamed_value",
    "change_type": "change_column :parents, :value, :integer",
    "set_not_null": "change_column_null :parents, :value, false",
    "drop_not_null": "change_column_null :parents, :value, true",
    "change_default": "change_column_default :parents, :value, from: '5', to: '9'",
    "add_foreign_key": "add_foreign_key :parents, :tenants, column: :tenant_id",
    "remove_foreign_key": "remove_foreign_key :parents, :tenants, column: :tenant_id",
    "add_reference": "add_reference :parents, :owner, foreign_key: { to_table: :tenants }",
    "add_timestamps": "add_timestamps :parents, null: true",
    "add_check_constraint": "add_check_constraint :parents, 'CAST(value AS INTEGER) > 0', name: 'positive_value'",
    "remove_check_constraint": "remove_check_constraint :parents, name: 'positive_value'",
    "rename_table": "rename_table :parents, :renamed_parents",
    "remove_index": "remove_index :parents, name: 'idx_operation'",
}
DRIZZLE = ("add_column", "drop_column", "rename_column", "change_type", "set_not_null", "drop_not_null",
           "set_default", "drop_default", "add_foreign_key", "drop_foreign_key", "add_unique", "drop_unique",
           "add_index", "drop_index", "rename_table")


def cases():
    for framework, operations in (("rails", RAILS), ("drizzle", DRIZZLE)):
        for operation in operations:
            for context in CONTEXTS:
                yield framework, operation, context


def fixture(framework, operation, context):
    op, ctx = operation, context
    incoming = ctx in ("C1", "C2", "C3", "C4")
    # C8's FK is independent from the FK operated on in add/drop-FK trials.
    value = "value TEXT" + (" NOT NULL" if op == "drop_not_null" else "")
    if op in ("change_default", "drop_default"):
        value += " DEFAULT '5'"
    columns = ["id INTEGER PRIMARY KEY", "payload TEXT", value, "tenant_id INTEGER"]
    if ctx == "C8":
        columns.append("ancestor_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE")
    if op in ("remove_foreign_key", "drop_foreign_key"):
        columns.append("CONSTRAINT fk_tenant FOREIGN KEY(tenant_id) REFERENCES tenants(id)")
    if op == "remove_check_constraint":
        columns.append("CONSTRAINT positive_value CHECK (CAST(value AS INTEGER) > 0)")
    schema = "CREATE TABLE tenants(id INTEGER PRIMARY KEY, payload TEXT);\nCREATE TABLE parents(" + ", ".join(columns) + ");\n"
    schema += "CREATE INDEX idx_declared ON parents(payload);\n"
    if op == "drop_unique":
        schema += "CREATE UNIQUE INDEX parents_value_unique ON parents(value);\n"
    if op in ("remove_index", "drop_index"):
        schema += "CREATE INDEX idx_operation ON parents(value);\n"
    tables = ["tenants", "parents"]
    preserve = {"tenants": ["id", "payload"], "parents": ["id", "payload", "tenant_id"]}
    if op not in ("remove_column", "drop_column"):
        preserve["parents"].append("value")
    if ctx == "C8":
        preserve["parents"].append("ancestor_id")
    seed = "INSERT INTO tenants VALUES(1,'tenant-a'),(2,'tenant-b');\n"
    extra = ",ancestor_id" if ctx == "C8" else ""
    seed += f"INSERT INTO parents(id,payload,value,tenant_id{extra}) VALUES(1,'alpha','11',1{',1' if extra else ''}),(2,'beta','22',2{',2' if extra else ''});\n"
    action = {"C1": "CASCADE", "C2": "SET NULL", "C3": "RESTRICT", "C4": "CASCADE"}.get(ctx)
    if incoming:
        schema += f"CREATE TABLE children(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id) ON DELETE {action}, payload TEXT);\n"
        seed += "INSERT INTO children VALUES(1,1,'child-a'),(2,1,'child-b'),(3,2,'child-c');\n"
        tables.append("children")
        preserve["children"] = ["id", "parent_id", "payload"]
    if ctx == "C4":
        schema += "CREATE TABLE grandchildren(id INTEGER PRIMARY KEY, child_id INTEGER REFERENCES children(id) ON DELETE CASCADE, payload TEXT);\n"
        seed += "INSERT INTO grandchildren VALUES(1,1,'grand-a'),(2,2,'grand-b'),(3,3,'grand-c');\n"
        tables.append("grandchildren")
        preserve["grandchildren"] = ["id", "child_id", "payload"]
    if ctx == "C5":
        schema += "CREATE TABLE audit(id INTEGER PRIMARY KEY, parent_id INTEGER, message TEXT);\nCREATE TRIGGER trg_external AFTER UPDATE OF payload ON parents BEGIN INSERT INTO audit(parent_id,message) VALUES(NEW.id,NEW.payload); END;\n"
        tables.append("audit")
        preserve["audit"] = ["id", "parent_id", "message"]
    if ctx == "C6":
        schema += "CREATE INDEX idx_external ON parents(tenant_id);\n"
    if ctx == "C7":
        schema += "CREATE VIEW parent_view AS SELECT id,payload FROM parents;\n"
    spec = {"id": f"matrix_{framework}_{op}_{ctx}", "framework": framework, "operation": op, "context": ctx,
            "schema": "schema.sql", "seed": "seed.sql", "migration": "migrations", "before": "before.ts", "after": "after.ts",
            "tables": tables, "preserve": preserve, "views": ["parent_view"] if ctx == "C7" else [],
            "triggers": ["trg_external"] if ctx == "C5" else [], "removed_objects": []}
    def column(name, **attributes):
        return {"kind": "column", "table": "parents", "name": name, "attributes": attributes}
    if op == "add_column":
        expected = column("note")
    elif op in ("remove_column", "drop_column"):
        expected = {"kind": "absent_column", "table": "parents", "name": "value"}
    elif op == "rename_column":
        expected = {"kind": "all", "items": [column("renamed_value"), {"kind": "absent_column", "table": "parents", "name": "value"}]}
        spec["column_rename"] = {"value": "renamed_value"}
    elif op == "change_type":
        expected = column("value", type="INTEGER")
    elif op in ("set_not_null", "drop_not_null"):
        expected = column("value", notnull=int(op == "set_not_null"))
    elif op in ("change_default", "set_default", "drop_default"):
        expected = column("value", default=None if op == "drop_default" else "'9'")
    elif op == "add_foreign_key":
        expected = {"kind": "foreign_key", "table": "parents", "column": "tenant_id", "target": "tenants"}
    elif op in ("remove_foreign_key", "drop_foreign_key"):
        expected = {"kind": "absent_fk", "table": "parents", "column": "tenant_id"}
    elif op == "add_reference":
        expected = {"kind": "all", "items": [column("owner_id"), {"kind": "foreign_key", "table": "parents", "column": "owner_id", "target": "tenants"}]}
    elif op == "add_timestamps":
        expected = {"kind": "all", "items": [column("created_at"), column("updated_at")]}
    elif op in ("add_check_constraint", "remove_check_constraint", "add_unique", "drop_unique"):
        expected = {"kind": "unique" if "unique" in op else "check", "present": op.startswith("add")}
        if op == "drop_unique":
            spec["removed_objects"] = ["index:parents_value_unique"]
    elif op == "rename_table":
        spec["table_rename"] = {"parents": "renamed_parents"}
        expected = {"kind": "table", "name": "renamed_parents", "old": "parents"}
    elif op == "add_index":
        expected = {"kind": "index", "name": "idx_operation", "sql": "CREATE INDEX idx_operation ON parents(value)"}
    else:
        expected = {"kind": "absent_object", "object": "index:idx_operation"}
        spec["removed_objects"] = ["index:idx_operation"]
    spec["expected"] = expected
    return spec, schema, seed


def typescript(operation, context, after):
    op, ctx = operation, context
    table = "renamed_parents" if after and op == "rename_table" else "parents"
    value_name = "renamed_value" if after and op == "rename_column" else "value"
    value_type = "integer" if after and op == "change_type" else "text"
    value = f"{value_type}('{value_name}')"
    if (op == "drop_not_null" and not after) or (op == "set_not_null" and after):
        value += ".notNull()"
    if op == "drop_default" and not after:
        value += ".default('5')"
    if op == "set_default" and after:
        value += ".default('9')"
    if (op == "drop_unique" and not after) or (op == "add_unique" and after):
        value += ".unique()"
    cols = ["id: integer('id').primaryKey()", "payload: text('payload')"]
    if not (op == "drop_column" and after):
        cols.append(f"value: {value}")
    tenant = "tenantId: integer('tenant_id')"
    if (op == "drop_foreign_key" and not after) or (op == "add_foreign_key" and after):
        tenant += ".references(() => tenants.id)"
    cols.append(tenant)
    if ctx == "C8":
        cols.append("ancestorId: integer('ancestor_id').references(() => tenants.id, { onDelete: 'cascade' })")
    if op == "add_column" and after:
        cols.append("note: text('note')")
    indexes = ["index('idx_declared').on(t.payload)"]
    if (op == "drop_index" and not after) or (op == "add_index" and after):
        indexes.append("index('idx_operation').on(t.value)")
    source = "import { sqliteTable, integer, text, index } from 'drizzle-orm/sqlite-core';\n"
    source += "export const tenants = sqliteTable('tenants', { id: integer('id').primaryKey(), payload: text('payload') });\n"
    source += f"export const parents = sqliteTable('{table}', {{ {', '.join(cols)} }}, t => [{', '.join(indexes)}]);\n"
    action = {"C1": "cascade", "C2": "set null", "C3": "restrict", "C4": "cascade"}.get(ctx)
    if action:
        source += f"export const children = sqliteTable('children', {{ id: integer('id').primaryKey(), parentId: integer('parent_id').references(() => parents.id, {{ onDelete: '{action}' }}), payload: text('payload') }});\n"
    if ctx == "C4":
        source += "export const grandchildren = sqliteTable('grandchildren', { id: integer('id').primaryKey(), childId: integer('child_id').references(() => children.id, { onDelete: 'cascade' }), payload: text('payload') });\n"
    if ctx == "C5":
        source += "export const audit = sqliteTable('audit', { id: integer('id').primaryKey(), parentId: integer('parent_id'), message: text('message') });\n"
    return source


def materialize(root, framework, operation, context):
    spec, schema, seed = fixture(framework, operation, context)
    folder = Path(root) / spec["id"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "case.json").write_text(json.dumps(spec, indent=2) + "\n")
    (folder / "schema.sql").write_text(schema)
    (folder / "seed.sql").write_text(seed)
    if framework == "rails":
        (folder / "migrations").mkdir(exist_ok=True)
        (folder / "migrations/20260101000001_matrix_change.rb").write_text(
            "class MatrixChange < ActiveRecord::Migration[8.0]\n  def change\n    " + RAILS[operation] + "\n  end\nend\n")
    else:
        for after, revision in ((False, "before"), (True, "after")):
            (folder / f"{revision}.ts").write_text(typescript(operation, context, after))
    return folder, spec
