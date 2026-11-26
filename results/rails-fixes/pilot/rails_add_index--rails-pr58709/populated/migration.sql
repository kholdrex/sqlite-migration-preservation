SELECT name FROM pragma_table_list WHERE schema <> 'temp' AND name NOT IN ('sqlite_sequence', 'sqlite_schema') AND type IN ('table','view');
PRAGMA foreign_keys;
PRAGMA defer_foreign_keys;
PRAGMA defer_foreign_keys = ON;
PRAGMA foreign_keys = OFF;
CREATE INDEX "idx_parents_tenant" ON "parents" ("tenant_id");
PRAGMA defer_foreign_keys = 0;
PRAGMA foreign_keys = 1;