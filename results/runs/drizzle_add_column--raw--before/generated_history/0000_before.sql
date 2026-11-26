CREATE TABLE `audit` (
	`id` integer PRIMARY KEY NOT NULL,
	`message` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `children` (
	`id` integer PRIMARY KEY NOT NULL,
	`parent_id` integer NOT NULL,
	`payload` text NOT NULL,
	FOREIGN KEY (`parent_id`) REFERENCES `parents`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `idx_children_parent` ON `children` (`parent_id`);--> statement-breakpoint
CREATE TABLE `parents` (
	`id` integer PRIMARY KEY NOT NULL,
	`tenant_id` integer,
	`name` text DEFAULT 'a'
);
--> statement-breakpoint
CREATE INDEX `idx_parents_name` ON `parents` (`name`);--> statement-breakpoint
CREATE TABLE `tenants` (
	`id` integer PRIMARY KEY NOT NULL,
	`name` text NOT NULL
);
