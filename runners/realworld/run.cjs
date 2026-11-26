// Run the real synchronous migrator without importing project code.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const [runtime, driverRuntime, database, folder, evidenceFlag, target] = process.argv.slice(2);
const evidence = evidenceFlag === '--evidence';
const ormRequire = createRequire(path.join(runtime, 'package.json'));
const driverRequire = createRequire(path.join(driverRuntime, 'package.json'));
const Database = driverRequire('better-sqlite3');
const { drizzle } = ormRequire('drizzle-orm/better-sqlite3');
const { migrate } = ormRequire('drizzle-orm/better-sqlite3/migrator');
const events = [];
const trace = [];
const submitted = [];
let active = { origin: 'framework' };
const db = new Database(database, { verbose: sql => {
  if (evidence) trace.push({ sql, ...active });
  if (/^\s*(?:begin|commit|rollback|pragma)\b/i.test(sql)) events.push(sql);
}});
if (evidence) {
  // Only the pending migration runs, so its statements are matched in file order.
  const source = fs.readFileSync(path.join(folder, target), 'utf8');
  let offset = 0;
  const chunks = source.split('--> statement-breakpoint').map(sql => {
    const start = offset;
    offset += sql.length + '--> statement-breakpoint'.length;
    return { sql: sql.trim(), byte_start: Buffer.byteLength(source.slice(0, start)),
      byte_end: Buffer.byteLength(source.slice(0, start + sql.length)) };
  });
  let next = 0;
  const provenance = sql => {
    let index = chunks.findIndex((chunk, i) => i >= next && chunk.sql === sql.trim());
    if (index < 0) index = chunks.findIndex(chunk => chunk.sql === sql.trim());
    if (index < 0) return { origin: 'framework' };
    next = index + 1;
    return { origin: 'project', source: {
      file: target, byte_start: chunks[index].byte_start, byte_end: chunks[index].byte_end,
    } };
  };
  const prepare = db.prepare.bind(db);
  db.prepare = sql => {
    const context = provenance(sql);
    submitted.push({ sql, ...context });
    const statement = prepare(sql);
    for (const method of ['run', 'get', 'all']) {
      const execute = statement[method].bind(statement);
      statement[method] = (...args) => {
        active = context;
        try { return execute(...args); }
        finally { active = { origin: 'framework' }; }
      };
    }
    return statement;
  };
  const exec = db.exec.bind(db);
  db.exec = sql => {
    active = provenance(sql);
    submitted.push({ sql, ...active });
    try { return exec(sql); }
    finally { active = { origin: 'framework' }; }
  };
}
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
if (evidence) {
  result.trace = trace;
  result.submitted = submitted;
}
process.stdout.write(JSON.stringify(result));
