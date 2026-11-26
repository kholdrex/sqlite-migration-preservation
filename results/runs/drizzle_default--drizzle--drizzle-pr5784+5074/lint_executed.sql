
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
	`name` text DEFAULT 'b'
);

INSERT INTO `__new_parents`("id", "tenant_id", "name") SELECT "id", "tenant_id", "name" FROM `parents`;

DROP TABLE `parents`;

ALTER TABLE `__new_parents` RENAME TO `parents`;

INSERT OR REPLACE INTO `children` SELECT * FROM `__bak_children`;

DROP TABLE `__bak_children`;

CREATE INDEX `idx_parents_name` ON `parents` (`name`);
INSERT INTO "__drizzle_migrations" ("hash", "created_at") VALUES('d85b8d9b362963ebbff62ddb7f2c622a'/*+32 bytes*/, 1791579598382.0);
COMMIT;
PRAGMA foreign_keys=ON;
