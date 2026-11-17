"""`slayer-evals` command line: build, truth, run, report."""

import argparse
import contextlib
import shlex
import sys
import tempfile
from pathlib import Path

from slayer_evals.core import DATASETS, Dataset, Table, Task
from slayer_evals.dataset import BuiltDataset, build_datasets, load_datasets
from slayer_evals.report import write_report
from slayer_evals.runner import (
    DEFAULT_MODEL,
    SELECTABLE_PROFILES,
    AuthError,
    MotleyWarmUpError,
    RunConfig,
    run_benchmark,
)
from slayer_evals.tasks import (
    SUITE_DIRS,
    TRUTH_DIR,
    SnapshotDriftError,
    TaskFormatError,
    TruthError,
    check_coverage,
    check_layout,
    check_prompts,
    check_snapshots,
    check_truth_sizes,
    compute_truths,
    load_tasks,
    write_snapshots,
)


def _csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="slayer-evals", description="Do agents reach for SLayer's DSL, and does it beat raw SQL on correctness?"
    )
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="build each dataset's database and SLayer store template into <out>/<dataset>/")
    b.add_argument("--out", type=Path, default=Path("data"))
    b.add_argument("--seed", type=int, help="seed for every dataset (default: each dataset's own)")

    t = sub.add_parser("truth", help="check (or --write) the committed truth snapshots and the task-set checks")
    t.add_argument("--write", action="store_true", help="regenerate the snapshots instead of checking them")
    t.add_argument("--tasks-dir", type=Path, default=Path("tasks"))
    t.add_argument("--dataset-dir", type=Path, help="a build root from `build` (default: build afresh)")

    r = sub.add_parser("run", help="run tasks against an agent and write a run directory")
    auth = r.add_mutually_exclusive_group()
    auth.add_argument("--subscription-auth", dest="auth_mode", action="store_const", const="subscription")
    auth.add_argument("--api-key-auth", dest="auth_mode", action="store_const", const="api-key")
    r.add_argument("--env-file", type=Path, help="KEY=VALUE file with CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY")
    r.add_argument("--tasks-dir", type=Path, default=Path("tasks"))
    r.add_argument("--dataset-dir", type=Path, help="a build root from `build` (default: build afresh)")
    r.add_argument("--out", type=Path, default=Path("runs"))
    r.add_argument("--agent", default=RunConfig().agent, help="module:Class of the agent adapter")
    r.add_argument("--tasks", type=_csv, default=[], help="comma-separated task ids")
    r.add_argument("--rows", type=_csv, default=[], help="comma-separated rows, e.g. Q1,Q4: tasks covering any of them")
    r.add_argument("--suites", type=_csv, default=[], help=f"comma-separated, from {', '.join(SUITE_DIRS)}")
    r.add_argument(
        "--profiles",
        type=_csv,
        default=RunConfig().profiles,
        help=f"comma-separated, from {', '.join(SELECTABLE_PROFILES)} (default: {', '.join(RunConfig().profiles)})",
    )
    r.add_argument("--models", type=_csv, default=[DEFAULT_MODEL])
    r.add_argument("--trials", type=int, default=1, help="N: trials per task (repeat) or the attempt cap (until-pass)")
    r.add_argument("--mode", choices=["repeat", "until-pass"], default="repeat")
    r.add_argument("--concurrency", type=int, default=3)
    r.add_argument("--max-turns", type=int, default=60)
    r.add_argument("--timeout", type=float, default=900.0, help="wall-clock budget per trial, seconds")
    r.add_argument("--slayer-command", type=shlex.split, help="SLayer executable to test, e.g. a local checkout")
    r.add_argument("--motley-url", default=RunConfig().motley_url, help="Motley MCP endpoint for the Motley profiles")
    r.add_argument(
        "--motley-seed-cmd",
        type=shlex.split,
        help="command that seeds one Motley org; --user-id, --store and --db are appended",
    )

    rep = sub.add_parser("report", help="(re)generate report.md of a run directory")
    rep.add_argument("run_dir", type=Path)
    return p


def _datasets(stack: contextlib.ExitStack, dataset_dir: Path | None, tasks: list[Task]) -> dict[Dataset, BuiltDataset]:
    needed: list[Dataset] = [d for d in DATASETS if any(t.dataset == d for t in tasks)]
    if dataset_dir is not None:
        return load_datasets(dataset_dir, needed)
    return build_datasets(Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="slayer-evals-data-"))), needed)


def _truth(args: argparse.Namespace) -> int:
    tasks = load_tasks(args.tasks_dir)
    truths: dict[str, Table] = {}
    with contextlib.ExitStack() as stack:
        for dataset, built in _datasets(stack, args.dataset_dir, tasks).items():
            truths |= compute_truths([t for t in tasks if t.dataset == dataset], built.db_path)
    snapshot_dir = args.tasks_dir / TRUTH_DIR
    if args.write:
        write_snapshots(truths, snapshot_dir)
        print(f"wrote {len(truths)} truth snapshots to {snapshot_dir}")
    else:
        check_snapshots(truths, snapshot_dir)
    problems = check_coverage(tasks) + check_layout(args.tasks_dir) + check_prompts(tasks) + check_truth_sizes(truths)
    for problem in problems:
        print(f"warning: {problem}", file=sys.stderr)
    print(f"{len(tasks)} tasks, snapshots {'written' if args.write else 'up to date'}")
    return 0


def _run(args: argparse.Namespace) -> int:
    cfg = RunConfig(
        tasks_dir=args.tasks_dir,
        dataset_dir=args.dataset_dir,
        out_dir=args.out,
        agent=args.agent,
        auth_mode=args.auth_mode,
        env_file=args.env_file,
        task_ids=args.tasks,
        rows=args.rows,
        suites=args.suites,
        profiles=args.profiles,
        models=args.models,
        n=args.trials,
        mode=args.mode,
        concurrency=args.concurrency,
        max_turns=args.max_turns,
        timeout_s=args.timeout,
        slayer_command=args.slayer_command,
        motley_url=args.motley_url,
        motley_seed_command=args.motley_seed_cmd,
    )
    run_dir = run_benchmark(cfg)
    print(f"run written to {run_dir} (report: {run_dir / 'report.md'})")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            for built in build_datasets(args.out, seed=args.seed).values():
                print(f"built {built.db_path} and {built.store_dir}")
            return 0
        if args.command == "truth":
            return _truth(args)
        if args.command == "run":
            return _run(args)
        print(f"wrote {write_report(args.run_dir)}")
        return 0
    except (AuthError, TaskFormatError, TruthError, SnapshotDriftError, MotleyWarmUpError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
