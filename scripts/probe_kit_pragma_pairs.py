"""Check which rebuilds in one generated Drizzle file run with foreign keys disabled."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smp.checks import statements
from smp.generate import generate, history_sql
from smp.environment import cache_dir, scratch_scope

# Two rebuilds in one diff; the cascade parent sorts after the unrelated table.
SCHEMA = """import {{ sqliteTable, integer, text }} from 'drizzle-orm/sqlite-core';
export const aFirst = sqliteTable('a_first', {{ id: integer('id').primaryKey(), name: text('name').default('{d}') }});
export const parents = sqliteTable('parents', {{ id: integer('id').primaryKey(), name: text('name').default('{d}') }});
export const children = sqliteTable('children', {{ id: integer('id').primaryKey(),
  parentId: integer('parent_id').notNull().references(() => parents.id, {{ onDelete: 'cascade' }}) }});
"""
SEED = ("INSERT INTO a_first VALUES (1, 'z');", "INSERT INTO parents VALUES (1, 'x'), (2, 'y');",
        "INSERT INTO children VALUES (1, 1), (2, 2), (3, 2);")


def disabled_drops(sql):
    """Tables dropped while the file's own pragmas leave foreign keys disabled."""
    enabled, dropped = True, {}
    for statement in statements(sql):
        statement = re.sub(r"^\s*-->[^\n]*\n", "", statement).strip()
        pragma = re.match(r"PRAGMA\s+foreign_keys\s*=\s*(\w+)", statement, re.I)
        if pragma:
            enabled = pragma.group(1).upper() in ("ON", "1")
        drop = re.match(r"DROP TABLE\s+[`\"]?(\w+)", statement, re.I)
        if drop:
            dropped[drop.group(1)] = not enabled
    return dropped


def replay(initial, upgrade, transactional):
    db = sqlite3.connect(":memory:", isolation_level=None)
    for statement in statements(initial):
        db.execute(statement)
    db.execute("PRAGMA foreign_keys=ON")
    for statement in SEED:
        db.execute(statement)
    if transactional:
        db.execute("BEGIN")
    for statement in statements(upgrade):
        db.execute(statement)
    if transactional:
        db.execute("COMMIT")
    counts = {t: db.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("a_first", "parents", "children")}
    db.close()
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/kit_pragma_pairs.json")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        parser.error("Output must be inside the repository")
    if output.exists():
        parser.error("Use a fresh output file")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = cache_dir() / "kit-pragma-pairs" / scratch_scope(output)
    if work.exists():
        shutil.rmtree(work)
    case = work / "case"
    case.mkdir(parents=True)
    (case / "before.ts").write_text(SCHEMA.format(d="a"))
    (case / "after.ts").write_text(SCHEMA.format(d="b"))
    (case / "case.json").write_text(json.dumps({"id": "kit_pragma_pairs", "before": "before.ts", "after": "after.ts"}))
    pins = json.loads((ROOT / "versions.json").read_text())["drizzle"]
    results = []
    for label in ("current", "v1-rc5"):
        generated = generate(case, label, scope=scratch_scope(output))
        history = {p.relative_to(generated / "history").as_posix(): p.read_text()
                   for p in (generated / "history").rglob("*.sql")}
        initial, upgrade = history_sql(history, "before"), history_sql(history, "after")
        results.append({
            "label": label, "pins": pins[label], "upgrade_sql": upgrade,
            "pragma_statements": len(re.findall(r"PRAGMA\s+foreign_keys", upgrade, re.I)),
            "drop_with_foreign_keys_disabled": disabled_drops(upgrade),
            "autocommit": replay(initial, upgrade, False),
            "transaction": replay(initial, upgrade, True),
        })
        shutil.rmtree(generated)
    shutil.rmtree(work)
    result = {"seed_rows": {"a_first": 1, "parents": 2, "children": 3}, "sqlite": sqlite3.sqlite_version, "results": results}
    output.write_text(json.dumps(result, indent=2) + "\n")
    for r in results:
        print(r["label"], r["drop_with_foreign_keys_disabled"], "autocommit", r["autocommit"], "transaction", r["transaction"])


if __name__ == "__main__":
    main()
