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
INSERT INTO "ar_internal_metadata" ("key", "value", "created_at", "updated_at") VALUES ('environment', 'default_env', '2026-10-09 23:39:55.992520', '2026-10-09 23:39:55.992521') RETURNING "key";
SELECT "schema_migrations"."version" FROM "schema_migrations" ORDER BY "schema_migrations"."version" ASC;
WITH master AS (
  SELECT name, type, sql FROM sqlite_master
  UNION ALL
  SELECT name, type, sql FROM sqlite_temp_master
)

SELECT m.name AS table_name, fk.id, fk.seq, fk."table", fk."from", fk."to", fk.on_update, fk.on_delete
FROM master m
JOIN pragma_foreign_key_list(m.name) fk
WHERE m.type = 'table'
  AND m.name IN ('parents')
;
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
  AND m.name IN ('parents')
ORDER BY m.name, t.cid
;
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
  AND m.name IN ('parents')
ORDER BY m.name, t.cid
;
SELECT sql FROM sqlite_master
WHERE type = 'trigger' AND tbl_name = 'parents'
UNION ALL
SELECT sql FROM sqlite_temp_master
WHERE type = 'trigger' AND tbl_name = 'parents'
;
SELECT name FROM sqlite_master WHERE type = 'table' AND name != 'parents';
PRAGMA foreign_key_list('tenants');
PRAGMA foreign_key_list('children');
BEGIN immediate TRANSACTION;
COMMIT TRANSACTION;
PRAGMA foreign_keys;
PRAGMA defer_foreign_keys;
PRAGMA defer_foreign_keys = ON;
PRAGMA foreign_keys = OFF;
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
  AND m.name IN ('parents')
ORDER BY m.name, t.cid
;
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
  AND m.name IN ('parents')
ORDER BY m.name, t.cid
;
SAVEPOINT active_record_1;
CREATE TEMPORARY TABLE "aparents" ("id" integer PRIMARY KEY AUTOINCREMENT NOT NULL, "tenant_id" integer, "name" text DEFAULT 'a');
WITH master AS (
  SELECT name, type, sql FROM sqlite_master
  UNION ALL
  SELECT name, type, sql FROM sqlite_temp_master
)

SELECT m.name AS table_name, i.name, i."unique"
FROM master m
JOIN pragma_index_list(m.name) i
WHERE m.type = 'table'
  AND m.name IN ('parents')
  AND i.name NOT GLOB 'sqlite_*'
;
WITH master AS (
  SELECT name, type, sql FROM sqlite_master
  UNION ALL
  SELECT name, type, sql FROM sqlite_temp_master
)

SELECT m.name AS index_name, m.sql, i.name
FROM master m
JOIN pragma_index_info(m.name) i
WHERE m.type = 'index'
  AND m.name IN ('idx_parents_name')
ORDER BY m.name, i.seqno
;
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
  AND m.name IN ('aparents')
ORDER BY m.name, t.cid
;
CREATE INDEX "tidx_aparents_name" ON "aparents" ("name");
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
  AND m.name IN ('parents')
ORDER BY m.name, t.cid
;
INSERT INTO "aparents" ("id","tenant_id","name")
                     SELECT "id","tenant_id","name" FROM "parents";
DROP TABLE "parents";
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
  AND m.name IN ('aparents')
ORDER BY m.name, t.cid
;
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
  AND m.name IN ('aparents')
ORDER BY m.name, t.cid
;
CREATE TABLE "parents" ("id" integer PRIMARY KEY AUTOINCREMENT NOT NULL, "tenant_id" integer, "name" text DEFAULT 'b');
WITH master AS (
  SELECT name, type, sql FROM sqlite_master
  UNION ALL
  SELECT name, type, sql FROM sqlite_temp_master
)

SELECT m.name AS table_name, i.name, i."unique"
FROM master m
JOIN pragma_index_list(m.name) i
WHERE m.type = 'table'
  AND m.name IN ('aparents')
  AND i.name NOT GLOB 'sqlite_*'
;
WITH master AS (
  SELECT name, type, sql FROM sqlite_master
  UNION ALL
  SELECT name, type, sql FROM sqlite_temp_master
)

SELECT m.name AS index_name, m.sql, i.name
FROM master m
JOIN pragma_index_info(m.name) i
WHERE m.type = 'index'
  AND m.name IN ('tidx_aparents_name')
ORDER BY m.name, i.seqno
;
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
  AND m.name IN ('parents')
ORDER BY m.name, t.cid
;
CREATE INDEX "idx_parents_name" ON "parents" ("name");
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
  AND m.name IN ('aparents')
ORDER BY m.name, t.cid
;
INSERT INTO "parents" ("id","tenant_id","name")
                     SELECT "id","tenant_id","name" FROM "aparents";
DROP TABLE "aparents";
RELEASE SAVEPOINT active_record_1;
PRAGMA defer_foreign_keys = 0;
PRAGMA foreign_keys = 1;
BEGIN immediate TRANSACTION;
INSERT INTO "schema_migrations" ("version") VALUES ('20260101000001');
COMMIT TRANSACTION;
