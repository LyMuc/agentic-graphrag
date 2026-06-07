"""
Fill chatbot_answer and context for benchmark test-version JSON files.

Examples:
  python -m benchmark_dataset.scripts.fill_test_answers benchmark_dataset/test_versions/cap_duong/test_v1_1705_cap_duong.json
  python -m benchmark_dataset.scripts.fill_test_answers benchmark_dataset/test_versions --concurrency 2
  python -m benchmark_dataset.scripts.fill_test_answers benchmark_dataset/test_versions/cap_duong/test_v1_1705_cap_duong.json --overwrite
  python -m benchmark_dataset.scripts.fill_test_answers benchmark_dataset/test_versions/cap_duong/test_v1_1705_cap_duong.json --list-rows
  python -m benchmark_dataset.scripts.fill_test_answers benchmark_dataset/test_versions/cap_duong/test_v1_1705_cap_duong.json --rows 2
  python -m benchmark_dataset.scripts.fill_test_answers benchmark_dataset/test_versions/cap_duong/test_v1_1705_cap_duong.json --rows 1,3,5-7

By default, a row is processed only when chatbot_answer or context is empty.
When --rows is used, only those rows are run (always, even if already filled).
The context field is stored as a JSON string of the raw retriever output, not
as the formatted text that is sent to the final answer LLM.
"""

from __future__ import annotations

import argparse
import asyncio
import json
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

from adapter.config import chat_stream  # noqa: E402
from application.router import _router_tool_descriptions, tool_choice, tool_picker_prompt  # noqa: E402
from application.retriever_policy import evaluate_retriever_policy  # noqa: E402
from scripts._common import (  # noqa: E402
    TEST_VERSIONS_DIR,
    backup_paths,
    is_filled,
    question_id,
    read_json,
    write_json,
)

# Reuse the exact tool registry and final-answer prompt used by Chainlit.
from presentation.main import main_prompt, tools  # noqa: E402


def list_json_files(path: str) -> list[str]:
    if os.path.isfile(path):
        if not path.endswith(".json"):
            raise ValueError(f"Input file must be .json: {path}")
        return [path]

    if not os.path.isdir(path):
        raise FileNotFoundError(path)

    out: list[str] = []
    for root, _, names in os.walk(path):
        for name in names:
            if name.endswith(".json"):
                out.append(os.path.join(root, name))
    return sorted(out)


def should_process(row: dict[str, Any], overwrite: bool, selected_rows: set[int] | None) -> bool:
    if selected_rows is not None:
        return True
    if overwrite:
        return True
    return not is_filled(row.get("chatbot_answer")) or not is_filled(row.get("context"))


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
        raise ValueError(
            f"Row(s) out of range (file has {max_row} rows): {invalid}"
        )
    if not rows:
        raise ValueError(f"No valid rows parsed from: {spec!r}")
    return rows


def print_rows(path: str) -> None:
    records = read_json(path)
    print(f"{path} ({len(records)} rows)")
    for idx, row in enumerate(records, start=1):
        question = str(row.get("question", "")).strip().replace("\n", " ")
        if len(question) > 100:
            question = question[:97] + "..."
        filled = is_filled(row.get("chatbot_answer")) and is_filled(row.get("context"))
        status = "filled" if filled else "pending"
        qid = question_id(str(row.get("question", "")))
        print(f"  [{idx:>2}] ({status}, qid={qid}) {question}")


def raw_context_json(tool_response: list[Any]) -> str:
    return json.dumps(tool_response, ensure_ascii=False, default=str)


def contexts_text_for_llm(tool_response: list[Any]) -> str:
    contexts: list[Any] = []
    for res in tool_response:
        if isinstance(res, dict) and "contexts" in res:
            contexts.extend(res["contexts"])
        else:
            contexts.append(res)
    return "\n\n".join(str(ctx) for ctx in contexts)


async def execute_tool_call(tool_call: dict[str, Any], question: str) -> Any:
    tool_name = tool_call["name"]
    if tool_name not in tools:
        raise KeyError(f"Router returned unknown tool: {tool_name}")

    function_to_call = tools[tool_name]["function"]
    function_args = tool_call.get("args", {}) if tool_name == "respond" else {"query": question}
    return await function_to_call(**function_args)


def unique_tool_calls(llm_tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_tools: set[str] = set()
    out: list[dict[str, Any]] = []
    for tool_call in llm_tool_calls:
        tool_name = tool_call["name"]
        if tool_name in seen_tools:
            continue
        seen_tools.add(tool_name)
        out.append(tool_call)
    return out


def policy_tool_calls(
    question: str,
    llm_tool_calls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decision = evaluate_retriever_policy(
        question,
        [call["name"] for call in llm_tool_calls],
    )
    print("  policy final:", ", ".join(decision.final_tools) or "(none)")
    for line in decision.audit:
        print("   -", line)

    by_name: dict[str, dict[str, Any]] = {}
    for call in unique_tool_calls(llm_tool_calls):
        name = call["name"]
        by_name[name] = {**call, "name": name}

    return [
        by_name.get(tool_name, {"name": tool_name, "args": {}})
        for tool_name in decision.final_tools
    ]


async def retrieve_context(question: str) -> list[Any]:
    llm_tool_calls = await tool_choice(
        [
            {"role": "system", "content": tool_picker_prompt},
            {
                "role": "user",
                "content": f"Câu hỏi của người dùng cần tìm công cụ để giải quyết: '{question}'",
            },
        ],
        tools=_router_tool_descriptions(tools),
    )
    tool_calls = policy_tool_calls(question, llm_tool_calls)
    missing = [call["name"] for call in tool_calls if call["name"] not in tools]
    if missing:
        raise KeyError(
            "RetrieverPolicy selected tool(s) not registered in tools: "
            + ", ".join(sorted(set(missing)))
        )
    print("  tools:", ", ".join(call["name"] for call in tool_calls) or "(none)")
    return list(await asyncio.gather(*(execute_tool_call(call, question) for call in tool_calls)))


async def generate_answer(question: str, tool_response: list[Any]) -> str:
    contexts_text = contexts_text_for_llm(tool_response)
    llm_messages = [
        {"role": "system", "content": main_prompt},
        {
            "role": "system",
            "content": f"Dữ liệu lấy được từ hệ thống cho câu hỏi '{question}':\n{contexts_text}",
        },
        {"role": "user", "content": f"Câu hỏi của người dùng: {question}"},
    ]

    chunks: list[str] = []
    async for token in chat_stream(llm_messages):
        chunks.append(token)
    return "".join(chunks)


async def fill_row(row: dict[str, Any], row_number: int) -> None:
    question = str(row.get("question", "")).strip()
    if not question:
        raise ValueError(f"Row {row_number} has no question.")

    print(f"[{row_number}] {question}")
    tool_response = await retrieve_context(question)
    row["context"] = raw_context_json(tool_response)
    row["chatbot_answer"] = await generate_answer(question, tool_response)


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
        "path",
        nargs="?",
        default=TEST_VERSIONS_DIR,
        help="A test-version .json file or directory. Default: benchmark_dataset/test_versions.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-run every row, including rows that already have chatbot_answer and context.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of questions to run at the same time. Default: 1.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not back up JSON files before modifying them.",
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
        help=(
            "Run only selected 1-based row numbers in a single file. "
            "Examples: 2 | 1,3,5 | 2-5 | 1,3-5. Use with --list-rows to see numbers."
        ),
    )
    parser.add_argument(
        "--list-rows",
        action="store_true",
        help="Print numbered questions in the file and exit (no LLM calls).",
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    if args.concurrency < 1:
        raise ValueError("--concurrency must be >= 1")

    if args.rows and args.list_rows:
        raise ValueError("Use either --rows or --list-rows, not both.")

    if args.list_rows:
        if not os.path.isfile(args.path):
            raise ValueError("--list-rows requires a single .json file path.")
        print_rows(args.path)
        return

    selected_rows: set[int] | None = None
    if args.rows:
        if not os.path.isfile(args.path):
            raise ValueError("--rows requires a single .json file path, not a directory.")
        records = read_json(args.path)
        selected_rows = parse_row_spec(args.rows, max_row=len(records))
        print(f"Selected rows: {sorted(selected_rows)}")

    files = list_json_files(args.path)
    if not files:
        print(f"No JSON files found in {args.path}")
        return

    if args.rows and len(files) != 1:
        raise ValueError("--rows can only be used with one JSON file.")

    if not args.no_backup:
        backup_dir = backup_paths(files, "fill_test_answers")
        if backup_dir:
            print(f"Backup created: {backup_dir}")

    total = 0
    for path in files:
        total += await process_file(
            path,
            overwrite=args.overwrite,
            concurrency=args.concurrency,
            save_each=args.save_each,
            selected_rows=selected_rows,
        )

    print(f"Done. Filled {total} rows across {len(files)} file(s).")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
