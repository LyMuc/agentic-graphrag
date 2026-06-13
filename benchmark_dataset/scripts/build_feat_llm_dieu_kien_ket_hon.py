#!/usr/bin/env python3
"""
Tổng hợp tối đa 30 câu hỏi đại diện cho chủ đề điều kiện kết hôn (Điều 8, Điều 5 LHNGD 2014).

Chỉ lấy câu từ benchmark đã có trường can_cu_phap_ly_chinh.
Đầu ra: mảng JSON, mỗi phần tử chỉ gồm question và can_cu_phap_ly_chinh.

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_dieu_kien_ket_hon.py
    python benchmark_dataset/scripts/build_feat_llm_dieu_kien_ket_hon.py --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
BENCHMARK_PATH = PACKAGE_DIR / "benchmark_grouped" / "dieu_kien_ket_hon.json"
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "dieu_kien_ket_hon.json"
MAX_QUESTIONS = 30

# Taxonomy intent (nội bộ, không ghi ra file đầu ra).
# Intent cụ thể đặt trước intent rộng để tránh chọn trùng câu.
INTENT_SPECS: list[dict] = [
    {
        "intent_id": "I01_hon_nhan_dong_gioi",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_8",
            "Luat_HNGD_2014_Dieu_5",
            "Luat_HNGD_2014_Dieu_3_Khoan_3",
        ],
        "prefer_keywords": ["đồng giới", "cùng giới"],
        "require_any_prefer_keyword": True,
        "slots": 2,
    },
    {
        "intent_id": "I02_do_tuoi_ket_hon",
        "match_articles": ["Luat_HNGD_2014_Dieu_8"],
        "prefer_keywords": [
            "tuổi",
            "sinh năm",
            "18 tuổi",
            "2024",
            "2026",
            "độ tuổi",
        ],
        "require_any_prefer_keyword": True,
        "exclude_keywords": ["xung khắc", "tín ngưỡng", "ông bà nội"],
        "slots": 3,
    },
    {
        "intent_id": "I03_truong_hop_cam_ket_hon",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_5_Khoan_2",
            "Luat_HNGD_2014_Dieu_5",
        ],
        "prefer_keywords": [
            "bị cấm",
            "trường hợp nào",
            "huyết thống",
        ],
        "exclude_keywords": [
            "cha dượng",
            "cha chồng",
            "em chồng",
            "anh vợ",
            "con riêng",
            "cận huyết",
            "ba đời",
            "anh em",
        ],
        "slots": 2,
    },
    {
        "intent_id": "I04_huyet_thong_ba_doi",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d",
            "Luat_HNGD_2014_Dieu_3_Khoan_18",
            "Luat_HNGD_2014_Dieu_3",
            "Luat_HNGD_2014_Dieu_5",
        ],
        "prefer_keywords": [
            "ba đời",
            "cận huyết",
            "họ hàng",
            "dòng máu",
            "anh em cùng cha",
            "cháu nội",
            "phạm vi",
            "chú họ",
        ],
        "require_any_prefer_keyword": True,
        "exclude_keywords": [
            "cha dượng",
            "cha chồng",
            "em chồng",
            "em gái vợ",
            "em trai chồng",
            "con riêng",
            "án treo",
            "án tích",
            "ly hôn",
            "bại liệt",
        ],
        "slots": 5,
    },
    {
        "intent_id": "I05_quan_he_gia_dinh_vo_chong",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d",
            "Luat_HNGD_2014_Dieu_5_Khoan_2",
            "Luat_HNGD_2014_Dieu_3_Khoan_17",
            "Luat_HNGD_2014_Dieu_3_Khoan_18",
            "Luat_HNGD_2014_Dieu_8",
        ],
        "prefer_keywords": [
            "cha chồng",
            "cha dượng",
            "con dâu",
            "em chồng",
            "anh vợ",
            "em trai chồng",
            "em gái vợ",
            "con riêng",
            "ba đời",
        ],
        "require_any_prefer_keyword": True,
        "slots": 6,
    },
    {
        "intent_id": "I06_dang_ky_va_vo_chong_hop_phap",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_9",
            "Luat_HNGD_2014_Dieu_8",
            "Luat_HNGD_2014_Dieu_3_Khoan_1",
            "Luat_HNGD_2014_Dieu_3_Khoan_5",
        ],
        "prefer_keywords": [
            "đăng ký",
            "đám cưới",
            "vợ chồng hợp pháp",
            "công nhận là vợ chồng",
        ],
        "require_any_prefer_keyword": True,
        "slots": 2,
    },
    {
        "intent_id": "I07_tinh_trang_ca_nhan",
        "match_articles": ["Luat_HNGD_2014_Dieu_8", "Luat_HNGD_2014_Dieu_5"],
        "prefer_keywords": [
            "án tích",
            "án treo",
            "ly hôn",
            "khẩu",
            "bại liệt",
        ],
        "require_any_prefer_keyword": True,
        "exclude_keywords": [
            "ba đời",
            "cha dượng",
            "cha chồng",
            "đồng giới",
        ],
        "slots": 3,
    },
    {
        "intent_id": "I08_tinh_huong_ca_nhan",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_8",
            "Luat_HNGD_2014_Dieu_5",
            "Luat_HNGD_2014_Dieu_3_Khoan_18",
        ],
        "require_loai": "Tình huống",
        "slots": 3,
    },
    {
        "intent_id": "I09_yeu_to_dac_biet",
        "match_articles": ["Luat_HNGD_2014_Dieu_8", "Luat_HNGD_2014_Dieu_5"],
        "prefer_keywords": [
            "xung khắc",
            "tín ngưỡng",
            "giáo viên",
            "học sinh",
        ],
        "require_any_prefer_keyword": True,
        "slots": 2,
    },
    {
        "intent_id": "I10_dieu_kien_tong_quat",
        "match_articles": ["Luat_HNGD_2014_Dieu_8"],
        "prefer_keywords": [
            "điều kiện kết hôn",
            "điều kiện để kết hôn",
            "muốn kết hôn",
            "đáp ứng",
            "điều kiện được kết hôn",
            "điều kiện đăng ký",
        ],
        "exclude_keywords": [
            "cha dượng",
            "cha chồng",
            "em chồng",
            "anh vợ",
            "con riêng",
            "đồng giới",
            "sinh năm",
            "18 tuổi",
            "án tích",
            "án treo",
            "bại liệt",
            "xung khắc",
            "giáo viên",
            "ba đời",
            "cận huyết",
            "vợ chồng hợp pháp",
            "đám cưới",
        ],
        "slots": 2,
    },
]

FALLBACK_INDICES: list[int] = []


def _normalize_question(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\n.*@gmail\.com.*", "", text, flags=re.IGNORECASE)
    return text[:2000]


def _has_can_cu(row: dict) -> bool:
    cc = row.get("can_cu_phap_ly_chinh")
    return isinstance(cc, list) and len(cc) > 0


def _article_base(article_id: str) -> str:
    return article_id.split("_Khoan")[0].split("_Diem")[0]


def _matches_articles(can_cu: list[str], articles: list[str]) -> bool:
    for article in articles:
        if article == "Luat_HNGD_2014":
            if any(
                c == "Luat_HNGD_2014" or c.startswith("Luat_HNGD_2014_Dieu_")
                for c in can_cu
            ):
                return True
            continue

        base = _article_base(article)
        for c in can_cu:
            c_base = _article_base(c)
            if c == article or c.startswith(article + "_") or c_base == base:
                return True
            if article in c or base in c:
                return True
    return False


def _score_candidate(row: dict, spec: dict) -> float:
    q = row["question"].lower()
    score = 0.0

    if row.get("loai_cau_hoi") == "Lý thuyết":
        score += 10
    elif row.get("loai_cau_hoi") == "Tình huống":
        score += 3

    for kw in spec.get("prefer_keywords", []):
        if kw.lower() in q:
            score += 5

    for kw in spec.get("exclude_keywords", []):
        if kw.lower() in q:
            score -= 20

    cc = row.get("can_cu_phap_ly_chinh") or []
    for sub in spec.get("require_can_cu_substrings", []):
        if any(sub in c for c in cc):
            score += 8

    min_cc = spec.get("min_can_cu_count")
    if min_cc and len(cc) >= min_cc:
        score += 6

    for c in cc:
        if "Dieu_8" in c:
            score += 2
        if "Dieu_5" in c:
            score += 2

    score -= len(q) / 500
    return score


def _select_for_intent(
    benchmark: list[dict],
    spec: dict,
    used: set[int],
) -> list[int]:
    articles = spec["match_articles"]
    require_loai = spec.get("require_loai")
    candidates: list[tuple[float, int]] = []

    for i, row in enumerate(benchmark):
        if i in used or not _has_can_cu(row):
            continue
        if require_loai and row.get("loai_cau_hoi") != require_loai:
            continue
        cc = row["can_cu_phap_ly_chinh"]
        if not _matches_articles(cc, articles):
            continue
        if spec.get("require_can_cu_substrings"):
            if not any(
                sub in c
                for c in cc
                for sub in spec["require_can_cu_substrings"]
            ):
                continue
        q_lower = row["question"].lower()
        if spec.get("require_any_prefer_keyword"):
            if not any(kw.lower() in q_lower for kw in spec.get("prefer_keywords", [])):
                continue
            if any(kw.lower() in q_lower for kw in spec.get("exclude_keywords", [])):
                continue
        candidates.append((_score_candidate(row, spec), i))

    candidates.sort(key=lambda x: (-x[0], x[1]))
    slots = spec.get("slots", 1)
    return [idx for _, idx in candidates[:slots]]


def build_output(
    benchmark: list[dict],
    verbose: bool = False,
) -> tuple[list[dict], dict[str, list[int]]]:
    classified = [i for i, row in enumerate(benchmark) if _has_can_cu(row)]
    if not classified:
        raise ValueError("Không có câu nào trong benchmark có can_cu_phap_ly_chinh")

    used: set[int] = set()
    selected_indices: list[int] = []
    coverage: dict[str, list[int]] = {}

    for spec in INTENT_SPECS:
        if len(selected_indices) >= MAX_QUESTIONS:
            break
        remaining = MAX_QUESTIONS - len(selected_indices)
        spec_slots = min(spec.get("slots", 1), remaining)
        if spec_slots <= 0:
            continue
        spec_run = {**spec, "slots": spec_slots}
        picks = _select_for_intent(benchmark, spec_run, used)
        coverage[spec["intent_id"]] = picks
        for idx in picks:
            if idx not in used and len(selected_indices) < MAX_QUESTIONS:
                used.add(idx)
                selected_indices.append(idx)

    for idx in FALLBACK_INDICES:
        if len(selected_indices) >= MAX_QUESTIONS:
            break
        if idx in used or idx >= len(benchmark) or not _has_can_cu(benchmark[idx]):
            continue
        used.add(idx)
        selected_indices.append(idx)
        coverage.setdefault("_fallback", []).append(idx)

    if len(selected_indices) < MAX_QUESTIONS:
        for i in classified:
            if len(selected_indices) >= MAX_QUESTIONS:
                break
            if i not in used:
                used.add(i)
                selected_indices.append(i)
                coverage.setdefault("_fill", []).append(i)

    selected_indices = selected_indices[:MAX_QUESTIONS]

    output: list[dict] = []
    for idx in selected_indices:
        row = benchmark[idx]
        output.append(
            {
                "question": _normalize_question(row["question"]),
                "can_cu_phap_ly_chinh": list(row["can_cu_phap_ly_chinh"]),
            }
        )

    if verbose:
        report_path = OUTPUT_PATH.with_suffix(".coverage.txt")
        lines: list[str] = []
        intent_by_idx: dict[int, str] = {}
        for intent_id, indices in coverage.items():
            if intent_id.startswith("_"):
                continue
            for idx in indices:
                intent_by_idx.setdefault(idx, intent_id)

        lines.append("--- Coverage theo intent ---")
        for spec in INTENT_SPECS:
            iid = spec["intent_id"]
            picks = coverage.get(iid, [])
            lines.append(f"{iid} ({len(picks)}/{spec.get('slots', 1)}):")
            for idx in picks:
                q = benchmark[idx]["question"][:120]
                lines.append(f"  #{idx + 1}: {q}")

        lines.append("")
        lines.append("--- Cau da chon ---")
        for n, idx in enumerate(selected_indices, 1):
            if idx in coverage.get("_fallback", []):
                intent = "_fallback"
            elif idx in coverage.get("_fill", []):
                intent = "_fill"
            else:
                intent = intent_by_idx.get(idx, "?")
            lines.append(f"{n:2d}. #{idx + 1} [{intent}]")

        report_path.write_text("\n".join(lines), encoding="utf-8")

    return output, coverage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="In coverage intent và chỉ số câu đã chọn",
    )
    args = parser.parse_args()

    if not BENCHMARK_PATH.is_file():
        print(f"Benchmark not found: {BENCHMARK_PATH}", file=sys.stderr)
        return 1

    with BENCHMARK_PATH.open(encoding="utf-8") as f:
        benchmark = json.load(f)

    n_classified = sum(1 for r in benchmark if _has_can_cu(r))
    print(f"Loaded {len(benchmark)} questions ({n_classified} with can_cu_phap_ly_chinh)")

    if n_classified < MAX_QUESTIONS:
        print(
            f"Warning: only {n_classified} classified rows; output may have < {MAX_QUESTIONS} items",
            file=sys.stderr,
        )

    output, coverage = build_output(benchmark, verbose=args.verbose)

    filled_intents = sum(
        1 for spec in INTENT_SPECS if coverage.get(spec["intent_id"])
    )
    print(
        f"Intent covered: {filled_intents}/{len(INTENT_SPECS)}; "
        f"selected: {len(output)}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(output)} items -> feat_llm/dieu_kien_ket_hon.json")
    if args.verbose:
        print("Coverage report -> feat_llm/dieu_kien_ket_hon.coverage.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
