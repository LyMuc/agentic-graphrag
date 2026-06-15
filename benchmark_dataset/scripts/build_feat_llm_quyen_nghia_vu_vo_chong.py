#!/usr/bin/env python3
"""
Lọc và seed câu hỏi cho chủ đề quyền, nghĩa vụ nhân thân giữa vợ và chồng
(Điều 17–23 LHNGD 2014).

Nguồn:
  - benchmark_grouped/*.json, benchmark/*.json — câu có can_cu_phap_ly_chinh thuộc Điều 17–23;
  - SEED_QUESTIONS — câu seed theo extraction/Luật_HNGD_2014/output_articles.

Đầu ra: feat_llm/quyen_nghia_vu_vo_chong.json (tối đa 35 câu; question + can_cu_phap_ly_chinh).

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_quyen_nghia_vu_vo_chong.py
    python benchmark_dataset/scripts/build_feat_llm_quyen_nghia_vu_vo_chong.py --verbose
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
BENCHMARK_DIR = PACKAGE_DIR / "benchmark"
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "quyen_nghia_vu_vo_chong.json"
MAX_QUESTIONS = 35

TARGET_DIEU = set(range(17, 24))
DIEU_17_23_RE = re.compile(r"Luat_HNGD_2014_Dieu_(17|18|19|20|21|22|23)(?:_|$)")

# Seed theo Điều 17–23 (extraction/Luật_HNGD_2014/output_articles).
SEED_QUESTIONS: list[dict] = [
    # --- Điều 17: bình đẳng về quyền, nghĩa vụ ---
    {
        "question": (
            "Vợ, chồng bình đẳng với nhau về quyền và nghĩa vụ trong gia đình "
            "được quy định như thế nào theo Luật Hôn nhân và gia đình 2014?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_17"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Chồng tự quyết định mọi việc trong gia đình mà không hỏi ý vợ "
            "có vi phạm nguyên tắc bình đẳng giữa vợ và chồng không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_17"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 18: bảo vệ quyền, nghĩa vụ nhân thân ---
    {
        "question": (
            "Quyền, nghĩa vụ về nhân thân của vợ và chồng được pháp luật "
            "tôn trọng và bảo vệ như thế nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_18"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Gia đình chồng can thiệp vào quyền tự do cá nhân của vợ "
            "có được coi là xâm phạm quyền nhân thân được pháp luật bảo vệ không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_18"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 19 khoản 1: tình nghĩa vợ chồng ---
    {
        "question": (
            "Vợ chồng có những nghĩa vụ gì về thương yêu, chung thủy, tôn trọng "
            "và chăm sóc lẫn nhau theo Luật Hôn nhân và gia đình?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_19_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Chồng có quan hệ tình cảm với người khác khi vẫn đang trong hôn nhân "
            "có vi phạm nghĩa vụ chung thủy của vợ chồng không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_19_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Vợ chồng có nghĩa vụ cùng nhau chia sẻ và thực hiện các công việc "
            "trong gia đình không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_19_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Chồng hoặc vợ ngoại tình thì có là căn cứ để xét chia tài sản chung không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_19_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 19 khoản 2: nghĩa vụ sống chung ---
    {
        "question": (
            "Vợ chồng ly thân vì một bên đi làm ở tỉnh khác có được coi là "
            "lý do chính đáng không sống chung với nhau không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_19_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Vợ chồng thỏa thuận không sống chung với nhau có được pháp luật "
            "hôn nhân và gia đình công nhận không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_19_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Vợ chồng không đeo nhẫn cưới có vi phạm quy định về tình nghĩa "
            "vợ chồng theo pháp luật không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_19"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 20: lựa chọn nơi cư trú ---
    {
        "question": (
            "Việc lựa chọn nơi cư trú của vợ chồng có bị ràng buộc bởi phong tục, "
            "tập quán hoặc địa giới hành chính không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_20"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Sau khi kết hôn, vợ có bắt buộc phải về ở chung với gia đình chồng "
            "theo quy định pháp luật không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_20"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 21: danh dự, nhân phẩm, uy tín ---
    {
        "question": (
            "Vợ, chồng có nghĩa vụ tôn trọng, giữ gìn và bảo vệ danh dự, nhân phẩm, "
            "uy tín cho nhau như thế nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_21"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Chồng đăng thông tin riêng tư của vợ lên mạng xã hội làm ảnh hưởng "
            "danh dự vợ có vi phạm nghĩa vụ của vợ chồng không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_21"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 22: tự do tín ngưỡng, tôn giáo ---
    {
        "question": (
            "Vợ, chồng có nghĩa vụ tôn trọng quyền tự do tín ngưỡng, tôn giáo "
            "của nhau theo Luật Hôn nhân và gia đình không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_22"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Chồng cấm vợ đi lễ theo tôn giáo có vi phạm quy định về quyền "
            "và nghĩa vụ giữa vợ và chồng không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_22"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 23: học tập, làm việc, hoạt động xã hội ---
    {
        "question": (
            "Vợ, chồng có quyền, nghĩa vụ tạo điều kiện giúp đỡ nhau chọn nghề nghiệp "
            "và học tập theo quy định pháp luật không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_23"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Chồng cấm vợ đi làm, kiếm tiền có vi phạm quy định về quyền và nghĩa vụ "
            "của vợ chồng không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_23"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Vợ có quyền tham gia hoạt động chính trị, kinh tế, văn hóa, xã hội "
            "khi chồng không đồng ý không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_23"],
        "loai_cau_hoi": "Tình huống",
    },
]


def _normalize_question(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\n.*@gmail\.com.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n.*@yahoo\.com.*", "", text, flags=re.IGNORECASE)
    return text[:2000]


def _has_can_cu(row: dict) -> bool:
    cc = row.get("can_cu_phap_ly_chinh")
    return isinstance(cc, list) and len(cc) > 0


def _matches_dieu_17_23(can_cu: list[str]) -> bool:
    return any(DIEU_17_23_RE.search(c) for c in can_cu)


def _question_key(text: str) -> str:
    return _normalize_question(text).lower()


def _dieu_numbers(can_cu: list[str]) -> set[int]:
    nums: set[int] = set()
    for c in can_cu:
        m = DIEU_17_23_RE.search(c)
        if m:
            nums.add(int(m.group(1)))
    return nums


def _append_unique(
    rows: list[dict],
    seen: set[str],
    row: dict,
    source: str,
) -> None:
    key = _question_key(row["question"])
    if key in seen:
        return
    seen.add(key)
    rows.append(
        {
            "question": _normalize_question(row["question"]),
            "can_cu_phap_ly_chinh": list(row["can_cu_phap_ly_chinh"]),
            "_source": source,
            "_loai_cau_hoi": row.get("loai_cau_hoi") or "",
        }
    )


def _cap_rows(rows: list[dict], max_n: int) -> list[dict]:
    """Giữ tối đa max_n câu; ưu tiên mỗi Điều 17–23 có ít nhất một câu."""
    if len(rows) <= max_n:
        return rows

    selected: list[dict] = []
    covered: set[int] = set()
    used_keys: set[str] = set()

    for r in rows:
        if len(selected) >= max_n:
            break
        dieu = _dieu_numbers(r["can_cu_phap_ly_chinh"])
        if dieu - covered:
            key = _question_key(r["question"])
            if key not in used_keys:
                selected.append(r)
                used_keys.add(key)
                covered |= dieu

    for r in rows:
        if len(selected) >= max_n:
            break
        key = _question_key(r["question"])
        if key in used_keys:
            continue
        selected.append(r)
        used_keys.add(key)

    return selected[:max_n]


def _load_json_rows(folder: Path) -> list[tuple[dict, str]]:
    rows: list[tuple[dict, str]] = []
    if not folder.is_dir():
        return rows
    for path in sorted(folder.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            continue
        for row in data:
            rows.append((row, path.name))
    return rows


def build_output(verbose: bool = False) -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    skipped: list[str] = []

    for folder in (GROUPED_DIR, BENCHMARK_DIR):
        for row, source_file in _load_json_rows(folder):
            if not _has_can_cu(row):
                continue
            cc = row["can_cu_phap_ly_chinh"]
            if not _matches_dieu_17_23(cc):
                continue
            _append_unique(
                rows,
                seen,
                {
                    "question": row["question"],
                    "can_cu_phap_ly_chinh": cc,
                    "loai_cau_hoi": row.get("loai_cau_hoi") or "",
                },
                source_file,
            )

    n_benchmark = len(rows)

    for seed in SEED_QUESTIONS:
        _append_unique(rows, seen, seed, "seed")

    if not rows:
        raise ValueError(
            "Không có câu nào (benchmark hoặc seed) thuộc Điều 17–23 LHNGD 2014"
        )

    rows = _cap_rows(rows, MAX_QUESTIONS)

    output = [
        {
            "question": r["question"],
            "can_cu_phap_ly_chinh": r["can_cu_phap_ly_chinh"],
        }
        for r in rows
    ]

    if verbose:
        report_path = OUTPUT_PATH.with_suffix(".coverage.txt")
        covered: set[int] = set()
        for r in rows:
            covered |= _dieu_numbers(r["can_cu_phap_ly_chinh"])
        missing = sorted(TARGET_DIEU - covered)

        lines = [
            f"Tổng câu: {len(output)} / tối đa {MAX_QUESTIONS}",
            f"  benchmark: {n_benchmark}, seed: {len(SEED_QUESTIONS)}",
            f"Điều 17–23 được phủ: {len(covered)}/7",
            f"Điều chưa có câu: {missing or 'không'}",
            "",
            "--- Theo nguồn ---",
        ]
        by_source: dict[str, int] = {}
        for r in rows:
            by_source[r["_source"]] = by_source.get(r["_source"], 0) + 1
        for src, n in sorted(by_source.items()):
            lines.append(f"  {src}: {n}")

        lines.append("")
        lines.append("--- Theo điều luật (căn cứ chính) ---")
        by_dieu: dict[str, int] = {}
        for r in rows:
            for c in r["can_cu_phap_ly_chinh"]:
                m = DIEU_17_23_RE.search(c)
                if m:
                    dieu = f"Điều {m.group(1)}"
                    by_dieu[dieu] = by_dieu.get(dieu, 0) + 1
        for dieu, n in sorted(by_dieu.items(), key=lambda x: int(x[0].split()[1])):
            lines.append(f"  {dieu}: {n} lần")

        lines.append("")
        lines.append("--- Chi tiết ---")
        for i, r in enumerate(rows, 1):
            matched = [c for c in r["can_cu_phap_ly_chinh"] if DIEU_17_23_RE.search(c)]
            loai = r["_loai_cau_hoi"] or "?"
            lines.append(f"{i:2d}. [{r['_source']}|{loai}] {matched}")
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
        help="Ghi báo cáo coverage ra feat_llm/quyen_nghia_vu_vo_chong.coverage.txt",
    )
    args = parser.parse_args()

    output = build_output(verbose=args.verbose)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(output)} items -> feat_llm/quyen_nghia_vu_vo_chong.json")
    if args.verbose:
        print("Coverage report -> feat_llm/quyen_nghia_vu_vo_chong.coverage.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
