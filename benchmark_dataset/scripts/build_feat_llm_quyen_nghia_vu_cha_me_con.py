#!/usr/bin/env python3
"""
Lọc và seed câu hỏi cho chủ đề quyền, nghĩa vụ cha mẹ và con (Điều 68–80 LHNGD 2014).

Nguồn:
  - benchmark_grouped/quyen_nghia_vu_cha_me_con.json — câu có can_cu_phap_ly_chinh thuộc Điều 68–80;
  - SEED_QUESTIONS — câu seed theo nội dung extraction/Luật_HNGD_2014/output_articles.

Đầu ra: feat_llm/quyen_nghia_vu_cha_me_con.json (tối đa 30 câu; mỗi phần tử: question + can_cu_phap_ly_chinh).

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_quyen_nghia_vu_cha_me_con.py
    python benchmark_dataset/scripts/build_feat_llm_quyen_nghia_vu_cha_me_con.py --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
BENCHMARK_PATH = PACKAGE_DIR / "benchmark_grouped" / "quyen_nghia_vu_cha_me_con.json"
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "quyen_nghia_vu_cha_me_con.json"
MAX_QUESTIONS = 30

DIEU_68_80_RE = re.compile(r"Luat_HNGD_2014_Dieu_(68|69|7[0-9]|80)(?:_|$)")

# Seed theo Điều 68–80 (extraction/Luật_HNGD_2014/output_articles).
SEED_QUESTIONS: list[dict] = [
    # --- Điều 68: bảo vệ quyền, nghĩa vụ cha mẹ và con ---
    {
        "question": (
            "Quyền và nghĩa vụ của cha mẹ và con theo Luật Hôn nhân và gia đình "
            "được Nhà nước bảo vệ như thế nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_68"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con sinh ra khi cha mẹ chưa đăng ký kết hôn có quyền và nghĩa vụ "
            "như con trong hôn nhân hợp pháp không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_68_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cha mẹ và con thỏa thuận về tài sản có được làm ảnh hưởng đến quyền "
            "của con chưa thành niên không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_68_Khoan_4"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Giữa con nuôi và cha nuôi, mẹ nuôi có các quyền, nghĩa vụ của cha mẹ "
            "và con theo quy định nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_68_Khoan_3"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 69: bổ sung khoản chưa có trong benchmark ---
    {
        "question": (
            "Cha mẹ có được phân biệt đối xử với con trai và con gái hoặc vì con "
            "sinh ra ngoài hôn nhân không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_69_Khoan_4"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cha mẹ có được ép con chưa thành niên lao động nặng hoặc xúi giục con "
            "làm việc trái pháp luật không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_69_Khoan_4"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 70: bổ sung ---
    {
        "question": (
            "Con đã thành niên có quyền tự do lựa chọn nghề nghiệp và nơi cư trú "
            "theo Luật Hôn nhân và gia đình không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_70_Khoan_4"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 71: chăm sóc, nuôi dưỡng ---
    {
        "question": (
            "Cha, mẹ có nghĩa vụ và quyền ngang nhau trong việc chăm sóc, nuôi dưỡng con "
            "chưa thành niên không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_71"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con có nghĩa vụ chăm sóc, nuôi dưỡng cha mẹ khi cha mẹ già yếu, ốm đau "
            "hoặc mất năng lực hành vi dân sự không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_71_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Gia đình có nhiều con, bố bị liệt không tự chăm sóc được. "
            "Các con có phải cùng nhau nuôi dưỡng bố không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_71_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 72: giáo dục con ---
    {
        "question": (
            "Cha mẹ có những nghĩa vụ, quyền gì trong việc giáo dục và tạo điều kiện "
            "học tập cho con?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_72"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cha mẹ có được ép con theo học ngành nghề do cha mẹ chọn thay cho con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_72_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cha mẹ gặp khó khăn không tự giáo dục con được thì có thể nhờ cơ quan, "
            "tổ chức hỗ trợ không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_72_Khoan_3"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 73: đại diện cho con ---
    {
        "question": (
            "Ai là người đại diện theo pháp luật của con chưa thành niên "
            "theo Luật Hôn nhân và gia đình?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_73"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cha mẹ bán nhà đứng tên con 10 tuổi có cần sự thỏa thuận của cả hai "
            "cha mẹ không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_73_Khoan_3"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Mẹ một mình ký hợp đồng mua sắm đồ dùng thiết yếu cho con 8 tuổi "
            "có hợp pháp không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_73_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 74: bồi thường thiệt hại ---
    {
        "question": (
            "Cha mẹ có phải bồi thường thiệt hại do con chưa thành niên gây ra "
            "cho người khác không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_74"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con 12 tuổi nghịch phá làm vỡ kính cửa hàng. Cha mẹ có trách nhiệm "
            "bồi thường không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_74"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 75: tài sản riêng của con ---
    {
        "question": (
            "Tài sản riêng của con theo Luật Hôn nhân và gia đình bao gồm những loại "
            "tài sản nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_75"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con 16 tuổi sống chung với cha mẹ có phải đóng góp thu nhập lao động "
            "vào chi tiêu gia đình không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_75_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 76: quản lý tài sản riêng ---
    {
        "question": (
            "Con từ đủ 15 tuổi có thể tự quản lý tài sản riêng của mình không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Ai quản lý tài sản riêng của con dưới 15 tuổi theo quy định pháp luật?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 77: định đoạt tài sản riêng ---
    {
        "question": (
            "Cha mẹ quản lý tài sản riêng của con dưới 15 tuổi có quyền định đoạt "
            "tài sản đó vì lợi ích của con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_77"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con 16 tuổi muốn bán xe máy đứng tên mình có cần cha mẹ đồng ý bằng văn bản "
            "không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_77_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 78: cha nuôi, mẹ nuôi, con nuôi ---
    {
        "question": (
            "Quyền, nghĩa vụ của cha nuôi, mẹ nuôi và con nuôi được xác lập "
            "kể từ thời điểm nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_78"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Khi Tòa án quyết định chấm dứt việc nuôi con nuôi thì quyền, nghĩa vụ "
            "giữa cha nuôi, mẹ nuôi và con nuôi như thế nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_78_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Quyền, nghĩa vụ giữa cha đẻ, mẹ đẻ và con được khôi phục khi nào "
            "sau khi chấm dứt nuôi con nuôi?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_78_Khoan_3"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 79: bổ sung tình huống ---
    {
        "question": (
            "Mẹ kế có nghĩa vụ trông nom, nuôi dưỡng, giáo dục con riêng của chồng "
            "cùng sống chung với mình không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_79_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Con riêng của vợ có nghĩa vụ chăm sóc, phụng dưỡng cha dượng "
            "cùng sống chung không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_79_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 80: con dâu, con rể ---
    {
        "question": (
            "Con dâu, con rể sống chung với cha mẹ chồng hoặc cha mẹ vợ có những quyền, "
            "nghĩa vụ gì đối với nhau?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_80"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con rể sống chung với bố mẹ vợ có nghĩa vụ quan tâm, chăm sóc, giúp đỡ "
            "cha mẹ vợ theo quy định pháp luật không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_80"],
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


def _matches_dieu_68_80(can_cu: list[str]) -> bool:
    return any(DIEU_68_80_RE.search(c) for c in can_cu)


def _question_key(text: str) -> str:
    return _normalize_question(text).lower()


def _dieu_numbers(can_cu: list[str]) -> set[int]:
    nums: set[int] = set()
    for c in can_cu:
        m = DIEU_68_80_RE.search(c)
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
    """Giữ tối đa max_n câu; ưu tiên mỗi Điều 68–80 có ít nhất một câu."""
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


def build_output(benchmark: list[dict], verbose: bool = False) -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    skipped: list[str] = []

    for row in benchmark:
        if not _has_can_cu(row):
            skipped.append(row.get("question", "")[:120])
            continue
        cc = row["can_cu_phap_ly_chinh"]
        if not _matches_dieu_68_80(cc):
            skipped.append(row.get("question", "")[:120])
            continue
        _append_unique(rows, seen, row, "benchmark")

    n_benchmark = len(rows)

    for seed in SEED_QUESTIONS:
        _append_unique(rows, seen, seed, "seed")

    if not rows:
        raise ValueError(
            "Không có câu nào (benchmark hoặc seed) thuộc Điều 68–80 LHNGD 2014"
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
        all_dieu = set(range(68, 81))
        covered: set[int] = set()
        for r in rows:
            covered |= _dieu_numbers(r["can_cu_phap_ly_chinh"])
        missing = sorted(all_dieu - covered)

        lines = [
            f"Tổng câu: {len(output)} / tối đa {MAX_QUESTIONS}",
            f"  benchmark: {n_benchmark}, seed: {len(SEED_QUESTIONS)}",
            f"Điều 68–80 được phủ: {len(covered)}/13",
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
                m = DIEU_68_80_RE.search(c)
                if m:
                    dieu = f"Điều {m.group(1)}"
                    by_dieu[dieu] = by_dieu.get(dieu, 0) + 1
        for dieu, n in sorted(by_dieu.items(), key=lambda x: int(x[0].split()[1])):
            lines.append(f"  {dieu}: {n} lần")

        lines.append("")
        lines.append("--- Chi tiết ---")
        for i, r in enumerate(rows, 1):
            matched = [c for c in r["can_cu_phap_ly_chinh"] if DIEU_68_80_RE.search(c)]
            loai = r["_loai_cau_hoi"] or "?"
            lines.append(f"{i:2d}. [{r['_source']}|{loai}] {matched}")
            lines.append(f"    {r['question'][:120]}")

        if skipped:
            lines.append("")
            lines.append("--- Bỏ qua (benchmark) ---")
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
        help=(
            "Ghi báo cáo coverage ra "
            "feat_llm/quyen_nghia_vu_cha_me_con.coverage.txt"
        ),
    )
    args = parser.parse_args()

    if not BENCHMARK_PATH.is_file():
        print(f"Benchmark not found: {BENCHMARK_PATH}", file=sys.stderr)
        return 1

    with BENCHMARK_PATH.open(encoding="utf-8") as f:
        benchmark = json.load(f)

    output = build_output(benchmark, verbose=args.verbose)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(output)} items -> feat_llm/quyen_nghia_vu_cha_me_con.json")
    if args.verbose:
        print("Coverage report -> feat_llm/quyen_nghia_vu_cha_me_con.coverage.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
