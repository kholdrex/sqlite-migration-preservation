"""Use Alembic's command API with its default transaction configuration."""
import json
from pathlib import Path
import sqlite3
import sys

import alembic
from alembic import command
from alembic.config import Config
import sqlalchemy as sa

work, database = Path(sys.argv[1]), Path(sys.argv[2])
executed = []
engine = sa.create_engine('sqlite:///' + str(database))
with engine.connect() as connection:
    raw = connection.connection.driver_connection
    raw.execute('PRAGMA foreign_keys=ON')
    metadata = {'alembic': alembic.__version__, 'sqlalchemy': sa.__version__,
                'sqlite': sqlite3.sqlite_version, 'foreign_keys_before': raw.execute('PRAGMA foreign_keys').fetchone()[0]}
    raw.set_trace_callback(executed.append)
    cfg = Config()
    cfg.set_main_option('script_location', str(work / 'migration'))
    cfg.attributes['connection'] = connection
    try:
        command.upgrade(cfg, 'head')
        metadata['success'] = True
    except Exception as exc:
        metadata.update(success=False, error=f'{type(exc).__name__}: {exc}')
        connection.rollback()
    metadata['foreign_keys_after'] = raw.execute('PRAGMA foreign_keys').fetchone()[0]
    raw.set_trace_callback(None)
engine.dispose()
(work / 'executed.sql').write_text('\n'.join(s.rstrip(';') + ';' for s in executed))
(work / 'runner.json').write_text(json.dumps(metadata))
