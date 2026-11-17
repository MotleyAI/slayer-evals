## Why

Storyline's `backend/scripts/eval_backend.sh seed` brings up a local eval backend on `127.0.0.1:8100` and seeds a trial
org. Port 8100 keeps it clear of a dev backend on 8000. With the default Motley URL on 8100, a Motley run needs only
`--motley-seed-cmd`.

## What Changes

- The default `--motley-url` becomes `http://localhost:8100/api/v1/mcp/`.
- The README's Motley section shows only `--motley-seed-cmd` with storyline's eval script, and points to storyline's
  `docs/eval_org_seed.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `benchmark-runs`: the default Motley URL.

## Impact

- `src/slayer_evals/runner/config.py`, `README.md`, `tests/test_motley_runner.py`.
- No architecture-model change.
