#!/usr/bin/env python3
"""
Tổng hợp câu hỏi đại diện cho chủ đề hôn nhân chấm dứt do vợ/chồng chết
(Điều 65–67 LHNGD 2014).

Nguồn:
  - benchmark/*.json — câu đã có can_cu_phap_ly_chinh chứa Điều 65|66|67;
  - SUPPLEMENT_QUESTIONS — câu benchmark chưa phân loại nhưng căn cứ rõ từ ground_truth;
  - SEED_QUESTIONS — câu seed theo nội dung Điều 66 (extraction).

Đầu ra: feat_llm/hon_nhan_cham_dut_do_vo_chong_chet.json
(mỗi phần tử: question + can_cu_phap_ly_chinh).

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_hon_nhan_cham_dut_do_vo_chong_chet.py
    python benchmark_dataset/scripts/build_feat_llm_hon_nhan_cham_dut_do_vo_chong_chet.py --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
BENCHMARK_DIR = PACKAGE_DIR / "benchmark"
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "hon_nhan_cham_dut_do_vo_chong_chet.json"

DIEU_65_67_RE = re.compile(r"Luat_HNGD_2014_Dieu_6[567](?:_|$)")

# Câu trong benchmark chưa có can_cu_phap_ly_chinh — bổ sung căn cứ thủ công.
SUPPLEMENT_QUESTIONS: list[dict] = [
    {
        "question": "Chồng chết thì quan hệ hôn nhân có chấm dứt không?",
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_65"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Theo quy định pháp luật điều chỉnh về hôn nhân thì nếu người chồng "
            "không may bị chết thì quan hệ hôn nhân giữa vợ và chồng có chấm dứt hay không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_65"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": "Chồng bị tuyên bố đã chết trở về có được lại chia tài sản không?",
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_67"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Cách đây 4 năm, chị họ tôi bị lừa bán sang Trung Quốc, nay chị ấy đã trở về nước. "
            "Thời gian vắng nhà, theo yêu cầu của chồng chị (anh M), Tòa án đã tuyên bố chị bị mất tích. "
            "Sau đó anh M đã kết hôn với người phụ nữ khác. Xin hỏi, trong trường hợp này, "
            "chị tôi có được khôi phục lại quan hệ hôn nhân với anh M không? "
            "nếu không được khôi phục lại quan hệ hôn nhân với anh M thì tài sản chung của 2 người "
            "có trước đó được giải quyết thế nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_67"],
        "loai_cau_hoi": "Tình huống",
    },
]

# Seed theo Điều 66 — Giải quyết tài sản khi một bên chết/tuyên bố đã chết.
SEED_QUESTIONS: list[dict] = [
    {
        "question": (
            "Khi một bên vợ chồng chết thì bên còn sống có được quản lý tài sản chung không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_66_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Một bên vợ chồng chết hoặc bị tòa án tuyên bố đã chết thì "
            "tài sản chung được giải quyết như thế nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_66"],
        "loai_cau_hoi": "Lý thuyết",
    },
]

INTENT_SPECS: list[dict] = [
    {
        "intent_id": "I01_thoi_diem_cham_dut_dieu_65",
        "match_articles": ["Luat_HNGD_2014_Dieu_65"],
        "require_can_cu_substrings": ["Luat_HNGD_2014_Dieu_65"],
        "exclude_can_cu_substrings": ["Luat_HNGD_2014_Dieu_57", "Luat_HNGD_2014_Dieu_9"],
        "prefer_keywords": [
            "quan hệ hôn nhân chấm dứt khi nào",
            "thời điểm chấm dứt",
        ],
        "exclude_keywords": ["biệt tích", "xé giấy"],
        "slots": 1,
    },
    {
        "intent_id": "I02_tuyen_bo_chet_biet_tich",
        "match_articles": ["Luat_HNGD_2014_Dieu_65"],
        "prefer_keywords": ["biệt tích", "tuyên bố", "kết hôn với chồng mới"],
        "slots": 1,
    },
    {
        "intent_id": "I03_vo_chong_chet_cham_dut",
        "match_articles": ["Luat_HNGD_2014_Dieu_65"],
        "prefer_keywords": ["chết", "chấm dứt"],
        "exclude_keywords": ["biệt tích", "trở về", "xé giấy", "đăng ký kết hôn"],
        "slots": 1,
    },
    {
        "intent_id": "I04_tuyen_bo_chet_tro_ve_dieu_67",
        "match_articles": ["Luat_HNGD_2014_Dieu_67"],
        "prefer_keywords": ["trở về", "tuyên bố đã chết", "khôi phục"],
        "slots": 1,
    },
    {
        "intent_id": "I05_tai_san_khi_tro_ve_dieu_67",
        "match_articles": ["Luat_HNGD_2014_Dieu_67"],
        "prefer_keywords": ["tài sản", "chia"],
        "slots": 1,
    },
    {
        "intent_id": "I06_quan_ly_tai_san_dieu_66",
        "match_articles": ["Luat_HNGD_2014_Dieu_66"],
        "prefer_keywords": ["quản lý tài sản chung", "quản lý"],
        "slots": 1,
    },
    {
        "intent_id": "I09_chia_tai_san_dieu_66",
        "match_articles": ["Luat_HNGD_2014_Dieu_66"],
        "prefer_keywords": ["tài sản chung", "giải quyết"],
        "exclude_keywords": ["trở về", "khôi phục"],
        "slots": 1,
    },
    {
        "intent_id": "I07_cac_truong_hop_cham_dut_tong_quat",
        "match_articles": ["Luat_HNGD_2014_Dieu_65"],
        "prefer_keywords": ["chấm dứt quan hệ hôn nhân", "xé giấy"],
        "slots": 1,
    },
    {
        "intent_id": "I08_thoi_diem_ket_hop_dieu_57_65",
        "match_articles": ["Luat_HNGD_2014_Dieu_65"],
        "require_can_cu_substrings": ["Luat_HNGD_2014_Dieu_57"],
        "prefer_keywords": ["thời điểm chấm dứt"],
        "slots": 1,
    },
]


def _normalize_question(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\n.*@gmail\.com.*", "", text, flags=re.IGNORECASE)
    return text[:2000]


def _has_can_cu(row: dict) -> bool:
    cc = row.get("can_cu_phap_ly_chinh")
    return isinstance(cc, list) and len(cc) > 0


def _has_dieu_65_67(can_cu: list[str]) -> bool:
    return any(DIEU_65_67_RE.search(c) for c in can_cu)


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


def _append_to_pool(
    pool: list[dict],
    seen_questions: set[str],
    row: dict,
) -> None:
    norm_q = _normalize_question(row["question"]).lower()
    if norm_q in seen_questions:
        return
    seen_questions.add(norm_q)
    pool.append(row)


def _load_benchmark_pool() -> list[dict]:
    pool: list[dict] = []
    seen_questions: set[str] = set()

    for fp in sorted(BENCHMARK_DIR.glob("qa_*.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        for row in data:
            if not _has_can_cu(row):
                continue
            cc = row["can_cu_phap_ly_chinh"]
            if not _has_dieu_65_67(cc):
                continue
            _append_to_pool(pool, seen_questions, row)

    for row in SUPPLEMENT_QUESTIONS + SEED_QUESTIONS:
        _append_to_pool(pool, seen_questions, row)

    return pool


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
    for c in cc:
        if DIEU_65_67_RE.search(c):
            score += 4

    if len(cc) == 1:
        score += 3

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
        if i in used:
            continue
        if require_loai and row.get("loai_cau_hoi") != require_loai:
            continue
        cc = row["can_cu_phap_ly_chinh"]
        if not _matches_articles(cc, spec["match_articles"]):
            continue
        if spec.get("require_can_cu_substrings"):
            if not all(
                any(sub in c for c in cc)
                for sub in spec["require_can_cu_substrings"]
            ):
                continue
        if spec.get("exclude_can_cu_substrings"):
            if any(
                any(sub in c for c in cc)
                for sub in spec["exclude_can_cu_substrings"]
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
    if not benchmark:
        raise ValueError(
            "Không có câu nào trong benchmark/ thỏa can_cu_phap_ly_chinh + Điều 65–67"
        )

    used: set[int] = set()
    selected_indices: list[int] = []
    coverage: dict[str, list[int]] = {}

    for spec in INTENT_SPECS:
        picks = _select_for_intent(benchmark, spec, used)
        coverage[spec["intent_id"]] = picks
        for idx in picks:
            if idx not in used:
                used.add(idx)
                selected_indices.append(idx)

    for i, row in enumerate(benchmark):
        if i not in used:
            used.add(i)
            selected_indices.append(i)
            coverage.setdefault("_fill", []).append(i)

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
            intent = intent_by_idx.get(idx, "_fill")
            if idx in coverage.get("_fill", []):
                intent = "_fill"
            lines.append(f"{n:2d}. #{idx + 1} [{intent}]")
            lines.append(f"    {benchmark[idx]['can_cu_phap_ly_chinh']}")

        report_path.write_text("\n".join(lines), encoding="utf-8")

    return output, coverage


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    benchmark = _load_benchmark_pool()
    print(f"Loaded {len(benchmark)} unique classified questions (Điều 65–67)")

    output, coverage = build_output(benchmark, verbose=args.verbose)

    filled_intents = sum(
        1 for spec in INTENT_SPECS if coverage.get(spec["intent_id"])
    )
    print(f"Intent covered: {filled_intents}/{len(INTENT_SPECS)}; selected: {len(output)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(output)} items -> feat_llm/hon_nhan_cham_dut_do_vo_chong_chet.json")
    if args.verbose:
        print("Coverage report -> feat_llm/hon_nhan_cham_dut_do_vo_chong_chet.coverage.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
