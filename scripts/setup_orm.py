"""Install the retained ORM pins into repository-local runtimes."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smp.environment import local_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', default='python3.13')
    args = parser.parse_args()
    env = local_env()
    env['XDG_CACHE_HOME'] = str(ROOT / '.cache/orm')
    for label in ('django-current', 'django-previous', 'alembic'):
        folder = ROOT / 'runners/orm' / label
        subprocess.run([args.python, '-m', 'venv', str(folder / '.venv')], env=env, check=True)
        requirements = folder / 'requirements.lock'
        subprocess.run([str(folder / '.venv/bin/python'), '-m', 'pip', 'install', '--no-cache-dir',
                        '-r', str(requirements)], cwd=ROOT, env=env, check=True)
    subprocess.run(['npm', 'ci', '--no-audit', '--no-fund'], cwd=ROOT / 'runners/prisma', env=env, check=True)


if __name__ == '__main__':
    main()
