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
SELECT sql FROM sqlite_master
WHERE type = 'trigger' AND tbl_name = 'parents'
UNION ALL
SELECT sql FROM sqlite_temp_master
WHERE type = 'trigger' AND tbl_name = 'parents'
;
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