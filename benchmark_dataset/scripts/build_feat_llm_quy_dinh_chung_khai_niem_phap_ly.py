#!/usr/bin/env python3
"""
Lọc câu hỏi có can_cu_phap_ly_chinh từ benchmark chủ đề quy định chung, khái niệm pháp lý
(Điều 2–5, Điều 3 LHNGD 2014).

Nguồn: benchmark_grouped/quy_dinh_chung_khai_niem_phap_ly.json
Đầu ra: feat_llm/quy_dinh_chung_khai_niem_phap_ly.json
(mỗi phần tử: question + can_cu_phap_ly_chinh).

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_quy_dinh_chung_khai_niem_phap_ly.py
    python benchmark_dataset/scripts/build_feat_llm_quy_dinh_chung_khai_niem_phap_ly.py --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
BENCHMARK_PATH = (
    PACKAGE_DIR / "benchmark_grouped" / "quy_dinh_chung_khai_niem_phap_ly.json"
)
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "quy_dinh_chung_khai_niem_phap_ly.json"


def _normalize_question(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\n.*@gmail\.com.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n.*@yahoo\.com.*", "", text, flags=re.IGNORECASE)
    return text[:2000]


def _has_can_cu(row: dict) -> bool:
    cc = row.get("can_cu_phap_ly_chinh")
    return isinstance(cc, list) and len(cc) > 0


def _question_key(text: str) -> str:
    return _normalize_question(text).lower()


def build_output(benchmark: list[dict], verbose: bool = False) -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    skipped: list[str] = []

    for row in benchmark:
        if not _has_can_cu(row):
            skipped.append(row.get("question", "")[:120])
            continue
        key = _question_key(row["question"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "question": _normalize_question(row["question"]),
                "can_cu_phap_ly_chinh": list(row["can_cu_phap_ly_chinh"]),
                "_loai_cau_hoi": (row.get("loai_cau_hoi") or "").strip(),
            }
        )

    if not rows:
        raise ValueError(
            "Không có câu nào trong benchmark có can_cu_phap_ly_chinh"
        )

    output = [
        {
            "question": r["question"],
            "can_cu_phap_ly_chinh": r["can_cu_phap_ly_chinh"],
        }
        for r in rows
    ]

    if verbose:
        report_path = OUTPUT_PATH.with_suffix(".coverage.txt")
        lines = [
            f"Tổng câu benchmark: {len(benchmark)}",
            f"Câu có căn cứ chính: {len(output)}",
            f"Bỏ qua (không có căn cứ): {len(skipped)}",
            "",
            "--- Theo điều luật (căn cứ chính) ---",
        ]
        by_article: dict[str, int] = {}
        for r in rows:
            for c in r["can_cu_phap_ly_chinh"]:
                by_article[c] = by_article.get(c, 0) + 1
        for article, n in sorted(by_article.items()):
            lines.append(f"  {article}: {n}")

        lines.append("")
        lines.append("--- Chi tiết ---")
        for i, r in enumerate(rows, 1):
            loai = r["_loai_cau_hoi"] or "?"
            lines.append(f"{i:2d}. [{loai}] {r['can_cu_phap_ly_chinh']}")
            lines.append(f"    {r['question'][:120]}")

        if skipped:
            lines.append("")
            lines.append("--- Bỏ qua ---")
            for q in skipped:
                lines.append(f"  {q}")

        report_path.write_text("\n".join(lines), encoding="utf-8")

    return output


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        action="store_true",
        help=(
            "Ghi báo cáo coverage ra "
            "feat_llm/quy_dinh_chung_khai_niem_phap_ly.coverage.txt"
        ),
    )
    args = parser.parse_args()

    if not BENCHMARK_PATH.is_file():
        print(f"Benchmark not found: {BENCHMARK_PATH}", file=sys.stderr)
        return 1

    with BENCHMARK_PATH.open(encoding="utf-8") as f:
        benchmark = json.load(f)

    n_classified = sum(1 for r in benchmark if _has_can_cu(r))
    print(
        f"Loaded {len(benchmark)} questions "
        f"({n_classified} with can_cu_phap_ly_chinh)"
    )

    output = build_output(benchmark, verbose=args.verbose)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        f"Wrote {len(output)} items -> "
        "feat_llm/quy_dinh_chung_khai_niem_phap_ly.json"
    )
    if args.verbose:
        print(
            "Coverage report -> "
            "feat_llm/quy_dinh_chung_khai_niem_phap_ly.coverage.txt"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
