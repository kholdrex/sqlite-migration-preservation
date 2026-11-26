PRAGMA foreign_keys=OFF;--> statement-breakpoint
CREATE TABLE `__new_parents` (
	`id` integer PRIMARY KEY NOT NULL,
	`tenant_id` integer,
	`name` text DEFAULT 'b'
);
--> statement-breakpoint
INSERT INTO `__new_parents`("id", "tenant_id", "name") SELECT "id", "tenant_id", "name" FROM `parents`;--> statement-breakpoint
DROP TABLE `parents`;--> statement-breakpoint
ALTER TABLE `__new_parents` RENAME TO `parents`;--> statement-breakpoint
PRAGMA foreign_keys=ON;--> statement-breakpoint
CREATE INDEX `idx_parents_name` ON `parents` (`name`);