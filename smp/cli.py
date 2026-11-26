import argparse
import json
from pathlib import Path

from .pilot import DEFAULT_DOCTOR, run_case, run_pilot
from .environment import ROOT


def main():
    parser = argparse.ArgumentParser(description="SQLite migration preservation pilot")
    sub = parser.add_subparsers(dest="command", required=True)
    realworld = sub.add_parser("realworld", help="Replay pinned public Drizzle histories with synthetic rows")
    realworld.add_argument("--input", type=Path, help="Repository/path/blob-SHA TSV")
    realworld.add_argument("--probe", type=Path, help="Probe JSON, used to prioritize cascade candidates")
    realworld.add_argument("--repo", help="One public owner/repository")
    realworld.add_argument("--migration", help="Repository-relative migration SQL path")
    realworld.add_argument("--commit", help="Full pinned commit SHA (single repository only)")
    realworld.add_argument("--orm-version", help="Exact ORM version for reproducible single-repository replay")
    realworld.add_argument("--output", type=Path, required=True)
    realworld.add_argument("--target", type=int, default=20)
    realworld.add_argument("--rows", type=int, default=3)
    realworld.add_argument("--max-repos", type=int)
    realworld.add_argument("--resume", action="store_true")
    realworld.add_argument("--pins", type=Path, help="Reuse commit and resolved ORM pins from an earlier realworld.json")
    realworld.add_argument("--evidence-dir", type=Path, help="Opt in to complete pinned rerun; full evidence goes in this ignored local directory")
    pilot = sub.add_parser("pilot", help="Run every case and execution path")
    pilot.add_argument("--output", type=Path, required=True)
    upstream = sub.add_parser("upstream-fixes", help="Run every case on its upstream-fix pins")
    upstream.add_argument("--labels", nargs="+", help="Select exact upstream pin labels")
    upstream.add_argument("--output", type=Path, required=True)
    matrix = sub.add_parser("operation-matrix", help="Run the generated operation/context matrix")
    matrix.add_argument("--output", type=Path, required=True)
    matrix.add_argument("--workers", type=int, default=6)
    rails_fixes = sub.add_parser("rails-fixes", help="Run and compare the additional Rails fix pins")
    rails_fixes.add_argument("--output", type=Path, required=True)
    rails_fixes.add_argument("--workers", type=int, default=6)
    atomicity = sub.add_parser("rails-atomicity", help="Inject failures after a C1 parent rebuild on six Rails pins")
    atomicity.add_argument("--output", type=Path, required=True)
    for name in ("frameworks", "operations", "labels", "contexts"):
        matrix.add_argument(f"--{name}", nargs="+")
    case = sub.add_parser("run", help="Run one populated/empty case pair")
    case.add_argument("case", type=Path)
    case.add_argument("--path", choices=["raw", "raw-tx", "rails", "drizzle"], required=True)
    pins = json.loads((ROOT / "versions.json").read_text())
    labels = sorted({label for framework in pins.values() for label in framework})
    case.add_argument("--version", choices=labels, default="current")
    case.add_argument("--output", type=Path, required=True)
    for command in (pilot, upstream, case, matrix, rails_fixes):
        command.add_argument("--doctor", type=Path, default=DEFAULT_DOCTOR)
    args = parser.parse_args()
    aggregate = {"pilot": "pilot.json", "upstream-fixes": "upstream_fixes.json", "rails-fixes": "rails_fixes.json",
                 "rails-atomicity": "rails_atomicity.json", "realworld": "realworld.json"}.get(args.command)
    if aggregate and (args.output / aggregate).exists() and not getattr(args, "resume", False):
        parser.error(f"{args.output} already holds {aggregate}; choose a new output directory")
    if args.command == "realworld":
        if args.rows < 1 or args.target < 1 or (args.commit and not args.repo) or (args.orm_version and not args.repo):
            parser.error("positive --rows/--target required; version/commit overrides require --repo")
        from .realworld import run
        result = run(args)
        print(json.dumps(result["summary"], indent=2))
    elif args.command == "rails-atomicity":
        from .rails_atomicity import run, attach_report
        result = run(args.output)
        attach_report(args.output, result)
        print(f"Wrote {len(result['rows'])} atomicity executions")
    elif args.command == "rails-fixes":
        from .rails_fixes import collect
        result = collect(args.output, args.doctor, args.workers)
        print(f"Wrote {len(result['rows'])} matrix pairs and {len(result['pilot']['runs'])} pilot pairs")
    elif args.command == "operation-matrix":
        from .operation_matrix import run_matrix
        try:
            result = run_matrix(args.output, args.doctor, args.workers, args.frameworks,
                                args.operations, args.labels, args.contexts)
        except (FileNotFoundError, PermissionError, ValueError) as exc:
            parser.error(str(exc))
        print(f"Wrote {len(result['rows'])} pairs; {len(result['errors'])} infrastructure errors")
        if result["errors"]:
            raise SystemExit(1)
    elif args.command in ("pilot", "upstream-fixes"):
        result = run_pilot(args.output, args.doctor, upstream=args.command == "upstream-fixes",
                           labels=getattr(args, "labels", None))
        filename = "upstream_fixes.json" if args.command == "upstream-fixes" else "pilot.json"
        print(f"Wrote {len(result['runs'])} runs to {args.output / filename}")
    else:
        result = run_case(args.case, args.path, args.version, args.output, args.doctor)
        print(json.dumps(result["detectors"]["populated_invariants"], indent=2))


if __name__ == "__main__":
    main()
