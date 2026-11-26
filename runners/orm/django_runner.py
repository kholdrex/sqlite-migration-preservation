"""Run autodetection and migrations through Django management commands."""
import io
import json
import os
from pathlib import Path
import sqlite3
import sys

work, action = Path(sys.argv[1]).resolve(), sys.argv[2]
sys.path.insert(0, str(work))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import django

django.setup()
from django.core.management import call_command
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

if action == 'generate':
    call_command('makemigrations', 'matrixapp', interactive=False, verbosity=0)
elif action == 'sql':
    stream = io.StringIO()
    call_command('sqlmigrate', 'matrixapp', '0002', stdout=stream)
    (work / 'migration.sql').write_text(stream.getvalue())
else:
    connection.ensure_connection()
    recorder = MigrationRecorder(connection)
    recorder.ensure_schema()
    recorder.record_applied('matrixapp', '0001_initial')
    executed = []
    connection.connection.set_trace_callback(executed.append)
    metadata = {'django': django.get_version(), 'sqlite': sqlite3.sqlite_version,
                'foreign_keys_before': connection.connection.execute('PRAGMA foreign_keys').fetchone()[0]}
    try:
        call_command('migrate', interactive=False, verbosity=0)
        metadata['success'] = True
    except Exception as exc:
        metadata.update(success=False, error=f'{type(exc).__name__}: {exc}')
    metadata['foreign_keys_after'] = connection.connection.execute('PRAGMA foreign_keys').fetchone()[0]
    connection.connection.set_trace_callback(None)
    (work / 'executed.sql').write_text('\n'.join(s.rstrip(';') + ';' for s in executed))
    (work / 'runner.json').write_text(json.dumps(metadata))
    connection.close()
