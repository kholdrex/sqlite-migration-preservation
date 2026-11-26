// Run the real synchronous migrator without importing project code.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const [runtime, driverRuntime, database, folder] = process.argv.slice(2);
const ormRequire = createRequire(path.join(runtime, 'package.json'));
const driverRequire = createRequire(path.join(driverRuntime, 'package.json'));
const Database = driverRequire('better-sqlite3');
const { drizzle } = ormRequire('drizzle-orm/better-sqlite3');
const { migrate } = ormRequire('drizzle-orm/better-sqlite3/migrator');
const events = [];
const db = new Database(database, { verbose: sql => {
  // Persist only transaction/pragma events, never interpolated application SQL.
  if (/^\s*(?:begin|commit|rollback|pragma)\b/i.test(sql)) events.push(sql);
}});
db.pragma('foreign_keys=ON');
const result = {
  node: process.version,
  sqlite: db.prepare('select sqlite_version()').pluck().get(),
  better_sqlite3: JSON.parse(fs.readFileSync(path.join(driverRuntime, 'node_modules/better-sqlite3/package.json'))).version,
  foreign_keys_before: db.pragma('foreign_keys', { simple: true }),
};
try {
  migrate(drizzle(db), { migrationsFolder: folder });
  result.success = true;
} catch (error) {
  result.success = false;
  // Drizzle wrappers include SQL; the underlying SQLite error is sufficient.
  const cause = error.cause || error;
  result.error = `${cause.code || cause.name}: ${cause.message}`.split('\n')[0];
}
result.foreign_keys_after = db.pragma('foreign_keys', { simple: true });
result.transaction_open_after = db.inTransaction;
result.events = events;
db.close();
process.stdout.write(JSON.stringify(result));
