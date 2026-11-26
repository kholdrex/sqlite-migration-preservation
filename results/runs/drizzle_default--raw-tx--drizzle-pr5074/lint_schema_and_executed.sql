CREATE TABLE tenants (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE parents (id INTEGER PRIMARY KEY, tenant_id INTEGER, name TEXT DEFAULT 'a');
CREATE TABLE children (id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL REFERENCES parents(id) ON DELETE CASCADE, payload TEXT NOT NULL);
CREATE TABLE audit (id INTEGER PRIMARY KEY, message TEXT NOT NULL);
CREATE INDEX idx_parents_name ON parents(name);
CREATE INDEX idx_children_parent ON children(parent_id);
CREATE TRIGGER trg_children_update AFTER UPDATE ON children
BEGIN INSERT INTO audit(message) VALUES ('updated'); END;
CREATE VIEW child_payloads AS SELECT id, payload FROM children;

BEGIN;
PRAGMA foreign_keys=OFF;
--> statement-breakpoint
CREATE TEMP TABLE `__bak_children` AS SELECT * FROM `children`;
--> statement-breakpoint
CREATE TABLE `__new_parents` (
	`id` integer PRIMARY KEY NOT NULL,
	`tenant_id` integer,
	`name` text DEFAULT 'b'
);
--> statement-breakpoint
INSERT INTO `__new_parents`("id", "tenant_id", "name") SELECT "id", "tenant_id", "name" FROM `parents`;
--> statement-breakpoint
DROP TABLE `parents`;
--> statement-breakpoint
DROP TABLE `parents`;
--> statement-breakpoint
DROP TABLE `parents`;
--> statement-breakpoint
ALTER TABLE `__new_parents` RENAME TO `parents`;
--> statement-breakpoint
INSERT OR REPLACE INTO `children` SELECT * FROM `__bak_children`;
--> statement-breakpoint
DROP TABLE `__bak_children`;
--> statement-breakpoint
PRAGMA foreign_keys=ON;
--> statement-breakpoint
CREATE INDEX `idx_parents_name` ON `parents` (`name`);
COMMIT;
