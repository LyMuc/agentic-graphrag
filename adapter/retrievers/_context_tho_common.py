"""Cypher snippets dùng chung cho Context_Tho — văn bản sắp có hiệu lực."""

from __future__ import annotations

# Sửa điều kiện hien_hanh (2 biến thể trong codebase)
_HIEN_HANH_OLD_SIMPLE = """    OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAY_THE_BOI*1..]->(hien_hanh)
    WHERE hien_hanh.ngay_het_hieu_luc IS NULL"""

_HIEN_HANH_NEW_SIMPLE = """    OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAY_THE_BOI*1..]->(hien_hanh)
    WHERE hien_hanh.ngay_co_hieu_luc <= $target_date
    AND hien_hanh.ngay_het_hieu_luc IS NULL"""

_HIEN_HANH_OLD_V3 = """OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAY_THE_BOI*1..]->(hien_hanh)
  WHERE hien_hanh.ngay_het_hieu_luc IS NULL
    AND hien_hanh.id <> chi_tiet_ap_dung.id"""

_HIEN_HANH_NEW_V3 = """OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAY_THE_BOI*1..]->(hien_hanh)
  WHERE hien_hanh.ngay_co_hieu_luc <= $target_date
    AND hien_hanh.ngay_het_hieu_luc IS NULL
    AND hien_hanh.id <> chi_tiet_ap_dung.id"""

FUTURE_EFFECTIVE_MATCH_CYPHER = """
    // 8. VĂN BẢN ĐÃ BAN HÀNH, CHƯA CÓ HIỆU LỰC (sắp tác động tới căn cứ hiện hành)
    OPTIONAL MATCH (chi_tiet_ap_dung)-[:DUOC_SUA_DOI_BOI]->(sua_doi_sap)
    WHERE sua_doi_sap.ngay_co_hieu_luc > $target_date

    OPTIONAL MATCH (chi_tiet_ap_dung)-[:HUONG_DAN_BOI]->(hd_sap)
    WHERE hd_sap.ngay_co_hieu_luc > $target_date

    OPTIONAL MATCH (hd_sap)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_hd_sap)
    WHERE chi_tiet_hd_sap.ngay_co_hieu_luc > $target_date

    OPTIONAL MATCH (chi_tiet_huong_dan)-[:DUOC_SUA_DOI_BOI]->(sua_hd_sap)
    WHERE sua_hd_sap.ngay_co_hieu_luc > $target_date

    OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAY_THE_BOI*1..]->(thay_the_sap)
    WHERE thay_the_sap.ngay_co_hieu_luc > $target_date

    OPTIONAL MATCH (thay_the_sap)-[:CO_KHOAN|CO_DIEM*1..2]->(chi_tiet_thay_the_sap)
    WHERE chi_tiet_thay_the_sap.ngay_co_hieu_luc > $target_date

    OPTIONAL MATCH (chi_tiet_ap_dung)-[:BAI_BO_BOI*1..]->(bai_bo_sap)
    WHERE bai_bo_sap.ngay_co_hieu_luc > $target_date
"""

FUTURE_EFFECTIVE_MATCH_CYPHER_V3 = """
// 8b. VĂN BẢN ĐÃ BAN HÀNH, CHƯA CÓ HIỆU LỰC
OPTIONAL MATCH (chi_tiet_ap_dung)-[:DUOC_SUA_DOI_BOI]->(sua_doi_sap)
  WHERE sua_doi_sap.ngay_co_hieu_luc > $target_date

OPTIONAL MATCH (chi_tiet_ap_dung)-[:HUONG_DAN_BOI]->(hd_sap)
  WHERE hd_sap.ngay_co_hieu_luc > $target_date

OPTIONAL MATCH (hd_sap)-[:CO_KHOAN|CO_DIEM*1..2]->(chi_tiet_hd_sap)
  WHERE chi_tiet_hd_sap.ngay_co_hieu_luc > $target_date

OPTIONAL MATCH (chi_tiet_huong_dan)-[:DUOC_SUA_DOI_BOI]->(sua_hd_sap)
  WHERE sua_hd_sap.ngay_co_hieu_luc > $target_date

OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAY_THE_BOI*1..]->(thay_the_sap)
  WHERE thay_the_sap.ngay_co_hieu_luc > $target_date

OPTIONAL MATCH (thay_the_sap)-[:CO_KHOAN|CO_DIEM*1..2]->(chi_tiet_thay_the_sap)
  WHERE chi_tiet_thay_the_sap.ngay_co_hieu_luc > $target_date

OPTIONAL MATCH (chi_tiet_ap_dung)-[:BAI_BO_BOI*1..]->(bai_bo_sap)
  WHERE bai_bo_sap.ngay_co_hieu_luc > $target_date
"""

_SAP_HIEU_LUC_ITEM_FIELDS = """            id: {id_expr},
            noidung: {noidung_expr},
            cap_bac: {cap_bac_expr},
            ngay_ban_hanh: {ngay_ban_hanh_expr},
            ngay_hieu_luc: {ngay_hieu_luc_expr},
            ngay_het_hieu_luc: {ngay_het_hieu_luc_expr},
            loai_tac_dong: '{loai_tac_dong}',
            id_duoc_tac_dong: {id_duoc_tac_dong_expr}"""

RETURN_SAP_HIEU_LUC_FIELDS = """,
        can_cu_sap_hieu_luc: [item IN (
            collect(DISTINCT {
""" + _SAP_HIEU_LUC_ITEM_FIELDS.format(
    id_expr="sua_doi_sap.id",
    noidung_expr="sua_doi_sap.noidung",
    cap_bac_expr="sua_doi_sap.cap_bac_phap_ly",
    ngay_ban_hanh_expr="sua_doi_sap.ngay_ban_hanh",
    ngay_hieu_luc_expr="sua_doi_sap.ngay_co_hieu_luc",
    ngay_het_hieu_luc_expr="sua_doi_sap.ngay_het_hieu_luc",
    loai_tac_dong="SUA_DOI_BOI",
    id_duoc_tac_dong_expr="chi_tiet_ap_dung.id",
) + """
            })
            + collect(DISTINCT {
""" + _SAP_HIEU_LUC_ITEM_FIELDS.format(
    id_expr="coalesce(chi_tiet_hd_sap.id, hd_sap.id)",
    noidung_expr="coalesce(chi_tiet_hd_sap.noidung, hd_sap.noidung)",
    cap_bac_expr="coalesce(chi_tiet_hd_sap.cap_bac_phap_ly, hd_sap.cap_bac_phap_ly)",
    ngay_ban_hanh_expr="coalesce(chi_tiet_hd_sap.ngay_ban_hanh, hd_sap.ngay_ban_hanh)",
    ngay_hieu_luc_expr="coalesce(chi_tiet_hd_sap.ngay_co_hieu_luc, hd_sap.ngay_co_hieu_luc)",
    ngay_het_hieu_luc_expr="coalesce(chi_tiet_hd_sap.ngay_het_hieu_luc, hd_sap.ngay_het_hieu_luc)",
    loai_tac_dong="HUONG_DAN_BOI",
    id_duoc_tac_dong_expr="chi_tiet_ap_dung.id",
) + """
            })
            + collect(DISTINCT {
""" + _SAP_HIEU_LUC_ITEM_FIELDS.format(
    id_expr="sua_hd_sap.id",
    noidung_expr="sua_hd_sap.noidung",
    cap_bac_expr="sua_hd_sap.cap_bac_phap_ly",
    ngay_ban_hanh_expr="sua_hd_sap.ngay_ban_hanh",
    ngay_hieu_luc_expr="sua_hd_sap.ngay_co_hieu_luc",
    ngay_het_hieu_luc_expr="sua_hd_sap.ngay_het_hieu_luc",
    loai_tac_dong="SUA_DOI_HUONG_DAN",
    id_duoc_tac_dong_expr="coalesce(chi_tiet_huong_dan.id, huong_dan.id, chi_tiet_ap_dung.id)",
) + """
            })
            + collect(DISTINCT {
""" + _SAP_HIEU_LUC_ITEM_FIELDS.format(
    id_expr="thay_the_sap.id",
    noidung_expr="thay_the_sap.noidung",
    cap_bac_expr="thay_the_sap.cap_bac_phap_ly",
    ngay_ban_hanh_expr="thay_the_sap.ngay_ban_hanh",
    ngay_hieu_luc_expr="thay_the_sap.ngay_co_hieu_luc",
    ngay_het_hieu_luc_expr="thay_the_sap.ngay_het_hieu_luc",
    loai_tac_dong="THAY_THE",
    id_duoc_tac_dong_expr="chi_tiet_ap_dung.id",
) + """
            })
            + collect(DISTINCT CASE WHEN chi_tiet_thay_the_sap IS NOT NULL THEN {
                id: chi_tiet_thay_the_sap.id,
                noidung: chi_tiet_thay_the_sap.noidung,
                cap_bac: chi_tiet_thay_the_sap.cap_bac_phap_ly,
                ngay_ban_hanh: chi_tiet_thay_the_sap.ngay_ban_hanh,
                ngay_hieu_luc: chi_tiet_thay_the_sap.ngay_co_hieu_luc,
                ngay_het_hieu_luc: chi_tiet_thay_the_sap.ngay_het_hieu_luc,
                loai_tac_dong: 'THAY_THE',
                id_duoc_tac_dong: chi_tiet_ap_dung.id
            } END)
            + collect(DISTINCT {
""" + _SAP_HIEU_LUC_ITEM_FIELDS.format(
    id_expr="bai_bo_sap.id",
    noidung_expr="bai_bo_sap.noidung",
    cap_bac_expr="bai_bo_sap.cap_bac_phap_ly",
    ngay_ban_hanh_expr="bai_bo_sap.ngay_ban_hanh",
    ngay_hieu_luc_expr="bai_bo_sap.ngay_co_hieu_luc",
    ngay_het_hieu_luc_expr="bai_bo_sap.ngay_het_hieu_luc",
    loai_tac_dong="BAI_BO",
    id_duoc_tac_dong_expr="chi_tiet_ap_dung.id",
) + """
            })
            + collect(DISTINCT CASE WHEN chi_tiet_ap_dung.ngay_het_hieu_luc > $target_date THEN {
                id: chi_tiet_ap_dung.id,
                noidung: chi_tiet_ap_dung.noidung,
                cap_bac: chi_tiet_ap_dung.cap_bac_phap_ly,
                ngay_ban_hanh: chi_tiet_ap_dung.ngay_ban_hanh,
                ngay_hieu_luc: chi_tiet_ap_dung.ngay_co_hieu_luc,
                ngay_het_hieu_luc: chi_tiet_ap_dung.ngay_het_hieu_luc,
                loai_tac_dong: 'HET_HIEU_LUC',
                id_duoc_tac_dong: chi_tiet_ap_dung.id
            } END)
        ) WHERE item.id IS NOT NULL],
        lien_ket_sap_hieu_luc: [pair IN (
            collect(DISTINCT {id_van_ban: sua_doi_sap.id, id_duoc_tac_dong: chi_tiet_ap_dung.id, loai_tac_dong: 'SUA_DOI_BOI'})
            + collect(DISTINCT {id_van_ban: coalesce(chi_tiet_hd_sap.id, hd_sap.id), id_duoc_tac_dong: chi_tiet_ap_dung.id, loai_tac_dong: 'HUONG_DAN_BOI'})
            + collect(DISTINCT {id_van_ban: sua_hd_sap.id, id_duoc_tac_dong: coalesce(chi_tiet_huong_dan.id, huong_dan.id), loai_tac_dong: 'SUA_DOI_HUONG_DAN'})
            + collect(DISTINCT {id_van_ban: thay_the_sap.id, id_duoc_tac_dong: chi_tiet_ap_dung.id, loai_tac_dong: 'THAY_THE'})
            + collect(DISTINCT {id_van_ban: bai_bo_sap.id, id_duoc_tac_dong: chi_tiet_ap_dung.id, loai_tac_dong: 'BAI_BO'})
            + collect(DISTINCT CASE WHEN chi_tiet_ap_dung.ngay_het_hieu_luc > $target_date THEN {
                id_van_ban: chi_tiet_ap_dung.id, id_duoc_tac_dong: chi_tiet_ap_dung.id, loai_tac_dong: 'HET_HIEU_LUC'
            } END)
        ) WHERE pair.id_van_ban IS NOT NULL AND pair.id_duoc_tac_dong IS NOT NULL]"""


def enhance_domain_retriever_cypher(cypher: str) -> str:
    """Inject văn bản sắp hiệu lực vào Cypher domain retriever chuẩn."""
    if "can_cu_sap_hieu_luc" in cypher:
        return cypher

    out = cypher.replace(_HIEN_HANH_OLD_SIMPLE, _HIEN_HANH_NEW_SIMPLE)
    if "    RETURN {" not in out:
        raise ValueError("Cypher domain retriever thiếu marker '    RETURN {'")
    out = out.replace("    RETURN {", FUTURE_EFFECTIVE_MATCH_CYPHER + "\n    RETURN {", 1)
    marker = "    } AS Context_Tho"
    if marker not in out:
        raise ValueError("Cypher domain retriever thiếu marker '} AS Context_Tho'")
    out = out.replace(marker, RETURN_SAP_HIEU_LUC_FIELDS + "\n" + marker, 1)
    return out
