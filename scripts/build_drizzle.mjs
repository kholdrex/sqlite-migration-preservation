import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const root = path.resolve(import.meta.dirname, '..');
const require = createRequire(path.join(root, 'runners/build-drizzle/package.json'));
const esbuild = require('esbuild');
const [kind, source, output] = process.argv.slice(2).map((value, index) => index ? path.resolve(value) : value);

if (kind === 'orm') {
  for (const [format, extension] of [['esm', '.js'], ['cjs', '.cjs']]) {
    await esbuild.build({
      absWorkingDir: path.dirname(source),
      entryPoints: [path.basename(source)],
      outfile: path.join(output, `sqlite-core/dialect${extension}`),
      bundle: true,
      format,
      platform: 'node',
      target: 'es2020',
      sourcemap: true,
      plugins: [{
        name: 'published-module-paths',
        setup(build) {
          build.onResolve({ filter: /^(~\/|\.\/)/ }, args => {
            if (args.kind === 'entry-point') return;
            const relative = args.path.startsWith('~/')
              ? path.posix.relative('sqlite-core', args.path.slice(2))
              : args.path;
            const specifier = relative.startsWith('.') ? relative : `./${relative}`;
            return { path: specifier.replace(/\.ts$/, extension), external: true };
          });
        },
      }],
    });
  }
} else if (kind === 'kit') {
  const pkg = JSON.parse(fs.readFileSync(path.join(source, 'package.json')));
  // Runtime entries and external drivers match the package's upstream build.ts.
  const drivers = ['pg', 'postgres', '@vercel/postgres', '@neondatabase/serverless',
    '@electric-sql/pglite', 'mysql2', '@planetscale/database', '@libsql/client',
    'better-sqlite3', 'bun:sqlite'];
  const common = {
    absWorkingDir: source,
    bundle: true,
    target: 'node16',
    platform: 'node',
    nodePaths: [path.join(root, 'runners/build-drizzle/node_modules')],
    external: ['esbuild', 'drizzle-orm', ...drivers],
  };
  for (const [entry, filename, format] of [
    ['utils', 'utils.js', 'cjs'], ['utils', 'utils.mjs', 'esm'],
    ['cli/index', 'bin.cjs', 'cjs'], ['index', 'index.js', 'cjs'],
    ['index', 'index.mjs', 'esm'], ['api', 'api.js', 'cjs'], ['api', 'api.mjs', 'esm'],
  ]) {
    await esbuild.build({
      ...common,
      entryPoints: [`src/${entry}.ts`],
      outfile: path.join(output, filename),
      format,
      ...(entry === 'utils' ? { external: [...common.external, 'commander', 'json-diff', 'glob'] } : {}),
      ...(entry === 'cli/index' ? { define: { 'process.env.DRIZZLE_KIT_VERSION': JSON.stringify(pkg.version) } } : {}),
      ...(['utils', 'cli/index'].includes(entry) ? { banner: { js: '#!/usr/bin/env node' } } : {}),
      ...(entry === 'api' && format === 'esm'
        ? { banner: { js: "import { createRequire } from 'module'; const require = createRequire(import.meta.url);" } } : {}),
      metafile: true,
    }).then(result => fs.writeFileSync(path.join(output, `${filename}.inputs.json`),
      JSON.stringify(result.metafile.inputs, null, 2) + '\n'));
  }
  const api = path.join(output, 'api.js');
  fs.writeFileSync(api, fs.readFileSync(api, 'utf8').replace(/await import\(/g, 'require('));
} else {
  throw new Error(`Unknown build: ${kind}`);
}
