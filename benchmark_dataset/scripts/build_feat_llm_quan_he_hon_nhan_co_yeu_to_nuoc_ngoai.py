#!/usr/bin/env python3
"""
Lọc câu hỏi có ít nhất một căn cứ chính thuộc Điều 121–130 LHNGD 2014
(quan hệ hôn nhân và gia đình có yếu tố nước ngoài).

Quét toàn bộ benchmark_grouped/*.json; chỉ giữ câu đã có can_cu_phap_ly_chinh.
Đầu ra: feat_llm/quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.json
(mỗi phần tử: question + can_cu_phap_ly_chinh).

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.py
    python benchmark_dataset/scripts/build_feat_llm_quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.py --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
GROUPED_DIR = PACKAGE_DIR / "benchmark_grouped"
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.json"

DIEU_121_130_RE = re.compile(r"Luat_HNGD_2014_Dieu_(12[1-9]|130)(?:_|$)")


def _normalize_question(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\n.*@gmail\.com.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n.*@yahoo\.com.*", "", text, flags=re.IGNORECASE)
    return text[:2000]


def _has_can_cu(row: dict) -> bool:
    cc = row.get("can_cu_phap_ly_chinh")
    return isinstance(cc, list) and len(cc) > 0


def _matches_dieu_121_130(can_cu: list[str]) -> bool:
    return any(DIEU_121_130_RE.search(c) for c in can_cu)


def _question_key(text: str) -> str:
    return _normalize_question(text).lower()


def collect_from_grouped() -> tuple[list[dict], dict[str, list[str]]]:
    """Trả về (rows, provenance) với provenance[question_key] = [file, ...]."""
    seen: set[str] = set()
    rows: list[dict] = []
    provenance: dict[str, list[str]] = {}

    for fp in sorted(GROUPED_DIR.glob("*.json")):
        with fp.open(encoding="utf-8") as f:
            benchmark = json.load(f)
        for row in benchmark:
            if not _has_can_cu(row):
                continue
            cc = row["can_cu_phap_ly_chinh"]
            if not _matches_dieu_121_130(cc):
                continue
            key = _question_key(row["question"])
            provenance.setdefault(key, []).append(fp.name)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "question": _normalize_question(row["question"]),
                    "can_cu_phap_ly_chinh": list(cc),
                    "_source": fp.name,
                    "_loai_cau_hoi": row.get("loai_cau_hoi") or "",
                }
            )

    return rows, provenance


def build_output(verbose: bool = False) -> list[dict]:
    rows, provenance = collect_from_grouped()
    if not rows:
        raise ValueError(
            "Không có câu nào trong benchmark_grouped có can_cu_phap_ly_chinh "
            "thuộc Điều 121–130 LHNGD 2014"
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
            f"Tổng câu lọc được: {len(output)}",
            "",
            "--- Theo file nguồn ---",
        ]
        by_source: dict[str, int] = {}
        for r in rows:
            by_source[r["_source"]] = by_source.get(r["_source"], 0) + 1
        for src, n in sorted(by_source.items()):
            lines.append(f"  {src}: {n}")

        lines.append("")
        lines.append("--- Chi tiết ---")
        for i, r in enumerate(rows, 1):
            matched = [c for c in r["can_cu_phap_ly_chinh"] if DIEU_121_130_RE.search(c)]
            lines.append(f"{i:2d}. [{r['_source']}] {matched}")
            lines.append(f"    {r['question'][:120]}")

        dupes = {k: v for k, v in provenance.items() if len(v) > 1}
        if dupes:
            lines.append("")
            lines.append("--- Trùng câu giữa các file (bỏ qua bản sao) ---")
            for k, files in dupes.items():
                lines.append(f"  {files}: {k[:80]}...")

        report_path.write_text("\n".join(lines), encoding="utf-8")

    return output


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ghi báo cáo coverage ra feat_llm/quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.coverage.txt",
    )
    args = parser.parse_args()

    if not GROUPED_DIR.is_dir():
        print(f"Grouped benchmark not found: {GROUPED_DIR}", file=sys.stderr)
        return 1

    output = build_output(verbose=args.verbose)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(output)} items -> feat_llm/quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.json")
    if args.verbose:
        print("Coverage report -> feat_llm/quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.coverage.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
