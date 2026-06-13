#!/usr/bin/env python3
"""
Tổng hợp câu hỏi đại diện cho chủ đề hạn chế quyền cha mẹ với con chưa thành niên
(Điều 85–87 LHNGD 2014).

Nguồn: toàn bộ benchmark/*.json — chỉ lấy câu đã có can_cu_phap_ly_chinh và
trong đó có ít nhất một mã Luat_HNGD_2014_Dieu_85|86|87.

Đầu ra: feat_llm/han_che_quyen_cha_me_con_chua_thanh_nien.json
(mỗi phần tử: question + can_cu_phap_ly_chinh).

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_han_che_quyen_cha_me_con_chua_thanh_nien.py
    python benchmark_dataset/scripts/build_feat_llm_han_che_quyen_cha_me_con_chua_thanh_nien.py --verbose
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
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "han_che_quyen_cha_me_con_chua_thanh_nien.json"

DIEU_85_87_RE = re.compile(r"Luat_HNGD_2014_Dieu_8[567](?:_|$)")

INTENT_SPECS: list[dict] = [
    {
        "intent_id": "I01_truong_hop_han_che_dieu_85",
        "match_articles": ["Luat_HNGD_2014_Dieu_85"],
        "require_can_cu_substrings": ["Luat_HNGD_2014_Dieu_85"],
        "exclude_can_cu_substrings": ["Luat_HNGD_2014_Dieu_86", "Luat_HNGD_2014_Dieu_81"],
        "prefer_keywords": [
            "trường hợp nào",
            "các trường hợp",
            "trong các trường hợp",
            "hạn chế quyền đối với con chưa thành niên",
        ],
        "exclude_keywords": ["thăm nom", "mẹ không được nuôi", "ông bà", "làm cha"],
        "slots": 2,
    },
    {
        "intent_id": "I02_dieu_85_va_86",
        "match_articles": [
            "Luat_HNGD_2014_Dieu_85",
            "Luat_HNGD_2014_Dieu_86",
        ],
        "require_can_cu_substrings": ["Luat_HNGD_2014_Dieu_86"],
        "prefer_keywords": ["hạn chế quyền làm cha", "yêu cầu tòa án"],
        "slots": 1,
    },
    {
        "intent_id": "I03_tinh_huong_dac_biet",
        "match_articles": ["Luat_HNGD_2014_Dieu_85"],
        "prefer_keywords": ["đi tù", "bố đi tù"],
        "require_loai": "Tình huống",
        "slots": 1,
    },
    {
        "intent_id": "I04_han_che_tham_nom",
        "match_articles": ["Luat_HNGD_2014_Dieu_85"],
        "prefer_keywords": ["thăm nom"],
        "require_any_prefer_keyword": True,
        "slots": 1,
    },
    {
        "intent_id": "I05_me_khong_duoc_nuoi_khi_han_che",
        "match_articles": ["Luat_HNGD_2014_Dieu_85"],
        "require_can_cu_substrings": ["Luat_HNGD_2014_Dieu_81"],
        "prefer_keywords": ["mẹ không được nuôi", "không được nuôi con"],
        "slots": 1,
    },
    {
        "intent_id": "I06_hau_qua_dieu_87",
        "match_articles": ["Luat_HNGD_2014_Dieu_87"],
        "prefer_keywords": [
            "hậu quả",
            "bị hạn chế",
            "không được trông nom",
        ],
        "exclude_keywords": ["ông bà", "giành quyền nuôi cháu", "ly hôn"],
        "slots": 1,
    },
]

# Câu có Dieu 87 nhưng thuộc chủ đề nuôi con sau ly hôn — loại khỏi feat_llm chủ đề này.
EXCLUDE_QUESTION_PATTERNS = [
    re.compile(r"ông bà.*giành quyền nuôi", re.I),
    re.compile(r"giành quyền nuôi cháu", re.I),
]


def _normalize_question(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\n.*@gmail\.com.*", "", text, flags=re.IGNORECASE)
    return text[:2000]


def _has_can_cu(row: dict) -> bool:
    cc = row.get("can_cu_phap_ly_chinh")
    return isinstance(cc, list) and len(cc) > 0


def _has_dieu_85_87(can_cu: list[str]) -> bool:
    return any(DIEU_85_87_RE.search(c) for c in can_cu)


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


def _is_excluded(row: dict) -> bool:
    q = row.get("question", "")
    return any(p.search(q) for p in EXCLUDE_QUESTION_PATTERNS)


def _load_benchmark_pool() -> list[dict]:
    pool: list[dict] = []
    seen_questions: set[str] = set()

    for fp in sorted(BENCHMARK_DIR.glob("qa_*.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        for row in data:
            if not _has_can_cu(row):
                continue
            cc = row["can_cu_phap_ly_chinh"]
            if not _has_dieu_85_87(cc):
                continue
            if _is_excluded(row):
                continue
            norm_q = _normalize_question(row["question"]).lower()
            # Gộp các câu thăm nom trùng ý
            dedup_key = norm_q
            if "thăm nom" in norm_q and "hạn chế" in norm_q:
                dedup_key = "__han_che_tham_nom__"
            if dedup_key in seen_questions:
                continue
            seen_questions.add(dedup_key)
            pool.append(row)

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
    min_cc = spec.get("min_can_cu_count")
    if min_cc and len(cc) >= min_cc:
        score += 6

    for c in cc:
        if DIEU_85_87_RE.search(c):
            score += 4

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
            "Không có câu nào trong benchmark/ thỏa can_cu_phap_ly_chinh + Điều 85–87"
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
            intent = intent_by_idx.get(idx, coverage.get("_fill") and "_fill" or "?")
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
    print(f"Loaded {len(benchmark)} unique classified questions (Điều 85–87)")

    output, coverage = build_output(benchmark, verbose=args.verbose)

    filled_intents = sum(
        1 for spec in INTENT_SPECS if coverage.get(spec["intent_id"])
    )
    print(f"Intent covered: {filled_intents}/{len(INTENT_SPECS)}; selected: {len(output)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(output)} items -> feat_llm/han_che_quyen_cha_me_con_chua_thanh_nien.json")
    if args.verbose:
        print("Coverage report -> feat_llm/han_che_quyen_cha_me_con_chua_thanh_nien.coverage.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
