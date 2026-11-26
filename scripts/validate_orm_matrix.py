"""Recompute classifications and coverage from retained ORM evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smp.matrix_spec import CONTEXTS
from smp.operation_matrix import read_gzip
from smp.checks import require
from smp.orm_checks import transaction_structure
from smp.orm_matrix import checked_violations
from smp.orm_spec import OPERATIONS, orm_fixture
from smp.preservation import classify, digest
from smp.rebuild import CLASSIFIER, rebuild, recorded_rebuild


def validate(result, complete=True):
    require(not result['errors'], result['errors'])
    rows = result['rows']
    require(rows, 'No rows to validate')
    keys = {(r['framework'], r['version_label'], r['mode'], r['operation'], r['context'], r['path']) for r in rows}
    require(len(keys) == len(rows))
    if complete:
        expected = set()
        for fw, pin, modes in [('django', 'django-current', ['default']), ('django', 'django-previous', ['default']),
                               ('alembic', 'alembic', ['auto', 'always']), ('prisma', 'prisma-stable', ['default'])]:
            for mode in modes:
                for op in OPERATIONS:
                    if fw == 'prisma' and 'check_constraint' in op:
                        continue
                    for ctx in CONTEXTS:
                        for path in (mode if fw == 'alembic' else fw, 'raw', 'raw-tx'):
                            expected.add((fw, pin, mode, op, ctx, path))
        require(keys == expected, (len(keys), len(expected), expected - keys))
        unsupported = {(r['version_label'], r['operation'], r['context']) for r in result['unsupported']}
        expected_unsupported = {('prisma-latest-tag', op, ctx) for op in OPERATIONS for ctx in CONTEXTS}
        expected_unsupported.update(('prisma-stable', op, ctx)
                                    for op in ('add_check_constraint', 'remove_check_constraint') for ctx in CONTEXTS)
        require(len(result['unsupported']) == len(unsupported) == 198)
        require(unsupported == expected_unsupported)
    cache = {}
    rebuilt = rebuild if result.get('rebuild_classifier') == CLASSIFIER else recorded_rebuild
    for row in rows:
        artifact = row['artifacts']
        if artifact not in cache:
            cache[artifact] = read_gzip(ROOT / artifact)
        evidence = cache[artifact]
        spec, schema, seed = orm_fixture(row['framework'], row['operation'], row['context'])
        require((spec, schema, seed) == (evidence['spec'], evidence['schema'], evidence['seed']))
        require(row in evidence['rows'])
        require(row['spec'] == spec)
        for population, trial in row['trials'].items():
            execution, before, after = trial['execution'], trial['before'], trial['after']
            found = checked_violations(before, after, spec, execution)
            require(trial['violations'] == found)
            require(trial['outcome'] == classify(execution['success'], found, before, after))
            for snapshot in (before, after):
                for data in snapshot['content'].values():
                    if 'rows' in data:
                        require(digest(data['rows']) == data['digest'])
            trace = evidence['trials'][row['path'] + '/' + population]['executed.sql']
            require(transaction_structure(trace) == trial['transaction_structure'])
            require(rebuilt(evidence['generation']['migration.sql']) == trial['planned_rebuild'] == row['planned_rebuild'])
            if execution.get('trace_available', True):
                require(rebuilt(trace) == trial['rebuild'])
                require(execution['foreign_keys_before'] == 1)
            else:
                require(row['path'] == 'prisma' and trial['rebuild'] is None and not trace)
            if row['path'] == 'django':
                name = 'Django' if row['version_label'] == 'django-current' else 'Django_previous'
                require(execution['django'] == result['pins'][name])
            if row['path'] in ('auto', 'always'):
                require(execution['alembic'] == result['pins']['alembic'])
                require(execution['sqlalchemy'] == result['pins']['SQLAlchemy'])
            if row['path'] == 'prisma':
                require(execution['prisma'] == result['pins']['prisma_stable'])
                observed = execution['connection_observations']
                require(observed[0][0] == 'before' and observed[0][1] == execution['foreign_keys_before'] == 1)
                require(observed[-1][0] in ('after', 'failure'))
                require(observed[-1][1] == execution['foreign_keys_after'])
                require(all(item[3] == execution['sqlite'] for item in observed))
        require(row['outcome'] == row['trials']['populated']['outcome'])
        require(row['detectors']['empty_db'] == (not row['trials']['empty']['execution']['success']))
        require(row['detectors']['populated_invariants'] == bool(row['trials']['populated']['violations']))
        for detector in row['detectors']['lint'].values():
            if detector['available']:
                require(detector['detected'] == bool(detector['output']['findings']))
    return {'pairs': len(rows), 'executions': len(rows) * 2, 'coverage_complete': complete,
            'outcomes': dict(Counter(r['outcome'] for r in rows))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    parser.add_argument('--subset', action='store_true')
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    summary = validate(result, not args.subset)
    from smp.orm_report import write_report
    import tempfile
    cache = ROOT / '.cache/orm'
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as folder:
        regenerated = Path(folder) / 'orm_matrix.md'
        write_report(result, regenerated)
        require(regenerated.read_bytes() == args.result.with_suffix('.md').read_bytes())
    summary['report_reproduced'] = True
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
