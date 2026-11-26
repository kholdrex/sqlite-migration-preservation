import argparse
import copy
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from smp.realworld import PATHS, summary, write_report
from smp.realworld_evidence import PERMISSIVE, compare_results, encoded, loss_signature, redact, sha256, write_gzip
from scripts.paper_numbers import Numbers, realworld_numbers


def paper_counts(original, rerun):
    old, new = Numbers(), Numbers()
    realworld_numbers(old, original)
    realworld_numbers(new, rerun)
    published = json.loads((ROOT / 'paper/numbers.json').read_text())['macros']
    quantities = {name: {'original': entry['value'], 'rerun': new.macros.get(name, {}).get('value'),
                         'paper': published.get(name, {}).get('value')}
                  for name, entry in old.macros.items()}
    quantities['nExecutionsRealworld'] = {
        'original': sum(t['outcome'] != 'unreplayable' for r in original['rows'] for t in r['paths'].values()),
        'rerun': sum(t['outcome'] != 'unreplayable' for r in rerun['rows'] for t in r['paths'].values()),
        'paper': published['nExecutionsRealworld']['value'],
    }
    return {'all_match': all(q['original'] == q['rerun'] == q['paper'] for q in quantities.values()),
            'quantities': quantities}


def compact_provenance(document):
    result = copy.deepcopy(document)
    for section in result['paths'].values():
        for boundary in ('before', 'after'):
            for entry in section.get(boundary, {}).get('sqlite_schema', []):
                if 'sources' not in entry:
                    continue
                sources = entry.pop('sources')
                if 'schema_sources' in result and result['schema_sources'] != sources:
                    raise ValueError('schema provenance sets differ')
                result['schema_sources'] = sources
                entry['sources_ref'] = '#/schema_sources'
    return result


def expand_provenance(document):
    result = copy.deepcopy(document)
    for section in result['paths'].values():
        for boundary in ('before', 'after'):
            for entry in section.get(boundary, {}).get('sqlite_schema', []):
                if entry.pop('sources_ref', None) == '#/schema_sources':
                    entry['sources'] = result['schema_sources']
    result.pop('schema_sources', None)
    return result


def audit(original, full, public, local, output):
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)
    check(public.get('stop_reason') == 'all pinned attempts completed', 'incomplete run')
    check(public['summary'] == summary(public['rows']), 'public summary mismatch')
    check(public['summary'] == full['summary'], 'publication changed summary')
    for name, digest in public['source_hashes'].items():
        check(sha256((ROOT / name).read_bytes()) == digest, 'source changed: ' + name)
    check(len(full['rows']) == len(public['rows']) == len(original['rows']), 'attempt count mismatch')
    totals = Counter()
    index = []
    for row, published_row, pin in zip(full['rows'], public['rows'], original['rows']):
        label = row['repo'] + ':' + row['migration_file']
        check((row['repo'], row['migration_file'], row['commit'], row['orm']['resolved']) ==
              (pin['repo'], pin['migration_file'], pin['commit'], pin['orm']['resolved']), label + ': pins changed')
        ref = published_row['evidence']
        name = Path(ref['file']).name
        full_path = local / name
        check(sha256(full_path.read_bytes()) == ref['full_sha256'], label + ': full artifact hash mismatch')
        public_path = output / ref['file']
        check(sha256(public_path.read_bytes()) == ref['sha256'], label + ': public artifact hash mismatch')
        check(public_path.stat().st_size == ref['bytes'], label + ': size mismatch')
        document = json.loads(gzip.decompress(full_path.read_bytes()))
        published = json.loads(gzip.decompress(public_path.read_bytes()))
        expected = document if row.get('license') in PERMISSIVE else redact(document)
        check(expand_provenance(published) == expected, label + ': publication differs from release rule')
        check(ref['mode'] == ('full' if row.get('license') in PERMISSIVE else 'redacted'), label + ': license class mismatch')
        index.append({'repo': row['repo'], 'migration_file': row['migration_file'],
                      'file': name, 'sha256': ref['full_sha256']})
        for source in document['source_statements']:
            check(sha256(source['sql'].encode()) == source['source']['sha256'], label + ': statement hash mismatch')
            check(source['source']['byte_end'] - source['source']['byte_start'] == len(source['sql'].encode()), label + ': source span mismatch')
        for path in PATHS:
            section = document['paths'][path]
            trial = row['paths'][path]
            if section.get('not_executed'):
                check(trial['outcome'] == 'unreplayable', label + ': executed path marked absent')
                totals['unexecuted_paths'] += 1
                continue
            totals['executed_paths'] += 1
            check(bool(section['trace']), label + '/' + path + ': empty trace')
            totals['target_trace_callbacks'] += len(section['trace'])
            totals['project_submissions'] += sum(s['origin'] == 'project' for s in section['submitted'])
            for boundary in ('before', 'after'):
                state = section[boundary]
                names = {s['name'] for s in state['sqlite_schema'] if s['type'] == 'table'}
                check(names == set(state['tables']), label + ': snapshot omits tables')
                check(all(len(values) == len(table['columns']) for table in state['tables'].values() for values in table['rows']), label + ': incomplete row')
                totals['snapshots'] += 1
            actual_counts = {name: len(table['rows']) for name, table in section['after']['tables'].items()
                             if not name.startswith(('sqlite_', '__drizzle_'))}
            check(actual_counts == trial.get('counts_after'), label + '/' + path + ': snapshot counts differ from assessment')
            if path == 'drizzle':
                check('__drizzle_migrations' in section['before']['tables'], label + ': missing before journal')
                check('__drizzle_migrations' in section['after']['tables'], label + ': missing after journal')
            for item in section['trace'] + section['submitted']:
                check(item['origin'] in ('framework', 'project'), label + ': unknown origin')
                if item['origin'] == 'project':
                    check(bool(item.get('sources')), label + ': missing project provenance')
    return {'valid': not errors, 'errors': errors, 'coverage': dict(totals)}, index


def report(comparison, result, validation):
    s = result['summary']
    lines = ['# RQ4 rerun comparison', '',
             f"Observed {result['observed_at']}; completed {result['completed_at']}.", '',
             f"Compared all {comparison['migrations_compared']} pinned migrations. "
             f"Migrations with scientific differences: {comparison['migrations_with_differences']}. "
             f"All aggregate counts match: {comparison['summary_matches']}.", '',
             f"{s['migrations_replayed']} replayed; {s['migrations_attempted'] - s['migrations_replayed']} unreplayable. "
             f"{s['qualifying_migrations_replayed']} qualifying parent rebuilds in {s['qualifying_repositories']} repositories "
             f"({s['qualifying_distinct_migration_hashes']} distinct migration hashes); {s['controls_replayed']} controls.", '',
             '| Path | Preserved | Silent loss | Loud | Unreplayable |',
             '| --- | ---: | ---: | ---: | ---: |']
    for path in PATHS:
        counts = s['path_outcomes'][path]
        lines.append('| ' + path + ' | ' + ' | '.join(str(counts.get(k, 0)) for k in ('preserved', 'silent-loss', 'loud', 'unreplayable')) + ' |')
    lines += ['', 'Qualifying migrations only:', '', '| Path | Preserved | Silent loss | Loud |', '| --- | ---: | ---: | ---: |']
    for path in PATHS:
        counts = s['qualifying_path_outcomes'][path]
        lines.append('| ' + path + ' | ' + ' | '.join(str(counts.get(k, 0)) for k in ('preserved', 'silent-loss', 'loud')) + ' |')
    differences = [dict(repo=r['repo'], migration_file=r['migration_file'], **d)
                   for r in comparison['comparisons'] for d in r['differences'] + r['execution_differences']]
    lines += ['', f"Differing scientific or execution fields: {len(differences)}.", '']
    for d in differences:
        lines.append(f"- {d['repo']} `{d['migration_file']}`, `{d['field']}`: {d['original']} → {d['rerun']}. Cause: {d['cause']}.")
    paper = comparison['paper_counts']
    lines += [f"All {len(paper['quantities'])} RQ4 paper quantities reproduce: {paper['all_match']}. "
              'The existing paper adjudication excludes the intentionally superseded '
              '`activity_events_org_id_idx` index in `saltbo/zpan` / `0054_lively_nuke.sql`. '
              'After that same adjudication, silent-loss counts are 19 Drizzle, 12 raw and 23 raw-tx '
              '(unadjudicated: 20, 13 and 24). Among qualifying migrations, 11 change from '
              'Drizzle silent loss to raw preservation and four remain silent loss. '
              'The original paper and its generated numbers are unchanged.', '']
    lines += [f"Published gzip evidence: {result['evidence_bytes']:,} bytes in {len(result['rows'])} artifacts. "
              f"License split: {result['licensing']['full_repositories']} full, {result['licensing']['redacted_repositories']} redacted repositories.", '',
              'Recorded labels: ' + ', '.join(f'{key}: {value}' for key, value in sorted(result['licensing']['recorded_labels'].items())) + '.', '',
              'Complete before/after snapshots exist for every executed target path. Unexecuted paths retain their failure reasons and available setup traces; no target snapshots are invented. '
              'Schema provenance in restricted artifacts is a conservative DDL dependency set stored once under `schema_sources`; '
              '`sources_ref: #/schema_sources` resolves to byte/line positions in pinned files. It is not a minimal schema derivation.', '',
              'Original row identities cannot be compared because the original snapshots were not retained. '
              'The comparison checks every original finding (including retained synthetic row differences), qualification, seed count, '
              'outcome, lost table, missing row count and after count. SQLite callback traces and submitted statements are distinguished as described in the protocol.', '',
              f"Artifact audit: {validation['valid']}; coverage: `{json.dumps(validation['coverage'], sort_keys=True)}`.", '',
              '## Migration-by-migration comparison', '',
              'Each row reports the rerun result; `same` means all compared fields match the original. '
              'Loss cells list missing rows by table and tables whose values differ from the reference. '
              'A value difference can reflect a failed migration; the path outcome remains authoritative.', '',
              '| Repository / migration | Qualification | Drizzle | Raw | Raw-tx | Comparison |',
              '| --- | --- | --- | --- | --- | --- |']
    by_key = {(r['repo'], r['migration_file']): r for r in comparison['comparisons']}
    for row in result['rows']:
        key = row['repo'], row['migration_file']
        cmp = by_key[key]
        label = 'parent' if row.get('qualifying_parent_rebuild') else 'control' if row.get('control_no_dependents') else row['status']
        cells = []
        for path, loss in loss_signature(row).items():
            detail = []
            if loss['lost_tables']:
                detail.append('lost tables: ' + ', '.join(loss['lost_tables']))
            if loss['missing_rows']:
                detail.append('missing rows: ' + ', '.join(f'{name}={count}' for name, count in loss['missing_rows'].items()))
            if loss['changed_value_tables']:
                detail.append('values: ' + ', '.join(loss['changed_value_tables']))
            cells.append(row['paths'][path]['outcome'] + ('; ' + '; '.join(detail) if detail else ''))
        values = [row['repo'] + ' / `' + row['migration_file'] + '`', label, *cells,
                  'different' if cmp['differences'] or cmp['execution_differences'] else 'same']
        lines.append('| ' + ' | '.join(v.replace('|', '\\|') for v in values) + ' |')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Compact publication provenance and audit a completed RQ4 rerun')
    parser.add_argument('--original', type=Path, default=ROOT / 'results/realworld.json')
    parser.add_argument('--local', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    original = json.loads(args.original.read_text())
    full = json.loads((args.local / 'realworld.json').read_text())
    public = json.loads((args.output / 'realworld.json').read_text())
    if public.get('format_version') != 2 or public.get('stop_reason') != 'all pinned attempts completed':
        raise ValueError('requires a completed opt-in rerun')
    if sha256(args.original.read_bytes()) != public['pins_sha256']:
        raise ValueError('original pins changed')
    for row in public['rows']:
        ref = row['evidence']
        path = args.output / ref['file']
        document = json.loads(gzip.decompress(path.read_bytes()))
        compressed = write_gzip(path, compact_provenance(document))
        ref.update(sha256=compressed['sha256'], bytes=compressed['bytes'])
    public['evidence_bytes'] = sum(r['evidence']['bytes'] for r in public['rows'])
    public['publication_source_hashes'] = {name: sha256((ROOT / name).read_bytes())
                                         for name in ('scripts/finalize_realworld_rerun.py', 'scripts/paper_numbers.py')}
    comparison = compare_results(original, full)
    comparison['paper_counts'] = paper_counts(original, full)
    validation, index = audit(original, full, public, args.local, args.output)
    if not validation['valid']:
        print(json.dumps(validation, indent=2))
        raise SystemExit(1)
    public['evidence_validation'] = validation
    write_report(args.output, public)
    (args.local / 'full-evidence-index.json').write_bytes(encoded(index) + b'\n')
    (args.output / 'comparison.json').write_bytes(encoded(comparison) + b'\n')
    (args.output / 'comparison.md').write_text(report(comparison, public, validation))
    print(json.dumps({'validation': validation, 'scientific_differences': comparison['migrations_with_differences'],
                      'summary_matches': comparison['summary_matches'], 'published_bytes': public['evidence_bytes']}, indent=2))
    if not comparison['paper_counts']['all_match'] or comparison['migrations_with_differences'] or any(r['execution_differences'] for r in comparison['comparisons']):
        raise SystemExit('comparison differences require diagnosis')


if __name__ == '__main__':
    main()
