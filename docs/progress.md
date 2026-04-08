# Progress

Last Updated: 2026-04-08

## Current Status
- UI monolith was split into smaller modules under `app/` and `app/components/`.
- SWE guardrail linter was added at `scripts/swe_lint.py`.
- Memory-bank docs now include `docs/tech-stack.md`, `docs/architecture.md`, and this file.

## Recent Changes
- Introduced checks for:
  - file-size and long-function warnings,
  - mixed-concern detection,
  - import-path integrity,
  - markdown path hygiene,
  - dependency pinning hygiene,
  - optional live outdated checks (`--check-outdated`).

## Next Steps
- Incrementally split large pipeline modules (notably `scripts/build_dataset.py`) into smaller stages.
- Add more focused tests around dataset transforms and normalization boundaries.
- Decide whether to run `scripts/swe_lint.py --strict` in CI after cleanup.

## Risks
- Legacy larger files can still accumulate drift until refactors are completed.
- Optional outdated checks depend on network/package-manager availability.
- Regex-based JS heuristics may miss some edge cases; treat lint output as guardrails, not formal proof.
