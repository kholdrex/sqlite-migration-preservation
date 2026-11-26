
			CREATE TABLE IF NOT EXISTS "__drizzle_migrations" (
				id SERIAL PRIMARY KEY,
				hash text NOT NULL,
				created_at numeric
			)
		;
SELECT id, hash, created_at FROM "__drizzle_migrations" ORDER BY created_at DESC LIMIT 1;
BEGIN;
PRAGMA foreign_keys=OFF;

CREATE TABLE `__new_parents` (
	`id` integer PRIMARY KEY NOT NULL,
	`tenant_id` integer,
	`name` text DEFAULT 'b'
);

INSERT INTO `__new_parents`("id", "tenant_id", "name") SELECT "id", "tenant_id", "name" FROM `parents`;

DROP TABLE `parents`;

ALTER TABLE `__new_parents` RENAME TO `parents`;

PRAGMA foreign_keys=ON;

CREATE INDEX `idx_parents_name` ON `parents` (`name`);
INSERT INTO "__drizzle_migrations" ("hash", "created_at") VALUES('9c82ce41ff6f1dba26ba9517112c61b9'/*+32 bytes*/, 1791579605584.0);
COMMIT;
