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

# --- Tham chiếu bổ trợ: heading Điều/Khoản cha khi THAM_CHIEU_DEN trỏ tới Khoản/Điểm ---
_TC_HL = (
    "{node}.ngay_co_hieu_luc <= $target_date "
    "AND ({node}.ngay_het_hieu_luc IS NULL OR {node}.ngay_het_hieu_luc > $target_date)"
)


def _ancestor_match_for_seed(seed: str, prefix: str, indent: str = "    ") -> str:
    """OPTIONAL MATCH đi ngược CO_KHOAN/CO_DIEM từ node tham chiếu."""
    i = indent
    dieu, khoan, ong = f"dieu_cha_{prefix}", f"khoan_cha_{prefix}", f"dieu_ong_{prefix}"
    hl = _TC_HL
    return f"""
{i}// Heading cha — {seed}
{i}OPTIONAL MATCH ({dieu})-[:CO_KHOAN]->({seed})
{i}  WHERE {seed} IS NOT NULL
{i}    AND {hl.format(node=dieu)}
{i}OPTIONAL MATCH ({khoan})-[:CO_DIEM]->({seed})
{i}  WHERE {seed} IS NOT NULL
{i}    AND {hl.format(node=khoan)}
{i}OPTIONAL MATCH ({ong})-[:CO_KHOAN]->({khoan})
{i}  WHERE {khoan} IS NOT NULL
{i}    AND {hl.format(node=ong)}"""


def _bo_tro_collect_domain(node: str) -> str:
    return f""" + collect(DISTINCT {{
            id: {node}.id,
            noidung: {node}.noidung,
            cap_bac: {node}.cap_bac_phap_ly,
            ngay_hieu_luc: {node}.ngay_co_hieu_luc,
            ngay_het_hieu_luc: {node}.ngay_het_hieu_luc
        }})"""


def _ancestor_collects_for_prefix(prefix: str) -> str:
    dieu, khoan, ong = f"dieu_cha_{prefix}", f"khoan_cha_{prefix}", f"dieu_ong_{prefix}"
    return (
        _bo_tro_collect_domain(dieu)
        + _bo_tro_collect_domain(khoan)
        + _bo_tro_collect_domain(ong)
    )


THAM_CHIEU_ANCESTOR_MATCH_DOMAIN = (
    "\n    // 7b. Heading cha cho tham chiếu (đi ngược CO_KHOAN/CO_DIEM)"
    + _ancestor_match_for_seed("luat_tham_chieu", "ltc")
    + _ancestor_match_for_seed("chi_tiet_tham_chieu", "ctt")
)

THAM_CHIEU_ANCESTOR_MATCH_HD_DOMAIN = (
    "\n    // 8b. Heading cha cho tham chiếu từ hướng dẫn"
    + _ancestor_match_for_seed("luat_tham_chieu_tu_hd", "ltc_hd")
    + _ancestor_match_for_seed("chi_tiet_tc_tu_hd", "ctt_hd")
)

THAM_CHIEU_ANCESTOR_COLLECT_DOMAIN = (
    _ancestor_collects_for_prefix("ltc")
    + _ancestor_collects_for_prefix("ctt")
)

THAM_CHIEU_ANCESTOR_COLLECT_HD_DOMAIN = (
    _ancestor_collects_for_prefix("ltc_hd")
    + _ancestor_collects_for_prefix("ctt_hd")
)

_MARKER_BO_TRO_BEFORE_LIEN_KET = """            ngay_het_hieu_luc: chi_tiet_tham_chieu.ngay_het_hieu_luc
        }),
        lien_ket_huong_dan:"""

_MARKER_BO_TRO_HD_BEFORE_LIEN_KET = """            ngay_het_hieu_luc: chi_tiet_tc_tu_hd.ngay_het_hieu_luc
        }),
        lien_ket_huong_dan:"""


def _bo_tro_collect_v3(node: str) -> str:
    return f"""  collect(DISTINCT {{
    id: {node}.id,
    noidung: {node}.noidung,
    cap_bac: {node}.cap_bac_phap_ly,
    ngay_hieu_luc: {node}.ngay_co_hieu_luc,
    ngay_het_hieu_luc: {node}.ngay_het_hieu_luc
  }})"""


def tham_chieu_ancestor_collect_parts_v3() -> str:
    """Các collect DISTINCT cho WITH V3 (gom vào tc_all)."""
    parts = []
    for prefix in ("ltc", "ctt", "ltc_hd", "ctt_hd"):
        for role in ("dieu_cha", "khoan_cha", "dieu_ong"):
            var = f"{role}_{prefix}" if role != "dieu_ong" else f"dieu_ong_{prefix}"
            parts.append(_bo_tro_collect_v3(var))
    return "\n    + ".join(parts) if parts else ""


THAM_CHIEU_ANCESTOR_MATCH_V3 = (
    "\n// 7b-8b. Heading cha cho tham chiếu (đi ngược CO_KHOAN/CO_DIEM)"
    + _ancestor_match_for_seed("luat_tham_chieu", "ltc", indent="")
    + _ancestor_match_for_seed("chi_tiet_tham_chieu", "ctt", indent="")
    + _ancestor_match_for_seed("luat_tham_chieu_tu_hd", "ltc_hd", indent="")
    + _ancestor_match_for_seed("chi_tiet_tc_tu_hd", "ctt_hd", indent="")
)


def enhance_domain_retriever_cypher(cypher: str) -> str:
    """Inject văn bản sắp hiệu lực + heading cha tham chiếu vào Cypher domain retriever."""
    if "can_cu_sap_hieu_luc" in cypher:
        return cypher

    out = cypher.replace(_HIEN_HANH_OLD_SIMPLE, _HIEN_HANH_NEW_SIMPLE)
    if "    RETURN {" not in out:
        raise ValueError("Cypher domain retriever thiếu marker '    RETURN {'")

    if "// 7b. Heading cha cho tham chiếu" not in out:
        ancestor_match = THAM_CHIEU_ANCESTOR_MATCH_DOMAIN
        if "luat_tham_chieu_tu_hd" in out:
            ancestor_match += THAM_CHIEU_ANCESTOR_MATCH_HD_DOMAIN
        out = out.replace("    RETURN {", ancestor_match + "\n    RETURN {", 1)

        if "luat_tham_chieu_tu_hd" in out and _MARKER_BO_TRO_HD_BEFORE_LIEN_KET in out:
            out = out.replace(
                _MARKER_BO_TRO_HD_BEFORE_LIEN_KET,
                _MARKER_BO_TRO_HD_BEFORE_LIEN_KET.replace(
                    "        }),\n        lien_ket_huong_dan:",
                    "        })"
                    + THAM_CHIEU_ANCESTOR_COLLECT_DOMAIN
                    + THAM_CHIEU_ANCESTOR_COLLECT_HD_DOMAIN
                    + ",\n        lien_ket_huong_dan:",
                ),
                1,
            )
        elif _MARKER_BO_TRO_BEFORE_LIEN_KET in out:
            out = out.replace(
                _MARKER_BO_TRO_BEFORE_LIEN_KET,
                _MARKER_BO_TRO_BEFORE_LIEN_KET.replace(
                    "        }),\n        lien_ket_huong_dan:",
                    "        })"
                    + THAM_CHIEU_ANCESTOR_COLLECT_DOMAIN
                    + ",\n        lien_ket_huong_dan:",
                ),
                1,
            )

    out = out.replace("    RETURN {", FUTURE_EFFECTIVE_MATCH_CYPHER + "\n    RETURN {", 1)
    marker = "    } AS Context_Tho"
    if marker not in out:
        raise ValueError("Cypher domain retriever thiếu marker '} AS Context_Tho'")
    out = out.replace(marker, RETURN_SAP_HIEU_LUC_FIELDS + "\n" + marker, 1)
    return out
