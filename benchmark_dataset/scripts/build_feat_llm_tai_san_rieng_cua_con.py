#!/usr/bin/env python3
"""
Lọc và tổng hợp câu hỏi cho chủ đề tài sản riêng của con (Điều 75–77 LHNGD 2014).

Nguồn:
  - benchmark/*.json — toàn bộ file qa_*.json;
  - benchmark_grouped/*.json — toàn bộ file theo chủ đề;
  - SEED_QUESTIONS — câu seed theo nội dung Điều 75–77.

Chỉ lấy câu đã có can_cu_phap_ly_chinh và trong đó có ít nhất một mã
Luat_HNGD_2014_Dieu_75|76|77.

Đầu ra: feat_llm/tai_san_rieng_cua_con.json (mỗi phần tử: question + can_cu_phap_ly_chinh).

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_tai_san_rieng_cua_con.py
    python benchmark_dataset/scripts/build_feat_llm_tai_san_rieng_cua_con.py --verbose
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
BENCHMARK_GROUPED_DIR = PACKAGE_DIR / "benchmark_grouped"
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "tai_san_rieng_cua_con.json"
MAX_QUESTIONS = 35

DIEU_75_77_RE = re.compile(r"Luat_HNGD_2014_Dieu_(75|76|77)(?:_|$)")

# Seed theo từng khoản extraction/Luật_HNGD_2014/output_articles (Điều 75–77).
SEED_QUESTIONS: list[dict] = [
    # --- Điều 75: Quyền có tài sản riêng của con ---
    {
        "question": "Con có quyền có tài sản riêng theo Luật Hôn nhân và gia đình không?",
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_75"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Tài sản riêng của con theo Luật Hôn nhân và gia đình bao gồm những loại "
            "tài sản nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_75_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Tài sản được hình thành từ tài sản riêng của con có được coi là tài sản "
            "riêng của con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_75_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Ông bà tặng cho cháu 12 tuổi một khoản tiền riêng, tiền đó có phải tài sản "
            "riêng của con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_75_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Hoa lợi, lợi tức phát sinh từ tài sản riêng của con thuộc loại tài sản gì "
            "theo Luật Hôn nhân và gia đình?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_75_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con được thừa kế riêng từ ông bà, phần tài sản thừa kế đó có phải tài sản "
            "riêng của con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_75_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Thu nhập do con lao động kiếm được có được coi là tài sản riêng của con "
            "theo Luật Hôn nhân và gia đình không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_75_Khoan_1"],
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
    {
        "question": (
            "Con từ đủ 15 tuổi sống chung với cha mẹ có nghĩa vụ chăm lo đời sống chung "
            "của gia đình như thế nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_75_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con đã thành niên sống chung với cha mẹ có nghĩa vụ đóng góp thu nhập vào "
            "nhu cầu của gia đình không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_75_Khoan_3"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 76: Quản lý tài sản riêng của con ---
    {
        "question": "Con từ đủ 15 tuổi có thể tự quản lý tài sản riêng của mình không?",
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con 17 tuổi không muốn tự quản lý tài sản có thể nhờ cha mẹ quản lý giúp "
            "theo quy định pháp luật không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Ai quản lý tài sản riêng của con dưới 15 tuổi theo quy định pháp luật?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con mất năng lực hành vi dân sự, tài sản riêng của con do ai quản lý?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cha mẹ có thể ủy quyền cho ông bà quản lý tài sản riêng của con chưa "
            "thành niên không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Tài sản riêng của con dưới 15 tuổi do cha mẹ quản lý được giao lại cho con "
            "khi nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con khôi phục năng lực hành vi dân sự thì tài sản riêng do cha mẹ quản lý "
            "có được giao lại cho con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Cha mẹ và con có thể thỏa thuận khác về thời điểm giao tài sản riêng "
            "cho con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con chưa thành niên được tặng cho nhà đất, cha mẹ có quyền quản lý tài sản "
            "đó như thế nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Cha mẹ có phải quản lý tài sản riêng của con khi con đang do người khác "
            "giám hộ theo Bộ luật dân sự không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_3"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Người tặng cho con tài sản có thể chỉ định người khác quản lý thay cha mẹ "
            "theo di chúc hoặc hợp đồng tặng cho không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_3"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con chưa thành niên được Tòa án giao cho ông bà giám hộ thì ai quản lý "
            "tài sản riêng của con?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_76_Khoan_4"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 77: Định đoạt tài sản riêng của con ---
    {
        "question": (
            "Cha mẹ quản lý tài sản riêng của con dưới 15 tuổi có quyền định đoạt "
            "tài sản đó vì lợi ích của con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_77_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cha mẹ muốn bán xe đứng tên con 10 tuổi có phải xem xét nguyện vọng "
            "của con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_77_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Con từ đủ 9 tuổi trở lên có được xem xét nguyện vọng khi cha mẹ định đoạt "
            "tài sản riêng của con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_77_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Người giám hộ quản lý tài sản riêng của con dưới 15 tuổi có quyền định đoạt "
            "tài sản đó vì lợi ích của con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_77_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con từ đủ 15 tuổi đến dưới 18 tuổi có quyền tự định đoạt tài sản riêng "
            "của mình không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_77_Khoan_2"],
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
    {
        "question": (
            "Con 16 tuổi muốn chuyển nhượng đất đứng tên mình có cần cha mẹ đồng ý "
            "bằng văn bản không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_77_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Con 17 tuổi dùng tiền tiết kiệm mở quán ăn có cần cha mẹ đồng ý bằng văn bản "
            "không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_77_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Ai có quyền định đoạt tài sản riêng của con đã thành niên mất năng lực hành "
            "vi dân sự?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_77_Khoan_3"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con đã thành niên mất năng lực hành vi dân sự, người giám hộ có quyền định "
            "đoạt tài sản riêng của con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_77_Khoan_3"],
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


def _matches_dieu_75_77(can_cu: list[str]) -> bool:
    return any(DIEU_75_77_RE.search(c) for c in can_cu)


def _question_key(text: str) -> str:
    return _normalize_question(text).lower()


def _dieu_numbers(can_cu: list[str]) -> set[int]:
    nums: set[int] = set()
    for c in can_cu:
        m = DIEU_75_77_RE.search(c)
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


def _load_benchmark_rows() -> list[dict]:
    rows: list[dict] = []
    for directory in (BENCHMARK_DIR, BENCHMARK_GROUPED_DIR):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                continue
            for row in data:
                if isinstance(row, dict):
                    row = dict(row)
                    row["_source_file"] = path.name
                    rows.append(row)
    return rows


def _cap_rows(rows: list[dict], max_n: int) -> list[dict]:
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


def build_output(benchmark_rows: list[dict], verbose: bool = False) -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    skipped_no_can_cu = 0
    skipped_other_dieu = 0
    n_benchmark = 0

    for row in benchmark_rows:
        if not _has_can_cu(row):
            skipped_no_can_cu += 1
            continue
        cc = row["can_cu_phap_ly_chinh"]
        if not _matches_dieu_75_77(cc):
            skipped_other_dieu += 1
            continue
        before = len(rows)
        _append_unique(rows, seen, row, row.get("_source_file", "benchmark"))
        if len(rows) > before:
            n_benchmark += 1

    for seed in SEED_QUESTIONS:
        _append_unique(rows, seen, seed, "seed")

    if not rows:
        raise ValueError(
            "Không có câu nào (benchmark/benchmark_grouped hoặc seed) "
            "thuộc Điều 75–77 LHNGD 2014"
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
        all_dieu = {75, 76, 77}
        covered: set[int] = set()
        for r in rows:
            covered |= _dieu_numbers(r["can_cu_phap_ly_chinh"])
        missing = sorted(all_dieu - covered)

        lines = [
            f"Tổng câu: {len(output)} / tối đa {MAX_QUESTIONS}",
            f"  benchmark/benchmark_grouped khớp Điều 75–77: {n_benchmark}",
            f"  seed: {len(SEED_QUESTIONS)}",
            f"  bỏ qua (không có can_cu): {skipped_no_can_cu}",
            f"  bỏ qua (can_cu khác Điều 75–77): {skipped_other_dieu}",
            f"Điều 75–77 được phủ: {len(covered)}/3",
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
                m = DIEU_75_77_RE.search(c)
                if m:
                    dieu_num = m.group(1)
                    dieu = f"Điều {dieu_num}"
                    by_dieu[dieu] = by_dieu.get(dieu, 0) + 1
        for dieu, n in sorted(by_dieu.items(), key=lambda x: int(x[0].split()[1])):
            lines.append(f"  {dieu}: {n} lần")

        lines.append("")
        lines.append("--- Chi tiết ---")
        for i, r in enumerate(rows, 1):
            matched = [c for c in r["can_cu_phap_ly_chinh"] if DIEU_75_77_RE.search(c)]
            loai = r["_loai_cau_hoi"] or "?"
            lines.append(f"{i:2d}. [{r['_source']}|{loai}] {matched}")
            lines.append(f"    {r['question'][:120]}")

        report_path.write_text("\n".join(lines), encoding="utf-8")

    return output


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ghi báo cáo coverage ra feat_llm/tai_san_rieng_cua_con.coverage.txt",
    )
    args = parser.parse_args()

    benchmark_rows = _load_benchmark_rows()
    output = build_output(benchmark_rows, verbose=args.verbose)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(output)} items -> feat_llm/tai_san_rieng_cua_con.json")
    if args.verbose:
        print("Coverage report -> feat_llm/tai_san_rieng_cua_con.coverage.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
