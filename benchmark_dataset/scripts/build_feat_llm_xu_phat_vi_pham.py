#!/usr/bin/env python3
"""
Tổng hợp tối đa 30 câu hỏi đại diện cho chủ đề xử phạt vi phạm hành chính / hình sự
trong lĩnh vực hôn nhân gia đình.

Nguồn: benchmark_grouped/xu_phat_vi_pham.json (chỉ câu có can_cu_phap_ly_chinh).
Lọc theo intent để tránh nhiều câu cùng ý hỏi (vd. nhiều câu « không cấp dưỡng »).

Đầu ra: feat_llm/xu_phat_vi_pham.json (question + can_cu_phap_ly_chinh).

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_xu_phat_vi_pham.py
    python benchmark_dataset/scripts/build_feat_llm_xu_phat_vi_pham.py --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
BENCHMARK_PATH = PACKAGE_DIR / "benchmark_grouped" / "xu_phat_vi_pham.json"
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "xu_phat_vi_pham.json"
MAX_QUESTIONS = 30

# Intent cụ thể đặt trước intent rộng để tránh chọn trùng câu.
INTENT_SPECS: list[dict] = [
    {
        "intent_id": "I01_hop_dong_hon_nhan_trai_phap_luat",
        "match_articles": ["NghiDinh_82_2020_ND_CP_Dieu_59"],
        "prefer_keywords": ["hợp đồng hôn nhân"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I02_ngoai_tinh_vphc",
        "match_articles": [
            "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1",
            "NghiDinh_82_2020_ND_CP_Dieu_59",
        ],
        "prefer_keywords": ["ngoại tình", "phạt hành chính", "phạt tiền"],
        "exclude_keywords": ["truy cứu", "hình sự", "phạt tù", "tù"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I03_chiem_doat_tai_san_rieng",
        "match_articles": ["NghiDinh_282_2025_ND_CP_Dieu_44"],
        "prefer_keywords": ["chiếm đoạt", "tài sản riêng"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I04_cap_duong_vphc",
        "match_articles": ["NghiDinh_282_2025_ND_CP_Dieu_43"],
        "prefer_keywords": [
            "cấp dưỡng",
            "phạt",
            "xử phạt",
            "vi phạm hành chính",
        ],
        "exclude_keywords": ["hình sự", "truy cứu", "phạt tù", "tù"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I05_bao_luc_gia_dinh",
        "match_articles": ["NghiDinh_282_2025_ND_CP_Dieu_45"],
        "require_loai": "Tình huống",
        "slots": 1,
    },
    {
        "intent_id": "I06_cuong_ep_ly_hon_vphc",
        "match_articles": ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2"],
        "prefer_keywords": ["cưỡng ép", "ly hôn"],
        "exclude_keywords": ["hình sự", "truy cứu"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I07_thach_cuoi_can_tro_ket_hon_vphc",
        "match_articles": [
            "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1",
        ],
        "prefer_keywords": ["thách cưới", "cản trở kết hôn", "cản trở người khác kết hôn"],
        "exclude_keywords": ["hình sự", "truy cứu", "cưỡng ép"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I08_ket_hon_can_huyet_vphc",
        "match_articles": [
            "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_a",
            "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2",
        ],
        "prefer_keywords": [
            "ba đời",
            "cận huyết",
            "họ trong phạm vi",
        ],
        "exclude_keywords": ["hình sự", "truy cứu", "loạn luân"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I09_ket_hon_cha_me_nuoi",
        "match_articles": ["NghiDinh_82_2020_ND_CP_Dieu_59"],
        "prefer_keywords": ["cha nuôi", "mẹ nuôi"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I10_ket_hon_gia_nhap_quoc_tich",
        "match_articles": [
            "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2",
            "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_3",
        ],
        "prefer_keywords": ["giả", "quốc tịch", "nhập quốc tịch"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I11_tao_hon_chua_du_tuoi",
        "match_articles": ["NghiDinh_82_2020_ND_CP_Dieu_58"],
        "prefer_keywords": ["chưa đủ tuổi", "tảo hôn", "kết hôn khi chưa"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I12_can_tro_tham_nuoi_con",
        "match_articles": ["NghiDinh_282_2025_ND_CP_Dieu_42"],
        "prefer_keywords": ["thăm", "nuôi con", "cản trở"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I13_vi_pham_mot_vo_mot_chong_lhngd",
        "match_articles": ["Luat_HNGD_2014_Dieu_5_Khoan_2"],
        "prefer_keywords": ["một vợ", "một chồng", "nguyên tắc hôn nhân"],
        "exclude_keywords": ["truy cứu", "hình sự"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I14_ngoai_tinh_hinh_su_ly_thuyet",
        "match_articles": ["BoLuat_HinhSu_2015_Dieu_182"],
        "require_loai": "Lý thuyết",
        "prefer_keywords": ["ngoại tình", "một vợ", "một chồng", "hình sự", "truy cứu"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I15_ngoai_tinh_hinh_su_tinh_huong",
        "match_articles": ["BoLuat_HinhSu_2015_Dieu_182"],
        "require_loai": "Tình huống",
        "prefer_keywords": ["ngoại tình", "gia đình"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I16_cuong_ep_ly_hon_hinh_su",
        "match_articles": ["BoLuat_HinhSu_2015_Dieu_181"],
        "prefer_keywords": ["cưỡng ép", "ly hôn"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I17_khong_cap_duong_hinh_su",
        "match_articles": ["BoLuat_HinhSu_2015_Dieu_186"],
        "prefer_keywords": ["cấp dưỡng", "hình sự", "truy cứu", "trốn tránh"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I18_to_chuc_tao_hon_hinh_su",
        "match_articles": ["BoLuat_HinhSu_2015_Dieu_183"],
        "prefer_keywords": ["tổ chức", "hôn lễ", "tảo hôn", "chưa đủ tuổi"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I19_loan_luan_hinh_su",
        "match_articles": ["BoLuat_HinhSu_2015_Dieu_184"],
        "prefer_keywords": ["cận huyết", "loạn luân", "hình sự", "truy cứu"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I20_can_tro_ket_hon_che_tai",
        "match_articles": [
            "BoLuat_HinhSu_2015_Dieu_181",
            "NghiDinh_82_2020_ND_CP_Dieu_59",
        ],
        "min_can_cu_count": 2,
        "prefer_keywords": [
            "cản trở người khác kết hôn",
            "ra sức cản trở",
            "chế tài",
        ],
        "exclude_keywords": ["cận huyết", "thách cưới", "ba đời"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I21_ket_hon_trai_phap_luat_tong_quat",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_3_Khoan_6",
            "Luat_HNGD_2014_Dieu_5_Khoan_2",
        ],
        "min_can_cu_count": 3,
        "prefer_keywords": ["kết hôn trái pháp luật", "trường hợp nào"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I22_tinh_huong_phuc_tap",
        "match_articles": [
            "NghiDinh_82_2020_ND_CP_Dieu_59",
            "Luat_HNGD_2014_Dieu_3",
        ],
        "require_loai": "Tình huống",
        "min_can_cu_count": 2,
        "slots": 1,
    },
    {
        "intent_id": "I23_ngoai_tinh_muc_tu_toi_da",
        "match_articles": ["BoLuat_HinhSu_2015_Dieu_182"],
        "prefer_keywords": ["phạt tù", "cao nhất", "bao nhiêu năm"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I24_vi_pham_mvomvc_hinh_su",
        "match_articles": ["BoLuat_HinhSu_2015_Dieu_182"],
        "prefer_keywords": ["một vợ", "một chồng", "hình sự"],
        "exclude_keywords": ["ngoại tình", "phạt tù cao nhất", "khi nào"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I25_khong_cap_duong_hs_con",
        "match_articles": ["BoLuat_HinhSu_2015_Dieu_186"],
        "prefer_keywords": ["cho con", "con sau"],
        "exclude_keywords": ["trốn tránh", "vợ và chồng", "giữa vợ"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I26_khong_cap_duong_hs_vo_chong",
        "match_articles": ["BoLuat_HinhSu_2015_Dieu_186"],
        "prefer_keywords": ["vợ và chồng", "giữa vợ", "phạt tù"],
        "exclude_keywords": ["trốn tránh", "cho con"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I27_ket_hon_can_huyet_vphc_va_hs",
        "match_articles": [
            "BoLuat_HinhSu_2015_Dieu_184",
            "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2",
        ],
        "min_can_cu_count": 2,
        "prefer_keywords": ["cận huyết", "phạt"],
        "exclude_keywords": ["truy cứu", "hình sự", "ba đời"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
]


def _normalize_question(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\n.*@gmail\.com.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n.*@yahoo\.com.*", "", text, flags=re.IGNORECASE)
    return text[:2000]


def _normalize_article_id(article_id: str) -> str:
    return article_id.replace("Nghi_dinh_", "NghiDinh_")


def _has_can_cu(row: dict) -> bool:
    cc = row.get("can_cu_phap_ly_chinh")
    return isinstance(cc, list) and len(cc) > 0


def _article_base(article_id: str) -> str:
    article_id = _normalize_article_id(article_id)
    return article_id.split("_Khoan")[0].split("_Diem")[0]


def _matches_articles(can_cu: list[str], articles: list[str]) -> bool:
    normalized_cc = [_normalize_article_id(c) for c in can_cu]
    for article in articles:
        article = _normalize_article_id(article)
        base = _article_base(article)
        for c in normalized_cc:
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
        score += 5

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
    require_loai = spec.get("require_loai")
    candidates: list[tuple[float, int]] = []

    for i, row in enumerate(benchmark):
        if i in used or not _has_can_cu(row):
            continue
        if require_loai and row.get("loai_cau_hoi") != require_loai:
            continue
        cc = row["can_cu_phap_ly_chinh"]
        if not _matches_articles(cc, spec["match_articles"]):
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
        lines.append("--- Câu đã chọn ---")
        for n, idx in enumerate(selected_indices, 1):
            intent = intent_by_idx.get(idx, "?")
            cc = ", ".join(benchmark[idx]["can_cu_phap_ly_chinh"])
            lines.append(f"{n:2d}. #{idx + 1} [{intent}]")
            lines.append(f"    {cc}")
            lines.append(f"    {benchmark[idx]['question'][:120]}")

        report_path.write_text("\n".join(lines), encoding="utf-8")

    return output, coverage


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ghi báo cáo coverage intent ra feat_llm/xu_phat_vi_pham.coverage.txt",
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

    print(f"Wrote {len(output)} items -> feat_llm/xu_phat_vi_pham.json")
    if args.verbose:
        print("Coverage report -> feat_llm/xu_phat_vi_pham.coverage.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
