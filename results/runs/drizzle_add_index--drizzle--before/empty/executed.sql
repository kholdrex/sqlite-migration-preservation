
			CREATE TABLE IF NOT EXISTS "__drizzle_migrations" (
				id SERIAL PRIMARY KEY,
				hash text NOT NULL,
				created_at numeric
			)
		;
SELECT id, hash, created_at FROM "__drizzle_migrations" ORDER BY created_at DESC LIMIT 1;
BEGIN;
CREATE INDEX `idx_parents_tenant` ON `parents` (`tenant_id`);
INSERT INTO "__drizzle_migrations" ("hash", "created_at") VALUES('794f8e1360c3e6f677cf9a4b8f52f53a'/*+32 bytes*/, 1791517434685.0);
COMMIT;
