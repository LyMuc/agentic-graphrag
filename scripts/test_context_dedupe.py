"""Smoke test dedupe xuyên mục trong chuan_hoa_Context_cho_LLM."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.utils import chuan_hoa_Context_cho_LLM


DIEU_X = "Luat_Test_2014_Dieu_38"
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


def main() -> None:
    tests = [
        test_cross_section_same_original,
        test_original_vs_amended_both_kept,
        test_amended_cross_section_dedupe,
        test_sap_hieu_luc_content_deduped_link_kept,
        test_van_ban_thay_the_filtered_by_registry,
    ]
    print("Running cross-section context dedupe smoke tests...\n")
    for fn in tests:
        fn()
        print()
    print("All smoke tests passed.")


if __name__ == "__main__":
    main()
