
			CREATE TABLE IF NOT EXISTS "__drizzle_migrations" (
				id SERIAL PRIMARY KEY,
				hash text NOT NULL,
				created_at numeric
			)
		;
SELECT id, hash, created_at FROM "__drizzle_migrations" ORDER BY created_at DESC LIMIT 1;
BEGIN;
ALTER TABLE `parents` ADD `note` text;
INSERT INTO "__drizzle_migrations" ("hash", "created_at") VALUES('0b24eec491f2066ab54097e0c55db278'/*+32 bytes*/, 1791579591487.0);
COMMIT;
