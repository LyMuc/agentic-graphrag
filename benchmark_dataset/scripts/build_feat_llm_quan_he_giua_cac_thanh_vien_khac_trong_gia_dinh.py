#!/usr/bin/env python3
"""
Lọc và seed câu hỏi cho chủ đề quyền, nghĩa vụ giữa các thành viên khác trong gia đình
(Điều 103–106 LHNGD 2014).

Nguồn:
  - benchmark_grouped/*.json — câu có can_cu_phap_ly_chinh thuộc Điều 103–106;
  - SEED_QUESTIONS — câu seed theo nội dung extraction/Luật_HNGD_2014/output_articles.

Đầu ra: feat_llm/quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.json
(mỗi phần tử: question + can_cu_phap_ly_chinh).

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.py
    python benchmark_dataset/scripts/build_feat_llm_quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.py --verbose
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
OUTPUT_PATH = (
    PACKAGE_DIR
    / "feat_llm"
    / "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.json"
)

DIEU_103_106_RE = re.compile(r"Luat_HNGD_2014_Dieu_(10[3-6])(?:_|$)")

# Seed theo Điều 103–106 (extraction/Luật_HNGD_2014/output_articles).
SEED_QUESTIONS: list[dict] = [
    # --- Điều 103: quyền, nghĩa vụ chung giữa các thành viên khác ---
    {
        "question": (
            "Các thành viên khác trong gia đình có những quyền, nghĩa vụ gì đối với nhau "
            "theo quy định chung của Luật Hôn nhân và gia đình?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_103"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Quyền, lợi ích hợp pháp về nhân thân và tài sản của các thành viên gia đình "
            "có được pháp luật bảo vệ không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_103_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Khi các thành viên gia đình sống chung thì có những nghĩa vụ gì về "
            "công việc gia đình và đóng góp duy trì đời sống chung?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_103_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Thành viên gia đình sống chung có nghĩa vụ đóng góp công sức, tiền hoặc tài sản "
            "như thế nào cho gia đình?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_103_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Nhà nước có chính sách gì để khuyến khích các thế hệ trong gia đình "
            "quan tâm, chăm sóc, giúp đỡ nhau?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_103_Khoan_3"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Em 22 tuổi đang sống chung với dì ruột. Dì em yêu cầu em đóng góp một phần "
            "tiền ăn ở hàng tháng theo khả năng thực tế. Em có nghĩa vụ phải đóng góp không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_103_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 104: ông bà nội, ngoại và cháu ---
    {
        "question": (
            "Ông bà nội, ông bà ngoại có những quyền, nghĩa vụ gì đối với cháu "
            "theo Luật Hôn nhân và gia đình?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_104"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Ông bà nội, ông bà ngoại có nghĩa vụ trông nom, chăm sóc, giáo dục cháu "
            "và sống mẫu mực nêu gương cho con cháu không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_104_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Trong trường hợp nào ông bà nội, ông bà ngoại có nghĩa vụ nuôi dưỡng cháu?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_104_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cháu có những nghĩa vụ gì đối với ông bà nội, ông bà ngoại?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_104_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cháu đã thành niên có nghĩa vụ nuôi dưỡng ông bà nội, ông bà ngoại "
            "trong trường hợp nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_104_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cháu 16 tuổi mồ côi cả cha lẫn mẹ, không có anh chị em đủ điều kiện nuôi dưỡng. "
            "Ông bà ngoại có nghĩa vụ nuôi dưỡng cháu không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_104_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Cháu đã thành niên nhưng mất năng lực hành vi dân sự, không có khả năng lao động "
            "và không có tài sản tự nuôi mình, không có anh chị em nuôi dưỡng. "
            "Ông bà nội có phải nuôi dưỡng cháu không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_104_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Ông bà nội không có con để nuôi dưỡng mình, chỉ còn cháu đã thành niên. "
            "Cháu có nghĩa vụ nuôi dưỡng ông bà không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_104_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 105: anh, chị, em ---
    {
        "question": (
            "Anh, chị, em có những quyền, nghĩa vụ gì đối với nhau "
            "theo Luật Hôn nhân và gia đình?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_105"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Anh chị em có nghĩa vụ nuôi dưỡng nhau trong trường hợp nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_105"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Khi không còn cha mẹ thì anh chị em có nghĩa vụ trông nom, nuôi dưỡng "
            "em út chưa thành niên không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_105"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cha mẹ không có điều kiện trông nom, nuôi dưỡng, chăm sóc, giáo dục con thì "
            "anh chị em có nghĩa vụ gì?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_105"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Bố mẹ bị tù, em gái 11 tuổi không còn ai trông nom. "
            "Anh trai 25 tuổi có nghĩa vụ nuôi dưỡng em không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_105"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Cha mẹ già yếu, bệnh tật không còn sức chăm sóc con nhỏ 8 tuổi. "
            "Chị gái đã thành niên có phải trông nom, nuôi dưỡng em không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_105"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Hai anh em cùng sống trong một hộ gia đình, anh trai có quyền yêu cầu em "
            "thương yêu, chăm sóc, giúp đỡ lẫn nhau theo quy định pháp luật không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_105"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 106: cô, dì, chú, cậu, bác ruột và cháu ruột ---
    {
        "question": (
            "Cô, dì, chú, cậu, bác ruột và cháu ruột có những quyền, nghĩa vụ gì đối với nhau?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_106"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cô, dì, chú, cậu, bác ruột có nghĩa vụ nuôi dưỡng cháu ruột "
            "trong trường hợp nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_106"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Người cần được nuôi dưỡng không còn cha, mẹ, con và không còn người thuộc "
            "Điều 104, 105 hoặc những người này không có điều kiện nuôi dưỡng thì "
            "cô dì chú cậu bác có nghĩa vụ gì?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_106"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cháu ruột 14 tuổi mồ côi cha mẹ, ông bà đã mất, anh chị em không có điều kiện "
            "nuôi dưỡng. Cô ruột có nghĩa vụ nuôi dưỡng cháu không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_106"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Chú ruột đang nuôi cháu mồ côi nhưng không còn khả năng tài chính. "
            "Cháu đã thành niên có nghĩa vụ chăm sóc, giúp đỡ chú theo quy định không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_106"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Bác ruột và cháu ruột có quyền, nghĩa vụ thương yêu, chăm sóc, giúp đỡ nhau "
            "khi còn cha mẹ của cháu không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_106"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Người cần nuôi dưỡng không còn con và không còn ông bà, anh chị em có điều kiện "
            "nuôi dưỡng. Dì ruột có phải nuôi dưỡng người đó không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_106"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Cậu ruột muốn yêu cầu cháu ruột đã thành niên thực hiện nghĩa vụ nuôi dưỡng "
            "khi cậu không còn vợ con và không có anh chị em. Căn cứ pháp lý là gì?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_106"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Quyền, nghĩa vụ nuôi dưỡng giữa cô dì chú cậu bác ruột và cháu ruột khác gì "
            "so với quyền, nghĩa vụ giữa ông bà và cháu?"
        ),
        "can_cu_phap_ly_chinh": [
            "Luat_HNGD_2014_Dieu_104",
            "Luat_HNGD_2014_Dieu_106",
        ],
        "loai_cau_hoi": "Lý thuyết",
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


def _matches_dieu_103_106(can_cu: list[str]) -> bool:
    return any(DIEU_103_106_RE.search(c) for c in can_cu)


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
            if not _matches_dieu_103_106(cc):
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


def build_output(verbose: bool = False) -> list[dict]:
    grouped_rows, provenance = collect_from_grouped()
    seen = {_question_key(r["question"]) for r in grouped_rows}
    rows = list(grouped_rows)

    for seed in SEED_QUESTIONS:
        _append_unique(rows, seen, seed, "seed")

    if not rows:
        raise ValueError(
            "Không có câu nào (benchmark hoặc seed) thuộc Điều 103–106 LHNGD 2014"
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
            f"Tổng câu: {len(output)} (benchmark: {len(grouped_rows)}, seed: {len(SEED_QUESTIONS)})",
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
                m = DIEU_103_106_RE.search(c)
                if m:
                    dieu = f"Điều {m.group(1)}"
                    by_dieu[dieu] = by_dieu.get(dieu, 0) + 1
        for dieu, n in sorted(by_dieu.items()):
            lines.append(f"  {dieu}: {n} lần xuất hiện")

        lines.append("")
        lines.append("--- Chi tiết ---")
        for i, r in enumerate(rows, 1):
            matched = [
                c for c in r["can_cu_phap_ly_chinh"] if DIEU_103_106_RE.search(c)
            ]
            lines.append(f"{i:2d}. [{r['_source']}] {matched}")
            lines.append(f"    {r['question'][:120]}")

        dupes = {k: v for k, v in provenance.items() if len(v) > 1}
        if dupes:
            lines.append("")
            lines.append("--- Trùng câu giữa các file benchmark (bỏ qua bản sao) ---")
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
        help=(
            "Ghi báo cáo coverage ra "
            "feat_llm/quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.coverage.txt"
        ),
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

    print(
        f"Wrote {len(output)} items -> "
        "feat_llm/quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.json"
    )
    if args.verbose:
        print(
            "Coverage report -> "
            "feat_llm/quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.coverage.txt"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
