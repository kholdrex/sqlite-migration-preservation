"""Validate the retained public-history evidence without fetching project data."""
import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smp.realworld import PATHS, summary
from smp.source_provenance import verify_sources
from smp.replay_notices import publication_notices
from smp.realworld_evidence import PERMISSIVE

PRODUCERS = {1: ('smp/realworld.py', 'smp/realworld_seed.py', 'runners/realworld/run.cjs'),
             2: ('smp/realworld.py', 'smp/realworld_seed.py', 'smp/realworld_evidence.py', 'runners/realworld/run.cjs',
                 'scripts/rebuild_realworld_evidence.py')}
PUBLISHERS = ('scripts/finalize_realworld_rerun.py', 'scripts/paper_numbers.py')


def source_provenance(result):
    """Producer files are required for every format; a finalized publication also names its publishing scripts."""
    producers = verify_sources(result.get('source_hashes'), ROOT, PRODUCERS[result.get('format_version', 1)])
    if 'publication_source_hashes' in result:
        verify_sources(result['publication_source_hashes'], ROOT, PUBLISHERS)
    return producers


def row_counts(snapshot):
    """Rows per application table; the migrator's and SQLite's own tables are left out, as in the replay."""
    return {name: len(table['rows']) for name, table in snapshot['tables'].items()
            if not name.startswith(('__drizzle_', 'sqlite_'))}


def validate(result, evidence_root=None):
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)
    check(result['summary'] == summary(result['rows']), 'summary does not match rows')
    try:
        source_provenance(result)
    except ValueError as exc:
        errors.append(str(exc))
    seen = set()
    for row in result['rows']:
        label = f"{row['repo']}:{row['migration_file']}"
        check(label not in seen, f'duplicate attempt: {label}')
        seen.add(label)
        check(set(row['paths']) == set(PATHS), f'missing paths: {label}')
        if row['status'] == 'unreplayable':
            check(bool(row.get('reason')) or all(p.get('reason') for p in row['paths'].values()), f'missing failure reason: {label}')
            continue
        check(bool(re.fullmatch('[0-9a-f]{40}', row.get('commit', ''))), f'unpinned commit: {label}')
        check(bool(re.fullmatch('[0-9a-f]{64}', row.get('migration_sha256', ''))), f'unhashed migration: {label}')
        check(bool(row.get('orm', {}).get('resolved')), f'ORM version absent: {label}')
        check(bool(row.get('seed_counts')) and all(n >= result['rows_per_table'] for n in row['seed_counts'].values()), f'incomplete seed: {label}')
        check(row['qualifying_parent_rebuild'] == any(d['on_delete'] in ('CASCADE', 'SET NULL') and d['seeded_references'] > 0 for d in row['dependents']), f'parent classification: {label}')
        check(row['control_no_dependents'] == (not row['dependents']), f'control classification: {label}')
        for path, trial in row['paths'].items():
            outcome = trial['outcome']
            check(outcome in ('preserved', 'silent-loss', 'loud', 'unreplayable'), f'invalid outcome: {label}/{path}')
            if outcome == 'unreplayable':
                check(bool(trial.get('reason') or trial.get('execution', {}).get('assessment_error')), f'path reason absent: {label}/{path}')
                continue
            execution = trial['execution']
            check(execution['foreign_keys_before'] == 1, f'FK entry mode: {label}/{path}')
            check(execution['success'] == (outcome != 'loud'), f'success classification: {label}/{path}')
            if outcome == 'preserved':
                check(not trial['findings'], f'preserved with findings: {label}/{path}')
            if outcome == 'silent-loss':
                check(bool(trial['findings']), f'loss without findings: {label}/{path}')
            if path == 'drizzle' and execution['success']:
                check(execution['target_journal_records'] == 1, f'target skipped: {label}')
    if result.get('format_version', 1) >= 2:
        # A complete-evidence run has an artifact for every attempt, replayed or not.
        for row in result['rows']:
            check(bool(row.get('evidence')), f"missing evidence reference: {row['repo']}:{row['migration_file']}")
    if evidence_root is not None:
        for row in result['rows']:
            ref = row.get('evidence')
            if not ref:
                continue
            label = row['repo'] + ':' + row['migration_file']
            path = (Path(evidence_root) / ref['file']).resolve()
            if not path.is_relative_to(Path(evidence_root).resolve()) or not path.is_file():
                errors.append('missing artifact: ' + label)
                continue
            raw = path.read_bytes()
            check(hashlib.sha256(raw).hexdigest() == ref['sha256'], 'artifact hash mismatch: ' + label)
            check(len(raw) == ref['bytes'], 'artifact size mismatch: ' + label)
            try:
                notices = publication_notices(row, ROOT) if row.get('license') in PERMISSIVE else None
                check(ref['mode'] == ('full' if notices else 'redacted'), 'publication mode mismatch: ' + label)
                check(ref.get('license_notices') == notices, 'notice index mismatch: ' + label)
                document = json.loads(gzip.decompress(raw))
                check(document['repo'] == row['repo'] and document['commit'] == row['commit']
                      and document['migration_file'] == row['migration_file'], 'artifact identity mismatch: ' + label)
                if row['status'] != 'unreplayable':
                    # The expected state is the reference execution, or the state before it when it failed.
                    reference = document['paths']['reference']
                    expected = row_counts(reference['after' if row['reference']['success'] else 'before'])
                    check(expected == row['reference']['counts'], 'reference row counts differ from the snapshot: ' + label)
                    for path, trial in row['paths'].items():
                        section = document['paths'][path]
                        if 'after' not in section:
                            continue
                        before, after = row_counts(section['before']), row_counts(section['after'])
                        check(trial.get('counts_after') == after, f'row counts differ from the snapshot: {label}/{path}')
                        lost = [{'kind': 'row_count', 'table': table, 'before': before.get(table), 'expected': count,
                                 'after': after.get(table)} for table, count in expected.items() if after.get(table) != count]
                        recorded = [f for f in trial['findings'] if f['kind'] == 'row_count']
                        table = lambda finding: finding['table']
                        check(sorted(lost, key=table) == sorted(recorded, key=table),
                              f'row-count findings differ from the snapshot: {label}/{path}')
                if ref['mode'] == 'redacted':
                    check(all('sql' not in item for item in document['source_statements']), 'source SQL in redacted artifact: ' + label)
                    for section in [document['setup'], document['journal_setup'], *document['paths'].values()]:
                        for item in section.get('trace', []) + section.get('submitted', []):
                            if item['origin'] == 'project':
                                check('sql' not in item and bool(item.get('sha256')) and bool(item.get('sources')),
                                      'project SQL in redacted trace: ' + label)
                        for boundary in ('before', 'after'):
                            for entry in section.get(boundary, {}).get('sqlite_schema', []):
                                check(entry.get('tbl_name') == '__drizzle_migrations' or
                                      ('sql' not in entry and bool(entry.get('sha256'))),
                                      'schema SQL in redacted artifact: ' + label)
            except (ValueError, OSError, KeyError) as exc:
                errors.append(label + ': ' + str(exc))
    counts = result['summary']
    if result.get('stop_reason') == 'qualifying target and no-dependent control reached':
        check(counts['qualifying_migrations_replayed'] >= result['target_qualifying_migrations'], 'target not reached')
        check(counts['controls_replayed'] > 0, 'no controls')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', nargs='?', type=Path, default=ROOT / 'results/realworld.json')
    args = parser.parse_args()
    result = json.loads(args.file.read_text())
    errors = validate(result, args.file.parent)
    print(json.dumps({'valid': not errors, 'errors': errors, 'summary': result['summary'],
                      'source_provenance': source_provenance(result) if not errors else None}, indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
