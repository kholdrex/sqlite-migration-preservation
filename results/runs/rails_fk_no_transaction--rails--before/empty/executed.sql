SELECT name FROM pragma_table_list WHERE schema <> 'temp' AND name NOT IN ('sqlite_sequence', 'sqlite_schema') AND name = 'schema_migrations' AND type IN ('table');
CREATE TABLE "schema_migrations" ("version" varchar NOT NULL PRIMARY KEY);
SELECT name FROM pragma_table_list WHERE schema <> 'temp' AND name NOT IN ('sqlite_sequence', 'sqlite_schema') AND name = 'ar_internal_metadata' AND type IN ('table');
CREATE TABLE "ar_internal_metadata" ("key" varchar NOT NULL PRIMARY KEY, "value" varchar, "created_at" datetime(6) NOT NULL, "updated_at" datetime(6) NOT NULL);
SELECT * FROM "ar_internal_metadata" WHERE "ar_internal_metadata"."key" = ? ORDER BY "ar_internal_metadata"."key" ASC LIMIT 1;
INSERT INTO "ar_internal_metadata" ("key", "value", "created_at", "updated_at") VALUES ('environment', 'default_env', '2026-10-09 03:44:11.449619', '2026-10-09 03:44:11.449621') RETURNING "key";
SELECT "schema_migrations"."version" FROM "schema_migrations" ORDER BY "schema_migrations"."version" ASC;
PRAGMA foreign_key_list('parents');
PRAGMA table_xinfo("parents");
SELECT sql FROM
  (SELECT * FROM sqlite_master UNION ALL
   SELECT * FROM sqlite_temp_master)
WHERE type = 'table' AND name = 'parents'
;
            SELECT sql
            FROM sqlite_master
            WHERE name = 'parents' AND type = 'table'
            UNION ALL
            SELECT sql
            FROM sqlite_temp_master
            WHERE name = 'parents' AND type = 'table'
;
BEGIN immediate TRANSACTION;
PRAGMA foreign_keys;
PRAGMA defer_foreign_keys;
PRAGMA defer_foreign_keys = ON;
PRAGMA foreign_keys = OFF;
PRAGMA table_xinfo("parents");
SELECT sql FROM
  (SELECT * FROM sqlite_master UNION ALL
   SELECT * FROM sqlite_temp_master)
WHERE type = 'table' AND name = 'parents'
;
PRAGMA table_xinfo("parents");
SELECT sql FROM
  (SELECT * FROM sqlite_master UNION ALL
   SELECT * FROM sqlite_temp_master)
WHERE type = 'table' AND name = 'parents'
;
CREATE TEMPORARY TABLE "aparents" ("id" integer PRIMARY KEY AUTOINCREMENT NOT NULL, "tenant_id" integer, "name" text DEFAULT 'a');
PRAGMA index_list("parents");
SELECT sql
FROM sqlite_master
WHERE name = 'idx_parents_name' AND type = 'index'
UNION ALL
SELECT sql
FROM sqlite_temp_master
WHERE name = 'idx_parents_name' AND type = 'index'
;
PRAGMA index_info('idx_parents_name');
PRAGMA table_xinfo("aparents");
SELECT sql FROM
  (SELECT * FROM sqlite_master UNION ALL
   SELECT * FROM sqlite_temp_master)
WHERE type = 'table' AND name = 'aparents'
;
CREATE INDEX "tidx_aparents_name" ON "aparents" ("name");
PRAGMA table_xinfo("parents");
SELECT sql FROM
  (SELECT * FROM sqlite_master UNION ALL
   SELECT * FROM sqlite_temp_master)
WHERE type = 'table' AND name = 'parents'
;
INSERT INTO "aparents" ("id","tenant_id","name")
                     SELECT "id","tenant_id","name" FROM "parents";
DROP TABLE "parents";
PRAGMA table_xinfo("aparents");
SELECT sql FROM
  (SELECT * FROM sqlite_master UNION ALL
   SELECT * FROM sqlite_temp_master)
WHERE type = 'table' AND name = 'aparents'
;
PRAGMA table_xinfo("aparents");
SELECT sql FROM
  (SELECT * FROM sqlite_master UNION ALL
   SELECT * FROM sqlite_temp_master)
WHERE type = 'table' AND name = 'aparents'
;
CREATE TABLE "parents" ("id" integer PRIMARY KEY AUTOINCREMENT NOT NULL, "tenant_id" integer, "name" text DEFAULT 'a', CONSTRAINT "fk_rails_ab0c47d6c3"
FOREIGN KEY ("tenant_id")
  REFERENCES "tenants" ("id")
);
PRAGMA index_list("aparents");
SELECT sql
FROM sqlite_master
WHERE name = 'tidx_aparents_name' AND type = 'index'
UNION ALL
SELECT sql
FROM sqlite_temp_master
WHERE name = 'tidx_aparents_name' AND type = 'index'
;
PRAGMA index_info('tidx_aparents_name');
PRAGMA table_xinfo("parents");
SELECT sql FROM
  (SELECT * FROM sqlite_master UNION ALL
   SELECT * FROM sqlite_temp_master)
WHERE type = 'table' AND name = 'parents'
;
CREATE INDEX "idx_parents_name" ON "parents" ("name");
PRAGMA table_xinfo("aparents");
SELECT sql FROM
  (SELECT * FROM sqlite_master UNION ALL
   SELECT * FROM sqlite_temp_master)
WHERE type = 'table' AND name = 'aparents'
;
INSERT INTO "parents" ("id","tenant_id","name")
                     SELECT "id","tenant_id","name" FROM "aparents";
DROP TABLE "aparents";
PRAGMA defer_foreign_keys = 0;
PRAGMA foreign_keys = 1;
COMMIT TRANSACTION;
INSERT INTO "schema_migrations" ("version") VALUES ('20260101000001') RETURNING "version";
