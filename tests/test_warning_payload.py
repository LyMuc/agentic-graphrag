from __future__ import annotations

from application.legal_context import (
    build_legal_context_bundle,
    legal_context_bundle_to_context_tho,
    merge_legal_context_bundles,
)
from application.warning_payload import (
    build_legal_warning_metadata,
    build_validity_warning_payload,
    dedupe_rows_by_ancestor,
    format_provision_label,
)


def _bundle(context_tho: dict, target_date: str = "2026-06-11", *, is_user_provided_date: bool = False) -> dict:
    return build_legal_context_bundle(
        context_tho,
        target_date,
        is_user_provided_date,
        retriever_name="test",
        template_name="template",
        citation_links={
            "Luat_HNGD_2014_Dieu_35": "https://example.test/dieu-35",
            "Luat_HoTich_2026_Dieu_16": "https://example.test/dieu-16",
        },
    )


def test_format_provision_label_dieu_khoan_diem():
    assert format_provision_label("Luat_HNGD_2014_Dieu_35") == "Điều 35 Luật HNGD 2014"
    assert (
        format_provision_label("Luat_HoTich_2026_Dieu_16")
        == "Điều 16 Luật Hộ tịch 2026"
    )
    assert (
        format_provision_label("Luat_HNGD_2014_Dieu_35_Khoan_2")
        == "Khoản 2 Điều 35 Luật HNGD 2014"
    )
    assert (
        format_provision_label("Luat_HNGD_2014_Dieu_35_Khoan_2_Diem_a")
        == "Điểm a Khoản 2 Điều 35 Luật HNGD 2014"
    )


def test_expired_row_without_replacement():
    bundle = _bundle(
        {
            "can_cu_chinh": [
                {
                    "id_goc_tu_router": "Luat_HNGD_2014_Dieu_35",
                    "id_thuc_te_ap_dung": "Luat_HNGD_2014_Dieu_35",
                    "noidung": "Nội dung",
                    "cap_bac": 1,
                    "het_hieu_luc": True,
                    "ngay_hieu_luc": "2015-01-01",
                    "ngay_het_hieu_luc": "2026-12-31",
                }
            ],
        }
    )
    payload = build_validity_warning_payload(bundle)
    assert payload is not None
    row = payload["expired_rows"][0]
    assert row["basis_id"] == "Luat_HNGD_2014_Dieu_35"
    assert row["expiry_date"] == "31-12-2026"
    assert row["replacement_name"] == "—"


def test_expired_row_with_replacement_relation():
    bundle = _bundle(
        {
            "can_cu_chinh": [
                {
                    "id_goc_tu_router": "NghiDinh_82_2020_ND_CP_Dieu_58",
                    "id_thuc_te_ap_dung": "NghiDinh_82_2020_ND_CP_Dieu_58",
                    "noidung": "Cũ",
                    "cap_bac": 5,
                    "het_hieu_luc": True,
                    "ngay_hieu_luc": "2020-09-01",
                    "ngay_het_hieu_luc": "2026-05-18",
                },
                {
                    "id_goc_tu_router": "NghiDinh_109_2026_ND_CP_Dieu_61",
                    "id_thuc_te_ap_dung": "NghiDinh_109_2026_ND_CP_Dieu_61",
                    "noidung": "Mới",
                    "cap_bac": 5,
                    "het_hieu_luc": False,
                    "ngay_hieu_luc": "2026-06-01",
                    "ngay_het_hieu_luc": None,
                },
            ],
            "lien_ket_hien_hanh": [
                {
                    "id_hien_hanh": "NghiDinh_109_2026_ND_CP_Dieu_61",
                    "id_duoc_thay_the": "NghiDinh_82_2020_ND_CP_Dieu_58",
                }
            ],
        }
    )
    payload = build_validity_warning_payload(bundle)
    assert payload is not None
    row = payload["expired_rows"][0]
    assert row["replacement_id"] == "NghiDinh_109_2026_ND_CP_Dieu_61"
    assert row["replacement_effective_date"] == "01-06-2026"


def test_replacement_effective_date_from_future_relations_only():
    """Historical target_date: replacement is in can_cu_sap_hieu_luc, not can_cu_chinh."""
    bundle = _bundle(
        {
            "can_cu_chinh": [
                {
                    "id_goc_tu_router": "NghiDinh_82_2020_ND_CP_Dieu_58",
                    "id_thuc_te_ap_dung": "NghiDinh_82_2020_ND_CP_Dieu_58",
                    "noidung": "Phạt tiền tảo hôn (cũ)",
                    "cap_bac": 5,
                    "het_hieu_luc": True,
                    "ngay_hieu_luc": "2020-09-01",
                    "ngay_het_hieu_luc": "2026-05-18",
                },
            ],
            "can_cu_sap_hieu_luc": [
                {
                    "id": "NghiDinh_109_2026_ND_CP_Dieu_61",
                    "noidung": "Phạt tiền tảo hôn (mới)",
                    "cap_bac": 5,
                    "ngay_ban_hanh": "2026-04-01",
                    "ngay_hieu_luc": "2026-07-01",
                    "ngay_het_hieu_luc": None,
                    "loai_tac_dong": "THAY_THE_BOI",
                    "id_duoc_tac_dong": "NghiDinh_82_2020_ND_CP_Dieu_58",
                },
            ],
            "lien_ket_hien_hanh": [
                {
                    "id_hien_hanh": "NghiDinh_109_2026_ND_CP_Dieu_61",
                    "id_duoc_thay_the": "NghiDinh_82_2020_ND_CP_Dieu_58",
                }
            ],
        },
        target_date="2021-12-31",
        is_user_provided_date=True,
    )
    payload = build_validity_warning_payload(bundle)
    assert payload is not None
    row = payload["expired_rows"][0]
    assert row["basis_id"] == "NghiDinh_82_2020_ND_CP_Dieu_58"
    assert row["replacement_id"] == "NghiDinh_109_2026_ND_CP_Dieu_61"
    assert row["replacement_effective_date"] == "01-07-2026"


def test_replacement_effective_date_from_replacement_role_provision():
    """Current replacement at query_date: only in replacement_relations + role=replacement."""
    bundle = _bundle(
        {
            "can_cu_chinh": [
                {
                    "id_goc_tu_router": "NghiDinh_82_2020_ND_CP_Dieu_58",
                    "id_thuc_te_ap_dung": "NghiDinh_82_2020_ND_CP_Dieu_58",
                    "noidung": "Cũ",
                    "cap_bac": 5,
                    "het_hieu_luc": True,
                    "ngay_hieu_luc": "2020-09-01",
                    "ngay_het_hieu_luc": "2026-05-18",
                },
            ],
            "lien_ket_hien_hanh": [
                {
                    "id_hien_hanh": "NghiDinh_109_2026_ND_CP_Dieu_61",
                    "id_duoc_thay_the": "NghiDinh_82_2020_ND_CP_Dieu_58",
                }
            ],
        },
        target_date="2021-12-31",
        is_user_provided_date=True,
    )
    bundle["provisions"].append(
        {
            "id": "NghiDinh_109_2026_ND_CP_Dieu_61",
            "content": None,
            "role": "replacement",
            "legal_rank": None,
            "effective_from": "2026-05-18",
            "effective_until": None,
            "amendment_id": None,
            "amended_content": None,
            "amendment_effective_from": None,
            "amendment_effective_until": None,
            "source_id": None,
            "provenance": [],
        }
    )
    payload = build_validity_warning_payload(bundle)
    row = payload["expired_rows"][0]
    assert row["replacement_effective_date"] == "18-05-2026"


def test_expired_dedupe_hides_khoan_when_dieu_present():
    rows = [
        {"basis_id": "Luat_HNGD_2014_Dieu_35"},
        {"basis_id": "Luat_HNGD_2014_Dieu_35_Khoan_1"},
        {"basis_id": "Luat_HNGD_2014_Dieu_35_Khoan_1_Diem_a"},
        {"basis_id": "Luat_HNGD_2014_Dieu_35_Khoan_2"},
    ]
    deduped = dedupe_rows_by_ancestor(rows, "basis_id")
    assert [r["basis_id"] for r in deduped] == ["Luat_HNGD_2014_Dieu_35"]


def test_expired_dedupe_keeps_sibling_khoan_when_only_one_khoan_present():
    rows = [
        {"basis_id": "Luat_HNGD_2014_Dieu_35_Khoan_1"},
        {"basis_id": "Luat_HNGD_2014_Dieu_35_Khoan_2"},
    ]
    deduped = dedupe_rows_by_ancestor(rows, "basis_id")
    assert len(deduped) == 2


def test_expired_dedupe_keeps_khoan_hides_diem():
    rows = [
        {"basis_id": "Luat_HNGD_2014_Dieu_35_Khoan_2"},
        {"basis_id": "Luat_HNGD_2014_Dieu_35_Khoan_2_Diem_a"},
    ]
    deduped = dedupe_rows_by_ancestor(rows, "basis_id")
    assert [r["basis_id"] for r in deduped] == ["Luat_HNGD_2014_Dieu_35_Khoan_2"]


def test_future_rows_and_dedupe():
    bundle = _bundle(
        {
            "can_cu_sap_hieu_luc": [
                {
                    "id": "Luat_HoTich_2026_Dieu_16",
                    "noidung": "Điều 16. Đăng ký kết hôn",
                    "cap_bac": 1,
                    "ngay_ban_hanh": "2026-04-23",
                    "ngay_hieu_luc": "2027-03-01",
                    "ngay_het_hieu_luc": None,
                    "loai_tac_dong": "THAY_THE_BOI",
                    "id_duoc_tac_dong": "Luat_HoTich_2014_Dieu_18",
                },
                {
                    "id": "Luat_HoTich_2026_Dieu_16_Khoan_1",
                    "noidung": "Khoản 1",
                    "cap_bac": 1,
                    "ngay_ban_hanh": "2026-04-23",
                    "ngay_hieu_luc": "2027-03-01",
                    "ngay_het_hieu_luc": None,
                    "loai_tac_dong": "THAY_THE_BOI",
                    "id_duoc_tac_dong": "Luat_HoTich_2014_Dieu_18",
                },
            ],
        }
    )
    payload = build_validity_warning_payload(bundle)
    assert payload is not None
    future = payload["future_rows"]
    assert len(future) == 1
    assert future[0]["source_id"] == "Luat_HoTich_2026_Dieu_16"
    assert future[0]["impact_type"] == "Thay thế"
    assert future[0]["issued_date"] == "23-04-2026"
    assert future[0]["content_url"] == "https://example.test/dieu-16"


def test_future_rows_shown_when_user_provided_historical_date():
    bundle = _bundle(
        {
            "can_cu_sap_hieu_luc": [
                {
                    "id": "NghiDinh_109_2026_ND_CP_Dieu_61",
                    "noidung": "Phạt tiền tảo hôn",
                    "cap_bac": 5,
                    "ngay_ban_hanh": "2026-04-01",
                    "ngay_hieu_luc": "2026-06-01",
                    "ngay_het_hieu_luc": None,
                    "loai_tac_dong": "THAY_THE_BOI",
                    "id_duoc_tac_dong": "NghiDinh_82_2020_ND_CP_Dieu_58",
                }
            ],
        },
        target_date="2021-12-31",
        is_user_provided_date=True,
    )
    payload = build_validity_warning_payload(bundle)
    assert payload is not None
    assert len(payload["future_rows"]) == 1
    assert payload["future_rows"][0]["source_id"] == "NghiDinh_109_2026_ND_CP_Dieu_61"


def test_future_rows_excludes_het_hieu_luc():
    bundle = _bundle(
        {
            "can_cu_sap_hieu_luc": [
                {
                    "id": "Luat_Test_2026_Dieu_1",
                    "noidung": "Hết HL",
                    "cap_bac": 1,
                    "ngay_ban_hanh": "2026-01-01",
                    "ngay_hieu_luc": "2027-01-01",
                    "loai_tac_dong": "HET_HIEU_LUC",
                    "id_duoc_tac_dong": "Luat_Test_2014_Dieu_1",
                }
            ],
        }
    )
    payload = build_validity_warning_payload(bundle)
    assert payload is None


def test_conflict_payload_includes_source_content():
    bundle = _bundle(
        {
            "can_cu_chinh": [
                {
                    "id_goc_tu_router": "Luat_A_Dieu_1",
                    "id_thuc_te_ap_dung": "Luat_A_Dieu_1",
                    "noidung": "Nội dung nguồn",
                    "cap_bac": 1,
                    "het_hieu_luc": False,
                    "ngay_hieu_luc": "2015-01-01",
                    "ngay_het_hieu_luc": None,
                }
            ],
            "can_cu_mau_thuan": [
                {
                    "id_nguon": "Luat_A_Dieu_1",
                    "id_dich": "Luat_B_Dieu_2",
                    "noidung_giai_thich": "Mâu thuẫn kiểm thử",
                    "noidung_dich": "Nội dung đích",
                    "cap_bac": 1,
                }
            ],
        }
    )
    metadata = build_legal_warning_metadata([bundle])
    assert metadata is not None
    item = metadata["conflict"]["items"][0]
    assert item["summary"] == "Mâu thuẫn kiểm thử"
    assert item["details"][0]["content"] == "Nội dung nguồn"
    assert item["details"][1]["content"] == "Nội dung đích"


def test_replacement_relations_round_trip():
    context = {
        "can_cu_chinh": [],
        "lien_ket_hien_hanh": [
            {
                "id_hien_hanh": "Luat_Moi_Dieu_1",
                "id_duoc_thay_the": "Luat_Cu_Dieu_1",
            }
        ],
    }
    bundle = _bundle(context)
    assert bundle["replacement_relations"] == [
        {"id_hien_hanh": "Luat_Moi_Dieu_1", "id_duoc_thay_the": "Luat_Cu_Dieu_1"}
    ]
    restored = legal_context_bundle_to_context_tho(bundle)
    assert restored["lien_ket_hien_hanh"] == bundle["replacement_relations"]

    merged = merge_legal_context_bundles([bundle, bundle])
    assert len(merged["replacement_relations"]) == 1
