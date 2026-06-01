"""Smoke test dedupe xuyên mục trong chuan_hoa_Context_cho_LLM."""
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.utils import (
    _collect_dieu_ids_from_context,
    _format_bang_link_trich_dan,
    chuan_hoa_Context_cho_LLM,
)


DIEU_X = "Luat_Test_2014_Dieu_38"
KHOAN_X = "Luat_Test_2014_Dieu_38_Khoan_1"
DIEM_X = "Luat_Test_2014_Dieu_38_Khoan_1_Diem_a"
DIEU_Y = "Luat_Test_2014_Dieu_43"
ND_SUA = "NghiDinh_Test_Dieu_2"
DIEU_SAP = "Luat_Test_2026_Dieu_16"
LUAT_MOI = "Luat_Test_2026"


def _run(label: str, context_tho: dict, checks: list[tuple[str, bool]]) -> None:
    record = {"Context_Tho": context_tho}
    text = chuan_hoa_Context_cho_LLM(record, "2026-06-01", False)
    for snippet, should_contain in checks:
        found = snippet in text
        ok = found == should_contain
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {label}: {'có' if should_contain else 'không có'} {snippet!r} -> {found}")
        if not ok:
            raise AssertionError(f"{label}: expected {'contain' if should_contain else 'not contain'} {snippet!r}")


def test_cross_section_same_original() -> None:
    """Cùng (Dieu_X, '') ở chính + bổ trợ -> chỉ còn ở chính."""
    _run(
        "chinh+bo_tro trùng bản gốc",
        {
            "can_cu_chinh": [{
                "id_thuc_te_ap_dung": DIEU_X,
                "noidung": "Nội dung gốc chính",
                "cap_bac": 1,
            }],
            "can_cu_bo_tro": [{
                "id": DIEU_X,
                "noidung": "Nội dung trùng bổ trợ",
                "cap_bac": 2,
            }],
        },
        [
            ("Nội dung gốc chính", True),
            ("Nội dung trùng bổ trợ", False),
            ("--- CĂN CỨ THAM CHIẾU BỔ TRỢ", False),
        ],
    )


def test_original_vs_amended_both_kept() -> None:
    """Cùng Dieu_X nhưng một có id_sua_doi -> cả hai giữ."""
    _run(
        "bản gốc + bản sửa đổi",
        {
            "can_cu_chinh": [{
                "id_thuc_te_ap_dung": DIEU_X,
                "noidung": "Bản gốc",
                "cap_bac": 1,
            }],
            "can_cu_huong_dan": [{
                "id": DIEU_X,
                "id_sua_doi": ND_SUA,
                "noidung_sua_doi": "Bản đã sửa",
                "cap_bac": 2,
            }],
            "lien_ket_huong_dan": [{
                "id_huong_dan": ND_SUA,
                "id_duoc_huong_dan": DIEU_X,
            }],
        },
        [
            ("Bản gốc", True),
            ("Bản đã sửa", True),
            (f"được sửa đổi, bổ sung bởi [{ND_SUA}]", True),
        ],
    )


def test_amended_cross_section_dedupe() -> None:
    """Cùng (Dieu_X, ND_SUA) ở hướng dẫn + bổ trợ -> chỉ mục trước giữ."""
    _run(
        "huong_dan+bo_tro trùng sửa đổi",
        {
            "can_cu_chinh": [],
            "can_cu_huong_dan": [{
                "id": DIEU_X,
                "id_sua_doi": ND_SUA,
                "noidung_sua_doi": "HD sửa đổi",
                "cap_bac": 2,
            }],
            "can_cu_bo_tro": [{
                "id": DIEU_X,
                "id_sua_doi": ND_SUA,
                "noidung": "BT trùng sửa đổi",
                "cap_bac": 3,
            }],
        },
        [
            ("HD sửa đổi", True),
            ("BT trùng sửa đổi", False),
        ],
    )


def test_sap_hieu_luc_content_deduped_link_kept() -> None:
    """Sap HL: nội dung trùng chính bị loại; dòng liên kết vẫn hiện."""
    _run(
        "sap trùng chính",
        {
            "can_cu_chinh": [{
                "id_thuc_te_ap_dung": DIEU_SAP,
                "noidung": "Điều 16 hiện hành",
                "cap_bac": 1,
            }],
            "can_cu_sap_hieu_luc": [{
                "id": DIEU_SAP,
                "noidung": "Điều 16 sắp HL",
                "loai_tac_dong": "THAY_THE",
                "cap_bac": 1,
            }],
            "lien_ket_sap_hieu_luc": [{
                "id_van_ban": DIEU_SAP,
                "id_duoc_tac_dong": DIEU_X,
                "loai_tac_dong": "THAY_THE",
            }],
        },
        [
            ("Điều 16 hiện hành", True),
            ("Điều 16 sắp HL", False),
            (f"{DIEU_SAP} thay thế", True),
            ("CÓ_VĂN_BẢN_SẮP_CÓ_HIỆU_LỰC", True),
        ],
    )


def test_van_ban_thay_the_filtered_by_registry() -> None:
    """Văn bản thay thế trùng node đã trong registry bị loại."""
    record = {
        "Context_Tho": {
            "can_cu_chinh": [{
                "id_thuc_te_ap_dung": LUAT_MOI,
                "noidung": "Luật mới",
                "cap_bac": 1,
            }],
            "quy_dinh_hien_hanh_doi_chieu": [LUAT_MOI, "Luat_Test_2014"],
        }
    }
    text = chuan_hoa_Context_cho_LLM(record, "2026-06-01", False)
    marker = "--- VĂN BẢN THAY THẾ ---"
    assert marker in text, "Thiếu section văn bản thay thế"
    thay_the_block = text.split(marker, 1)[1].split("\n---", 1)[0]
    assert LUAT_MOI not in thay_the_block, f"ID trùng registry vẫn còn: {thay_the_block!r}"
    assert "Luat_Test_2014" in thay_the_block, f"ID thay thế hợp lệ bị mất: {thay_the_block!r}"
    print("  [OK] van_ban_thay_the: registry lọc đúng trong section thay thế")


def test_collect_dieu_ids_rollup() -> None:
    """Khoản/Điểm roll-up về cùng ID Điều, dedupe."""
    data = {
        "can_cu_chinh": [
            {"id_thuc_te_ap_dung": KHOAN_X},
            {"id_thuc_te_ap_dung": DIEM_X},
            {"id_thuc_te_ap_dung": DIEU_Y},
        ],
        "can_cu_mau_thuan": [{"id_nguon": DIEU_X, "id_dich": "Luat_Other_2010_Dieu_21_Khoan_1"}],
    }
    dieu_ids = _collect_dieu_ids_from_context(data)
    assert dieu_ids == {
        DIEU_X,
        DIEU_Y,
        "Luat_Other_2010_Dieu_21",
    }, f"Unexpected dieu ids: {dieu_ids}"
    assert KHOAN_X not in dieu_ids
    assert DIEM_X not in dieu_ids
    print("  [OK] collect_dieu_ids: roll-up + dedupe đúng")


def test_bang_link_section_dieu_only() -> None:
    """BẢNG LINK chỉ liệt kê cấp Điều, không có Khoản/Điểm."""
    fake_links = {
        DIEU_X: "https://example.test/?anchor=dieu_38",
        DIEU_Y: "https://example.test/?anchor=dieu_43",
    }
    with patch("utils.utils._fetch_tvpl_links", return_value=fake_links):
        record = {
            "Context_Tho": {
                "can_cu_chinh": [
                    {
                        "id_thuc_te_ap_dung": KHOAN_X,
                        "noidung": "Khoản 1",
                        "cap_bac": 1,
                    },
                    {
                        "id_thuc_te_ap_dung": DIEU_Y,
                        "noidung": "Điều 43",
                        "cap_bac": 1,
                    },
                ],
            }
        }
        text = chuan_hoa_Context_cho_LLM(record, "2026-06-01", False)

    assert "--- BẢNG LINK TRÍCH DẪN (TVPL) ---" in text
    assert f"[{DIEU_X}] → {fake_links[DIEU_X]}" in text
    assert f"[{DIEU_Y}] → {fake_links[DIEU_Y]}" in text
    assert KHOAN_X not in text.split("--- BẢNG LINK TRÍCH DẪN (TVPL) ---")[1]
    assert "_Khoan_" not in text.split("--- BẢNG LINK TRÍCH DẪN (TVPL) ---")[1]
    assert "_Diem_" not in text.split("--- BẢNG LINK TRÍCH DẪN (TVPL) ---")[1]
    print("  [OK] bang_link: chỉ cấp Điều trong section link")


def test_bang_link_empty_when_no_links() -> None:
    """Không có link Neo4j → không append section BẢNG LINK."""
    with patch("utils.utils._fetch_tvpl_links", return_value={}):
        text = chuan_hoa_Context_cho_LLM(
            {"Context_Tho": {"can_cu_chinh": [{"id_thuc_te_ap_dung": DIEU_X, "noidung": "x", "cap_bac": 1}]}},
            "2026-06-01",
            False,
        )
    assert "--- BẢNG LINK TRÍCH DẪN (TVPL) ---" not in text
    print("  [OK] bang_link: ẩn section khi không có URL")


def test_format_bang_link_trich_dan() -> None:
    out = _format_bang_link_trich_dan({"B_Dieu_2": "https://b", "A_Dieu_1": "https://a"})
    assert out.index("A_Dieu_1") < out.index("B_Dieu_2")
    assert "https://a" in out
    print("  [OK] format_bang_link: sắp xếp theo ID")


def main() -> None:
    tests = [
        test_cross_section_same_original,
        test_original_vs_amended_both_kept,
        test_amended_cross_section_dedupe,
        test_sap_hieu_luc_content_deduped_link_kept,
        test_van_ban_thay_the_filtered_by_registry,
        test_collect_dieu_ids_rollup,
        test_bang_link_section_dieu_only,
        test_bang_link_empty_when_no_links,
        test_format_bang_link_trich_dan,
    ]
    print("Running cross-section context dedupe smoke tests...\n")
    for fn in tests:
        fn()
        print()
    print("All smoke tests passed.")


if __name__ == "__main__":
    main()
