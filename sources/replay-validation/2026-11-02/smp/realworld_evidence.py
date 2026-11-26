import copy
import gzip
import hashlib
import json
import os
import platform
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .checks import identifier, statements
from .environment import ROOT

PERMISSIVE = {'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC'}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      default=lambda b: {'blob': b.hex()}).encode()


def write_gzip(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = gzip.compress(encoded(value), mtime=0)
    path.write_bytes(data)
    return {'file': path.name, 'sha256': sha256(data), 'bytes': len(data)}


def snapshot(database):
    with sqlite3.connect(database) as db:
        schema = [dict(zip(('type', 'name', 'tbl_name', 'rootpage', 'sql'), row))
                  for row in db.execute('SELECT type,name,tbl_name,rootpage,sql FROM sqlite_schema ORDER BY type,name')]
        content = {}
        for entry in schema:
            if entry['type'] != 'table':
                continue
            name = entry['name']
            columns = [row[1] for row in db.execute(f'PRAGMA table_xinfo({identifier(name)})')]
            rows = db.execute(f'SELECT {",".join(map(identifier, columns))} FROM {identifier(name)}').fetchall()
            rows.sort(key=encoded)
            content[name] = {'columns': columns, 'rows': rows}
        return {'sqlite_schema': schema, 'tables': content}


def source_catalog(extracted, target):
    catalog = []
    from .realworld import safe_path
    folder = extracted / safe_path(target).parent
    selected = [extracted / target]
    journal_path = folder / 'meta/_journal.json'
    if journal_path.exists():
        try:
            entries = json.loads(journal_path.read_text())['entries']
            index = next(i for i, entry in enumerate(entries) if entry['tag'] + '.sql' == Path(target).name)
            selected = [folder / (str(safe_path(entry['tag'])) + '.sql') for entry in entries[:index + 1]]
        except (ValueError, KeyError, StopIteration):
            pass
    for path in selected:
        if not path.is_file():
            continue
        data = path.read_bytes()
        sql = data.decode()
        try:
            parts = list(statements(sql))
        except ValueError:
            parts = [sql]
        offset = 0
        for ordinal, part in enumerate(parts, 1):
            start = sql.index(part, offset)
            end = start + len(part)
            catalog.append({'sql': part, 'source': {
                'file': str(path.relative_to(extracted)), 'file_sha256': sha256(data),
                'byte_start': len(sql[:start].encode()), 'byte_end': len(sql[:end].encode()),
                'line_start': sql.count('\n', 0, start) + 1,
                'line_end': sql.count('\n', 0, end) + 1, 'statement': ordinal,
                'sha256': sha256(part.encode()),
            }})
            offset = end
    return catalog


class Trace:
    def __init__(self, evidence, target=None):
        self.evidence = evidence
        self.target = target
        self.origin = 'framework'
        self.sources = []
        self.executed = []
        self.submitted = []

    def submit(self, sql, file=None):
        self.sources = self.evidence.sources(sql, file or self.target)
        self.origin = 'project'
        self.submitted.append({'sql': sql, 'origin': self.origin, 'sources': self.sources})

    def callback(self, sql):
        item = {'sql': sql, 'origin': self.origin}
        if self.origin == 'project':
            item['sources'] = self.sources
        self.executed.append(item)

    def data(self):
        return {'trace': self.executed, 'submitted': self.submitted}


class Evidence:
    def __init__(self, extracted, target):
        self.catalog = source_catalog(extracted, target)
        self.target = target
        self.stage = 'validation'
        self.setup = Trace(self)
        self.journal_setup = Trace(self)
        self.paths = {}
        self.traces = {}

    def sources(self, sql, file=None):
        from .realworld import tokens_without_comments
        key = tokens_without_comments(sql).strip()
        matches = [entry['source'] for entry in self.catalog
                   if (file is None or entry['source']['file'] == file)
                   and tokens_without_comments(entry['sql']).strip() == key]
        if not matches:
            raise ValueError('project statement has no pinned source position')
        return matches

    def start(self, path, database):
        self.stage = path
        self.traces[path] = Trace(self, self.target)
        self.paths[path] = {'before': snapshot(database)}

    def finish(self, path, database):
        self.paths[path].update(self.traces[path].data(), after=snapshot(database))

    def drizzle(self, trace, submitted):
        folder = str(Path(self.target).parent)
        for item in trace + submitted:
            if item['origin'] == 'project':
                source = item.pop('source')
                file = folder + '/' + source['file']
                matches = [entry['source'] for entry in self.catalog
                           if entry['source']['file'] == file
                           and entry['source']['byte_start'] < source['byte_end']
                           and entry['source']['byte_end'] > source['byte_start']]
                if not matches:
                    raise ValueError('Drizzle statement has no pinned source position')
                item['sources'] = matches
        self.traces['drizzle'].executed = trace
        self.traces['drizzle'].submitted = submitted

    def document(self, row):
        paths = dict(self.paths)
        for path, trial in row['paths'].items():
            if path not in paths:
                paths[path] = {'not_executed': True, 'reason': trial.get('reason', row.get('reason'))}
        return {'format_version': 1, 'repo': row['repo'], 'commit': row.get('commit'),
                'migration_file': row['migration_file'], 'recorded_license': row.get('license'),
                'stage': self.stage, 'status': row['status'], 'reason': row.get('reason'),
                'source_statements': self.catalog, 'setup': self.setup.data(),
                'journal_setup': self.journal_setup.data(), 'paths': paths}


def redact(document):
    from .realworld import tokens_without_comments
    result = copy.deepcopy(document)
    ddl_sources = [item['source'] for item in result['source_statements']
                   if re.match(r'\s*(CREATE|ALTER|DROP)\b', tokens_without_comments(item['sql']), re.I)]
    for item in result['source_statements']:
        item['sha256'] = sha256(item.pop('sql').encode())
    for section in [result['setup'], result['journal_setup'], *result['paths'].values()]:
        for item in section.get('trace', []) + section.get('submitted', []):
            if item['origin'] == 'project':
                if not item.get('sources'):
                    raise ValueError('cannot publish project SQL without provenance')
                item['sha256'] = sha256(item.pop('sql').encode())
        for boundary in ('before', 'after'):
            if boundary not in section:
                continue
            schema = section[boundary]['sqlite_schema']
            for i, entry in enumerate(schema):
                if entry['tbl_name'] == '__drizzle_migrations':
                    continue
                if not ddl_sources:
                    raise ValueError('cannot publish schema without pinned DDL provenance')
                schema[i] = {'sha256': sha256(encoded(entry)), 'sources': ddl_sources,
                             'provenance': 'conservative DDL dependency set; not a minimal derivation'}
    return result


def safe_aggregate(row, evidence):
    if row.get('license') in PERMISSIVE:
        return copy.deepcopy(row)
    result = copy.deepcopy(row)
    from .realworld import tokens_without_comments
    for path, trial in result['paths'].items():
        execution = trial.get('execution', {})
        trace = iter(evidence.traces[path].executed if path in evidence.traces else [])
        for i, event in enumerate(execution.get('events', [])):
            key = tokens_without_comments(event).strip().rstrip(';').lower()
            match = next((item for item in trace
                          if tokens_without_comments(item['sql']).strip().rstrip(';').lower() == key), None)
            if match is None:
                raise ValueError('event has no execution trace provenance')
            if match['origin'] == 'project':
                execution['events'][i] = {'sha256': sha256(event.encode()),
                                          'sources': match['sources']}
        if 'error' in execution:
            execution['error'] = 'Restricted diagnostic SHA-256: ' + sha256(execution['error'].encode())
    return result


def loss_signature(row):
    result = {}
    for path, trial in row['paths'].items():
        counts = [finding for finding in trial.get('findings', []) if finding['kind'] == 'row_count']
        result[path] = {
            'lost_tables': sorted(f['table'] for f in counts if f['after'] is None),
            'missing_rows': {f['table']: max(0, f['expected'] - (f['after'] or 0)) for f in counts
                             if f['expected'] > (f['after'] or 0)},
            'changed_value_tables': sorted(f['table'] for f in trial.get('findings', []) if f['kind'] == 'content_digest'),
        }
    return result


def compare_results(original, rerun):
    from .realworld import PATHS, summary
    def index(result):
        rows = {(r['repo'], r['migration_file']): r for r in result['rows']}
        if len(rows) != len(result['rows']):
            raise ValueError('duplicate migration attempts')
        return rows
    old, new = index(original), index(rerun)
    comparisons = []
    fields = ('status', 'qualifying_parent_rebuild', 'control_no_dependents', 'seed_counts',
              'rebuilt_tables', 'dependents', 'reference', 'reason', 'migration_sha256', 'history')
    for key in sorted(old.keys() | new.keys()):
        a, b = old.get(key), new.get(key)
        differences, runtime = [], []
        def check(field, before, after, destination=differences):
            if encoded(before) != encoded(after):
                destination.append({'field': field, 'original': before, 'rerun': after,
                                    'cause': 'unresolved; requires investigation'})
        if a is None or b is None:
            check('attempt_present', a is not None, b is not None)
        else:
            for field in fields:
                check(field, a.get(field), b.get(field))
            check('loss', loss_signature(a), loss_signature(b))
            for path in PATHS:
                for field in ('outcome', 'counts_after', 'findings', 'foreign_key_check', 'integrity_check', 'state_changed'):
                    check(f'{path}.{field}', a['paths'][path].get(field), b['paths'][path].get(field))
                for field in ('node', 'sqlite', 'better_sqlite3', 'success', 'error', 'foreign_keys_before', 'foreign_keys_after', 'target_journal_records', 'transaction_open_after'):
                    check(f'{path}.execution.{field}', a['paths'][path].get('execution', {}).get(field),
                          b['paths'][path].get('execution', {}).get(field), runtime)
            check('orm.resolved', a.get('orm', {}).get('resolved'), b.get('orm', {}).get('resolved'))
            check('commit', a.get('commit'), b.get('commit'))
        comparisons.append({'repo': key[0], 'migration_file': key[1], 'differences': differences,
                            'execution_differences': runtime,
                            'original_loss': loss_signature(a) if a else None,
                            'rerun_loss': loss_signature(b) if b else None})
    return {'original_summary': summary(original['rows']), 'rerun_summary': summary(rerun['rows']),
            'summary_matches': summary(original['rows']) == summary(rerun['rows']),
            'migrations_compared': len(comparisons),
            'migrations_with_differences': sum(bool(r['differences']) for r in comparisons),
            'comparisons': comparisons}


def run(args):
    import subprocess
    import tempfile
    from . import realworld
    if not args.pins or args.resume or args.commit or args.orm_version or args.max_repos:
        raise ValueError('evidence runs require --pins and a fresh output, without overrides or --resume')
    original = json.loads(args.pins.read_text())
    if args.rows != original['rows_per_table']:
        raise ValueError('seed size differs from recorded pins')
    local = args.evidence_dir.resolve()
    output = args.output.resolve()
    if not local.is_relative_to(ROOT) or not output.is_relative_to(ROOT):
        raise ValueError('evidence and output must be inside the working directory')
    if local == output or local.is_relative_to(output) or output.is_relative_to(local):
        raise ValueError('local evidence and publication directories must be separate')
    if output.exists():
        raise ValueError('publication output already exists; select a fresh dated directory')
    ignored = subprocess.run(['git', 'check-ignore', '-q', str(local / 'probe')], cwd=ROOT)
    if ignored.returncode:
        raise ValueError('full evidence directory must be git-ignored')
    if local.exists() and any(local.glob('*.json*')):
        raise ValueError('local evidence already exists; select a fresh directory')
    input_hashes = {key: sha256(path.read_bytes()) for key, path in (('corpus', args.input), ('probe', args.probe)) if path}
    if input_hashes != original['input_hashes']:
        raise ValueError('corpus/probe hashes differ from recorded pins')
    pins = original['rows']
    if args.repo:
        pins = [r for r in pins if r['repo'] == args.repo and (not args.migration or r['migration_file'] == args.migration)]
        if not pins:
            raise ValueError('requested migration absent from pins')
    if len({(r['repo'], r['migration_file']) for r in pins}) != len(pins):
        raise ValueError('duplicate pins')
    for row in pins:
        if not re.fullmatch('[a-f0-9]{40}', row.get('commit', '')) or not row.get('orm', {}).get('resolved'):
            raise ValueError('every attempt must have a commit and resolved ORM pin')
    local.mkdir(parents=True, exist_ok=True)
    os.environ['SMP_RUNTIME_ROOT'] = str(local / 'runtime')
    previous_cache = realworld.CACHE
    realworld.CACHE = local / 'cache'
    realworld.CACHE.mkdir()
    result = {'format_version': 2, 'observed_at': datetime.now(timezone.utc).isoformat(),
              'target_qualifying_migrations': original['target_qualifying_migrations'],
              'rows_per_table': args.rows, 'selection': 'exact attempted migrations from pins, in recorded order',
              'pins_sha256': sha256(args.pins.read_bytes()), 'input_hashes': input_hashes,
              'environment': {'python': platform.python_version(), 'platform': platform.platform(),
                              'sqlite_python': sqlite3.sqlite_version},
              'source_hashes': {name: sha256((ROOT / name).read_bytes()) for name in (
                  'smp/realworld.py', 'smp/realworld_seed.py', 'smp/realworld_evidence.py',
                  'runners/realworld/run.cjs', 'scripts/rebuild_realworld_evidence.py', 'PROTOCOL_realworld_rerun.md')},
              'publication_rule': {'full': sorted(PERMISSIVE), 'otherwise': 'project SQL and schema hashed with pinned source positions'},
              'rows': []}
    full_rows = []
    metadata_fields = ('repo', 'stars', 'license', 'metadata_observed_at', 'license_source', 'metadata_source', 'fork', 'default_branch')
    try:
        for number, prior in enumerate(pins, 1):
            repo, target = prior['repo'], prior['migration_file']
            print(f'{number}/{len(pins)}: {repo} {target}', flush=True)
            with tempfile.TemporaryDirectory(prefix='replay-', dir=realworld.CACHE) as directory:
                work = Path(directory)
                evidence = Evidence(work / 'extracted', target)
                try:
                    info, extracted = realworld.repository(repo, [target], work, prior['commit'],
                                                          {k: prior[k] for k in metadata_fields if k in prior})
                    evidence = Evidence(extracted, target)
                    runtime, version = realworld.orm_runtime(info, target, work, prior['orm']['resolved'])
                    if version['resolved'] != prior['orm']['resolved']:
                        raise realworld.Unreplayable('pinned ORM unavailable; fallback forbidden in evidence run')
                    if prior['orm'].get('registry_integrity') and version.get('registry_integrity') != prior['orm']['registry_integrity']:
                        raise realworld.Unreplayable('npm registry integrity differs from pin')
                    version.update({k: prior['orm'][k] for k in ('fallback', 'fallback_reason', 'same_minor_recovery_from') if k in prior['orm']})
                    row = realworld.replay(info, extracted, target, prior.get('search_blob_sha'), runtime, version, work, args.rows, evidence)
                except (realworld.Unreplayable, subprocess.TimeoutExpired, OSError, ValueError, KeyError) as exc:
                    row = {k: prior[k] for k in metadata_fields if k in prior}
                    row.update(commit=prior['commit'], migration_file=target, orm=prior['orm'], status='unreplayable',
                               reason=realworld.clean_error(exc), paths={p: {'outcome': 'unreplayable', 'reason': realworld.clean_error(exc)} for p in realworld.PATHS})
                document = evidence.document(row)
                document['observed_at'] = datetime.now(timezone.utc).isoformat()
                name = f'{number:03d}-' + sha256(f'{repo}:{target}'.encode())[:16] + '.json.gz'
                full_ref = write_gzip(local / name, document)
                published = document if row.get('license') in PERMISSIVE else redact(document)
                public_ref = write_gzip(output / 'evidence' / name, published)
                public_ref.update(file='evidence/' + name, mode='full' if row.get('license') in PERMISSIVE else 'redacted',
                                  full_sha256=full_ref['sha256'])
                row['evidence'] = public_ref
                full_rows.append(row)
                result['rows'].append(safe_aggregate(row, evidence))
                print('  ' + ', '.join(f'{p}={row["paths"][p]["outcome"]}' for p in realworld.PATHS), flush=True)
            realworld.write_report(output, result)
            realworld.write_report(local, {**result, 'rows': full_rows})
        result['completed_at'] = datetime.now(timezone.utc).isoformat()
        result['stop_reason'] = 'all pinned attempts completed'
        licenses = Counter({r['repo']: r.get('license') for r in pins}.values())
        result['licensing'] = {'recorded_labels': {k or 'null': v for k, v in licenses.items()},
                               'full_repositories': sum(v for k, v in licenses.items() if k in PERMISSIVE),
                               'redacted_repositories': sum(v for k, v in licenses.items() if k not in PERMISSIVE)}
        result['evidence_bytes'] = sum(r['evidence']['bytes'] for r in result['rows'])
        realworld.write_report(output, result)
        full = {**result, 'rows': full_rows}
        realworld.write_report(local, full)
        comparison = compare_results({**original, 'rows': pins}, full)
        (output / 'comparison.json').write_bytes(encoded(comparison) + b'\n')
        return result
    finally:
        realworld.CACHE = previous_cache
