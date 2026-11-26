CREATE TABLE tenants (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE parents (id INTEGER PRIMARY KEY, tenant_id INTEGER, name TEXT DEFAULT 'a');
CREATE TABLE children (id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL REFERENCES parents(id) ON DELETE CASCADE, payload TEXT NOT NULL);
CREATE TABLE audit (id INTEGER PRIMARY KEY, message TEXT NOT NULL);
CREATE INDEX idx_parents_name ON parents(name);
CREATE INDEX idx_children_parent ON children(parent_id);
CREATE TRIGGER trg_children_update AFTER UPDATE ON children
BEGIN INSERT INTO audit(message) VALUES ('updated'); END;
CREATE VIEW child_payloads AS SELECT id, payload FROM children;

SELECT name FROM pragma_table_list WHERE schema <> 'temp' AND name NOT IN ('sqlite_sequence', 'sqlite_schema') AND name = 'schema_migrations' AND type IN ('table');
CREATE TABLE "schema_migrations" ("version" varchar NOT NULL PRIMARY KEY);
SELECT name FROM pragma_table_list WHERE schema <> 'temp' AND name NOT IN ('sqlite_sequence', 'sqlite_schema') AND name = 'ar_internal_metadata' AND type IN ('table');
CREATE TABLE "ar_internal_metadata" ("key" varchar NOT NULL PRIMARY KEY, "value" varchar, "created_at" datetime(6) NOT NULL, "updated_at" datetime(6) NOT NULL);
SELECT * FROM "ar_internal_metadata" WHERE "ar_internal_metadata"."key" = ? ORDER BY "ar_internal_metadata"."key" ASC LIMIT 1;
SELECT name FROM pragma_table_list WHERE schema <> 'temp' AND name NOT IN ('sqlite_sequence', 'sqlite_schema') AND type IN ('table','view');
WITH master AS (
  SELECT name, type, sql FROM sqlite_master
  UNION ALL
  SELECT name, type, sql FROM sqlite_temp_master
)

SELECT m.name AS table_name, CASE WHEN m.type = 'table' THEN m.sql END AS create_table_sql,
       t."name", t."type", t."notnull", t."dflt_value", t."pk", t."hidden"
FROM master m
JOIN pragma_table_xinfo(m.name) t
WHERE m.type IN ('table', 'view')
  AND m.name IN ('ar_internal_metadata')
ORDER BY m.name, t.cid
;
INSERT INTO "ar_internal_metadata" ("key", "value", "created_at", "updated_at") VALUES ('environment', 'default_env', '2026-10-09 21:00:07.457260', '2026-10-09 21:00:07.457262') RETURNING "key";
SELECT "schema_migrations"."version" FROM "schema_migrations" ORDER BY "schema_migrations"."version" ASC;
BEGIN immediate TRANSACTION;
ALTER TABLE "parents" ADD "note" text;
INSERT INTO "schema_migrations" ("version") VALUES ('20260101000001');
COMMIT TRANSACTION;
