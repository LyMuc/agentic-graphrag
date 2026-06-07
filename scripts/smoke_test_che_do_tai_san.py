"""Smoke test cho retriever che_do_tai_san_cua_vo_chong.

Mục tiêu:
- Chạy retriever trên benchmark 28 câu (`test_v1_1705_che_do_tai_san_cua_vo_chong.json`).
- Bỏ qua các câu có can_cu_phap_ly_chinh tham chiếu tới Điều 59 (Q27 — out of
  scope Đ28-50, đã được khẳng định trong plan).
- Với mỗi câu, capture danh sách Điều-level IDs từ debug trace và so
  với `can_cu_phap_ly_chinh` của benchmark.
- In bảng kết quả + precision/recall (theo Điều, không tính Khoản/Điểm con).

Cách chạy:
    python scripts/smoke_test_che_do_tai_san.py
    python scripts/smoke_test_che_do_tai_san.py --max 5      # chỉ chạy 5 câu đầu
    python scripts/smoke_test_che_do_tai_san.py --question N # chạy đúng câu thứ N (0-indexed)

Lưu ý: smoke test này KHÔNG cần ground truth chuẩn 100% — mục đích là sanity
check rằng retriever không hoàn toàn miss target. Recall trung bình ≥ 0.6 là OK
trong giai đoạn đầu.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.cypher_templates.tai_san import TAI_SAN_REGISTRY  # noqa: E402
from adapter.retrievers.quan_he_giua_vo_va_chong.che_do_tai_san_cua_vo_chong import (  # noqa: E402
    _classify_templates,
    _extract_template_params,
    _run_trace_sync,
    _today_str,
)


BENCHMARK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "benchmark_dataset",
    "test_versions",
    "che_do_tai_san_cua_vo_chong",
    "test_v1_1705_che_do_tai_san_cua_vo_chong.json",
)

# Pattern Điều-level (no Khoan, no Diem)
_DIEU_PATTERN = re.compile(r"^(Luat_HNGD_2014_Dieu_\d+)(?:_Khoan_.*)?$")


def _normalize_to_dieu(legal_id: str) -> str | None:
    """Convert ID bất kỳ → Điều-level (vd Luat_HNGD_2014_Dieu_35).

    Returns None nếu không phải Luat_HNGD_2014.
    """
    m = _DIEU_PATTERN.match(legal_id)
    if m:
        return m.group(1)
    return None


def _is_out_of_scope(can_cu: list[str]) -> bool:
    """Đánh dấu out-of-scope nếu câu hỏi đi vào Đ59 (chia tài sản khi ly hôn).

    Quy tắc: tất cả can_cu_phap_ly_chinh nằm trong Đ59-64 → out-of-scope.
    """
    if not can_cu:
        return True
    dieu_set = set()
    for cid in can_cu:
        dieu = _normalize_to_dieu(cid)
        if dieu:
            num_match = re.search(r"Dieu_(\d+)", dieu)
            if num_match:
                dieu_set.add(int(num_match.group(1)))
    # Out-of-scope nếu MỌI điều đều >= 59 (chia tài sản khi ly hôn)
    if not dieu_set:
        return False
    return all(d >= 59 for d in dieu_set)


def _extract_seed_dieu_from_trace(trace: list[dict[str, Any]]) -> set[str]:
    """Trích Điều-level IDs từ seed_trace của 1 template."""
    out = set()
    for t in trace:
        dst = t.get("dst_id", "")
        if not isinstance(dst, str):
            continue
        d = _normalize_to_dieu(dst)
        if d:
            out.add(d)
    return out


async def _run_one_question(query: str) -> dict[str, Any]:
    """Chạy classify + extract + trace cho một câu hỏi.

    Trả dict: {templates: [...], seed_dieu_ids: set[str]}
    """
    choices = await _classify_templates(query)
    if not choices:
        return {"templates": [], "seed_dieu_ids": set(), "params_list": []}

    templates = [TAI_SAN_REGISTRY.get(c.template_name) for c in choices]
    extract_results = await asyncio.gather(
        *[_extract_template_params(query, t) for t in templates]
    )

    target_date = _today_str()
    all_seed = set()
    params_list = []
    for template, (params, _) in zip(templates, extract_results):
        trace = await asyncio.to_thread(_run_trace_sync, template, params, target_date)
        seed_dieu = _extract_seed_dieu_from_trace(trace)
        all_seed |= seed_dieu
        params_list.append(
            {
                "template": template.name,
                "params": template.build_params(params),
                "seed_dieu_ids": sorted(seed_dieu),
            }
        )
    return {
        "templates": [c.template_name for c in choices],
        "seed_dieu_ids": all_seed,
        "params_list": params_list,
    }


def _evaluate(
    expected: set[str], actual: set[str]
) -> tuple[float, float, set[str], set[str]]:
    """Trả (precision, recall, missing, extra)."""
    if not expected and not actual:
        return 1.0, 1.0, set(), set()
    if not expected:
        return 0.0, 0.0, set(), actual
    if not actual:
        return 0.0, 0.0, expected, set()
    tp = expected & actual
    precision = len(tp) / len(actual)
    recall = len(tp) / len(expected)
    return precision, recall, expected - actual, actual - expected


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max", type=int, default=None, help="Chỉ chạy N câu đầu")
    parser.add_argument(
        "--question", type=int, default=None, help="Chạy đúng câu thứ N (0-indexed)"
    )
    args = parser.parse_args()

    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if args.question is not None:
        cases = [data[args.question]]
        case_indices = [args.question]
    else:
        cases = data
        case_indices = list(range(len(data)))
        if args.max is not None:
            cases = cases[: args.max]
            case_indices = case_indices[: args.max]

    results = []
    for idx, case in zip(case_indices, cases):
        question = case["question"]
        expected_raw = case.get("can_cu_phap_ly_chinh", []) or []
        expected = set(
            d for d in (_normalize_to_dieu(c) for c in expected_raw) if d is not None
        )

        out_of_scope = _is_out_of_scope(expected_raw)

        print("\n" + "═" * 80)
        print(f"[Q{idx + 1}] {question}")
        print(f"  expected (chỉ Đ-level, chỉ Luật HNGD 2014): {sorted(expected)}")
        if out_of_scope:
            print("  (SKIP: out-of-scope Đ28-50, câu này thuộc Đ59-64.)")
            results.append(
                {
                    "idx": idx,
                    "question": question,
                    "expected": sorted(expected),
                    "skipped": True,
                }
            )
            continue

        try:
            run = await _run_one_question(question)
        except Exception as exc:
            print(f"  [ERROR] {exc}")
            results.append(
                {
                    "idx": idx,
                    "question": question,
                    "expected": sorted(expected),
                    "error": str(exc),
                }
            )
            continue

        actual = run["seed_dieu_ids"]
        actual_dieu = {a for a in actual if a and a.startswith("Luat_HNGD_2014_Dieu_")}

        precision, recall, missing, extra = _evaluate(expected, actual_dieu)
        print(f"  templates       : {run['templates']}")
        for pl in run["params_list"]:
            print(f"    • {pl['template']}: params={pl['params']}")
            print(f"      seed Đ-level: {pl['seed_dieu_ids']}")
        print(f"  actual (Đ-level): {sorted(actual_dieu)}")
        print(
            f"  precision={precision:.2f}  recall={recall:.2f}  "
            f"missing={sorted(missing)}  extra={sorted(extra)}"
        )

        results.append(
            {
                "idx": idx,
                "question": question,
                "templates": run["templates"],
                "expected": sorted(expected),
                "actual": sorted(actual_dieu),
                "precision": precision,
                "recall": recall,
                "missing": sorted(missing),
                "extra": sorted(extra),
                "skipped": False,
            }
        )

    # Summary
    in_scope = [r for r in results if not r.get("skipped") and "error" not in r]
    skipped = [r for r in results if r.get("skipped")]
    errored = [r for r in results if "error" in r]

    print("\n" + "═" * 80)
    print("SUMMARY")
    print("═" * 80)
    print(f"Tổng câu: {len(results)}")
    print(f"  - In-scope (đã đo): {len(in_scope)}")
    print(f"  - Skipped (out-of-scope Đ59+): {len(skipped)}")
    print(f"  - Errored: {len(errored)}")
    if in_scope:
        avg_p = sum(r["precision"] for r in in_scope) / len(in_scope)
        avg_r = sum(r["recall"] for r in in_scope) / len(in_scope)
        full_recall = sum(1 for r in in_scope if r["recall"] == 1.0)
        partial = sum(1 for r in in_scope if 0 < r["recall"] < 1.0)
        zero = sum(1 for r in in_scope if r["recall"] == 0)
        print(f"  - Avg precision: {avg_p:.3f}")
        print(f"  - Avg recall:    {avg_r:.3f}")
        print(f"  - Full recall (=1.0):    {full_recall}")
        print(f"  - Partial recall (0<x<1): {partial}")
        print(f"  - Zero recall:           {zero}")


if __name__ == "__main__":
    asyncio.run(main())
