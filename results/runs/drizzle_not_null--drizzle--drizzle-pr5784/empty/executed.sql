
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

CREATE TABLE `__new_parents` (
	`id` integer PRIMARY KEY NOT NULL,
	`tenant_id` integer,
	`name` text DEFAULT 'a' NOT NULL
);

INSERT INTO `__new_parents`("id", "tenant_id", "name") SELECT "id", "tenant_id", "name" FROM `parents`;

DROP TABLE `parents`;

ALTER TABLE `__new_parents` RENAME TO `parents`;

CREATE INDEX `idx_parents_name` ON `parents` (`name`);
INSERT INTO "__drizzle_migrations" ("hash", "created_at") VALUES('a887d0bf0b75b05bb0aca7b2f0be5357'/*+32 bytes*/, 1791579599259.0);
COMMIT;
PRAGMA foreign_keys=ON;
