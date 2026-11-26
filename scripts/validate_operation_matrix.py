"""Validate matrix coverage, trial evidence and classifications."""
import argparse
import json
import sys
import sqlite3
from contextlib import closing
from functools import lru_cache
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smp import generate
from smp.matrix_spec import cases, fixture
from smp.checks import canonical_sql, identifier, require
from smp.operation_matrix import read_gzip
from smp.preservation import classify, digest, expected_present, violations
from smp.rebuild import CLASSIFIER, rebuild, recorded_rebuild

# Kit 1.0 writes the unique index of this fixture as an inline constraint, so the generated starting schema
# differs from the fixture in that one object. The paper leaves these cells out (results/rerun-2026-11-01/README.md).
INLINE_UNIQUE = ("v1-rc5", "drop_unique")
NAMED_UNIQUE = canonical_sql("CREATE UNIQUE INDEX parents_value_unique ON parents(value)")


def schema_signature(sql):
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(sql)
        tables = {}
        for name, in db.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name"):
            columns = [list(row) for row in db.execute(f"PRAGMA table_info({identifier(name)})")]
            for column in columns:
                column[2] = column[2].upper()
                if column[5]:
                    column[3] = 1  # INTEGER PRIMARY KEY is non-null, with or without redundant NOT NULL.
            foreign_keys = sorted([list(row)[2:] for row in db.execute(f"PRAGMA foreign_key_list({identifier(name)})")])
            tables[name] = {"columns": columns, "foreign_keys": foreign_keys}
        indexes = {name: canonical_sql(sql) for name, sql in db.execute("SELECT name,sql FROM sqlite_schema WHERE type='index'")
                   if name != "idx_external"}
        return {"tables": tables, "indexes": indexes}


def inline_unique_on_value(sql):
    """Name of the index of an inline UNIQUE constraint on parents(value) alone."""
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(sql)
        for _, name, unique, origin, partial in db.execute("PRAGMA index_list(parents)"):
            columns = [row[2] for row in db.execute(f"PRAGMA index_info({identifier(name)})")]
            if unique and origin == "u" and not partial and columns == ["value"]:
                return name


def history_sql(generation, revision):
    return generate.history_sql({name.removeprefix("history/"): text for name, text in generation.items()
                                 if name.startswith("history/")}, revision)


@lru_cache(maxsize=None)
def validate_generation(archive, schema, inline_unique=False):
    """The generation archive and whether its starting schema has the inline constraint instead of the named index."""
    generation = read_gzip(archive)
    generated = history_sql(generation, "before")
    expected, actual = schema_signature(schema), schema_signature(generated)
    differs = expected != actual
    if differs and inline_unique:
        require(expected["indexes"].pop("parents_value_unique", None) == NAMED_UNIQUE, archive)
        require(actual["indexes"].pop(inline_unique_on_value(generated), None) == [], archive)
    require(expected == actual, archive)
    return generation, differs


def validate(result, complete=True):
    rows = result["rows"]
    require(rows, "No rows to validate")
    keys = {(r["framework"], r["operation"], r["context"], r["version_label"], r["path"]) for r in rows}
    require(len(keys) == len(rows), "Duplicate rows")
    require(not result["errors"], result["errors"])
    if complete:
        selection = result.get("selection", {})
        expected = {(fw, op, ctx, pin, path) for fw, op, ctx in cases() for pin in result["pins"][fw]
                    if (not selection.get("frameworks") or fw in selection["frameworks"])
                    and (not selection.get("operations") or op in selection["operations"])
                    and (not selection.get("contexts") or ctx in selection["contexts"])
                    and (not selection.get("labels") or pin in selection["labels"])
                    for path in (("rails",) if fw == "rails" else ("drizzle", "raw", "raw-tx"))}
        require(keys == expected, f"Coverage mismatch: missing {expected - keys}; extra {keys - expected}")
    support, inline_unique = set(), set()
    rebuilt = rebuild if result.get("rebuild_classifier") == CLASSIFIER else recorded_rebuild
    for row in rows:
        spec, schema, seed = fixture(row["framework"], row["operation"], row["context"])
        evidence = read_gzip(ROOT / row["artifacts"])
        require(evidence["row"] == row)
        require(evidence["spec"] == spec and evidence["schema"] == schema and evidence["seed"] == seed)
        require(row["outcome"] == row["trials"]["populated"]["outcome"])
        require(row["rebuild"] == row["trials"]["populated"]["rebuild"])
        for population, trial in row["trials"].items():
            before, after, execution = trial["before"], trial["after"], trial["execution"]
            require(not expected_present(before, spec["expected"]))
            require(execution["foreign_keys_before"] == 1)
            if row["path"] == "drizzle":
                require(all(execution[k] == v for k, v in result["pins"]["drizzle"][row["version_label"]].items()))
            elif row["path"] == "rails":
                require(execution["activerecord"] == result["pins"]["rails"][row["version_label"]]["activerecord"])
                if row["version_label"] not in ("before", "current"):
                    pin = result["upstream_fixes"][row["version_label"]]
                    require(execution["activerecord_revision"] == pin["commit"])
                    require(execution["adapter_sha256"] == pin["adapter_sha256"])
            found = violations(before, after, spec, execution)
            require(found == trial["violations"], row["artifacts"])
            require(classify(execution["success"], found, before, after) == trial["outcome"])
            require(rebuilt(evidence["evidence"][population]["executed.sql"]) == trial["rebuild"])
            for observation in (before, after):
                for data in list(observation["content"].values()) + list(observation["view_rows"].values()):
                    if "rows" in data:
                        require(digest(data["rows"]) == data["digest"])
            if population == "populated" and execution["success"] and expected_present(after, spec["expected"]):
                support.add((row["framework"], row["operation"], row["version_label"], row["path"]))
        detectors = row["detectors"]
        require(detectors["empty_db"] == (not row["trials"]["empty"]["execution"]["success"]))
        require(detectors["populated_invariants"] == bool(row["trials"]["populated"]["violations"]))
        for lint in detectors["lint"].values():
            require(lint["available"], lint)
            require(lint["detected"] == bool(lint["output"]["findings"]))
        if row["framework"] == "drizzle":
            archive = (ROOT / row["artifacts"]).parent / f"{row['case']}--{row['version_label']}--generation.json.gz"
            generation, differs = validate_generation(archive, schema, (row["version_label"], row["operation"]) == INLINE_UNIQUE)
            if differs:
                inline_unique.add(archive)
            for population in ("populated", "empty"):
                require(evidence["evidence"][population]["migration.sql"] == history_sql(generation, "after"))
    if complete:
        require(support == {(fw, op, pin, path) for fw, op, _, pin, path in keys}, "Operation support not established")
    return {"pairs_validated": len(rows), "executions": len(rows) * 2, "coverage_complete": complete,
            "outcomes": dict(Counter(r["outcome"] for r in rows)),
            "empty_outcomes": dict(Counter(r["trials"]["empty"]["outcome"] for r in rows)),
            **({"starting_schemas_with_inline_unique": len(inline_unique)} if inline_unique else {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--subset", action="store_true")
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    print(json.dumps(validate(result, not args.subset), indent=2))


if __name__ == "__main__":
    main()
