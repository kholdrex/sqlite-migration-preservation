CREATE TABLE tenants (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE parents (id INTEGER PRIMARY KEY, tenant_id INTEGER, name TEXT DEFAULT 'a');
CREATE TABLE children (id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL REFERENCES parents(id) ON DELETE CASCADE, payload TEXT NOT NULL);
CREATE TABLE audit (id INTEGER PRIMARY KEY, message TEXT NOT NULL);
CREATE INDEX idx_parents_name ON parents(name);
CREATE INDEX idx_children_parent ON children(parent_id);
CREATE TRIGGER trg_children_update AFTER UPDATE ON children
BEGIN INSERT INTO audit(message) VALUES ('updated'); END;
CREATE VIEW child_payloads AS SELECT id, payload FROM children;


			CREATE TABLE IF NOT EXISTS "__drizzle_migrations" (
				id SERIAL PRIMARY KEY,
				hash text NOT NULL,
				created_at numeric
			)
		;
SELECT id, hash, created_at FROM "__drizzle_migrations" ORDER BY created_at DESC LIMIT 1;
PRAGMA foreign_keys;
PRAGMA foreign_keys=OFF;
BEGIN;

CREATE TEMP TABLE `__bak_children` AS SELECT * FROM `children`;

CREATE TABLE `__new_parents` (
	`id` integer PRIMARY KEY NOT NULL,
	`tenant_id` integer,
	`name` text DEFAULT 'a' NOT NULL
);

INSERT INTO `__new_parents`("id", "tenant_id", "name") SELECT "id", "tenant_id", "name" FROM `parents`;

DROP TABLE `parents`;

ALTER TABLE `__new_parents` RENAME TO `parents`;

INSERT OR REPLACE INTO `children` SELECT * FROM `__bak_children`;

DROP TABLE `__bak_children`;

CREATE INDEX `idx_parents_name` ON `parents` (`name`);
INSERT INTO "__drizzle_migrations" ("hash", "created_at") VALUES('7e95b9f79496e751ea70ebd6cf3e3c44'/*+32 bytes*/, 1791579601054.0);
COMMIT;
PRAGMA foreign_keys=ON;
