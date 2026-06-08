#!/usr/bin/env python3
"""
Tổng hợp tối đa 30 câu hỏi đại diện cho chủ đề cấp dưỡng (Điều 107–119 Luật HNGD 2014).

Chỉ lấy câu từ benchmark đã có trường can_cu_phap_ly_chinh.
Đầu ra: mảng JSON, mỗi phần tử chỉ gồm question và can_cu_phap_ly_chinh.

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_cap_duong.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
BENCHMARK_PATH = PACKAGE_DIR / "benchmark_grouped" / "cap_duong.json"
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "cap_duong.json"
MAX_QUESTIONS = 30

# Taxonomy intent (nội bộ, không ghi ra file đầu ra)
INTENT_SPECS: list[dict] = [
    {
        "intent_id": "I01_pham_vi_khong_chuyen_giao",
        "match_articles": ["Luat_HNGD_2014_Dieu_107"],
        "prefer_keywords": ["chuyển giao", "thay thế", "ông bà nội"],
        "slots": 1,
    },
    {
        "intent_id": "I02_quyen_yeu_cau_buoc",
        "match_articles": ["Luat_HNGD_2014_Dieu_119"],
        "prefer_keywords": ["yêu cầu", "buộc", "khởi kiện", "đối tượng nào", "thi hành"],
        "slots": 3,
    },
    {
        "intent_id": "I03_cha_me_cap_duong_con",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_82",
            "Luat_HNGD_2014_Dieu_110",
            "Luat_HNGD_2014_Dieu_69",
        ],
        "prefer_keywords": [
            "không trực tiếp nuôi",
            "ngoài giá thú",
            "đăng ký kết hôn",
            "nghĩa vụ và quyền",
        ],
        "slots": 3,
    },
    {
        "intent_id": "I04_muc_cap_duong_con",
        "match_articles": ["Luat_HNGD_2014_Dieu_116"],
        "prefer_keywords": ["mức", "bao nhiêu", "tối thiểu", "tiền cấp dưỡng", "thay đổi"],
        "exclude_keywords": ["ông bà", "vợ chồng sau ly hôn", "tài sản riêng"],
        "slots": 2,
    },
    {
        "intent_id": "I05_phuong_thuc_cap_duong",
        "match_articles": ["Luat_HNGD_2014_Dieu_117"],
        "prefer_keywords": ["phương thức", "cách"],
        "slots": 1,
    },
    {
        "intent_id": "I06_cham_dut_nghia_vu",
        "match_articles": ["Luat_HNGD_2014_Dieu_118"],
        "prefer_keywords": ["chấm dứt"],
        "slots": 2,
    },
    {
        "intent_id": "I06_thoi_han_cap_duong_con",
        "match_articles": ["Luat_HNGD_2014_Dieu_110", "Luat_HNGD_2014_Dieu_82"],
        "prefer_keywords": ["tuổi", "bao nhiêu tuổi"],
        "slots": 1,
    },
    {
        "intent_id": "I07_tham_nom_va_tu_choi",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_81",
            "Luat_HNGD_2014_Dieu_90",
            "Luat_HNGD_2014_Dieu_91",
            "Luat_HNGD_2014_Dieu_83",
        ],
        "prefer_keywords": ["thăm", "gặp", "nhận cha", "quyền/nghĩa vụ"],
        "slots": 2,
    },
    {
        "intent_id": "I08_cap_duong_vo_chong",
        "match_articles": ["Luat_HNGD_2014_Dieu_115"],
        "prefer_keywords": ["vợ", "chồng", "khó khăn", "túng thiếu"],
        "exclude_keywords": ["tài sản riêng"],
        "slots": 2,
    },
    {
        "intent_id": "I09_tai_san_rieng_cap_duong",
        "match_articles": ["Luat_HNGD_2014_Dieu_115", "Luat_HNGD_2014_Dieu_116"],
        "prefer_keywords": ["tài sản riêng"],
        "slots": 1,
    },
    {
        "intent_id": "I10_ong_ba_chau",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_113",
            "Luat_HNGD_2014_Dieu_112",
        ],
        "prefer_keywords": ["ông bà", "cháu"],
        "slots": 2,
    },
    {
        "intent_id": "I11_tron_tranh_xu_ly",
        "match_articles": [
            "BoLuat_HinhSu_2015_Dieu_186",
            "Luat_HNGD_2014_Dieu_107_Khoan_2",
            "Luat_HNGD_2014_Dieu_119",
        ],
        "prefer_keywords": [
            "trốn tránh",
            "phạt tù",
            "thi hành",
            "không chịu",
            "chây ì",
        ],
        "slots": 2,
    },
    {
        "intent_id": "I12_song_chung_khong_dk_ket_hon",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_14",
            "Luat_HNGD_2014_Dieu_15",
            "Luat_HNGD_2014_Dieu_68",
        ],
        "prefer_keywords": ["không đăng ký", "chung sống", "trợ cấp"],
        "slots": 1,
    },
    {
        "intent_id": "I13_tinh_huong_ly_hon",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_81",
            "Luat_HNGD_2014_Dieu_82",
            "Luat_HNGD_2014_Dieu_116",
        ],
        "prefer_keywords": ["ly hôn", "tòa", "tháng"],
        "require_loai": "Tình huống",
        "slots": 3,
    },
    {
        "intent_id": "I14_nghi_quyet_01",
        "match_articles": ["NghiQuyet_01_2024_NQ_HDTP"],
        "prefer_keywords": ["nghị quyết", "hướng dẫn"],
        "slots": 1,
    },
    {
        "intent_id": "I15_giam_muc_kho_khan",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_116",
            "Luat_HNGD_2014_Dieu_117",
        ],
        "prefer_keywords": ["khó khăn", "nợ", "giảm", "tạm ngừng"],
        "require_loai": "Tình huống",
        "slots": 1,
    },
    {
        "intent_id": "I16_thay_doi_nguoi_nuoi",
        "match_articles": ["Luat_HNGD_2014_Dieu_82_Khoan_2", "Luat_HNGD_2014_Dieu_107"],
        "prefer_keywords": ["thay đổi người trực tiếp nuôi"],
        "slots": 1,
    },
    {
        "intent_id": "I17_phuong_thuc_vo_chong",
        "match_articles": ["Luat_HNGD_2014_Dieu_117"],
        "prefer_keywords": ["vợ chồng sau ly hôn", "giữa vợ chồng"],
        "slots": 1,
    },
]

# Chỉ số dự phòng (0-based, đã có can_cu_phap_ly_chinh) khi tự chọn chưa đủ 30 câu
FALLBACK_INDICES: list[int] = [
    14, 15, 26, 32, 33, 40,
]


def _normalize_question(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\n.*@gmail\.com.*", "", text, flags=re.IGNORECASE)
    return text[:2000]


def _has_can_cu(row: dict) -> bool:
    cc = row.get("can_cu_phap_ly_chinh")
    return isinstance(cc, list) and len(cc) > 0


def _matches_articles(can_cu: list[str], articles: list[str]) -> bool:
    for article in articles:
        base = article.split("_Khoan")[0].split("_Diem")[0]
        for c in can_cu:
            c_base = c.split("_Khoan")[0].split("_Diem")[0]
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
        candidates.append((_score_candidate(row, spec), i))

    candidates.sort(key=lambda x: (-x[0], x[1]))
    slots = spec.get("slots", 1)
    return [idx for _, idx in candidates[:slots]]


def build_output(benchmark: list[dict]) -> list[dict]:
    classified = [i for i, row in enumerate(benchmark) if _has_can_cu(row)]
    if not classified:
        raise ValueError("Không có câu nào trong benchmark có can_cu_phap_ly_chinh")

    used: set[int] = set()
    selected_indices: list[int] = []

    for spec in INTENT_SPECS:
        picks = _select_for_intent(benchmark, spec, used)
        for idx in picks:
            if idx not in used:
                used.add(idx)
                selected_indices.append(idx)

    for idx in FALLBACK_INDICES:
        if len(selected_indices) >= MAX_QUESTIONS:
            break
        if idx in used or idx >= len(benchmark) or not _has_can_cu(benchmark[idx]):
            continue
        used.add(idx)
        selected_indices.append(idx)

    if len(selected_indices) < MAX_QUESTIONS:
        for i in classified:
            if len(selected_indices) >= MAX_QUESTIONS:
                break
            if i not in used:
                used.add(i)
                selected_indices.append(i)

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
    return output


def main() -> int:
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

    output = build_output(benchmark)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(output)} items -> {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
