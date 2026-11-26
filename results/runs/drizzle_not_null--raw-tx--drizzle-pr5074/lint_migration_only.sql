PRAGMA foreign_keys=OFF;--> statement-breakpoint
CREATE TEMP TABLE `__bak_children` AS SELECT * FROM `children`;--> statement-breakpoint
CREATE TABLE `__new_parents` (
	`id` integer PRIMARY KEY NOT NULL,
	`tenant_id` integer,
	`name` text DEFAULT 'a' NOT NULL
);
--> statement-breakpoint
INSERT INTO `__new_parents`("id", "tenant_id", "name") SELECT "id", "tenant_id", "name" FROM `parents`;--> statement-breakpoint
DROP TABLE `parents`;--> statement-breakpoint
ALTER TABLE `__new_parents` RENAME TO `parents`;--> statement-breakpoint
INSERT OR REPLACE INTO `children` SELECT * FROM `__bak_children`;--> statement-breakpoint
DROP TABLE `__bak_children`;--> statement-breakpoint
PRAGMA foreign_keys=ON;--> statement-breakpoint
CREATE INDEX `idx_parents_name` ON `parents` (`name`);