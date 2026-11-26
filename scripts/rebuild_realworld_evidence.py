import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from smp.realworld import run


def main():
    parser = argparse.ArgumentParser(description='Rebuild full evidence from a pinned public commit into ignored local storage')
    parser.add_argument('--pins', type=Path, default=ROOT / 'results/realworld.json')
    parser.add_argument('--repo', required=True)
    parser.add_argument('--migration', required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--input', type=Path, default=ROOT / 'sources/realworld/drizzle_rebuild_files.tsv')
    parser.add_argument('--probe', type=Path, default=ROOT / 'sources/realworld/g3_probe.json')
    args = parser.parse_args()
    import json
    args.rows = json.loads(args.pins.read_text())['rows_per_table']
    args.resume = False
    args.commit = args.orm_version = args.max_repos = None
    run(args)


if __name__ == '__main__':
    main()
