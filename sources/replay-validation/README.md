# Replay source files

The two replay aggregates record the SHA-256 of the files that produced them.
The files with those hashes are kept here:

- `original/` for `results/realworld.json`;
- `2026-11-02/` for `results/realworld-rerun-2026-11-02/realworld.json`,
  including the scripts that wrote the published evidence.

`scripts/validate_realworld.py` hashes them and compares the result with each
aggregate. The current code in `smp/`, `runners/` and `scripts/` has changed
since; use it for new runs. The aggregate of 2 November also records the hash
of its protocol text, which is not part of this package and is not checked.
