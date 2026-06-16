"""Smoke test inject heading cha cho THAM_CHIEU_DEN."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.retrievers._context_tho_common import (  # noqa: E402
    tham_chieu_ancestor_collect_parts,
)
from adapter.cypher_templates.dieu_kien_ket_hon import (  # noqa: E402
    DIEU_KIEN_KET_HON_REGISTRY,
)
from adapter.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh import (  # noqa: E402
    QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY,
)
from utils.utils import chuan_hoa_Context_cho_LLM  # noqa: E402

DIEU_5 = "Luat_HNGD_2014_Dieu_5"
KHOAN_2 = "Luat_HNGD_2014_Dieu_5_Khoan_2"
DIEM_A = "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_a"


def test_simple_template_has_ancestor_headings() -> None:
    tpl = DIEU_KIEN_KET_HON_REGISTRY.get("dieu_kien_ket_hon_tong_quat")
    out = tpl.cypher
    assert "// 7b-8b. Heading cha" in out
    assert "dieu_cha_ltc" in out
    assert "dieu_ong_ctt" in out
    assert "dieu_cha_ltc.id" in out
    assert "dieu_cha_ltc_hd" in out
    print("  [OK] template dieu_kien_ket_hon: co ancestor truc tiep va tu huong dan")


def test_hd_template_has_ancestor_headings() -> None:
    tpl = QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.get(
        "quyen_nghia_vu_chung_thanh_vien_gia_dinh"
    )
    out = tpl.cypher
    assert "dieu_cha_ltc_hd" in out
    assert "dieu_ong_ctt_hd" in out
    print("  [OK] template HD: co ancestor tu huong dan")


def test_bo_tro_keeps_ancestor_headings() -> None:
    """Mock: Diem tham chieu + Dieu/Khoan cha — ca ba giu trong bo tro."""
    record = {
        "Context_Tho": {
            "can_cu_chinh": [{
                "id_thuc_te_ap_dung": "Luat_HNGD_2014_Dieu_8",
                "noidung": "Dieu 8",
                "cap_bac": 2,
            }],
            "can_cu_bo_tro": [
                {"id": DIEU_5, "noidung": "Dieu 5. Cam ket hon", "cap_bac": 2},
                {"id": KHOAN_2, "noidung": "2. Cac truong hop cam", "cap_bac": 2},
                {"id": DIEM_A, "noidung": "a) Ket hon gia", "cap_bac": 2},
            ],
        }
    }
    text = chuan_hoa_Context_cho_LLM(record, "2026-06-01", False)
    assert DIEU_5 in text
    assert KHOAN_2 in text
    assert DIEM_A in text
    assert "Cam ket hon" in text
    print("  [OK] bo_tro: giu heading Dieu + Khoan + Diem")


def test_kg_collect_parts_non_empty() -> None:
    parts = tham_chieu_ancestor_collect_parts()
    assert "dieu_cha_ltc" in parts
    assert "dieu_ong_ctt_hd" in parts
    print("  [OK] KG ancestor collect parts")


def main() -> None:
    print("Running tham chieu ancestor smoke tests...\n")
    test_simple_template_has_ancestor_headings()
    test_hd_template_has_ancestor_headings()
    test_bo_tro_keeps_ancestor_headings()
    test_kg_collect_parts_non_empty()
    print("\nAll passed.")


if __name__ == "__main__":
    main()
