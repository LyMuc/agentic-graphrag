"""Score router agent output (pre-policy llm_candidates) against expected_retrievers.

Writes metrics back into router_agent_test.json (single source of truth).

Usage:
  python -m benchmark_dataset.scripts.score_router_agent
  python -m benchmark_dataset.scripts.score_router_agent --input path/to/router_agent_test.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_DIR = SCRIPT_DIR.parent
REPO_ROOT = BENCHMARK_DIR.parent

for path in (str(REPO_ROOT), str(BENCHMARK_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scripts._common import read_json, write_json  # noqa: E402
from scripts._router_metrics import compute_metrics  # noqa: E402

DEFAULT_INPUT = BENCHMARK_DIR / "router_eval" / "router_agent_test.json"

PRE_POLICY_FIELDS = (
    "precision",
    "recall",
    "f1",
    "error_types",
    "missing",
    "extra",
    "actual_topic_keys",
    "passed",
)


def apply_pre_policy_metrics(case: dict[str, Any]) -> bool:
    """Ghi metrics pre-policy vào case. Returns True nếu đã chấm."""
    metrics = compute_metrics(
        list(case.get("llm_candidates") or []),
        expected_retrievers=list(case.get("expected_retrievers") or []),
    )
    case["precision"] = metrics["precision"]
    case["recall"] = metrics["recall"]
    case["f1"] = metrics["f1"]
    case["error_types"] = metrics["error_types"]
    case["missing"] = metrics["missing"]
    case["extra"] = metrics["extra"]
    case["actual_topic_keys"] = metrics["actual_topic_keys"]
    case["passed"] = metrics["passed"]
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="Also score cases with empty llm_candidates (default: skip unfilled rows).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = read_json(args.input)
    scored = 0
    skipped = 0

    for case in cases:
        if not args.include_empty and not case.get("llm_candidates"):
            skipped += 1
            continue
        apply_pre_policy_metrics(case)
        scored += 1

    write_json(args.input, cases)

    passed = sum(1 for row in cases if row.get("passed"))
    print(f"Scored {scored} router agent cases ({skipped} skipped)")
    print(f"passed={passed}/{scored}")
    print(f"Wrote: {args.input}")


if __name__ == "__main__":
    main()
