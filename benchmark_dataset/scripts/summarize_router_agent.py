"""Compute macro-average precision, recall, f1 for router agent evaluation.

Reads router_agent_test.json (pre-policy + policy_* post-policy fields).

Usage:
  python -m benchmark_dataset.scripts.summarize_router_agent
  python -m benchmark_dataset.scripts.summarize_router_agent --compare-pre-post
  python -m benchmark_dataset.scripts.summarize_router_agent --output path/to/summary.json

Writes summary to router_eval/router_agent_summary.json (pre-policy) or
router_eval/router_agent_compare_summary.json (--compare-pre-post).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
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

from scripts._common import ensure_dir, read_json, write_json  # noqa: E402

DEFAULT_INPUT = BENCHMARK_DIR / "router_eval" / "router_agent_test.json"
DEFAULT_PRE_SUMMARY = BENCHMARK_DIR / "router_eval" / "router_agent_summary.json"
DEFAULT_COMPARE_SUMMARY = BENCHMARK_DIR / "router_eval" / "router_agent_compare_summary.json"


def _is_pre_scored(row: dict[str, Any]) -> bool:
    return row.get("precision") is not None and row.get("recall") is not None


def _is_policy_scored(row: dict[str, Any]) -> bool:
    return row.get("policy_precision") is not None and row.get("policy_recall") is not None


def _avg(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(float(row[key]) for row in rows) / len(rows), 4)


def _group_stats(
    rows: list[dict[str, Any]],
    *,
    error_key: str = "error_types",
    passed_key: str = "passed",
    precision_key: str = "precision",
    recall_key: str = "recall",
    f1_key: str = "f1",
) -> dict[str, Any]:
    total = len(rows)
    if total == 0:
        return {}

    passed = sum(
        1 for row in rows if row.get(error_key) == ["Đúng"] or row.get(passed_key)
    )
    error_counter: Counter[str] = Counter()
    for row in rows:
        for err in row.get(error_key) or []:
            if err != "Đúng":
                error_counter[err] += 1

    return {
        "cases": total,
        "cases_passed": passed,
        "pass_rate": round(passed / total, 4),
        "avg_precision": _avg(rows, precision_key),
        "avg_recall": _avg(rows, recall_key),
        "avg_f1": _avg(rows, f1_key),
        "error_type_counts": dict(sorted(error_counter.items())),
    }


def build_pre_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    filled = [row for row in cases if row.get("llm_candidates")]
    scored = [row for row in filled if _is_pre_scored(row)]

    by_case_type: dict[str, list[dict[str, Any]]] = {}
    by_topic: dict[str, list[dict[str, Any]]] = {}
    for row in scored:
        by_case_type.setdefault(str(row.get("case_type", "")), []).append(row)
        by_topic.setdefault(str(row.get("primary_topic", "")), []).append(row)

    return {
        "overall": {
            **_group_stats(scored),
            "cases_total": len(cases),
            "cases_with_llm_candidates": len(filled),
            "cases_unscored": len(filled) - len(scored),
        },
        "by_case_type": {
            key: _group_stats(group) for key, group in sorted(by_case_type.items())
        },
        "by_primary_topic": {
            key: _group_stats(group) for key, group in sorted(by_topic.items())
        },
    }


def build_compare_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    filled = [row for row in cases if row.get("llm_candidates")]
    pre_scored = [row for row in filled if _is_pre_scored(row)]
    policy_scored = [row for row in filled if _is_policy_scored(row)]

    by_case_type: dict[str, list[dict[str, Any]]] = {}
    by_topic: dict[str, list[dict[str, Any]]] = {}
    for row in policy_scored:
        by_case_type.setdefault(str(row.get("case_type", "")), []).append(row)
        by_topic.setdefault(str(row.get("primary_topic", "")), []).append(row)

    policy_interventions = sum(1 for row in policy_scored if row.get("policy_intervened"))

    def pre_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return _group_stats(rows)

    def post_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return _group_stats(
            rows,
            error_key="policy_error_types",
            passed_key="policy_passed",
            precision_key="policy_precision",
            recall_key="policy_recall",
            f1_key="policy_f1",
        )

    return {
        "overall": {
            "cases_total": len(cases),
            "cases_with_llm_candidates": len(filled),
            "cases_pre_scored": len(pre_scored),
            "cases_policy_scored": len(policy_scored),
            "policy_intervention_rate": round(policy_interventions / len(policy_scored), 4)
            if policy_scored
            else 0.0,
            "pre_policy": pre_group(pre_scored),
            "post_policy": post_group(policy_scored),
        },
        "by_case_type": {
            key: {
                "pre_policy": pre_group([r for r in pre_scored if r.get("case_type") == key]),
                "post_policy": post_group(group),
            }
            for key, group in sorted(by_case_type.items())
        },
        "by_primary_topic": {
            key: {
                "pre_policy": pre_group([r for r in pre_scored if r.get("primary_topic") == key]),
                "post_policy": post_group(group),
            }
            for key, group in sorted(by_topic.items())
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument(
        "--output",
        default=None,
        help="Summary JSON path (default: router_agent_summary.json or router_agent_compare_summary.json).",
    )
    parser.add_argument(
        "--compare-pre-post",
        action="store_true",
        help="Summarize pre-policy (precision/recall) vs post-policy (policy_*).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = read_json(args.input)

    if args.compare_pre_post:
        summary = build_compare_summary(cases)
        overall = summary["overall"]
        pre = overall.get("pre_policy", {})
        post = overall.get("post_policy", {})
        print(f"Summarized {overall.get('cases_policy_scored', 0)} policy-scored cases")
        print(f"pre_policy pass_rate={pre.get('pass_rate')}")
        print(f"post_policy pass_rate={post.get('pass_rate')}")
        print(f"policy_intervention_rate={overall.get('policy_intervention_rate')}")
    else:
        summary = build_pre_summary(cases)
        overall = summary["overall"]
        print(f"Summarized {overall.get('cases', 0)} pre-policy scored cases")
        print(f"avg_precision={overall.get('avg_precision')}")
        print(f"avg_recall={overall.get('avg_recall')}")
        print(f"avg_f1={overall.get('avg_f1')}")
        print(f"pass_rate={overall.get('pass_rate')}")

    output = Path(
        args.output
        or (DEFAULT_COMPARE_SUMMARY if args.compare_pre_post else DEFAULT_PRE_SUMMARY)
    )
    ensure_dir(str(output.parent))
    write_json(str(output), [summary])
    print(f"Wrote: {output}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
