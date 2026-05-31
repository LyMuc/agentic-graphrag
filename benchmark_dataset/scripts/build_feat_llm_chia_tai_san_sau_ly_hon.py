#!/usr/bin/env python3
"""
Tổng hợp tối đa 30 câu hỏi đại diện cho chia tài sản sau ly hôn (Điều 59–64).

Chỉ lấy câu từ benchmark đã có trường can_cu_phap_ly_chinh.
Đầu ra: mảng JSON, mỗi phần tử chỉ gồm question và can_cu_phap_ly_chinh.

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_chia_tai_san_sau_ly_hon.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
BENCHMARK_PATH = PACKAGE_DIR / "benchmark_grouped" / "chia_tai_san_sau_ly_hon.json"
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "chia_tai_san_sau_ly_hon.json"
MAX_QUESTIONS = 30

# Hướng dẫn chọn câu (nội bộ, không ghi ra file đầu ra)
INTENT_SPECS: list[dict] = [
    {
        "intent_id": "I01_thoa_thuan_hoac_toa",
        "match_articles": ["Luat_HNGD_2014_Dieu_59"],
        "prefer_keywords": ["nguyên tắc", "thỏa thuận", "thực hiện như thế nào"],
        "slots": 1,
    },
    {
        "intent_id": "I02_chia_doi_khong_chia_deu",
        "match_articles": ["Luat_HNGD_2014_Dieu_59"],
        "prefer_keywords": ["chia đều", "mọi trường hợp"],
        "require_can_cu_substrings": ["Khoan_2"],
        "exclude_keywords": ["yếu tố nào", "trụ cột", "phải tính"],
        "slots": 1,
    },
    {
        "intent_id": "I03_yeu_to_cong_suc_hoan_canh",
        "match_articles": ["Luat_HNGD_2014_Dieu_59"],
        "prefer_keywords": ["trụ cột", "công sức", "yếu tố", "lao động"],
        "slots": 1,
    },
    {
        "intent_id": "I04_loi_vi_pham_quyen_nghia_vu",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_59",
            "TT_01_2016_TTLT_TANDTC_VKSNDTC_BTP",
        ],
        "prefer_keywords": ["lỗi", "vi phạm", "ngoại tình"],
        "slots": 1,
    },
    {
        "intent_id": "I05_chia_hien_vat_hoac_gia_tri",
        "match_articles": ["Luat_HNGD_2014_Dieu_59"],
        "prefer_keywords": ["trả góp", "căn nhà", "hiện vật", "giá trị"],
        "slots": 1,
    },
    {
        "intent_id": "I06_tai_san_rieng",
        "match_articles": ["Luat_HNGD_2014_Dieu_59", "Luat_HNGD_2014_Dieu_33"],
        "prefer_keywords": ["riêng", "quà cưới", "tặng cho", "ngày cưới"],
        "slots": 2,
    },
    {
        "intent_id": "I07_tron_lan_rieng_va_chung",
        "match_articles": ["Luat_HNGD_2014_Dieu_59"],
        "prefer_keywords": ["bỏ nhà", "cải tạo", "đóng góp"],
        "slots": 1,
    },
    {
        "intent_id": "I08_bao_ve_vo_va_con",
        "match_articles": ["Luat_HNGD_2014_Dieu_59"],
        "prefer_keywords": ["tính đến", "bảo vệ", "khó khăn", "phải tính"],
        "require_can_cu_substrings": ["Khoan_2"],
        "exclude_keywords": ["yếu tố nào", "trụ cột"],
        "slots": 1,
    },
    {
        "intent_id": "I09_no_va_nguoi_thu_ba",
        "match_articles": ["Luat_HNGD_2014_Dieu_60"],
        "prefer_keywords": ["nợ", "người thứ ba", "vay"],
        "slots": 2,
    },
    {
        "intent_id": "I10_song_chung_gia_dinh_khong_xacdinh",
        "match_articles": ["Luat_HNGD_2014_Dieu_61"],
        "prefer_keywords": ["sống chung", "gia đình"],
        "slots": 1,
    },
    {
        "intent_id": "I11_song_chung_gia_dinh_trich_phan",
        "match_articles": ["Luat_HNGD_2014_Dieu_33", "Luat_HNGD_2014_Dieu_61"],
        "prefer_keywords": ["bố mẹ", "mẹ chồng", "cha mẹ"],
        "slots": 1,
    },
    {
        "intent_id": "I12_quyen_su_dung_dat_rieng",
        "match_articles": ["Luat_HNGD_2014_Dieu_62"],
        "prefer_keywords": ["riêng", "không phải chia"],
        "slots": 1,
    },
    {
        "intent_id": "I13_chia_quyen_su_dung_dat_chung",
        "match_articles": ["Luat_HNGD_2014_Dieu_62"],
        "prefer_keywords": ["quyền sử dụng đất", "chia"],
        "slots": 2,
    },
    {
        "intent_id": "I14_nha_tren_dat_nguoi_khac",
        "match_articles": ["Luat_HNGD_2014_Dieu_62", "Luat_HNGD_2014_Dieu_33"],
        "prefer_keywords": ["giấu", "mua đất"],
        "slots": 1,
    },
    {
        "intent_id": "I15_quyen_luu_cu",
        "match_articles": ["Luat_HNGD_2014_Dieu_63"],
        "prefer_keywords": ["lưu cư", "ở lại", "nhà riêng"],
        "slots": 1,
    },
    {
        "intent_id": "I16_tai_san_dua_vao_kinh_doanh",
        "match_articles": ["Luat_HNGD_2014_Dieu_64"],
        "prefer_keywords": ["kinh doanh"],
        "slots": 2,
    },
    {
        "intent_id": "I17_phan_loai_tai_san_chung_rieng",
        "match_articles": ["Luat_HNGD_2014_Dieu_33"],
        "prefer_keywords": ["tài sản chung", "tài sản riêng", "đứng tên"],
        "slots": 2,
    },
    {
        "intent_id": "I18_gian_do_che_giau_tai_san",
        "match_articles": ["Luat_HNGD_2014_Dieu_59"],
        "prefer_keywords": ["gian dối", "giấu"],
        "slots": 1,
    },
    {
        "intent_id": "I19_thoa_thuan_che_do_tai_san",
        "match_articles": ["Luat_HNGD_2014_Dieu_35", "Luat_HNGD_2014_Dieu_47"],
        "prefer_keywords": ["thỏa thuận", "công chứng"],
        "slots": 1,
    },
    {
        "intent_id": "I20_tinh_huong_phuc_tap_da_yeu_to",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_59",
            "Luat_HNGD_2014_Dieu_33",
        ],
        "prefer_keywords": ["lao động", "ly hôn"],
        "min_can_cu_count": 2,
        "slots": 1,
    },
]

# Chỉ số dự phòng (đã có can_cu_phap_ly_chinh) khi tự chọn không đủ 30 câu
FALLBACK_INDICES: list[int] = [
    90, 83, 6, 54, 105, 59, 67, 57, 45, 123,
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
            if c == article or c.startswith(article) or c_base == base:
                return True
            if base in c:
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
    candidates: list[tuple[float, int]] = []

    for i, row in enumerate(benchmark):
        if i in used or not _has_can_cu(row):
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
