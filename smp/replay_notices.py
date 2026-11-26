import hashlib
import json
import re
from pathlib import Path

from .environment import ROOT


def publication_notices(row, root=None):
    root = Path(root or ROOT).resolve()
    repo = row['repo']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or '..' in repo.split('/'):
        raise ValueError('Invalid repository name in notice lookup')
    path = root / 'licenses/replay' / repo.replace('/', '__') / 'provenance.json'
    if not path.is_file():
        return None
    record = json.loads(path.read_text())
    if record.get('repo') != repo or record.get('commit') != row.get('commit'):
        return None
    applicable = False
    for notice in record['files']:
        local = (root / notice['file']).resolve()
        if not local.is_relative_to(path.parent.resolve()) or not local.is_file():
            raise ValueError(f'Missing pinned notice: {notice["file"]}')
        if hashlib.sha256(local.read_bytes()).hexdigest() != notice['sha256']:
            raise ValueError(f'Pinned notice hash mismatch: {notice["file"]}')
        source = Path(notice['path'])
        if re.match(r'^(licen[sc]e|copying)([._-]|$)', source.name, re.I):
            applicable |= Path(row['migration_file']).is_relative_to(source.parent)
    if not applicable or record.get('mode') != 'full':
        return None
    return {'file': path.relative_to(root).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'commit': record['commit']}
