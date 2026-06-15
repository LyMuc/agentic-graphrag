#!/usr/bin/env python3
"""
Lọc và seed câu hỏi cho chủ đề xác định cha, mẹ, con
(Điều 88–93, 99, 101–102 LHNGD 2014).

Nguồn:
  - benchmark_grouped/*.json, benchmark/*.json — câu có can_cu_phap_ly_chinh thuộc các Điều trên;
  - SEED_QUESTIONS — câu seed theo extraction/Luật_HNGD_2014/output_articles.

Đầu ra: feat_llm/xac_dinh_cha_me_con.json (question + can_cu_phap_ly_chinh).

Chạy:
    python benchmark_dataset/scripts/build_feat_llm_xac_dinh_cha_me_con.py
    python benchmark_dataset/scripts/build_feat_llm_xac_dinh_cha_me_con.py --verbose
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
OUTPUT_PATH = PACKAGE_DIR / "feat_llm" / "xac_dinh_cha_me_con.json"
MAX_QUESTIONS = 48

TARGET_DIEU = {88, 89, 90, 91, 92, 93, 99, 101, 102}
DIEU_RE = re.compile(
    r"Luat_HNGD_2014_Dieu_(88|89|90|91|92|93|99|101|102)(?:_|$)"
)

# Seed theo từng khoản extraction/Luật_HNGD_2014/output_articles.
SEED_QUESTIONS: list[dict] = [
    # --- Điều 88: Xác định cha, mẹ ---
    {
        "question": (
            "Con sinh ra trong thời kỳ hôn nhân được xác định là con chung của vợ chồng "
            "theo quy định nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_88_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con được sinh ra trong vòng 300 ngày kể từ khi chấm dứt hôn nhân "
            "có được coi là con chung của vợ chồng không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_88_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Vợ ly hôn được 8 tháng thì sinh con. Chồng cũ có phải cha của đứa trẻ "
            "theo quy định xác định cha, mẹ không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_88_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Con sinh trước ngày đăng ký kết hôn nhưng được cả hai bố mẹ thừa nhận "
            "có được xác định là con chung của vợ chồng không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_88_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Hai người đã làm đám cưới nhưng chưa đăng ký kết hôn, sau đó sinh con "
            "và cùng thừa nhận. Con có được coi là con chung của hai người không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_88_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Cha mẹ không thừa nhận con thì việc xác định quan hệ cha, mẹ, con "
            "được giải quyết như thế nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_88_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Chồng tôi phủ nhận con tôi sinh ra trong hôn nhân. Tôi có thể tự yêu cầu "
            "UBND xác định cha con mà không cần chứng cứ không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_88_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 89: Xác định con ---
    {
        "question": (
            "Người không được ghi nhận là cha hoặc mẹ có quyền yêu cầu Tòa án "
            "xác định một người là con mình không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_89_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cha ruột nhưng giấy khai sinh ghi tên người khác làm cha, tôi có thể "
            "khởi kiện yêu cầu xác định con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_89_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Người đang được ghi nhận là cha, mẹ có quyền yêu cầu Tòa án xác định "
            "một người không phải là con mình không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_89_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Sau khi xét nghiệm ADN, tôi phát hiện con 10 tuổi không phải con ruột. "
            "Tôi có thể yêu cầu Tòa án xác định không phải cha con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_89_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 90: Quyền nhận cha, mẹ ---
    {
        "question": (
            "Con có quyền nhận cha, mẹ của mình kể cả khi cha hoặc mẹ đã chết không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_90_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cha tôi mất khi tôi còn nhỏ, giờ tôi 25 tuổi có thể làm thủ tục "
            "nhận cha trên hộ tịch không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_90_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Con đã thành niên nhận cha có cần sự đồng ý của mẹ không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_90_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con trai 20 tuổi muốn nhận mẹ ruột, cha hiện tại có quyền ngăn cản "
            "hoặc bắt buộc phải đồng ý không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_90_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 91: Quyền nhận con ---
    {
        "question": (
            "Cha, mẹ có quyền nhận con kể cả trong trường hợp con đã chết không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_91_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con tôi mất trong tai nạn, trước đó chưa kịp ghi nhận trên hộ tịch. "
            "Tôi có quyền làm thủ tục nhận con đã chết không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_91_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Người vợ đang có chồng nhận con riêng sinh trước hôn nhân "
            "có cần sự đồng ý của chồng không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_91_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Tôi đã có vợ, phát hiện có con riêng với người khác. Vợ tôi không đồng ý "
            "thì tôi còn được nhận con không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_91_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 92: Người có yêu cầu chết ---
    {
        "question": (
            "Người có yêu cầu xác định cha, mẹ, con đã chết thì ai có quyền "
            "yêu cầu Tòa án xác định thay?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_92"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Anh trai tôi mất trong vụ tai nạn, trước khi mất anh đã nói có con riêng "
            "nhưng chưa kịp làm thủ tục. Gia đình có thể yêu cầu Tòa án xác định "
            "con cho anh tôi không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_92"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 93: Sinh con bằng kỹ thuật hỗ trợ sinh sản ---
    {
        "question": (
            "Vợ chồng sinh con bằng kỹ thuật hỗ trợ sinh sản thì việc xác định "
            "cha, mẹ được áp dụng theo quy định nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_93_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Phụ nữ độc thân sinh con bằng kỹ thuật hỗ trợ sinh sản thì ai "
            "được xác định là mẹ của con?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_93_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Người cho tinh trùng, cho noãn hoặc cho phôi trong thụ tinh ống nghiệm "
            "có phát sinh quan hệ cha, mẹ, con với đứa trẻ sinh ra không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_93_Khoan_3"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Vợ chồng tôi làm IVF, người bạn cho tinh trùng. Người bạn đó có phải "
            "cha pháp lý của con tôi sinh ra không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_93_Khoan_3"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Việc xác định cha, mẹ trong trường hợp mang thai hộ vì mục đích nhân đạo "
            "được áp dụng theo quy định nào của Luật Hôn nhân và gia đình?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_93_Khoan_4"],
        "loai_cau_hoi": "Lý thuyết",
    },
    # --- Điều 99: Tranh chấp KTHSS, mang thai hộ ---
    {
        "question": (
            "Tranh chấp về sinh con bằng kỹ thuật hỗ trợ sinh sản hoặc mang thai hộ "
            "vì mục đích nhân đạo do cơ quan nào giải quyết?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_99_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Vợ chồng nhờ mang thai hộ cùng chết trước khi giao con, bên mang thai hộ "
            "có quyền nhận nuôi đứa trẻ không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_99_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Bên mang thai hộ không nhận nuôi trẻ sau khi vợ chồng nhờ mang thai hộ "
            "đã chết thì việc giám hộ và cấp dưỡng được thực hiện thế nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_99_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 101: Thẩm quyền ---
    {
        "question": (
            "Việc xác định cha, mẹ, con không có tranh chấp thì cơ quan nào "
            "có thẩm quyền giải quyết?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_101_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Hai bên tranh chấp về cha con thì Tòa án hay cơ quan đăng ký hộ tịch "
            "có thẩm quyền xác định?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_101_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Người được yêu cầu xác định là cha đã chết, việc xác định cha, mẹ, con "
            "thuộc thẩm quyền của cơ quan nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_101_Khoan_2"],
        "loai_cau_hoi": "Tình huống",
    },
    # --- Điều 102: Người có quyền yêu cầu ---
    {
        "question": (
            "Cha, mẹ, con đã thành niên có quyền yêu cầu cơ quan đăng ký hộ tịch "
            "xác định quan hệ cha, mẹ, con trong trường hợp nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_102_Khoan_1"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con đã thành niên muốn xác định cha ruột, hai bên không tranh chấp. "
            "Tôi nên làm thủ tục ở UBND hay khởi kiện ra Tòa án?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_102_Khoan_1"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Ai có quyền yêu cầu Tòa án xác định cha, mẹ, con khi có tranh chấp?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_102_Khoan_2"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Người giám hộ có quyền yêu cầu Tòa án xác định cha, mẹ cho con "
            "chưa thành niên không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_102_Khoan_3_Diem_a"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cơ quan quản lý nhà nước về gia đình có quyền yêu cầu Tòa án "
            "xác định cha, mẹ cho trẻ em không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_102_Khoan_3_Diem_b"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Cơ quan quản lý nhà nước về trẻ em có thể đề nghị Tòa án xác định "
            "cha, mẹ cho trẻ bị bỏ rơi không?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_102_Khoan_3_Diem_c"],
        "loai_cau_hoi": "Tình huống",
    },
    {
        "question": (
            "Hội Liên hiệp Phụ nữ có quyền yêu cầu Tòa án xác định cha, mẹ, con "
            "trong những trường hợp nào?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_102_Khoan_3_Diem_d"],
        "loai_cau_hoi": "Lý thuyết",
    },
    {
        "question": (
            "Con đã thành niên bị mất năng lực hành vi dân sự, ai có quyền yêu cầu "
            "Tòa án xác định cha, mẹ cho con?"
        ),
        "can_cu_phap_ly_chinh": ["Luat_HNGD_2014_Dieu_102_Khoan_3"],
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


def _matches_target_dieu(can_cu: list[str]) -> bool:
    return any(DIEU_RE.search(c) for c in can_cu)


def _question_key(text: str) -> str:
    return _normalize_question(text).lower()


def _dieu_numbers(can_cu: list[str]) -> set[int]:
    nums: set[int] = set()
    for c in can_cu:
        m = DIEU_RE.search(c)
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
    """Giữ tối đa max_n câu; ưu tiên mỗi Điều mục tiêu có ít nhất một câu."""
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

    for folder in (GROUPED_DIR, BENCHMARK_DIR):
        for row, source_file in _load_json_rows(folder):
            if not _has_can_cu(row):
                continue
            cc = row["can_cu_phap_ly_chinh"]
            if not _matches_target_dieu(cc):
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
            "Không có câu nào (benchmark hoặc seed) thuộc Điều 88–93, 99, 101–102"
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
            f"Điều mục tiêu được phủ: {len(covered)}/{len(TARGET_DIEU)}",
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
                m = DIEU_RE.search(c)
                if m:
                    dieu = f"Điều {m.group(1)}"
                    by_dieu[dieu] = by_dieu.get(dieu, 0) + 1
        for dieu, n in sorted(by_dieu.items(), key=lambda x: int(x[0].split()[1])):
            lines.append(f"  {dieu}: {n} lần")

        lines.append("")
        lines.append("--- Chi tiết ---")
        for i, r in enumerate(rows, 1):
            matched = [c for c in r["can_cu_phap_ly_chinh"] if DIEU_RE.search(c)]
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
        help="Ghi báo cáo coverage ra feat_llm/xac_dinh_cha_me_con.coverage.txt",
    )
    args = parser.parse_args()

    output = build_output(verbose=args.verbose)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(output)} items -> feat_llm/xac_dinh_cha_me_con.json")
    if args.verbose:
        print("Coverage report -> feat_llm/xac_dinh_cha_me_con.coverage.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
