"""Small deterministic, constraint-aware synthetic SQLite fixtures."""
import itertools
import re
import sqlite3
import random

from .checks import identifier


class SeedError(ValueError):
    pass


def tables(db):
    return [r[0] for r in db.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name")
            if not r[0].startswith(('sqlite_', '__drizzle_'))]


def columns(db, table):
    return [dict(zip(('cid', 'name', 'type', 'notnull', 'default', 'pk', 'hidden'), r))
            for r in db.execute(f'PRAGMA table_xinfo({identifier(table)})') if not r[6]]


def foreign_keys(db, table):
    groups = {}
    for row in db.execute(f'PRAGMA foreign_key_list({identifier(table)})'):
        groups.setdefault(row[0], []).append(row)
    return [sorted(rows, key=lambda r: r[1]) for rows in groups.values()]


def candidates(col, schema, index):
    name, kind = col['name'], col['type'].upper()
    # Only read schema literals belonging to this column's finite CHECK domain.
    escaped = re.escape(name)
    enum = re.search(r'["`\[]?\b' + escaped + r'\b["`\]]?\s+IN\s*\(([^)]+)\)', schema, re.I)
    values = []
    if enum:
        for token in re.findall(r"'(?:''|[^'])*'|-?\d+(?:\.\d+)?", enum[1]):
            values.append(token[1:-1].replace("''", "'") if token.startswith("'") else float(token) if '.' in token else int(token))
    if 'INT' in kind or any(t in kind for t in ('REAL', 'NUM', 'FLOAT', 'DOUBLE', 'BOOL')):
        values += [index + 1, 1, 0, 10 + index, 100 + index, -1]
    elif 'BLOB' in kind:
        values += [f'synthetic-{index + 1}'.encode()]
    else:
        if 'json' in name.lower() or re.search(r'json_valid\s*\(\s*["`]?'+escaped, schema, re.I):
            values += ['{}', '[]']
        if 'email' in name.lower():
            values += [f'synthetic-{index + 1}@example.invalid']
        values += [f'synthetic-{name}-{index + 1}', f'00000000-0000-4000-8000-{index + 1:012d}',
                   '2024-01-01T00:00:00Z', str(index + 1), '{}', '[]', 'x', '']
    if not col['pk'] and not col['notnull']:
        values.append(None)
    return list(dict.fromkeys(values))


def check_expressions(schema):
    """Extract balanced CHECK bodies, respecting SQL quoted strings/identifiers."""
    result = []
    for match in re.finditer(r'\bCHECK\s*\(', schema, re.I):
        start, depth, quote, i = match.end(), 1, None, match.end()
        while i < len(schema):
            char = schema[i]
            if quote:
                if char == quote:
                    if i + 1 < len(schema) and schema[i + 1] == quote:
                        i += 1
                    else:
                        quote = None
            elif char in "'\"`":
                quote = char
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    result.append(schema[start:i])
                    break
            i += 1
    return result


def constraint_candidates(db, table, schema, options, row_index):
    """Bounded coordinate search using SQLite itself to evaluate CHECKs."""
    checks = check_expressions(schema)
    if not checks:
        return
    keys = list(options)
    prefix = (f'WITH {identifier(table)} ({",".join(map(identifier, keys))}) AS '
             f'(VALUES ({",".join("?" for _ in keys)})) SELECT ' +
             ','.join(f'CASE WHEN ({expr}) IS FALSE THEN 1 ELSE 0 END' for expr in checks))
    query = prefix + f' FROM {identifier(table)}'
    rng = random.Random(row_index)
    try:
        for restart in range(5):
            values = [options[k][0] if restart == 0 else rng.choice(options[k]) for k in keys]
            for _ in range(40):
                failed = db.execute(query, values).fetchone()
                score = sum(failed)
                if score == 0:
                    yield tuple(values)
                    break
                best, replacements = score, []
                active = ' '.join(expr for expr, failure in zip(checks, failed) if failure)
                for i, key in enumerate(keys):
                    if not re.search(r'\b' + re.escape(key) + r'\b', active):
                        continue
                    for value in options[key]:
                        if value == values[i]:
                            continue
                        trial = values[:]
                        trial[i] = value
                        candidate_score = sum(db.execute(query, trial).fetchone())
                        if candidate_score < best:
                            best, replacements = candidate_score, [(i, value)]
                        elif candidate_score == best:
                            replacements.append((i, value))
                if not replacements:
                    break
                i, value = rng.choice(replacements)
                values[i] = value
    except sqlite3.Error:
        # Generated fields, functions or affinity-dependent checks may require
        # actual INSERT evaluation; the ordinary bounded trials remain available.
        return


def seed(db, rows_per_table=3):
    """Populate every user table, resolving FK tuples against actual parent rows.

    Nullable FKs are deliberately populated. Unsupported cycles/checks fail the
    whole seed, never silently turn a positive fixture into an empty control.
    All changes are rolled back on failure; no project seed records are used.
    """
    names = tables(db)
    if any(db.execute(f'SELECT count(*) FROM {identifier(t)}').fetchone()[0] for t in names):
        raise SeedError('history contains data; synthetic-only seeding requires empty tables')
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('SAVEPOINT synthetic_seed')
    errors = {}
    pending = list(names)
    try:
        while pending:
            progress = False
            for table in pending[:]:
                cols = columns(db, table)
                schema = db.execute('SELECT sql FROM sqlite_schema WHERE name=?', (table,)).fetchone()[0]
                fks = foreign_keys(db, table)
                if any(fk[0][2] != table and (fk[0][2] in pending or fk[0][2] not in names) for fk in fks):
                    errors[table] = 'unresolved parent or cyclic foreign keys'
                    continue
                db.execute('SAVEPOINT seed_table')
                try:
                    for n in range(rows_per_table):
                        options = {c['name']: candidates(c, schema, n) for c in cols}
                        for fk in sorted(fks, key=lambda group: group[0][2] == table):
                            parent = fk[0][2]
                            pk = [c['name'] for c in sorted(columns(db, parent), key=lambda c: c['pk']) if c['pk']]
                            targets = [r[4] or pk[r[1]] for r in fk]
                            # A self-reference can point to the row being inserted.
                            if parent == table and n == 0:
                                values = [options[t][0] for t in targets]
                            else:
                                projection = ','.join(map(identifier, targets))
                                parents = db.execute(f'SELECT {projection} FROM {identifier(parent)} ORDER BY {projection}').fetchall()
                                if not parents:
                                    raise SeedError('parent has no synthetic rows')
                                values = parents[n % len(parents)]
                            for r, value in zip(fk, values):
                                options[r[3]] = [value]
                        keys = list(options)
                        insert = f'INSERT INTO {identifier(table)} ({",".join(map(identifier, keys))}) VALUES ({",".join("?" for _ in keys)})'
                        # Try the natural row, uniform alternatives, then small
                        # combinations. Bounded search keeps arbitrary CHECKs honest.
                        natural = tuple(options[k][0] for k in keys)
                        trials = [natural]
                        for j in range(1, 12):
                            trials.append(tuple(options[k][j % len(options[k])] for k in keys))
                        for key in keys:
                            for value in options[key][1:]:
                                trials.append(tuple(value if k == key else options[k][0] for k in keys))
                        trials = itertools.chain(trials, constraint_candidates(db, table, schema, options, n),
                                                 itertools.islice(itertools.product(*(options[k] for k in keys)), 300))
                        last_error = 'no candidate'
                        for values in trials:
                            db.execute('SAVEPOINT seed_row')
                            try:
                                db.execute(insert, values)
                                db.execute('RELEASE seed_row')
                                break
                            except sqlite3.Error as exc:
                                db.execute('ROLLBACK TO seed_row')
                                db.execute('RELEASE seed_row')
                                last_error = str(exc)
                        else:
                            raise SeedError(f'{table}: {last_error}')
                    db.execute('RELEASE seed_table')
                    pending.remove(table)
                    progress = True
                except (sqlite3.Error, SeedError) as exc:
                    db.execute('ROLLBACK TO seed_table')
                    db.execute('RELEASE seed_table')
                    errors[table] = str(exc)
            if not progress:
                raise SeedError('; '.join(f'{t}: {errors.get(t, "unresolved")}' for t in pending))
        violations = db.execute('PRAGMA foreign_key_check').fetchall()
        if violations:
            raise SeedError('synthetic fixture failed foreign_key_check')
        counts = {t: db.execute(f'SELECT count(*) FROM {identifier(t)}').fetchone()[0] for t in names}
        if any(n < rows_per_table for n in counts.values()):
            raise SeedError('trigger effects left a table under-populated')
        db.execute('RELEASE synthetic_seed')
        return counts
    except Exception:
        db.execute('ROLLBACK TO synthetic_seed')
        db.execute('RELEASE synthetic_seed')
        raise
