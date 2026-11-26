"""Failure injection after a C1 parent rebuild, observed from a fresh connection."""
import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .checks import canonical_sql, create_database, identifier, require
from .environment import ROOT, cache_dir
from .operation_matrix import read_gzip, write_gzip
from .pins import upstream_provenance
from .report import OMITTED, digest
from .runners import execute

LABELS = ("current", "rails-pr57128", "rails-pr58709", "rails-pr56811",
          "rails-pr57128+56811", "rails-pr58709+56811")
VERSION = "20261010000001"
SCHEMA = """CREATE TABLE parents(id INTEGER PRIMARY KEY, payload TEXT NOT NULL, value TEXT DEFAULT '5');
CREATE TABLE children(id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL REFERENCES parents(id) ON DELETE CASCADE, payload TEXT NOT NULL);
CREATE TABLE markers(id INTEGER PRIMARY KEY, note TEXT NOT NULL);
CREATE TABLE schema_migrations(version VARCHAR NOT NULL PRIMARY KEY);
"""
SEED = """INSERT INTO parents VALUES(1,'alpha','11'),(2,'beta','22');
INSERT INTO children VALUES(1,1,'one'),(2,2,'two'),(3,2,'three');
INSERT INTO markers VALUES(1,'original');
INSERT INTO schema_migrations VALUES('20260101000000');
"""


def scenarios():
    for transactional in (True, False):
        for precursor in ("data", "schema"):
            for failure in ("raise", "not_null"):
                yield {"id": f"{'transaction' if transactional else 'no_transaction'}_{precursor}_{failure}",
                       "transactional": transactional, "precursor": precursor, "failure": failure}


def migration(spec):
    precursor = ('execute "UPDATE markers SET note = \'written before rebuild\' WHERE id = 1"'
                 if spec["precursor"] == "data" else
                 'add_column :markers, :stage_note, :text, default: "added before rebuild"')
    failure = ('raise "atomicity injected failure"' if spec["failure"] == "raise" else
               'execute "UPDATE parents SET payload = NULL WHERE id = 1"')
    disable = "" if spec["transactional"] else "  disable_ddl_transaction!\n"
    return f'''class AtomicityFailure < ActiveRecord::Migration[8.1]
{disable}  def up
    {precursor}
    change_column_default :parents, :value, from: "5", to: "9"
    state = {{
      parents: connection.select_all("SELECT * FROM parents ORDER BY id").to_a,
      children: connection.select_all("SELECT * FROM children ORDER BY id").to_a,
      markers: connection.select_all("SELECT * FROM markers ORDER BY id").to_a,
      parent_default: connection.columns(:parents).find {{ |column| column.name == "value" }}.default,
      schema_migrations: connection.select_values("SELECT version FROM schema_migrations ORDER BY version")
    }}
    File.write(File.join(__dir__, "after_rebuild.json"), JSON.pretty_generate(state))
    {failure}
  end
end
'''


def observe(database):
    with closing(sqlite3.connect(database)) as db:
        tables = [name for name, in db.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name")
                  if not name.startswith("sqlite_") and name != "ar_internal_metadata"]
        rows, columns = {}, {}
        for table in tables:
            query = db.execute(f"SELECT * FROM {identifier(table)} ORDER BY 1")
            names = [column[0] for column in query.description]
            rows[table] = [dict(zip(names, row)) for row in query]
            columns[table] = [dict(zip(("cid", "name", "type", "notnull", "default", "pk"), row))
                              for row in db.execute(f"PRAGMA table_info({identifier(table)})")]
        schema = {f"{kind}:{name}": sql for kind, name, table, sql in db.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name")
                  if table in tables and not name.startswith("sqlite_")}
        return {"rows": rows, "columns": columns, "schema": schema,
                "foreign_key_check": [list(row) for row in db.execute("PRAGMA foreign_key_check")],
                "integrity_check": [row[0] for row in db.execute("PRAGMA integrity_check")],
                "observer_sqlite": sqlite3.sqlite_version}


def assess(before, after):
    """Separate surviving intended changes from damage to pre-existing data."""
    data_loss = []
    for table in ("parents", "children"):
        old = {r["id"]: r for r in before["rows"][table]}
        new = {r["id"]: r for r in after["rows"].get(table, [])}
        for key, row in old.items():
            if new.get(key) != row:
                data_loss.append({"table": table, "id": key, "before": row, "after": new.get(key)})
    schema_changed = {name for name in before["schema"] | after["schema"]
                      if canonical_sql(before["schema"].get(name)) != canonical_sql(after["schema"].get(name))}
    rows_changed = {table for table in before["rows"] | after["rows"]
                    if before["rows"].get(table) != after["rows"].get(table)}
    versions_same = (before["rows"]["schema_migrations"] == after["rows"].get("schema_migrations")
                     and "table:schema_migrations" not in schema_changed)
    marker = next((r for r in after["rows"].get("markers", []) if r["id"] == 1), {})
    default = next((c["default"] for c in after["columns"].get("parents", []) if c["name"] == "value"), None)
    survivors = {"precursor_data": marker.get("note") == "written before rebuild",
                 "precursor_schema": any(c["name"] == "stage_note" for c in after["columns"].get("markers", [])),
                 "rebuilt_parent_default": default in ("'9'", '"9"', "9")}
    classification = ("data loss" if data_loss else "partially committed" if schema_changed or rows_changed
                      else "fully rolled back")
    return {"classification": classification, "surviving_changes": survivors,
            "changed_schema_objects": sorted(schema_changed), "changed_row_tables": sorted(rows_changed),
            "schema_migrations_unchanged": versions_same, "data_loss": data_loss}


def run_trial(label, spec, output):
    source = migration(spec)
    archive = output / "rails-atomicity" / f"{spec['id']}--{label}.json.gz"
    if archive.exists():
        saved = read_gzip(archive)
        require(saved["schema"] == SCHEMA and saved["seed"] == SEED and saved["migration"] == source)
        validate_row(saved["row"], saved)
        return saved["row"]
    with tempfile.TemporaryDirectory(prefix="rails-atomicity-", dir=cache_dir()) as temporary:
        work = Path(temporary)
        migrations = work / "migrations"
        migrations.mkdir()
        (migrations / f"{VERSION}_atomicity_failure.rb").write_text(source)
        database = work / "database.db"
        create_database(database, SCHEMA, SEED, True)
        before = observe(database)
        execution = execute(work, {"migration": "migrations"}, "rails", label, database, work)
        stage = migrations / "after_rebuild.json"
        if not stage.exists():
            raise RuntimeError(f"Did not reach the injected failure for {label}/{spec['id']}: {execution}")
        after = observe(database)
        row = {"version_label": label, "scenario": spec, "execution": execution,
               "before": before, "after_rebuild": json.loads(stage.read_text()), "after": after,
               "assessment": assess(before, after), "artifacts": str(archive.relative_to(ROOT))}
        evidence = {p.name: p.read_text() for p in work.iterdir() if p.suffix in (".sql", ".json", ".log")}
        saved = {"row": row, "schema": SCHEMA, "seed": SEED, "migration": source, "evidence": evidence}
        validate_row(row, saved)
        write_gzip(archive, saved)
        return row


def validate_row(row, saved):
    require(saved["row"] == row)
    require(saved["schema"] == SCHEMA and saved["seed"] == SEED)
    require(saved["migration"] == migration(row["scenario"]))
    require(row["assessment"] == assess(row["before"], row["after"]))
    execution = row["execution"]
    require(not execution["success"] and execution["returncode"] == 1)
    expected = "atomicity injected failure" if row["scenario"]["failure"] == "raise" else "NOT NULL constraint failed: parents.payload"
    require(expected in execution["error"], execution)
    require(execution["foreign_keys_before"] == execution["foreign_keys_after"] == 1)
    pins = json.loads((ROOT / "versions.json").read_text())["rails"][row["version_label"]]
    require(execution["activerecord"] == pins["activerecord"] and execution["sqlite3_gem"] == pins["sqlite3"])
    provenance = upstream_provenance("rails", row["version_label"])
    if provenance:
        pin = provenance[row["version_label"]]
        require(execution["activerecord_revision"] == pin["commit"])
        require(execution["adapter_sha256"] == pin["adapter_sha256"])
    require(row["after_rebuild"]["parent_default"] == "9")
    events = json.loads(saved["evidence"]["events.json"])
    require(any(e["sql"] == 'DROP TABLE "parents"' for e in events))
    runner = json.loads(saved["evidence"]["runner.json"])
    require(runner == {k: v for k, v in execution.items() if k != "returncode"})
    for phase in ("before", "after"):
        require(row[phase]["foreign_key_check"] == [] and row[phase]["integrity_check"] == ["ok"])


def run(output, labels=LABELS):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Output must be inside the repository")
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for label in labels:
        for spec in scenarios():
            row = run_trial(label, spec, output)
            rows.append(row)
            print(f"{label} / {spec['id']}: {row['assessment']['classification']}", flush=True)
    result = {"format_version": 1, "observed_at": datetime.now(timezone.utc).isoformat(),
              "migration_version": VERSION, "populated": True, "context": "C1",
              "pins": {p: v for p, v in json.loads((ROOT / "versions.json").read_text())["rails"].items() if p in labels},
              "upstream_fixes": {p: v for p, v in json.loads((ROOT / "sources/upstream_fixes.json").read_text()).items() if p in labels},
              "rows": rows}
    result["runtime_code"] = runtime_code(rows)
    (output / "rails_atomicity.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def runtime_code(rows):
    sources = {}
    for label in dict.fromkeys(r["version_label"] for r in rows):
        execution = next(r["execution"] for r in rows if r["version_label"] == label)
        if "adapter_source" in execution:
            adapter = Path(execution["adapter_source"])
        else:
            adapter = next((ROOT / "vendor/bundle/ruby").glob(
                f"*/gems/activerecord-{execution['activerecord']}/lib/active_record/connection_adapters/sqlite3_adapter.rb"))
        gem = adapter.parents[3]
        files = {}
        for source, starts, width in ((adapter, ("restart = open_transactions", "def transaction_for_migration"), 16),
                                      (gem / "lib/active_record/migration.rb", ("def ddl_transaction",), 13)):
            content = source.read_text().splitlines()
            excerpts = []
            for index, line in enumerate(content):
                if any(start in line for start in starts):
                    excerpts.append({"first_line": index + 1, "lines": content[index:index + width]})
            files[str(source.relative_to(gem))] = {"sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                                                   "excerpts": excerpts}
        sources[label] = files
    return sources


def attach_report(output, result):
    from .rails_fixes import write_report
    output = Path(output)
    path = output / "rails_fixes.json"
    if path.exists():
        matrix = json.loads(path.read_text())
        matrix["atomicity"] = result
        path.write_text(json.dumps(matrix, separators=(",", ":")) + "\n")
        write_report(matrix, output / "rails_fixes.md")


ATOMICITY_OUTCOMES = "6babfca2d4280f730896a57b989e84ec3e8cb759ee7e9748943e8f2195b44bb1"


def atomicity_outcomes(rows):
    return digest(sorted([r["version_label"], r["scenario"]["id"], r["assessment"]["classification"],
                          r["assessment"]["surviving_changes"], r["assessment"]["schema_migrations_unchanged"],
                          len(r["after_rebuild"]["children"]), len(r["after"]["rows"]["children"])] for r in rows))


def report_lines(result):
    rows = result["rows"]
    recorded = atomicity_outcomes(rows) == ATOMICITY_OUTCOMES
    lines = ["## Failure injection: migration atomicity", "",
             f"Observed: {result['observed_at']}. {len(rows)} executions across "
             f"{len({r['version_label'] for r in rows})} pins, all starting with "
             "two parents, three C1 cascade children and a marker row.", "",
             "Each migration first updates `markers.note` to `written before rebuild` (data variant), or adds "
             "`markers.stage_note` with default `added before rebuild` (schema variant). It then runs "
             "`change_column_default :parents, :value, from: '5', to: '9'`, which rebuilds the parent. "
             "After recording the in-transaction state, it either raises `atomicity injected failure` or "
             "executes `UPDATE parents SET payload = NULL WHERE id = 1`, violating NOT NULL. "
             "All four combinations also run with `disable_ddl_transaction!`, giving eight variants per pin.", "",
             "For a transactional migration, the expected result is the original application rows and schema, "
             "including parent default '5', and unchanged `schema_migrations`. The latter is pre-created and "
             "seeded with version `20260101000000`; the failed migration is `20261010000001`. "
             "The observer reopens the database after the runner disconnects. Full rows, table definitions, "
             "column metadata, FK/integrity checks, failure messages and exact SQL are retained. "
             "`ar_internal_metadata` and SQLite internal tables are excluded from application comparison; "
             "`schema_migrations` rows and definition are included.", "",
             "`Fully rolled back` means persisted rows and schema match the starting state. "
             "`Partially committed` means intended changes survive the error. `Data loss` takes precedence "
             "if existing parent or child rows disappear or change; the JSON retains individual damaged rows "
             "and surviving intended changes. A transient loss that is restored by rollback is reported "
             "separately from persisted damage.", "",
             "### Transactional variants", "",
             "| Pin | Data + raise | Data + NOT NULL | Schema + raise | Schema + NOT NULL |",
             "|---|---|---|---|---|"]
    lookup = {(r["version_label"], r["scenario"]["id"]): r for r in rows}
    for label in LABELS:
        values = [lookup[label, f"transaction_{precursor}_{failure}"]["assessment"]["classification"]
                  for precursor in ("data", "schema") for failure in ("raise", "not_null")]
        lines.append(f"| {label} | " + " | ".join(values) + " |")
    lines += ["", "### Surviving changes", "",
              *(["Both failure types have the same result for a given pin and precursor. The SQL failure "
                 "itself does not persist a NULL parent payload."] if recorded else [OMITTED]), "",
              "| Pin | Transactional data variant | Transactional schema variant | Children after failure | schema_migrations |",
              "|---|---|---|---|---|"]
    for label in LABELS:
        data = lookup[label, "transaction_data_raise"]
        schema = lookup[label, "transaction_schema_raise"]
        def survived(row):
            names = {"precursor_data": "marker write", "precursor_schema": "marker column", "rebuilt_parent_default": "parent default '9'"}
            return ", ".join(names[k] for k, value in row["assessment"]["surviving_changes"].items() if value) or "none"
        lines.append(f"| {label} | {survived(data)} | {survived(schema)} | {len(data['after']['rows']['children'])}/3 | "
                     + ("unchanged" if data["assessment"]["schema_migrations_unchanged"] else "changed") + " |")
    findings = ["", "#57128 and #57128 + #56811 persist both the precursor and the completed parent rebuild "
              "despite the error. The failed migration version is absent, so migration bookkeeping does not "
              "signal the already committed application changes. Current, #56811, #58709 and #58709 + #56811 "
              "roll back all four transactional variants completely.", "",
              "Current and #56811 have zero children at the after-rebuild checkpoint in transactional "
              "variants: the rebuild did cascade-delete them. Their final ROLLBACK restores all three. "
              "The other four pins retain all children even at that checkpoint. Across these 48 failures, "
              "no pin leaves persisted parent/child data loss, FK violations or integrity errors. "
              "Every execution reaches the intended failure and finishes with foreign_keys ON.", "",
              "### Transaction boundaries and responsible code", "",
              "For transactional #57128 and its trigger-preserving combination, the trace is "
              "`BEGIN → precursor → COMMIT → SAVEPOINT → rebuild → RELEASE → BEGIN → failure → ROLLBACK`. "
              "The first COMMIT makes the precursor durable. With no outer database transaction open, "
              "releasing that outermost savepoint commits the rebuild. The final ROLLBACK cannot undo either. "
              "The adapter explicitly does this at "
              "[#57128 lines 704–718](https://github.com/emirn/rails/blob/8823c1370c7bc8910e609d1b6f27f4fc34f3d81d/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L704):", "",
              "```ruby", "restart = open_transactions == 1 && current_transaction.joinable? && referenced_by_destructive_foreign_key?(table_name)",
              "commit_db_transaction", "transaction(requires_new: restart) do", "# ...", "begin_db_transaction if restart", "```", "",
              "These are excerpts, not a contiguous replacement method. The combined adapter retains this "
              "code at lines 705–720; its only additional rebuild statement restores triggers. "
              "Exact numbered runtime excerpts and full-file hashes for all six pins are in "
              "[rails_atomicity.json](rails_atomicity.json).", "",
              "#58709 and #58709 + #56811 instead trace "
              "`foreign_keys=OFF → BEGIN → precursor → rebuild → failure → ROLLBACK → foreign_keys=ON`, "
              "with no intervening COMMIT or SAVEPOINT. Migrator calls "
              "`connection.transaction_for_migration(&block)` "
              "([line 1607](https://github.com/nicolasva/rails/blob/428884a88b3a42c914f5227819b6b672325b3312/activerecord/lib/active_record/migration.rb#L1607)), "
              "whose SQLite implementation wraps `transaction(&block)` in `disable_referential_integrity` "
              "([adapter lines 201–205](https://github.com/nicolasva/rails/blob/428884a88b3a42c914f5227819b6b672325b3312/activerecord/lib/active_record/connection_adapters/sqlite3_adapter.rb#L201)). "
              "These runs demonstrate rollback for the tested writes and rebuild, including a database error."]
    lines += findings if recorded else []
    lines += ["", "### Explicitly disabled migration transactions", "",
              "| Pin | Partial commits | Full rollbacks | Persisted data-loss trials | schema_migrations unchanged |",
              "|---|---:|---:|---:|---:|"]
    for label in LABELS:
        selected = [r for r in rows if r["version_label"] == label and not r["scenario"]["transactional"]]
        counts = [sum(r["assessment"]["classification"] == outcome for r in selected)
                  for outcome in ("partially committed", "fully rolled back", "data loss")]
        lines.append(f"| {label} | {counts[0]}/4 | {counts[1]} | {counts[2]} | "
                     f"{sum(r['assessment']['schema_migrations_unchanged'] for r in selected)}/4 |")
    lines += ["", *(["All six pins retain the marker write or added marker column and the parent default '9' "
              "in all four no-transaction variants. All three children survive. "] if recorded else []),
              "With transactions disabled the precursor is autocommitted and "
              "the adapter commits its own rebuild transaction before the injected failure, so no migration "
              "transaction remains to roll back. "
              "The responsible Migrator guard is "
              "`!migration.disable_ddl_transaction && connection.supports_ddl_transactions?`; when false, "
              "`ddl_transaction` simply executes `yield` "
              "([#58709 lines 1605–1614](https://github.com/nicolasva/rails/blob/428884a88b3a42c914f5227819b6b672325b3312/activerecord/lib/active_record/migration.rb#L1605)). "
              "Equivalent guards are retained in the other pins' runtime excerpts.", "",
              "The experiment covers one rebuild and two precursor/failure types with C1 populated fixtures. "
              "It does not establish behavior for nested transactions, concurrent connections, multiple rebuilds "
              "or every migration operation. Compressed per-trial evidence is linked by the raw rows under "
              "`results/rails-atomicity/`; temporary databases are removed after observation.", ""]
    return lines


def validate(result):
    keys = {(r["version_label"], r["scenario"]["id"]) for r in result["rows"]}
    require(keys == {(label, spec["id"]) for label in LABELS for spec in scenarios()})
    require(len(keys) == len(result["rows"]))
    require(set(result["runtime_code"]) == set(LABELS))
    require(result["migration_version"] == VERSION and result["context"] == "C1" and result["populated"])
    pins = json.loads((ROOT / "versions.json").read_text())["rails"]
    fixes = json.loads((ROOT / "sources/upstream_fixes.json").read_text())
    require(result["pins"] == {label: pins[label] for label in LABELS})
    require(result["upstream_fixes"] == {label: fixes[label] for label in LABELS if label != "current"})
    for row in result["rows"]:
        require(row["scenario"] in list(scenarios()))
        validate_row(row, read_gzip(ROOT / row["artifacts"]))
    for label, files in result["runtime_code"].items():
        if label != "current":
            require(files["lib/active_record/connection_adapters/sqlite3_adapter.rb"]["sha256"] == result["upstream_fixes"][label]["adapter_sha256"])
    return {"executions_validated": len(keys), "fully_rolled_back": sum(r["assessment"]["classification"] == "fully rolled back" for r in result["rows"]),
            "partially_committed": sum(r["assessment"]["classification"] == "partially committed" for r in result["rows"]),
            "data_loss": sum(r["assessment"]["classification"] == "data loss" for r in result["rows"])}
