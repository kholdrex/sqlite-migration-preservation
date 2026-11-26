"""Pinned public Drizzle histories, replayed locally with synthetic data only."""
import csv
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import tarfile
import time
import urllib.error
import tempfile
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .checks import canonical_sql, identifier, snapshot, statements, tokens_without_comments
from .environment import ROOT, local_env
from .preservation import digest
from .realworld_seed import SeedError, columns, foreign_keys, seed, tables

FALLBACK = '0.45.4'
PATHS = ('drizzle', 'raw', 'raw-tx')
IDENT = r'(?:`[^`]+`|"[^"]+"|\[[^]]+\]|[\w]+)'
CACHE = ROOT / '.cache' / 'realworld'
DRIVER = ROOT / 'runners' / 'drizzle' / 'current'


class Unreplayable(ValueError):
    pass


def command(args, cwd=None, timeout=120):
    result = subprocess.run(args, cwd=cwd or ROOT, env=local_env(), text=True,
                            capture_output=True, timeout=timeout)
    if result.returncode:
        # Do not retain remote output, which can contain arbitrary repository text.
        operation = next((a for a in args[1:] if a in ('fetch', 'checkout', 'show', 'pack', 'view')), 'execution')
        raise Unreplayable(f'{Path(args[0]).name} {operation} failed (exit {result.returncode})')
    return result.stdout


def github(repo):
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
        raise Unreplayable('invalid public GitHub repository name')
    cache = CACHE / 'metadata' / (repo.replace('/', '--') + '.json')
    if cache.exists():
        return json.loads(cache.read_text())
    endpoint = f'repos/{repo}'
    unavailable = CACHE / 'api-unavailable'
    use_api = not unavailable.exists() or time.time() - unavailable.stat().st_mtime > 3600
    if use_api and shutil.which('gh'):
        try:
            data = json.loads(command(['gh', 'api', endpoint]))
        except Unreplayable:
            data = None
    else:
        data = None
    if data is None and use_api:
        request = urllib.request.Request(f'https://api.github.com/{endpoint}', headers={'User-Agent': 'sqlite-migration-preservation'})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (403, 429):
                raise
            unavailable.touch()
    source = 'GitHub repository API'
    if data is None:
        # Public HTML carries exact counts in embedded JSON. Retain only the
        # requested metadata, never the page's README, names or profile data.
        request = urllib.request.Request(f'https://github.com/{repo}', headers={'User-Agent': 'sqlite-migration-preservation'})
        with urllib.request.urlopen(request, timeout=30) as response:
            page = response.read().decode()
        public = re.search(r'<meta\s+name="octolytics-dimension-repository_public"\s+content="true"', page)
        stars = re.search(r'"stargazerCount"\s*:\s*(\d+)', page)
        branch = re.search(r'"defaultBranch"\s*:\s*"([^"\\]+)"', page)
        license_match = re.search(r'"spdxId"\s*:\s*"([\w.+-]+)"', page)
        if not public or not stars:
            raise Unreplayable('public page does not expose verifiable visibility and exact star count')
        data = {'private': False, 'stargazers_count': int(stars[1]),
                'license': {'spdx_id': license_match[1]} if license_match else None,
                'fork': bool(re.search(r'<meta\s+name="octolytics-dimension-repository_is_fork"\s+content="true"', page)),
                'default_branch': branch[1] if branch else None}
        source = 'GitHub public repository page (API unavailable)'
    if data.get('private') is not False:
        raise Unreplayable('repository is not confirmed public')
    result = {'repo': repo, 'stars': data['stargazers_count'],
            'license': (data.get('license') or {}).get('spdx_id'),
            'metadata_observed_at': datetime.now(timezone.utc).isoformat(),
            'license_source': source + ' at observation time', 'metadata_source': source,
            'fork': data.get('fork', False), 'default_branch': data['default_branch']}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result))
    return result


def safe_path(value):
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or not value or '\\' in value:
        raise Unreplayable('unsafe migration path')
    return p


def repository(repo, targets, work, commit=None, metadata=None):
    """Fetch one shallow, blob-filtered detached revision; keep only migrations.

    Manifests/configs are read as data from selected blobs, never executed. The
    clone is removed before any history is replayed.
    """
    info = dict(metadata) if metadata is not None else github(repo)
    clone = work / 'clone'
    clone.mkdir()
    command(['git', 'init', '-q', str(clone)])
    command(['git', '-C', str(clone), 'remote', 'add', 'origin', f'https://github.com/{repo}.git'])
    command(['git', '-C', str(clone), 'config', 'remote.origin.promisor', 'true'])
    command(['git', '-C', str(clone), 'config', 'remote.origin.partialclonefilter', 'blob:none'])
    if commit and not re.fullmatch(r'[a-fA-F0-9]{40}', commit):
        raise Unreplayable('--commit must be a full 40-character SHA')
    ref = commit or 'HEAD'
    command(['git', '-C', str(clone), '-c', 'remote.origin.promisor=true', '-c', 'remote.origin.partialclonefilter=blob:none',
             'fetch', '--depth=1', '--filter=blob:none', 'origin', ref], timeout=180)
    sha = command(['git', '-C', str(clone), 'rev-parse', 'FETCH_HEAD']).strip()
    info['commit'] = sha
    tree = command(['git', '-C', str(clone), 'ls-tree', '-r', '--name-only', sha]).splitlines()
    folders = sorted({str(safe_path(t).parent) for t in targets})
    patterns = []
    for folder in folders:
        patterns += [f'/{folder}/*.sql', f'/{folder}/meta/_journal.json']
    command(['git', '-C', str(clone), 'sparse-checkout', 'init', '--no-cone'])
    (clone / '.git' / 'info' / 'sparse-checkout').write_text('\n'.join(patterns) + '\n')
    command(['git', '-C', str(clone), 'checkout', '--detach', sha], timeout=180)
    ancestors = {'.'}
    for folder in folders:
        ancestors.update(str(p) for p in PurePosixPath(folder).parents)
        ancestors.add(folder)
    manifests = [p for p in tree if PurePosixPath(p).name == 'package.json' and str(PurePosixPath(p).parent) in ancestors]
    configs = [p for p in tree if PurePosixPath(p).name in ('wrangler.toml', 'wrangler.json', 'wrangler.jsonc')
               and str(PurePosixPath(p).parent) in ancestors]
    evidence, packages = [], []
    for path in manifests:
        try:
            data = json.loads(command(['git', '-C', str(clone), 'show', f'{sha}:{path}']))
        except (ValueError, Unreplayable):
            continue
        deps = {**data.get('dependencies', {}), **data.get('devDependencies', {}), **data.get('optionalDependencies', {})}
        packages.append({'path': path, 'drizzle_orm': deps.get('drizzle-orm'), 'license': data.get('license')})
        for name in ('better-sqlite3', '@libsql/client', '@libsql/hrana-client', 'wrangler', '@cloudflare/workers-types', 'bun-types', '@types/bun'):
            if name in deps:
                evidence.append({'path': path, 'dependency': name, 'version': deps[name]})
        scripts = ' '.join(str(s) for s in data.get('scripts', {}).values())
        if re.search(r'\bbun\b', scripts):
            evidence.append({'path': path, 'runtime_hint': 'bun scripts; bun:sqlite not confirmed'})
    for path in configs:
        config = command(['git', '-C', str(clone), 'show', f'{sha}:{path}'])
        if re.search(r'\bd1_databases\b', config):
            evidence.append({'path': path, 'runtime_hint': 'Cloudflare D1 binding'})
    info['packages'] = packages
    info['runtime_evidence'] = evidence
    labels = []
    if any(e.get('runtime_hint') == 'Cloudflare D1 binding' for e in evidence):
        labels.append('D1 (binding)')
    elif any(e.get('dependency') in ('wrangler', '@cloudflare/workers-types') for e in evidence):
        labels.append('Cloudflare tooling; D1 unconfirmed')
    if any(e.get('dependency', '').startswith('@libsql/') for e in evidence):
        labels.append('libSQL dependency')
    if any(e.get('dependency') == 'better-sqlite3' for e in evidence):
        labels.append('better-sqlite3 dependency')
    if any('bun' in e.get('runtime_hint', '') or e.get('dependency') in ('bun-types', '@types/bun') for e in evidence):
        labels.append('Bun tooling; bun:sqlite unconfirmed')
    info['runtime'] = '; '.join(labels) or 'unknown from ancestor manifests/configs'
    info['runtime_scope'] = 'Dependencies/configuration are hints, not proof of the production adapter; no project code or D1 executed.'
    info['license_files'] = []
    for path in tree:
        if '/' not in path and re.match(r'^(LICENSE|LICENCE|COPYING)(\.|$)', path, re.I):
            blob = command(['git', '-C', str(clone), 'rev-parse', f'{sha}:{path}']).strip()
            info['license_files'].append({'path': path, 'blob_sha': blob})
    pinned_licenses = sorted({p['license'] for p in packages if isinstance(p.get('license'), str)})
    info['pinned_manifest_licenses'] = pinned_licenses
    extracted = work / 'extracted'
    for folder in folders:
        source = clone / folder
        if source.exists():
            for path in source.rglob('*'):
                if path.is_symlink():
                    raise Unreplayable('symlink in migration extraction')
                if path.is_file() and (path.suffix == '.sql' or path.name == '_journal.json'):
                    dest = extracted / path.relative_to(clone)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, dest)
    info['clone_bytes'] = sum(p.stat().st_size for p in clone.rglob('*') if p.is_file())
    shutil.rmtree(clone)
    return info, extracted


def orm_runtime(info, migration, work, override=None):
    parent = PurePosixPath(migration).parent
    eligible = [p for p in info['packages'] if p['drizzle_orm'] and
                (PurePosixPath(p['path']).parent in (parent, *parent.parents))]
    eligible.sort(key=lambda p: len(PurePosixPath(p['path']).parts), reverse=True)
    declared = eligible[0]['drizzle_orm'] if eligible else None
    result = {'declared': declared, 'package': eligible[0]['path'] if eligible else None,
              'fallback': False, 'fallback_reason': None}
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', declared or '')
    version = override or ('.'.join(match.groups()) if match else FALLBACK)
    if not match and not override:
        result.update(fallback=True, fallback_reason='no resolvable major/minor in ancestor package.json')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[\w.-]+)?', version):
        raise Unreplayable('invalid ORM version override')
    if version == FALLBACK:
        result['resolved'] = FALLBACK
        return DRIVER, result
    runtime = work / ('orm-' + version)
    runtime.mkdir(exist_ok=True)
    (runtime / 'package.json').write_text('{"private":true}')
    try:
        # Registry tarballs only: no project dependencies or lifecycle scripts.
        packed = json.loads(command(['npm', 'pack', f'drizzle-orm@{version}', '--ignore-scripts', '--json',
                                     '--pack-destination', str(runtime)], timeout=120))
        archive = runtime / packed[0]['filename']
        dest = runtime / 'node_modules' / 'drizzle-orm'
        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                parts = PurePosixPath(member.name).parts
                if not parts or parts[0] != 'package' or '..' in parts or member.issym() or member.islnk():
                    raise Unreplayable('unsafe npm archive')
                if member.isfile():
                    target = dest.joinpath(*parts[1:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(tar.extractfile(member).read())
        archive.unlink()
        (runtime / 'node_modules' / 'better-sqlite3').symlink_to(DRIVER / 'node_modules' / 'better-sqlite3', target_is_directory=True)
        result.update(resolved=version, registry_integrity=packed[0].get('integrity'))
        # Verify that this release actually provides the adapter entry points.
        command(['node', '-e', "require(process.argv[1]+'/node_modules/drizzle-orm/better-sqlite3/migrator.cjs')", str(runtime)])
        command(['node', '-e', "require(process.argv[1]+'/node_modules/drizzle-orm/better-sqlite3/index.cjs')", str(runtime)])
        return runtime, result
    except (Unreplayable, subprocess.TimeoutExpired, OSError, ValueError):
        shutil.rmtree(runtime, ignore_errors=True)
        if override:
            # A requested or recorded version is the experiment; another release would be a different one.
            raise Unreplayable(f'drizzle-orm {version} registry package or synchronous adapter unavailable')
        if match:
            try:
                minor = '.'.join(match.groups()[:2])
                available = json.loads(command(['npm', 'view', f'drizzle-orm@{minor}', 'version', '--json']))
                available = available if isinstance(available, list) else [available]
                compatible = [v for v in available if re.fullmatch(re.escape(minor) + r'\.\d+', v) and v != version]
                if compatible:
                    selected = max(compatible, key=lambda v: int(v.split('.')[2]))
                    recovered, metadata = orm_runtime(info, migration, work, selected)
                    metadata['same_minor_recovery_from'] = version
                    return recovered, metadata
            except (Unreplayable, subprocess.TimeoutExpired, ValueError, TypeError):
                pass
        result.update(resolved=FALLBACK, fallback=True,
                      fallback_reason=f'drizzle-orm {version} registry package or synchronous adapter unavailable')
        return DRIVER, result


def validate_sql(sql):
    for statement in statements(sql):
        clean = tokens_without_comments(statement).strip()
        if not clean:
            continue
        if re.search(r'\b(?:load_extension|readfile|writefile)\s*\(', clean, re.I):
            raise Unreplayable('SQL file/extension access is outside local replay scope')
        if not re.match(r'^(?:CREATE|ALTER|DROP|INSERT|UPDATE|DELETE|PRAGMA|BEGIN|COMMIT|END|ROLLBACK|SELECT|WITH)\b', clean, re.I):
            raise Unreplayable('unsupported SQL statement (file access and attachments are prohibited)')
        lexical = canonical_sql(clean)
        if re.match(r'INSERT\b', clean, re.I) and ('values' in lexical or 'from' not in lexical):
            raise Unreplayable('literal INSERT seed records excluded by synthetic-only policy')
        if re.match(r'(?:SELECT|WITH)\b', clean, re.I):
            raise Unreplayable('standalone SELECT/WITH requires manual review')
        if re.match(r'PRAGMA\b', clean, re.I) and not re.match(r'PRAGMA\s+(?:foreign_keys|defer_foreign_keys|legacy_alter_table)\s*(?:=|\()', clean, re.I):
            raise Unreplayable('unsupported PRAGMA')


def rebuilds(sql):
    aliases, rebuilt = {}, set()
    for statement in statements(tokens_without_comments(sql)):
        rename = re.search(r'ALTER\s+TABLE\s+(' + IDENT + r')\s+RENAME\s+TO\s+(' + IDENT + ')', statement, re.I)
        if rename:
            old, new = (v.strip('`"[]') for v in rename.groups())
            aliases[new] = aliases.get(old, old)
        insert = re.search(r'INSERT\s+INTO\s+(' + IDENT + ')', statement, re.I)
        if insert and insert[1].strip('`"[]').startswith('__new_'):
            # A transformation may SELECT from a different table. The __new_
            # target (and any preceding rename) identifies what is rebuilt.
            name = insert[1].strip('`"[]')[6:]
            rebuilt.add(aliases.get(name, name))
            aliases[insert[1].strip('`"[]')] = aliases.get(name, name)
    return sorted(rebuilt)


def raw(database, sql, transactional=False, reference=False, evidence=None):
    db = sqlite3.connect(database, isolation_level=None)
    if evidence is not None:
        db.set_trace_callback(evidence.callback)
    db.execute('PRAGMA foreign_keys=' + ('OFF' if reference else 'ON'))
    result = {'sqlite': sqlite3.sqlite_version, 'foreign_keys_before': db.execute('PRAGMA foreign_keys').fetchone()[0], 'events': []}
    try:
        if transactional:
            db.execute('BEGIN')
            result['events'].append('BEGIN')
        for statement in statements(sql):
            clean = tokens_without_comments(statement).strip()
            if reference and re.match(r'PRAGMA\s+foreign_keys\b', clean, re.I):
                continue
            if evidence is not None:
                evidence.submit(statement)
            try:
                db.execute(statement)
            finally:
                if evidence is not None:
                    evidence.origin = 'framework'
            if re.match(r'^(?:PRAGMA|BEGIN|COMMIT|ROLLBACK)\b', clean, re.I):
                result['events'].append(clean)
        if transactional:
            db.execute('COMMIT')
            result['events'].append('COMMIT')
        result['success'] = True
    except sqlite3.Error as exc:
        result.update(success=False, error=str(exc))
        if db.in_transaction:
            db.execute('ROLLBACK')
            result['events'].append('ROLLBACK')
    result['foreign_keys_after'] = db.execute('PRAGMA foreign_keys').fetchone()[0]
    db.close()
    return result


def content(database):
    with sqlite3.connect(database) as db:
        names = tables(db)
        state = snapshot(database, names)
        state['objects'] = {k: v for k, v in state['objects'].items()
                            if not v['table'].startswith('__drizzle_')}
        state['content'] = {}
        for table in names:
            cols = [c['name'] for c in columns(db, table)]
            rows = db.execute(f'SELECT {",".join(map(identifier, cols))} FROM {identifier(table)}').fetchall()
            rows.sort(key=lambda row: json.dumps(row, default=lambda b: {'blob': b.hex()}))
            state['content'][table] = {'columns': cols, 'rows': rows, 'digest': digest(rows)}
        state['view_rows'] = {}
        for key, obj in state['objects'].items():
            if obj['type'] == 'view':
                try:
                    rows = db.execute(f'SELECT * FROM {identifier(obj["name"])}').fetchall()
                    rows.sort(key=lambda row: json.dumps(row, default=lambda b: {'blob': b.hex()}))
                    state['view_rows'][key] = digest(rows)
                except sqlite3.Error:
                    state['view_rows'][key] = None
        state['state_digest'] = digest([state['content'], state['objects'], state['foreign_keys']])
        return state


def compare(before, expected, after, sql, execution):
    findings = []
    for table, data in expected['content'].items():
        actual = after['content'].get(table)
        if expected['counts'][table] != after['counts'].get(table):
            findings.append({'kind': 'row_count', 'table': table, 'before': before['counts'].get(table),
                             'expected': expected['counts'][table], 'after': after['counts'].get(table)})
        if actual is None or actual['columns'] != data['columns'] or actual['digest'] != data['digest']:
            findings.append({'kind': 'content_digest', 'table': table,
                             'columns': data['columns'], 'expected_synthetic_rows': data['rows'],
                             'actual_synthetic_rows': actual['rows'] if actual else None})
    for key, obj in expected['objects'].items():
        current = after['objects'].get(key)
        if current is None:
            findings.append({'kind': 'missing_object', 'object': key})
        elif canonical_sql(current['sql']) != canonical_sql(obj['sql']):
            findings.append({'kind': 'changed_object', 'object': key})
    # DROP TABLE can implicitly erase indexes/triggers even with FKs disabled.
    # An explicit DROP or CREATE of that object counts as an intended schema edit.
    clean = tokens_without_comments(sql)
    for key, obj in before['objects'].items():
        if obj['sql'] is None or key in after['objects']:
            continue
        if obj['table'] not in expected['counts'] and obj['table'] not in rebuilds(sql):
            # Objects belonging to an intentionally removed table are removed too.
            continue
        name = re.escape(obj['name'])
        explicit = re.search(r'\b(?:DROP|CREATE)\s+(?:UNIQUE\s+)?' + obj['type'] +
                             r'\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?["`\[]?' + name + r'(?:["`\]]|\b)', clean, re.I)
        if not explicit and not any(f.get('object') == key for f in findings):
            findings.append({'kind': 'implicit_object_loss', 'object': key})
    for table, fks in expected['foreign_keys'].items():
        if sorted((r[2:] for r in fks), key=str) != sorted((r[2:] for r in after['foreign_keys'].get(table, [])), key=str):
            findings.append({'kind': 'foreign_key_definition', 'table': table})
    for key in ('foreign_key_check', 'errors', 'view_errors'):
        if after[key]:
            findings.append({'kind': key, 'details': after[key]})
    if after['integrity_check'] != ['ok']:
        findings.append({'kind': 'integrity_check', 'details': after['integrity_check']})
    for name, value in expected['view_rows'].items():
        if after['view_rows'].get(name) != value:
            findings.append({'kind': 'view_rows', 'object': name})
    # Column metadata and objects compare the intended post-migration schema.
    if expected['columns'] != after['columns']:
        findings.append({'kind': 'intended_change_missing'})
    if execution.get('foreign_keys_after') != 1:
        findings.append({'kind': 'fk_enforcement'})
    return findings


def dependencies(database, rebuilt):
    result = []
    with sqlite3.connect(database) as db:
        for table in tables(db):
            for fk in foreign_keys(db, table):
                if fk[0][2] in rebuilt:
                    cols = [r[3] for r in fk]
                    condition = ' AND '.join(f'{identifier(c)} IS NOT NULL' for c in cols)
                    result.append({'parent': fk[0][2], 'child': table, 'columns': cols,
                                   'on_delete': fk[0][6], 'on_update': fk[0][5],
                                   'seeded_references': db.execute(f'SELECT count(*) FROM {identifier(table)} WHERE {condition}').fetchone()[0]})
    return result


def clean_error(error):
    # SQLite can echo CHECK bodies; redact quoted literals and limit diagnostics.
    return re.sub(r"'(?:''|[^'])*'", "'<literal>'", str(error).split('\n')[0])[:700]


def replay(info, extracted, target, search_blob, runtime, version, work, rows_per_table, evidence=None):
    row = {**info, 'migration_file': target, 'search_blob_sha': search_blob,
           'orm': version, 'rebuilt_tables': [], 'dependents': [], 'paths': {}, 'status': 'unreplayable'}
    try:
        folder = extracted / safe_path(target).parent
        migration = extracted / target
        if not migration.is_file():
            raise Unreplayable('migration file absent at pinned commit')
        sql = migration.read_text()
        row['migration_sha256'] = hashlib.sha256(sql.encode()).hexdigest()
        actual_blob = hashlib.sha1(b'blob ' + str(len(sql.encode())).encode() + b'\0' + sql.encode()).hexdigest()
        row['migration_blob_sha'] = actual_blob
        row['search_blob_matches'] = actual_blob == search_blob if search_blob else None
        row['rebuilt_tables'] = rebuilds(sql)
        if not row['rebuilt_tables']:
            raise Unreplayable('no __new_ table rebuild at pinned commit')
        journal_path = folder / 'meta' / '_journal.json'
        if not journal_path.is_file():
            raise Unreplayable('missing journal; custom migrator or different migration layout cannot be assumed')
        journal = json.loads(journal_path.read_text())
        if journal.get('dialect') != 'sqlite':
            raise Unreplayable('non-SQLite journal dialect')
        entries = journal['entries']
        matches = [i for i, e in enumerate(entries) if e['tag'] + '.sql' == migration.name]
        if len(matches) != 1:
            raise Unreplayable('migration absent or duplicated in journal')
        index = matches[0]
        relevant = entries[:index + 1]
        if index and relevant[-1]['when'] <= max(e['when'] for e in relevant[:-1]):
            raise Unreplayable('target timestamp is not newer than historical prefix; migrate() would skip target')
        row['journal_index'] = index
        row['history'] = []
        database = work / 'baseline.db'
        with sqlite3.connect(database, isolation_level=None) as db:
            if evidence is not None:
                evidence.stage = 'history'
                db.set_trace_callback(evidence.setup.callback)
            db.execute('PRAGMA foreign_keys=ON')
            for entry in relevant[:-1]:
                tag = str(safe_path(entry['tag']))
                prior = folder / (tag + '.sql')
                if not prior.is_file():
                    raise Unreplayable(f'missing historical migration: {tag}.sql')
                prior_sql = prior.read_text()
                validate_sql(prior_sql)
                try:
                    for statement in statements(prior_sql):
                        if evidence is not None:
                            evidence.setup.submit(statement, str(prior.relative_to(extracted)))
                        try:
                            db.execute(statement)
                        finally:
                            if evidence is not None:
                                evidence.setup.origin = 'framework'
                except sqlite3.Error as exc:
                    raise Unreplayable(f'history {tag}.sql: {clean_error(exc)}') from exc
                row['history'].append({'file': tag + '.sql', 'sha256': hashlib.sha256(prior_sql.encode()).hexdigest(), 'when': entry['when']})
            if db.in_transaction:
                raise Unreplayable('history leaves an open transaction')
            try:
                if evidence is not None:
                    evidence.stage = 'seed'
                row['seed_counts'] = seed(db, rows_per_table)
            except (SeedError, sqlite3.Error) as exc:
                raise Unreplayable('seeding failed: ' + clean_error(exc)) from exc
        row['dependents'] = dependencies(database, row['rebuilt_tables'])
        row['qualifying_parent_rebuild'] = any(d['on_delete'] in ('CASCADE', 'SET NULL') and d['seeded_references'] for d in row['dependents'])
        row['control_no_dependents'] = not row['dependents']
        validate_sql(sql)
        before = content(database)
        if before['foreign_key_check'] or before['integrity_check'] != ['ok'] or before['view_errors']:
            raise Unreplayable('baseline invariants fail before target migration')
        reference_db = work / 'reference.db'
        shutil.copyfile(database, reference_db)
        if evidence is not None:
            evidence.stage = 'reference'
            evidence.start('reference', reference_db)
        reference_execution = raw(reference_db, sql, reference=True,
                                  evidence=evidence.traces['reference'] if evidence is not None else None)
        if evidence is not None:
            evidence.finish('reference', reference_db)
        expected = content(reference_db) if reference_execution['success'] else before
        row['reference'] = {'success': reference_execution['success'], 'counts': expected['counts']}
        if not reference_execution['success']:
            row['reference']['error'] = clean_error(reference_execution.get('error', 'unknown'))
        # Supply the full historical journal to the real migrator and mark the
        # already-applied prefix with its actual timestamps and content hashes.
        migration_folder = work / 'migrate'
        (migration_folder / 'meta').mkdir(parents=True)
        (migration_folder / 'meta' / '_journal.json').write_text(json.dumps({**journal, 'entries': relevant}))
        for entry in relevant:
            source = folder / (str(safe_path(entry['tag'])) + '.sql')
            dest = migration_folder / (entry['tag'] + '.sql')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        for path in PATHS:
            trial = work / (path + '.db')
            shutil.copyfile(database, trial)
            try:
                if path == 'drizzle':
                    with sqlite3.connect(trial) as db:
                        if evidence is not None:
                            db.set_trace_callback(evidence.journal_setup.callback)
                        db.execute('CREATE TABLE __drizzle_migrations (id SERIAL PRIMARY KEY, hash text NOT NULL, created_at numeric)')
                        for entry in row['history']:
                            db.execute('INSERT INTO __drizzle_migrations(hash,created_at) VALUES (?,?)', (entry['sha256'], entry['when']))
                    if evidence is not None:
                        evidence.start(path, trial)
                    execution = json.loads(command(['node', str(ROOT / 'runners/realworld/run.cjs'), str(runtime), str(DRIVER), str(trial), str(migration_folder)] +
                                                   (['--evidence', migration.name] if evidence is not None else [])))
                    if evidence is not None:
                        evidence.drizzle(execution.pop('trace'), execution.pop('submitted'))
                    with sqlite3.connect(trial) as db:
                        recorded = db.execute('SELECT count(*) FROM __drizzle_migrations WHERE created_at=?', (relevant[-1]['when'],)).fetchone()[0]
                    execution['target_journal_records'] = recorded
                    if execution['success'] and recorded != 1:
                        raise Unreplayable('migrate() returned without recording the target migration')
                else:
                    if evidence is not None:
                        evidence.start(path, trial)
                    execution = raw(trial, sql, transactional=path == 'raw-tx',
                                    evidence=evidence.traces[path] if evidence is not None else None)
                if 'error' in execution:
                    execution['error'] = clean_error(execution['error'])
                after = content(trial)
                findings = compare(before, expected, after, sql, execution)
                outcome = ('silent-loss' if findings else 'preserved') if execution['success'] else 'loud'
                if execution['success'] and not reference_execution['success']:
                    outcome = 'unreplayable'
                    execution['assessment_error'] = 'reference migration failed; intended state unavailable'
                row['paths'][path] = {'outcome': outcome, 'execution': execution, 'findings': findings,
                                      'counts_after': after['counts'], 'foreign_key_check': after['foreign_key_check'],
                                      'integrity_check': after['integrity_check'],
                                      'state_changed': before['state_digest'] != after['state_digest']}
            except (Unreplayable, subprocess.TimeoutExpired, ValueError, sqlite3.Error) as exc:
                row['paths'][path] = {'outcome': 'unreplayable', 'reason': clean_error(exc)}
            finally:
                if evidence is not None and path in evidence.paths:
                    evidence.finish(path, trial)
        row['status'] = 'replayed' if any(p['outcome'] != 'unreplayable' for p in row['paths'].values()) else 'unreplayable'
    except (Unreplayable, sqlite3.Error, OSError, ValueError, KeyError, IndexError) as exc:
        row['reason'] = clean_error(exc)
        for path in PATHS:
            row['paths'].setdefault(path, {'outcome': 'unreplayable', 'reason': row['reason']})
    return row


def summary(rows):
    replayed = [r for r in rows if r['status'] == 'replayed']
    qualifying = [r for r in replayed if r.get('qualifying_parent_rebuild')]
    return {'repositories_attempted': len({r['repo'] for r in rows}), 'migrations_attempted': len(rows),
            'migrations_replayed': len(replayed), 'qualifying_migrations_replayed': len(qualifying),
            'qualifying_repositories': len({r['repo'] for r in qualifying}),
            'qualifying_distinct_migration_hashes': len({r['migration_sha256'] for r in qualifying}),
            'controls_replayed': sum(r.get('control_no_dependents', False) for r in replayed),
            'path_outcomes': {p: dict(Counter(r['paths'].get(p, {}).get('outcome', 'unreplayable') for r in rows)) for p in PATHS},
            'qualifying_path_outcomes': {p: dict(Counter(r['paths'].get(p, {}).get('outcome', 'unreplayable') for r in qualifying)) for p in PATHS},
            'control_path_outcomes': {p: dict(Counter(r['paths'].get(p, {}).get('outcome', 'unreplayable') for r in replayed if r.get('control_no_dependents'))) for p in PATHS},
            'search_blob_mismatches': sum(r.get('search_blob_matches') is False for r in rows),
            'unreplayable_reasons': dict(Counter(r.get('reason', 'all execution paths unavailable') for r in rows if r['status'] == 'unreplayable'))}


def write_report(output, result):
    result['summary'] = summary(result['rows'])
    output.mkdir(parents=True, exist_ok=True)
    temporary = output / 'realworld.json.tmp'
    temporary.write_text(json.dumps(result, indent=2, default=lambda b: {'blob': b.hex()}) + '\n')
    temporary.replace(output / 'realworld.json')
    s = result['summary']
    lines = ['# Public SQLite migration replays', '',
             f"Observed {result['observed_at']}. {s['migrations_attempted']} migrations in {s['repositories_attempted']} public repositories attempted; "
             f"{s['migrations_replayed']} replayed, including {s['qualifying_migrations_replayed']} parent rebuilds with populated CASCADE/SET NULL references "
             f"across {s['qualifying_repositories']} repositories ({s['qualifying_distinct_migration_hashes']} distinct migration hashes). "
             f"{s['controls_replayed']} no-dependent controls replayed.", '',
             'These are local synthetic-data results, not evidence that a project lost production data. '
             'The corpus is code-search selected and several repositories share migration files; counts are not prevalence estimates. '
             'All execution paths start with foreign_keys=ON. D1, libSQL and bun:sqlite are not executed. '
             'A better-sqlite3 result does not establish the behavior of those production runtimes.', '',
             'Histories are applied as raw SQLite SQL in journal order to empty databases, then every user table receives three synthetic rows by default. '
             'The target uses the actual better-sqlite3 migrate() entry point with the historical prefix marked applied, plus raw and raw-tx. '
             'The requested ORM version is taken from the nearest ancestor package.json; its numeric version is tried, with 0.45.4 as an explicit fallback. '
             'The better-sqlite3 driver is the harness pin, not the project driver. ', '',
             'Checks cover counts, complete synthetic row values, foreign-key definitions/checks, integrity, columns, indexes/triggers/views and view results. '
             'Intended changes are evaluated against the same migration with FK actions disabled; implicit object loss is additionally checked against the baseline. '
             'Trigger definitions are checked, but arbitrary application-specific trigger behavior is not inferred. '
             'An omitted index may be an intentional replacement; object-only findings establish an invariant difference, not developer intent. '
             'Outcomes depend on the generated seed, including values in fields that become NOT NULL. '
             'Literal INSERT records, unsupported SQL, missing journals and unsatisfied seed constraints remain unreplayable. '
             'Runtime labels are dependency/configuration evidence, not proof of the production adapter. '
             'Stars and GitHub license labels are observation-time metadata; commit-pinned license blob identifiers are in JSON.', '',
             '| Path | Preserved | Silent loss | Loud | Unreplayable |',
             '| --- | ---: | ---: | ---: | ---: |']
    for p, counts in s['path_outcomes'].items():
        lines.append(f"| {p} | " + ' | '.join(str(counts.get(k, 0)) for k in ('preserved', 'silent-loss', 'loud', 'unreplayable')) + ' |')
    lines += ['', '| Repository | Stars | Commit | Migration | Rebuilt table(s) | Dependents before rebuild | Drizzle | Raw | Raw-tx | Runtime evidence |',
              '| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |']
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    for r in result['rows']:
        sha = r.get('commit')
        commit = f'[{sha[:12]}](https://github.com/{r["repo"]}/tree/{sha})' if sha else 'unresolved'
        present = sha and r.get('reason') != 'migration file absent at pinned commit'
        migration = f'[{r["migration_file"]}](https://github.com/{r["repo"]}/blob/{sha}/{r["migration_file"]})' if present else r['migration_file']
        deps = '; '.join(f"{d['child']}.{','.join(d['columns'])} → {d['parent']} ({d['on_delete']}; {d['seeded_references']} rows)" for d in r.get('dependents', []))
        statuses = [r['paths'].get(p, {}).get('outcome', 'unreplayable') for p in PATHS]
        lines.append('| ' + ' | '.join(map(cell, [r['repo'], r.get('stars', '?'), commit, migration,
                                                ', '.join(r.get('rebuilt_tables', [])), deps or ('none' if r.get('control_no_dependents') else 'unresolved'),
                                                *statuses, r.get('runtime', 'unknown')])) + ' |')
    lines += ['', '## Outcomes and limitations', '']
    for r in result['rows']:
        prefix = f"{r['repo']} `{r['migration_file']}`"
        if r.get('reason'):
            lines.append(f"- {prefix}: unreplayable — {r['reason']}.")
            continue
        details = []
        for p in PATHS:
            trial = r['paths'].get(p, {})
            changed = [f"{f['table']} {f.get('expected')}→{f.get('after')} rows" for f in trial.get('findings', []) if f['kind'] == 'row_count']
            value_tables = sorted({f['table'] for f in trial.get('findings', []) if f['kind'] == 'content_digest'})
            objects = [f['object'] for f in trial.get('findings', []) if 'object' in f]
            extra = trial.get('execution', {}).get('error') or trial.get('reason')
            other = [f['kind'] for f in trial.get('findings', []) if 'object' not in f and f['kind'] not in ('row_count', 'content_digest')]
            detail = '; '.join(changed + ([f"changed values: {', '.join(value_tables)}"] if value_tables else []) + objects + other + ([extra] if extra else []))
            if detail:
                details.append(f'{p}: {detail}')
        version = r.get('orm', {})
        orm = f"ORM {version.get('declared') or 'undeclared'} → {version.get('resolved')}"
        if version.get('fallback'):
            orm += f" (fallback: {version['fallback_reason']})"
        lines.append(f"- {prefix}: {orm}. " + ('; '.join(details) if details else 'All checked invariants preserved.'))
    lines += ['', f"Stop reason: {result.get('stop_reason', 'run in progress')}. Full execution metadata, synthetic row differences and failure reasons are in `realworld.json`.", '']
    (output / 'realworld.md').write_text('\n'.join(lines))


def run(args):
    if getattr(args, 'evidence_dir', None) is not None:
        from .realworld_evidence import run
        return run(args)
    CACHE.mkdir(parents=True, exist_ok=True)
    targets = defaultdict(list)
    if args.repo:
        if not args.migration:
            raise ValueError('--repo requires --migration')
        targets[args.repo] = [(args.migration, None)]
        priority = [args.repo]
    else:
        if not args.input or not args.probe:
            raise ValueError('corpus mode requires --input and --probe')
        with args.input.open() as stream:
            for repo, path, blob in csv.reader(stream, delimiter='\t'):
                if (path, blob) not in targets[repo]:
                    targets[repo].append((path, blob))
        probes = json.loads(args.probe.read_text())
        positives = [p for p in probes if any(p.get('cascade_children_files', {}).values())]
        priority = [p['repo'] for p in positives]
        # Always attempt the nominated positive first, followed by one candidate
        # from each additional repository. Further candidates form a second pass.
        for p in positives:
            targets[p['repo']].sort(key=lambda item: item[0] != p['path'])
        priority += [r for r in targets if r not in priority]
    result = {'format_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(),
              'target_qualifying_migrations': args.target, 'rows_per_table': args.rows,
              'selection': '14 probe-positive repositories first; then one candidate per additional repository, then remaining candidates',
              'rows': []}
    result['source_hashes'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (Path(__file__), ROOT / 'smp/realworld_seed.py', ROOT / 'runners/realworld/run.cjs')}
    result['input_hashes'] = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                              for name, path in (('corpus', args.input), ('probe', args.probe)) if path}
    result['pins_sha256'] = hashlib.sha256(args.pins.read_bytes()).hexdigest() if args.pins else None
    result['arguments'] = {'repo': args.repo, 'migration': args.migration, 'commit': args.commit,
                           'orm_version': args.orm_version}
    report_path = args.output / 'realworld.json'
    if args.resume and report_path.exists():
        prior_result = json.loads(report_path.read_text())
        defaults = {'pins_sha256': None, 'arguments': dict.fromkeys(result['arguments'])}
        for field in ('source_hashes', 'input_hashes', 'rows_per_table', 'target_qualifying_migrations',
                      'pins_sha256', 'arguments'):
            if prior_result.get(field, defaults.get(field)) != result[field]:
                raise ValueError(f'{field} differs from the run in {args.output}; start a fresh output directory')
        result = prior_result
        result.pop('stop_reason', None)
    done = {(r['repo'], r['migration_file']) for r in result['rows']}
    pin_rows = json.loads(args.pins.read_text())['rows'] if args.pins else []
    pin_rows += result['rows']
    pins = {r['repo']: r['commit'] for r in pin_rows if r.get('commit')}
    versions = {(r['repo'], r['migration_file']): r.get('orm', {}).get('resolved') for r in pin_rows}
    prior_versions = {(r['repo'], r['migration_file']): r.get('orm', {}) for r in pin_rows}
    attempted_repos = {r['repo'] for r in result['rows']}
    # Max-repos bounds repositories, not migrations; useful for an initial smoke run.
    candidates = [(repo, *targets[repo][i]) for i in range(max(map(len, targets.values()))) for repo in priority if i < len(targets[repo])]
    for repo, target, blob in candidates:
        if (repo, target) in done:
            continue
        count = summary(result['rows'])['qualifying_migrations_replayed']
        # All 14 priority repositories are tried even when --target is lower.
        required_first = min(14, len(priority)) if not args.repo else 1
        if count >= args.target and all(r in attempted_repos for r in priority[:required_first]) and summary(result['rows'])['controls_replayed']:
            result['stop_reason'] = 'qualifying target and no-dependent control reached'
            break
        if args.max_repos and repo not in attempted_repos and len(attempted_repos) >= args.max_repos:
            result['stop_reason'] = 'max-repos limit reached (corpus not exhausted)'
            break
        print(f'{len(result["rows"]) + 1}: {repo} {target}', flush=True)
        with tempfile.TemporaryDirectory(prefix='replay-', dir=CACHE) as directory:
            work = Path(directory)
            info = {'repo': repo}
            try:
                info, extracted = repository(repo, [target], work, args.commit or pins.get(repo))
                pins[repo] = info['commit']
                runtime, version = orm_runtime(info, target, work, args.orm_version or versions.get((repo, target)))
                prior_version = prior_versions.get((repo, target), {})
                if not args.orm_version and prior_version.get('fallback'):
                    version.update(fallback=True, fallback_reason=prior_version['fallback_reason'])
                row = replay(info, extracted, target, blob, runtime, version, work, args.rows)
            except (Unreplayable, subprocess.TimeoutExpired, OSError, ValueError, KeyError) as exc:
                row = {**info, 'migration_file': target, 'status': 'unreplayable', 'reason': clean_error(exc),
                       'paths': {p: {'outcome': 'unreplayable', 'reason': clean_error(exc)} for p in PATHS}}
            result['rows'].append(row)
            attempted_repos.add(repo)
            done.add((repo, target))
            print('  ' + ', '.join(f'{p}={row["paths"][p]["outcome"]}' for p in PATHS) +
                  ('; ' + row['reason'] if row.get('reason') else ''), flush=True)
        write_report(args.output, result)
    else:
        result['stop_reason'] = 'requested repository replayed' if args.repo else 'all input migrations exhausted'
    write_report(args.output, result)
    return result
