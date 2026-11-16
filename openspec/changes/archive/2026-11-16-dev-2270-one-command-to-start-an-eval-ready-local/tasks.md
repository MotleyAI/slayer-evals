## 1. Default Motley URL

- [x] 1.1 Set `DEFAULT_MOTLEY_URL = "http://localhost:8100/api/v1/mcp/"` in `src/slayer_evals/runner/config.py`. Update the default-URL assertions in `tests/test_motley_runner.py`.
- [x] 1.2 Update the README's Motley section: only `--motley-seed-cmd "/path/to/storyline/backend/scripts/eval_backend.sh seed"`, the 8100 default, and a pointer to storyline's `docs/eval_org_seed.md`.
- [x] 1.3 Run the full non-integration suite. Verify it passes.
