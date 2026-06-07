"""Run RetrieverPolicy on llm_candidates and score post-policy output.

Reads and writes router_agent_test.json (single source of truth).
Does not call LLM or execute retrievers.

Usage:
  python -m benchmark_dataset.scripts.validate_router_agent
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

from application.retriever_catalog import DIRECT_TOOLS  # noqa: E402
from application.retriever_policy import evaluate_retriever_policy  # noqa: E402
from scripts._common import read_json, write_json  # noqa: E402
from scripts._router_metrics import compute_metrics  # noqa: E402

DEFAULT_INPUT = BENCHMARK_DIR / "router_eval" / "router_agent_test.json"


def _policy_retrievers(final_tools: list[str]) -> list[str]:
    """Lọc direct tools khỏi final_tools, giữ tên gốc."""
    seen: set[str] = set()
    out: list[str] = []
    for tool in final_tools:
        if tool in DIRECT_TOOLS or tool in seen:
            continue
        seen.add(tool)
        out.append(tool)
    return out


def apply_policy_metrics(case: dict[str, Any]) -> None:
    """Chạy policy và ghi policy_* fields vào case."""
    question = str(case.get("question", ""))
    llm_candidates = list(case.get("llm_candidates") or [])
    expected = list(case.get("expected_retrievers") or [])

    decision = evaluate_retriever_policy(question, llm_candidates)
    policy_retrievers = _policy_retrievers(decision.final_tools)

    metrics = compute_metrics(
        policy_retrievers,
        expected_retrievers=expected,
    )

    case["final_tools"] = decision.final_tools
    case["policy_retrievers"] = policy_retrievers
    case["policy_intervened"] = bool(decision.rejected_tools)
    case["rejected_tools"] = decision.rejected_tools
    case["policy_precision"] = metrics["precision"]
    case["policy_recall"] = metrics["recall"]
    case["policy_f1"] = metrics["f1"]
    case["policy_error_types"] = metrics["error_types"]
    case["policy_missing"] = metrics["missing"]
    case["policy_extra"] = metrics["extra"]
    case["policy_actual_topic_keys"] = metrics["actual_topic_keys"]
    case["policy_passed"] = metrics["passed"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = read_json(args.input)
    validated = 0
    skipped = 0

    for case in cases:
        if not case.get("llm_candidates"):
            skipped += 1
            continue
        apply_policy_metrics(case)
        validated += 1

    write_json(args.input, cases)

    policy_passed = sum(
        1 for row in cases if row.get("policy_passed") and row.get("llm_candidates")
    )
    intervened = sum(
        1
        for row in cases
        if row.get("policy_intervened") and row.get("llm_candidates")
    )
    print(f"Validated {validated} cases ({skipped} skipped, no llm_candidates)")
    print(f"policy_passed={policy_passed}/{validated}")
    print(f"policy_intervention_rate={intervened}/{validated}")
    print(f"Wrote: {args.input}")


if __name__ == "__main__":
    main()
