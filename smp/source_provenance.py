import hashlib
import json
from pathlib import Path

from .environment import ROOT


def verify_sources(hashes, root=None, required=()):
    """Check recorded source hashes against sources/replay-validation/ or, failing that, the current files.

    The hash of a protocol text is not checked: the texts the retained runs recorded are not published.
    """
    hashes = {name: digest for name, digest in (hashes or {}).items() if not name.startswith('PROTOCOL_')}
    if not hashes:
        raise ValueError('source hash manifest is empty')
    missing = sorted(set(required) - set(hashes))
    if missing:
        raise ValueError('source hash manifest lacks ' + ', '.join(missing))
    root = Path(root or ROOT).resolve()
    index = root / 'sources/replay-validation/index.json'
    records = json.loads(index.read_text()) if index.exists() else []
    for record in records:
        if any(record['source_hashes'].get(name) != digest for name, digest in hashes.items()):
            continue
        directory = (root / record['directory']).resolve()
        if not directory.is_relative_to(root / 'sources/replay-validation'):
            raise ValueError('Source snapshot escapes its archive directory')
        for name, digest in hashes.items():
            path = (directory / name).resolve()
            if not path.is_relative_to(directory) or not path.is_file():
                raise ValueError(f'Missing archived source: {name}')
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError(f'Archived source hash mismatch: {name}')
        return {'kind': 'retained source files', 'directory': record['directory'], 'files_verified': len(hashes)}
    for name, digest in hashes.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'No matching source snapshot; current source differs: {name}')
    return {'kind': 'current files', 'files_verified': len(hashes)}

