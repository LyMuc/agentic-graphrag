from __future__ import annotations

from unittest.mock import patch

from application.legal_context import (
    build_legal_context_bundle,
    decode_legal_context_bundle,
    encode_legal_context_bundle,
    merge_legal_context_bundles,
    process_context_strings,
)


def _context(
    *,
    main: list[dict] | None = None,
    guidance: list[dict] | None = None,
    support: list[dict] | None = None,
    guidance_relations: list[dict] | None = None,
    future: list[dict] | None = None,
    future_relations: list[dict] | None = None,
    conflicts: list[dict] | None = None,
    replacements: list[str] | None = None,
    replacement_relations: list[dict] | None = None,
) -> dict:
    """Build a minimal renderer-compatible Context_Tho test fixture.

    Args:
        main: Main legal provisions.
        guidance: Guidance provisions.
        support: Supporting cross-references.
        guidance_relations: Guidance-to-main relation dictionaries.
        future: Future-effective provisions.
        future_relations: Future-effect relation dictionaries.
        conflicts: Legal conflict annotations.
        replacements: Current-law replacement provision IDs.

    Returns:
        A Context_Tho dictionary with all expected collection keys.
    """

    return {
        "can_cu_chinh": main or [],
        "can_cu_huong_dan": guidance or [],
        "can_cu_bo_tro": support or [],
        "lien_ket_huong_dan": guidance_relations or [],
        "can_cu_sap_hieu_luc": future or [],
        "lien_ket_sap_hieu_luc": future_relations or [],
        "can_cu_mau_thuan": conflicts or [],
        "quy_dinh_hien_hanh_doi_chieu": replacements or [],
        "lien_ket_hien_hanh": replacement_relations or [],
    }


def _main_item(
    provision_id: str,
    *,
    amendment_id: str | None = None,
    effective_from: str = "2015-01-01",
    effective_until: str | None = None,
) -> dict:
    """Build one main-provision fixture.

    Args:
        provision_id: Legal node ID.
        amendment_id: Optional amending provision ID.
        effective_from: Provision effective date.
        effective_until: Optional expiry date.

    Returns:
        Main provision dictionary matching template Cypher output.
    """

    return {
        "id_goc_tu_router": provision_id,
        "id_thuc_te_ap_dung": provision_id,
        "noidung": f"Nội dung {provision_id}",
        "cap_bac": 1,
        "het_hieu_luc": bool(effective_until),
        "ngay_hieu_luc": effective_from,
        "ngay_het_hieu_luc": effective_until,
        "id_sua_doi": amendment_id,
        "noidung_sua_doi": f"Nội dung sửa đổi {amendment_id}" if amendment_id else None,
        "ngay_hieu_luc_sua_doi": "2025-07-01" if amendment_id else None,
        "ngay_het_hieu_luc_sua_doi": None,
    }


def _secondary_item(provision_id: str, rank: int = 2) -> dict:
    """Build a guidance/support provision fixture.

    Args:
        provision_id: Legal node ID.
        rank: Legal hierarchy rank used by the renderer.

    Returns:
        Provision dictionary matching guidance/support Cypher output.
    """

    return {
        "id": provision_id,
        "noidung": f"Nội dung {provision_id}",
        "cap_bac": rank,
        "ngay_hieu_luc": "2015-01-01",
        "ngay_het_hieu_luc": None,
    }


def _bundle(context_tho: dict, template: str, target_date: str = "2026-06-11") -> dict:
    """Build a bundle fixture without querying Neo4j citation links.

    Args:
        context_tho: Source Context_Tho fixture.
        template: Template provenance name.
        target_date: Applicable legal date.

    Returns:
        LegalContextBundle dictionary.
    """

    return build_legal_context_bundle(
        context_tho,
        target_date,
        False,
        retriever_name="test_retriever",
        template_name=template,
        citation_links={"Luat_HNGD_2014_Dieu_8": "https://example.test/dieu-8"},
    )


def test_role_priority_dedupes_main_support_and_preserves_provenance():
    """Verify main provisions outrank support duplicates and retain sources."""

    main_bundle = _bundle(
        _context(main=[_main_item("Luat_HNGD_2014_Dieu_8")]),
        "main_template",
    )
    support_bundle = _bundle(
        _context(support=[_secondary_item("Luat_HNGD_2014_Dieu_8")]),
        "support_template",
    )

    merged = merge_legal_context_bundles([support_bundle, main_bundle])

    assert len(merged["provisions"]) == 1
    assert merged["provisions"][0]["role"] == "main"
    assert {p["template"] for p in merged["provisions"][0]["provenance"]} == {
        "main_template",
        "support_template",
    }


def test_guidance_support_promotes_guidance_without_losing_relation():
    """Verify guidance outranks support without deleting its legal relation."""

    guidance_id = "NghiDinh_126_2014_ND_CP_Dieu_3"
    support_bundle = _bundle(
        _context(support=[_secondary_item(guidance_id)]),
        "support_template",
    )
    guidance_bundle = _bundle(
        _context(
            guidance=[_secondary_item(guidance_id)],
            guidance_relations=[
                {
                    "id_huong_dan": guidance_id,
                    "id_duoc_huong_dan": "Luat_HNGD_2014_Dieu_8",
                }
            ],
        ),
        "guidance_template",
    )

    merged = merge_legal_context_bundles([support_bundle, guidance_bundle])

    assert merged["provisions"][0]["role"] == "guidance"
    assert len(merged["guidance_relations"]) == 1


def test_different_amendments_and_dates_are_not_merged():
    """Verify amendment versions and different temporal scopes remain separate."""

    original = _bundle(
        _context(main=[_main_item("Luat_HNGD_2014_Dieu_8")]),
        "original",
    )
    amended = _bundle(
        _context(
            main=[
                _main_item(
                    "Luat_HNGD_2014_Dieu_8",
                    amendment_id="Luat_SuaDoi_2025_Dieu_1",
                )
            ]
        ),
        "amended",
    )

    merged = merge_legal_context_bundles([original, amended])
    pipeline = process_context_strings(
        [
            encode_legal_context_bundle(original),
            encode_legal_context_bundle(
                _bundle(
                    _context(main=[_main_item("Luat_HNGD_2014_Dieu_8")]),
                    "historical",
                    target_date="2020-01-01",
                )
            ),
        ]
    )

    assert len(merged["provisions"]) == 2
    assert len(pipeline.bundles) == 2


def test_relations_conflicts_future_and_replacements_are_deduplicated():
    """Verify non-provision legal annotations are deduplicated safely."""

    future_item = {
        "id": "Luat_HoTich_2026_Dieu_16",
        "noidung": "Nội dung tương lai",
        "cap_bac": 1,
        "ngay_ban_hanh": "2026-04-01",
        "ngay_hieu_luc": "2027-01-01",
        "ngay_het_hieu_luc": None,
        "loai_tac_dong": "THAY_THE",
        "id_duoc_tac_dong": "Luat_HoTich_2014_Dieu_37",
    }
    conflict = {
        "id_nguon": "Luat_A_Dieu_1",
        "id_dich": "Luat_B_Dieu_2",
        "noidung_giai_thich": "Mâu thuẫn kiểm thử",
        "noidung_dich": "Nội dung B",
        "cap_bac": 1,
    }
    context = _context(
        future=[future_item],
        future_relations=[
            {
                "id_van_ban": future_item["id"],
                "id_duoc_tac_dong": future_item["id_duoc_tac_dong"],
                "loai_tac_dong": "THAY_THE",
            }
        ],
        conflicts=[conflict],
        replacements=["Luat_Moi_Dieu_1"],
    )

    merged = merge_legal_context_bundles(
        [_bundle(context, "one"), _bundle(context, "two")]
    )

    assert len(merged["future_relations"]) == 1
    assert merged["future_relations"][0]["provision"]["content"] == "Nội dung tương lai"
    assert len(merged["conflicts"]) == 1
    assert merged["replacement_ids"] == ["Luat_Moi_Dieu_1"]


def test_replacement_relations_encode_and_merge():
    """Verify lien_ket_hien_hanh survives bundle encode/merge."""

    relation = {
        "id_hien_hanh": "NghiDinh_109_2026_ND_CP_Dieu_61",
        "id_duoc_thay_the": "NghiDinh_82_2020_ND_CP_Dieu_58",
    }
    context = _context(replacement_relations=[relation])
    bundle = _bundle(context, "replacement_template")

    assert bundle["replacement_relations"] == [relation]

    merged = merge_legal_context_bundles([bundle, bundle])
    assert merged["replacement_relations"] == [relation]


@patch("server.domain.legal.codec._fetch_provision_effective_dates")
def test_build_bundle_attaches_replacement_provisions(mock_fetch):
    mock_fetch.return_value = {"NghiDinh_109_2026_ND_CP_Dieu_61": "2026-05-18"}
    context = _context(
        main=[
            {
                "id_goc_tu_router": "NghiDinh_82_2020_ND_CP_Dieu_58",
                "id_thuc_te_ap_dung": "NghiDinh_82_2020_ND_CP_Dieu_58",
                "noidung": "Cũ",
                "cap_bac": 5,
                "het_hieu_luc": True,
                "ngay_hieu_luc": "2020-09-01",
                "ngay_het_hieu_luc": "2026-05-18",
            }
        ],
        replacements=["NghiDinh_109_2026_ND_CP_Dieu_61"],
        replacement_relations=[
            {
                "id_hien_hanh": "NghiDinh_109_2026_ND_CP_Dieu_61",
                "id_duoc_thay_the": "NghiDinh_82_2020_ND_CP_Dieu_58",
            }
        ],
    )
    bundle = build_legal_context_bundle(
        context,
        "2021-12-31",
        True,
        retriever_name="xu_phat_vi_pham",
        template_name="tao_hon",
        citation_links={},
    )
    replacement = [
        p for p in bundle["provisions"] if p.get("role") == "replacement"
    ]
    assert len(replacement) == 1
    assert replacement[0]["id"] == "NghiDinh_109_2026_ND_CP_Dieu_61"
    assert replacement[0]["effective_from"] == "2026-05-18"
    mock_fetch.assert_called_once()


def test_pipeline_renders_bundle_and_keeps_legacy_context():
    """Verify merged bundles render while unparseable legacy text is preserved."""

    encoded = encode_legal_context_bundle(
        _bundle(
            _context(main=[_main_item("Luat_HNGD_2014_Dieu_8")]),
            "template",
        )
    )

    pipeline = process_context_strings([encoded, "Legacy context không parse."])

    assert decode_legal_context_bundle(pipeline.encoded_contexts[0]) is not None
    assert pipeline.legacy_contexts == ["Legacy context không parse."]
    assert pipeline.rendered_text.count("Luat_HNGD_2014_Dieu_8") >= 1
    assert pipeline.rendered_text.count("Nội dung Luat_HNGD_2014_Dieu_8") == 1
    assert "https://example.test/dieu-8" in pipeline.rendered_text
