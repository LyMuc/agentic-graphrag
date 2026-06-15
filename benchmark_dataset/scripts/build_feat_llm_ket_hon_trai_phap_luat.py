#!/usr/bin/env python3
"""
Tổng hợp tối đa 30 câu hỏi đại diện cho chủ đề kết hôn trái pháp luật
(Điều 10–12 LHNGD 2014; Thông tư 01/2016).

Chỉ lấy câu từ benchmark đã có trường can_cu_phap_ly_chinh.
Đầu ra: mảng JSON, mỗi phần tử chỉ gồm question và can_cu_phap_ly_chinh.

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_ket_hon_trai_phap_luat.py
    python benchmark_dataset/scripts/build_feat_llm_ket_hon_trai_phap_luat.py --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
BENCHMARK_PATH = PACKAGE_DIR / "benchmark_grouped" / "ket_hon_trai_phap_luat.json"
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "ket_hon_trai_phap_luat.json"
MAX_QUESTIONS = 30

# Intent cụ thể đặt trước intent rộng để tránh chọn trùng câu.
INTENT_SPECS: list[dict] = [
    {
        "intent_id": "I01_dinh_nghia_va_truong_hop",
        "match_articles": ["Luat_HNGD_2014_Dieu_3_Khoan_6"],
        "prefer_keywords": [
            "là gì",
            "thế nào là",
            "trường hợp nào",
            "được xem là",
        ],
        "require_any_prefer_keyword": True,
        "slots": 3,
    },
    {
        "intent_id": "I02_xac_dinh_hanh_vi_vi_pham",
        "match_articles": ["Luat_HNGD_2014_Dieu_5_Khoan_2"],
        "prefer_keywords": ["hợp đồng hôn nhân", "vi phạm"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I03_tham_quyen_giai_quyet",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_11",
            "Luat_HNGD_2014_Dieu_10",
        ],
        "prefer_keywords": ["cơ quan nào", "thẩm quyền"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I04_xu_ly_va_cong_nhan_hon_nhan",
        "match_articles": ["Luat_HNGD_2014_Dieu_11"],
        "prefer_keywords": [
            "công nhận",
            "bị hủy không",
            "liệu có bị hủy",
        ],
        "exclude_keywords": ["thẩm quyền", "cơ quan nào"],
        "require_any_prefer_keyword": True,
        "slots": 2,
    },
    {
        "intent_id": "I05_hau_qua_phap_ly_sau_huy",
        "match_articles": ["Luat_HNGD_2014_Dieu_12"],
        "prefer_keywords": ["hậu quả pháp lý"],
        "exclude_keywords": ["tài sản", "thừa kế", "chia một nửa"],
        "require_any_prefer_keyword": True,
        "slots": 2,
    },
    {
        "intent_id": "I06_giai_quyet_tai_san_sau_huy",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_12",
            "Luat_HNGD_2014_Dieu_33",
        ],
        "prefer_keywords": ["tài sản", "chia", "thừa kế"],
        "require_any_prefer_keyword": True,
        "slots": 2,
    },
    {
        "intent_id": "I07_thu_tuc_ho_so_huy",
        "match_articles": [
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP",
        ],
        "prefer_keywords": ["giấy tờ", "căn cứ để hủy", "chuẩn bị"],
        "require_any_prefer_keyword": True,
        "slots": 2,
    },
    {
        "intent_id": "I08_quyen_cha_me",
        "match_articles": ["Luat_HNGD_2014_Dieu_10"],
        "prefer_keywords": ["cha, mẹ", "cha mẹ"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I09_quyen_hoi_phu_nu",
        "match_articles": ["Luat_HNGD_2014_Dieu_10"],
        "prefer_keywords": ["hội liên hiệp phụ nữ", "hội phụ nữ"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I10_quyen_nguoi_bi_ep",
        "match_articles": ["Luat_HNGD_2014_Dieu_10"],
        "prefer_keywords": [
            "bị ép kết hôn",
            "cưỡng ép kết hôn",
            "tự mình yêu cầu hủy",
            "cưỡng ép kết hôn",
        ],
        "require_any_prefer_keyword": True,
        "slots": 2,
    },
    {
        "intent_id": "I11_quyen_nguoi_than_khong_co",
        "match_articles": ["Luat_HNGD_2014_Dieu_10"],
        "require_loai": "Tình huống",
        "prefer_keywords": [
            "em gái em",
            "hàng xóm",
            "dì ruột",
            "cháu thân thiết",
            "có quyền yêu cầu",
        ],
        "exclude_keywords": [
            "tự mình",
            "bố mẹ em ép",
            "giấy tờ",
            "anh g",
            "mẹ tôi",
        ],
        "require_any_prefer_keyword": True,
        "slots": 4,
    },
    {
        "intent_id": "I12_quyen_yeu_cau_huy_tong_quat",
        "match_articles": ["Luat_HNGD_2014_Dieu_10"],
        "prefer_keywords": [
            "những ai",
            "ai có quyền",
            "người có quyền",
            "quy định như thế nào",
            "quy định người",
            "tuyên hủy",
        ],
        "exclude_keywords": [
            "cha, mẹ",
            "hội liên hiệp",
            "bị ép",
            "cưỡng ép",
            "hàng xóm",
            "dì ruột",
            "cháu thân",
            "em gái em",
            "tự mình",
            "giấy tờ",
            "anh g",
        ],
        "slots": 4,
    },
    {
        "intent_id": "I13_tinh_huong_phuc_tap",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_10",
            "Luat_HNGD_2014_Dieu_11",
            "Luat_HNGD_2014_Dieu_12",
            "Luat_HNGD_2014_Dieu_33",
            "Luat_HNGD_2014_Dieu_5_Khoan_2",
        ],
        "min_can_cu_count": 2,
        "require_loai": "Tình huống",
        "slots": 3,
    },
]

FALLBACK_INDICES: list[int] = []


def _normalize_question(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\n.*@gmail\.com.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n.*@yahoo\.com.*", "", text, flags=re.IGNORECASE)
    return text[:2000]


def _has_can_cu(row: dict) -> bool:
    cc = row.get("can_cu_phap_ly_chinh")
    return isinstance(cc, list) and len(cc) > 0


def _article_base(article_id: str) -> str:
    return article_id.split("_Khoan")[0].split("_Diem")[0]


def _matches_articles(can_cu: list[str], articles: list[str]) -> bool:
    for article in articles:
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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ghi báo cáo coverage intent ra feat_llm/ket_hon_trai_phap_luat.coverage.txt",
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

    print(f"Wrote {len(output)} items -> feat_llm/ket_hon_trai_phap_luat.json")
    if args.verbose:
        print("Coverage report -> feat_llm/ket_hon_trai_phap_luat.coverage.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
