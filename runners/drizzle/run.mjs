import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const [runtime, database, migrations, output] = process.argv.slice(2);
const require = createRequire(path.join(runtime, 'package.json'));
const Database = require('better-sqlite3');
const { drizzle } = require('drizzle-orm/better-sqlite3');
const { migrate } = require('drizzle-orm/better-sqlite3/migrator');
const executed = [];
const sqlite = new Database(database, { verbose: sql => executed.push(sql) });
sqlite.pragma('foreign_keys = ON');
const version = name => JSON.parse(fs.readFileSync(path.join(runtime, 'node_modules', name, 'package.json'))).version;
const metadata = {
  node: process.version,
  'drizzle-orm': version('drizzle-orm'),
  'drizzle-kit': version('drizzle-kit'),
  'better-sqlite3': version('better-sqlite3'),
  sqlite: sqlite.prepare('SELECT sqlite_version()').pluck().get(),
  foreign_keys_before: sqlite.pragma('foreign_keys', { simple: true }),
};
executed.length = 0;
try {
  // drizzle-orm 1.x treats a positional argument as a connection config, not a client.
  const db = metadata['drizzle-orm'].startsWith('0.') ? drizzle(sqlite) : drizzle({ client: sqlite });
  await migrate(db, { migrationsFolder: migrations });
  metadata.success = true;
} catch (error) {
  metadata.success = false;
  metadata.error = `${error.name}: ${error.message}`;
}
fs.writeFileSync(path.join(output, 'executed.sql'), executed.map(sql => `${sql.replace(/;\s*$/, '')};\n`).join(''));
metadata.foreign_keys_after = sqlite.pragma('foreign_keys', { simple: true });
fs.writeFileSync(path.join(output, 'runner.json'), JSON.stringify(metadata, null, 2));
sqlite.close();
process.exitCode = metadata.success ? 0 : 1;
