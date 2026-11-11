"""A stand-in for storyline's eval-org seed script that records each call.

`python fake_seed.py <state dir> [--fail-from K [--noise N]] [--hang-from K] [--sleep-from K --sleep S] --user-id U
--store S --db D`: calls are numbered from 1 (the warm-up is call 1); from call K on it fails (after N characters of
stderr noise), hangs with a child process, or sleeps first.
"""

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

FAIL_EXIT = 3
NOISE_MARKER = "early-seed-noise "


def _call_number(state: Path) -> int:
    with (state / "calls").open("a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        n = int(f.read() or "0") + 1
        f.seek(0)
        f.truncate()
        f.write(str(n))
    return n


def seed_calls(state: Path) -> list[dict[str, Any]]:
    """Recorded calls, in call order."""
    calls = [json.loads(p.read_text()) for p in state.glob("seed-*.json")]
    return sorted(calls, key=lambda c: c["call"])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("state", type=Path)
    p.add_argument("--fail-from", type=int)
    p.add_argument("--hang-from", type=int)
    p.add_argument("--sleep-from", type=int)
    p.add_argument("--sleep", type=float, default=0.0)
    p.add_argument("--noise", type=int, default=0)
    p.add_argument("--user-id", required=True)
    p.add_argument("--store", required=True)
    p.add_argument("--db", required=True)
    args = p.parse_args()
    args.state.mkdir(parents=True, exist_ok=True)
    n = _call_number(args.state)
    record: dict[str, Any] = {
        "call": n,
        "argv": sys.argv[1:],
        "user_id": args.user_id,
        "store": args.store,
        "store_is_dir": Path(args.store).is_dir(),
        "db": args.db,
        "env": dict(os.environ),
        "pid": os.getpid(),
        "start": time.time(),
        "end": None,
    }
    path = args.state / f"seed-{n}.json"
    path.write_text(json.dumps(record))
    print(f"seed-stderr {args.user_id}", file=sys.stderr, flush=True)
    if args.hang_from is not None and n >= args.hang_from:
        sleeper = subprocess.Popen(["sleep", "120"])
        (args.state / f"sleeper-{n}.pid").write_text(str(sleeper.pid))
        time.sleep(3600)
    if args.sleep_from is not None and n >= args.sleep_from:
        time.sleep(args.sleep)
    if args.fail_from is not None and n >= args.fail_from:
        print(NOISE_MARKER + "x" * args.noise, file=sys.stderr, flush=True)
        print(f"seed exploded for {args.user_id}", file=sys.stderr, flush=True)
        return FAIL_EXIT
    record["end"] = time.time()
    path.write_text(json.dumps(record))
    return 0


if __name__ == "__main__":
    sys.exit(main())
