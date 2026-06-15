#!/usr/bin/env python3
"""
Lọc và seed câu hỏi cho chủ đề đại diện và trách nhiệm liên đới vợ chồng (Điều 24–27 LHNGD 2014).

Nguồn:
  - benchmark/*.json, benchmark_grouped/*.json — câu có can_cu_phap_ly_chinh thuộc Điều 24–27;
  - SEED_QUESTIONS — câu seed theo extraction/Luật_HNGD_2014/output_articles (Điều 24–26).

Chỉ lấy câu đã có can_cu_phap_ly_chinh và trong đó có ít nhất một mã
Luat_HNGD_2014_Dieu_24|25|26|27. Điều 27 không seed thêm (đã đủ từ benchmark).

Đầu ra: feat_llm/dai_dien_trach_nhiem_vo_chong.json (mỗi phần tử: question + can_cu_phap_ly_chinh).

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_dai_dien_trach_nhiem_vo_chong.py
    python benchmark_dataset/scripts/build_feat_llm_dai_dien_trach_nhiem_vo_chong.py --verbose
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
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "dai_dien_trach_nhiem_vo_chong.json"

DIEU_24_27_RE = re.compile(r"Luat_HNGD_2014_Dieu_(24|25|26|27)(?:_|$)")

# Seed theo Điều 24–26 (extraction/Luật_HNGD_2014/output_articles). Không seed Điều 27.
SEED_QUESTIONS: list[dict] = [
    # --- Điều 24 khoản 1: căn cứ xác lập đại diện ---
    {
        "question": (
            "Việc đại diện giữa vợ và chồng trong xác lập, thực hiện, chấm dứt giao dịch "
            "được xác định theo những quy định pháp luật nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_24_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 24 khoản 2: ủy quyền cho nhau ---
    {
        "question": (
            "Vợ, chồng có thể ủy quyền cho nhau xác lập, thực hiện và chấm dứt giao dịch "
            "mà theo quy định phải có sự đồng ý của cả hai vợ chồng không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_24_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Chồng một mình ký hợp đồng bán nhà chung mà vợ không đồng ý "
            "có phù hợp quy định về đại diện giữa vợ và chồng không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_24_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 24 khoản 3: đại diện khi mất/hạn chế NLHVDV ---
    {
        "question": (
            "Vợ hoặc chồng mất năng lực hành vi dân sự thì bên kia có được đại diện "
            "cho bên đó trong giao dịch dân sự không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_24_Khoan_3"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Chồng bị hạn chế năng lực hành vi dân sự, vợ được Tòa án chỉ định làm "
            "người đại diện theo pháp luật có được đại diện cho chồng trong giao dịch không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_24_Khoan_3"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Người mất năng lực hành vi dân sự có luôn được vợ hoặc chồng đại diện "
            "trong mọi giao dịch không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_24_Khoan_3"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Khi ly hôn mà một bên vợ hoặc chồng mất năng lực hành vi dân sự, "
            "ai đại diện cho người đó trong vụ ly hôn?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_24_Khoan_3"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 25 khoản 1: đại diện trong kinh doanh chung ---
    {
        "question": (
            "Khi vợ chồng kinh doanh chung thì ai là người đại diện hợp pháp "
            "trong quan hệ kinh doanh đó?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_25_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Vợ chồng kinh doanh chung, vợ ký hợp đồng mua bán hàng hóa "
            "có được coi là đại diện hợp pháp cho chồng không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_25_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Vợ chồng trước khi tham gia quan hệ kinh doanh chung có thỏa thuận "
            "một người làm đại diện thì áp dụng như thế nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_25_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 25 khoản 2: tài sản chung đưa vào kinh doanh ---
    {
        "question": (
            "Vợ chồng đưa tài sản chung vào kinh doanh phải tuân thủ quy định nào "
            "của Luật Hôn nhân và gia đình 2014?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_25_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 26 khoản 1: GCN chỉ ghi tên một người ---
    {
        "question": (
            "Giấy chứng nhận quyền sử dụng đất chung của vợ chồng chỉ ghi tên chồng "
            "thì việc đại diện giao dịch áp dụng quy định nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_26_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Nhà chung của vợ chồng có sổ đỏ chỉ đứng tên vợ, chồng có được tự bán nhà "
            "mà không cần vợ đồng ý không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_26_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Tài sản chung có giấy chứng nhận quyền sở hữu chỉ ghi tên một vợ hoặc chồng "
            "thì việc đại diện giữa vợ và chồng được thực hiện theo quy định nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_26_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 26 khoản 2: giao dịch trái quy định, người thứ ba ngay tình ---
    {
        "question": (
            "Vợ tự bán tài sản chung có giấy chứng nhận chỉ ghi tên vợ trái quy định "
            "về đại diện giữa vợ và chồng thì giao dịch có hiệu lực không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_26_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Chồng một mình chuyển nhượng đất chung trên sổ chỉ ghi tên chồng "
            "cho người mua ngay tình thì giao dịch có bị vô hiệu không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_26_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Giao dịch do vợ hoặc chồng tự mình thực hiện trái quy định đại diện "
            "giữa vợ chồng có bị coi là vô hiệu trong mọi trường hợp không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_26_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
]


def _normalize_question(text: str) -> str:
    text = text.replace("\u200b", "")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\n.*@gmail\.com.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n.*@yahoo\.com.*", "", text, flags=re.IGNORECASE)
    return text[:2000]


def _has_can_cu(row: dict) -> bool:
    cc = row.get("can_cu_phap_ly_chinh")
    return isinstance(cc, list) and len(cc) > 0


def _matches_dieu_24_27(can_cu: list[str]) -> bool:
    return any(DIEU_24_27_RE.search(c) for c in can_cu)


def _question_key(text: str) -> str:
    return _normalize_question(text).lower()


def _dieu_numbers(can_cu: list[str]) -> set[int]:
    nums: set[int] = set()
    for c in can_cu:
        m = DIEU_24_27_RE.search(c)
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
            if "_pre_recovery_backup" in path.name or path.name.startswith("_"):
                continue
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                continue
            for row in data:
                if isinstance(row, dict):
                    item = dict(row)
                    item["_source_file"] = f"{directory.name}/{path.name}"
                    rows.append(item)
    return rows


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
        if not _matches_dieu_24_27(cc):
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
            "có can_cu_phap_ly_chinh thuộc Điều 24–27 LHNGD 2014"
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
        all_dieu = {24, 25, 26, 27}
        covered: set[int] = set()
        for r in rows:
            covered |= _dieu_numbers(r["can_cu_phap_ly_chinh"])
        missing = sorted(all_dieu - covered)

        lines = [
            f"Tổng câu: {len(output)}",
            f"  benchmark/benchmark_grouped khớp Điều 24–27: {n_benchmark}",
            f"  seed (Điều 24–26): {len(SEED_QUESTIONS)}",
            f"  bỏ qua (không có can_cu): {skipped_no_can_cu}",
            f"  bỏ qua (can_cu khác Điều 24–27): {skipped_other_dieu}",
            f"Điều 24–27 được phủ: {len(covered)}/4",
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
                m = DIEU_24_27_RE.search(c)
                if m:
                    dieu = f"Điều {m.group(1)}"
                    by_dieu[dieu] = by_dieu.get(dieu, 0) + 1
        for dieu, n in sorted(by_dieu.items(), key=lambda x: int(x[0].split()[1])):
            lines.append(f"  {dieu}: {n} lần")

        seed_khoan = {
            "Điều 24 khoản 1": "Luat_HNGD_2014_Dieu_24_Khoan_1",
            "Điều 24 khoản 2": "Luat_HNGD_2014_Dieu_24_Khoan_2",
            "Điều 24 khoản 3": "Luat_HNGD_2014_Dieu_24_Khoan_3",
            "Điều 25 khoản 1": "Luat_HNGD_2014_Dieu_25_Khoan_1",
            "Điều 25 khoản 2": "Luat_HNGD_2014_Dieu_25_Khoan_2",
            "Điều 26 khoản 1": "Luat_HNGD_2014_Dieu_26_Khoan_1",
            "Điều 26 khoản 2": "Luat_HNGD_2014_Dieu_26_Khoan_2",
        }
        lines.append("")
        lines.append("--- Phủ khoản seed (Điều 24–26) ---")
        for label, code in seed_khoan.items():
            hit = any(code in r["can_cu_phap_ly_chinh"] for r in rows)
            lines.append(f"  {label}: {'có' if hit else 'THIẾU'}")

        lines.append("")
        lines.append("--- Chi tiết ---")
        for i, r in enumerate(rows, 1):
            matched = [c for c in r["can_cu_phap_ly_chinh"] if DIEU_24_27_RE.search(c)]
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
        help=(
            "Ghi báo cáo coverage ra "
            "feat_llm/dai_dien_trach_nhiem_vo_chong.coverage.txt"
        ),
    )
    args = parser.parse_args()

    benchmark_rows = _load_benchmark_rows()
    output = build_output(benchmark_rows, verbose=args.verbose)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(output)} items -> feat_llm/dai_dien_trach_nhiem_vo_chong.json")
    if args.verbose:
        print("Coverage report -> feat_llm/dai_dien_trach_nhiem_vo_chong.coverage.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
