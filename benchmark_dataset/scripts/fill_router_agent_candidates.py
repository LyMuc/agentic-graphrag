"""Fill llm_candidates in router_agent_test.json by calling the router LLM (pre-policy).

This script ONLY calls the Router LLM (tool_choice). It does NOT:
  - run RetrieverPolicy
  - execute retriever functions
  - fetch context or generate chatbot answers

Usage:
  python -m benchmark_dataset.scripts.fill_router_agent_candidates --list-rows
  python -m benchmark_dataset.scripts.fill_router_agent_candidates --dry-run
  python -m benchmark_dataset.scripts.fill_router_agent_candidates --from-row 5 --to-row 10
  python -m benchmark_dataset.scripts.fill_router_agent_candidates --rows 1,3,5-7 --concurrency 2
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BENCHMARK_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(BENCHMARK_DIR)

for path in (REPO_ROOT, BENCHMARK_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from application.router import llm_candidate_names, llm_retriever_candidates  # noqa: E402
from application.router_tool_registry import router_tools_for_llm  # noqa: E402
from scripts._common import backup_paths, read_json, write_json  # noqa: E402

DEFAULT_INPUT = os.path.join(BENCHMARK_DIR, "router_eval", "router_agent_test.json")

TOOLS_FOR_LLM = router_tools_for_llm()


def parse_row_spec(spec: str, *, max_row: int) -> set[int]:
    """Parse 1-based row spec like '2', '1,3', '2-5', '1,3-5'."""
    rows: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s.strip()), int(end_s.strip())
            if start < 1 or end < start:
                raise ValueError(f"Invalid row range: {part!r}")
            rows.update(range(start, end + 1))
        else:
            row = int(part)
            if row < 1:
                raise ValueError(f"Row number must be >= 1, got {row}")
            rows.add(row)

    invalid = sorted(r for r in rows if r > max_row)
    if invalid:
        raise ValueError(f"Row(s) out of range (file has {max_row} rows): {invalid}")
    if not rows:
        raise ValueError(f"No valid rows parsed from: {spec!r}")
    return rows


def resolve_selected_rows(
    *,
    rows_spec: str | None,
    from_row: int | None,
    to_row: int | None,
    max_row: int,
) -> set[int] | None:
    if from_row is not None or to_row is not None:
        if rows_spec:
            raise ValueError("Use either --rows or --from-row/--to-row, not both.")
        if from_row is None or to_row is None:
            raise ValueError("Both --from-row and --to-row are required together.")
        if from_row < 1:
            raise ValueError(f"--from-row must be >= 1, got {from_row}")
        if to_row < from_row:
            raise ValueError(f"--to-row ({to_row}) must be >= --from-row ({from_row})")
        if to_row > max_row:
            raise ValueError(f"--to-row ({to_row}) exceeds file row count ({max_row})")
        return set(range(from_row, to_row + 1))

    if rows_spec:
        return parse_row_spec(rows_spec, max_row=max_row)
    return None


def has_candidates(row: dict[str, Any]) -> bool:
    value = row.get("llm_candidates")
    return isinstance(value, list) and len(value) > 0


def should_process(row: dict[str, Any], overwrite: bool, selected_rows: set[int] | None) -> bool:
    if selected_rows is not None:
        return True
    if overwrite:
        return True
    return not has_candidates(row)


def print_rows(path: str) -> None:
    records = read_json(path)
    print(f"{path} ({len(records)} rows)")
    for idx, row in enumerate(records, start=1):
        question = str(row.get("question", "")).strip().replace("\n", " ")
        if len(question) > 100:
            question = question[:97] + "..."
        status = "filled" if has_candidates(row) else "pending"
        print(f"  [{idx:>2}] ({status}) {question}")


def print_dry_run(path: str, selected_rows: set[int] | None) -> None:
    records = read_json(path)
    tool_names = sorted(
        entry["function"]["name"]
        for entry in TOOLS_FOR_LLM
        if isinstance(entry.get("function"), dict)
    )
    print(f"Router tools for LLM: {len(tool_names)}")
    for name in tool_names:
        print(f"  - {name}")

    if selected_rows is None:
        pending = [
            idx
            for idx, row in enumerate(records, start=1)
            if not has_candidates(row)
        ]
        print(f"\nWould fill {len(pending)}/{len(records)} pending rows (no --rows / range set).")
    else:
        ordered = sorted(selected_rows)
        print(f"\nWould fill rows: {ordered[0]}-{ordered[-1]} ({len(ordered)} rows)")
        for idx in ordered[:5]:
            q = str(records[idx - 1].get("question", "")).strip().replace("\n", " ")[:80]
            print(f"  [{idx}] {q}")
        if len(ordered) > 5:
            print(f"  ... and {len(ordered) - 5} more")
    print("\nDry run complete — no LLM calls made.")


async def route_question(question: str) -> list[str]:
    tool_calls = await llm_retriever_candidates(question, tools_for_llm=TOOLS_FOR_LLM)
    return llm_candidate_names(tool_calls)


async def fill_row(row: dict[str, Any], row_number: int) -> None:
    question = str(row.get("question", "")).strip()
    if not question:
        raise ValueError(f"Row {row_number} has no question.")

    print(f"[{row_number}] {question}")
    candidates = await route_question(question)
    row["llm_candidates"] = candidates
    print("  llm_candidates:", ", ".join(candidates) or "(none)")


async def process_file(
    path: str,
    *,
    overwrite: bool,
    concurrency: int,
    save_each: bool,
    selected_rows: set[int] | None = None,
) -> int:
    records = read_json(path)
    pending = [
        (idx, row)
        for idx, row in enumerate(records, start=1)
        if (selected_rows is None or idx in selected_rows)
        and should_process(row, overwrite, selected_rows)
    ]

    if not pending:
        print(f"-> {path}: no rows to fill.")
        return 0

    print(f"-> {path}: filling {len(pending)}/{len(records)} rows.")
    semaphore = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    completed = 0

    async def run_one(idx: int, row: dict[str, Any]) -> None:
        nonlocal completed
        async with semaphore:
            await fill_row(row, idx)
            async with lock:
                completed += 1
                if save_each:
                    write_json(path, records)
                    print(f"  saved progress: {completed}/{len(pending)}")

    await asyncio.gather(*(run_one(idx, row) for idx, row in pending))
    write_json(path, records)
    return len(pending)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help="router_agent_test.json path.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-run rows that already have llm_candidates.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Number of questions to run concurrently. Default: 2.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not back up JSON before modifying.",
    )
    parser.add_argument(
        "--save-each",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Save after each completed row. Default: true.",
    )
    parser.add_argument(
        "--rows",
        default=None,
        metavar="SPEC",
        help="Run selected 1-based rows. Examples: 2 | 1,3,5 | 5-10 | 1,3-5.",
    )
    parser.add_argument(
        "--from-row",
        type=int,
        default=None,
        metavar="X",
        help="First row to fill (1-based). Use with --to-row, e.g. --from-row 5 --to-row 10.",
    )
    parser.add_argument(
        "--to-row",
        type=int,
        default=None,
        metavar="Y",
        help="Last row to fill (1-based, inclusive). Use with --from-row.",
    )
    parser.add_argument(
        "--list-rows",
        action="store_true",
        help="Print numbered questions and exit (no LLM calls).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show tools and rows that would be filled; no LLM calls.",
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    if args.concurrency < 1:
        raise ValueError("--concurrency must be >= 1")

    if args.list_rows:
        print_rows(args.input)
        return

    records = read_json(args.input) if (args.rows or args.from_row or args.to_row or args.dry_run) else None
    selected_rows: set[int] | None = None
    if records is not None and (args.rows or args.from_row is not None or args.to_row is not None):
        selected_rows = resolve_selected_rows(
            rows_spec=args.rows,
            from_row=args.from_row,
            to_row=args.to_row,
            max_row=len(records),
        )
        print(f"Selected rows: {sorted(selected_rows)}")

    if args.dry_run:
        print_dry_run(args.input, selected_rows)
        return

    if not args.no_backup:
        backup_dir = backup_paths([args.input], "fill_router_agent_candidates")
        if backup_dir:
            print(f"Backup created: {backup_dir}")

    filled = await process_file(
        args.input,
        overwrite=args.overwrite,
        concurrency=args.concurrency,
        save_each=args.save_each,
        selected_rows=selected_rows,
    )
    print(f"Done. Filled {filled} row(s).")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
