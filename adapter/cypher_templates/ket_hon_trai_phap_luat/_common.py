"""Common Cypher snippets + helpers cho topic Kết hôn trái pháp luật (Đ3 K6, Đ10-12 + TTLT 01/2016)."""
from __future__ import annotations

from adapter.retrievers._context_tho_common import (
    ANCESTOR_REPLACEMENT_EXPAND_KG,
    FUTURE_EFFECTIVE_MATCH_CYPHER_KG,
    MAU_THUAN_MATCH_KG,
    THAM_CHIEU_ANCESTOR_MATCH_KG,
    tham_chieu_ancestor_collect_parts,
    tham_chieu_ancestor_with_vars,
)

TOPIC = "ket_hon_trai_phap_luat"
TOPIC_LABEL = "KetHonTraiPhapLuat"

SEMANTIC_TO_LEGAL_TAIL = """
WITH wl, leaf_seed_nodes
UNWIND leaf_seed_nodes AS sn
WITH wl, sn WHERE sn IS NOT NULL

OPTIONAL MATCH (sn)-[:CAN_CU_TAI]->(luat_semantic)
WHERE luat_semantic IS NOT NULL

OPTIONAL MATCH (luat_whitelist:DieuLuat)
WHERE luat_whitelist.id IN wl

WITH collect(DISTINCT luat_semantic) + collect(DISTINCT luat_whitelist) AS all_seeds
UNWIND all_seeds AS n_goc
WITH DISTINCT n_goc
WHERE n_goc IS NOT NULL
"""

EXPAND_AND_TIMEFILTER_CYPHER = """
// ============================================================
// PHẦN 2 — VÉT CẤU TRÚC + TIME-AWARE
// ============================================================
WITH collect(DISTINCT n_goc) AS goc_nodes
WITH goc_nodes, [n IN goc_nodes WHERE 'DieuLuat' IN labels(n) | n.id] AS dieu_seed_ids
UNWIND goc_nodes AS n_goc

WITH n_goc, dieu_seed_ids,
  CASE
    WHEN 'DieuLuat' IN labels(n_goc) THEN 'dieu'
    WHEN 'DieuKhoanLuat' IN labels(n_goc) THEN 'khoan'
    WHEN 'DieuKhoanDiemLuat' IN labels(n_goc) THEN 'diem'
    ELSE 'other'
  END AS cap_do_seed

OPTIONAL MATCH (n_goc)-[:CO_KHOAN]->(khoan_con) WHERE cap_do_seed = 'dieu'
OPTIONAL MATCH (khoan_con)-[:CO_DIEM]->(diem_tu_khoan) WHERE cap_do_seed = 'dieu'
OPTIONAL MATCH (n_goc)-[:CO_DIEM]->(diem_con) WHERE cap_do_seed = 'khoan'

OPTIONAL MATCH (dieu_cha)-[:CO_KHOAN]->(n_goc) WHERE cap_do_seed IN ['khoan', 'diem']
OPTIONAL MATCH (khoan_cha)-[:CO_DIEM]->(n_goc) WHERE cap_do_seed = 'diem'
OPTIONAL MATCH (dieu_ong)-[:CO_KHOAN]->(khoan_cha) WHERE cap_do_seed = 'diem'

WITH n_goc, dieu_seed_ids,
  [x IN [n_goc]
      + collect(DISTINCT khoan_con)
      + collect(DISTINCT diem_tu_khoan)
      + collect(DISTINCT diem_con)
    WHERE x IS NOT NULL] AS chi_tiet_desc,
  [x IN collect(DISTINCT dieu_cha)
      + collect(DISTINCT khoan_cha)
      + collect(DISTINCT dieu_ong)
    WHERE x IS NOT NULL] AS chi_tiet_anc

UNWIND chi_tiet_desc AS chi_tiet_goc
OPTIONAL MATCH (chi_tiet_goc)-[:THAY_THE_BOI*0..]->(chi_tiet_moi)
OPTIONAL MATCH (chi_tiet_goc)<-[:THAY_THE_BOI*0..]-(chi_tiet_cu)
OPTIONAL MATCH (chi_tiet_moi)-[:CO_KHOAN]->(thay_khoan_moi)
  WHERE chi_tiet_moi IS NOT NULL AND 'DieuLuat' IN labels(chi_tiet_moi)
OPTIONAL MATCH (thay_khoan_moi)-[:CO_DIEM]->(thay_diem_moi)
  WHERE chi_tiet_moi IS NOT NULL AND 'DieuLuat' IN labels(chi_tiet_moi)
OPTIONAL MATCH (chi_tiet_moi)-[:CO_DIEM]->(thay_diem_k_moi)
  WHERE chi_tiet_moi IS NOT NULL AND 'DieuKhoanLuat' IN labels(chi_tiet_moi)
OPTIONAL MATCH (chi_tiet_cu)-[:CO_KHOAN]->(thay_khoan_cu)
  WHERE chi_tiet_cu IS NOT NULL AND 'DieuLuat' IN labels(chi_tiet_cu)
OPTIONAL MATCH (thay_khoan_cu)-[:CO_DIEM]->(thay_diem_cu)
  WHERE chi_tiet_cu IS NOT NULL AND 'DieuLuat' IN labels(chi_tiet_cu)
OPTIONAL MATCH (chi_tiet_cu)-[:CO_DIEM]->(thay_diem_k_cu)
  WHERE chi_tiet_cu IS NOT NULL AND 'DieuKhoanLuat' IN labels(chi_tiet_cu)
WITH n_goc, dieu_seed_ids, chi_tiet_anc,
     collect(DISTINCT chi_tiet_goc)
       + collect(DISTINCT chi_tiet_moi)
       + collect(DISTINCT chi_tiet_cu)
       + collect(DISTINCT thay_khoan_moi)
       + collect(DISTINCT thay_diem_moi)
       + collect(DISTINCT thay_diem_k_moi)
       + collect(DISTINCT thay_khoan_cu)
       + collect(DISTINCT thay_diem_cu)
       + collect(DISTINCT thay_diem_k_cu) AS expanded_desc

""" + ANCESTOR_REPLACEMENT_EXPAND_KG + """

WITH n_goc, dieu_seed_ids,
     [x IN expanded_desc + expanded_anc WHERE x IS NOT NULL] AS tat_ca_phien_ban
UNWIND tat_ca_phien_ban AS node_xet_duyet

WITH DISTINCT n_goc, dieu_seed_ids, node_xet_duyet AS chi_tiet_ap_dung
WHERE chi_tiet_ap_dung.ngay_co_hieu_luc <= $target_date
  AND (chi_tiet_ap_dung.ngay_het_hieu_luc IS NULL
       OR chi_tiet_ap_dung.ngay_het_hieu_luc > $target_date)

OPTIONAL MATCH (chi_tiet_ap_dung)-[:DUOC_SUA_DOI_BOI]->(van_ban_sua_doi)
  WHERE van_ban_sua_doi.ngay_co_hieu_luc <= $target_date
    AND (van_ban_sua_doi.ngay_het_hieu_luc IS NULL
         OR van_ban_sua_doi.ngay_het_hieu_luc > $target_date)

OPTIONAL MATCH (chi_tiet_ap_dung)-[:HUONG_DAN_BOI]->(huong_dan)
  WHERE huong_dan.ngay_co_hieu_luc <= $target_date
    AND (huong_dan.ngay_het_hieu_luc IS NULL
         OR huong_dan.ngay_het_hieu_luc > $target_date)

OPTIONAL MATCH (huong_dan)-[:CO_KHOAN|CO_DIEM*1..2]->(chi_tiet_huong_dan)
  WHERE chi_tiet_huong_dan.ngay_co_hieu_luc <= $target_date
    AND (chi_tiet_huong_dan.ngay_het_hieu_luc IS NULL
         OR chi_tiet_huong_dan.ngay_het_hieu_luc > $target_date)

OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAY_THE_BOI*1..]->(hien_hanh)
  WHERE hien_hanh.ngay_co_hieu_luc <= $query_date
    AND hien_hanh.ngay_het_hieu_luc IS NULL
    AND hien_hanh.id <> chi_tiet_ap_dung.id

OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAM_CHIEU_DEN]->(luat_tham_chieu)
  WHERE luat_tham_chieu.ngay_co_hieu_luc <= $target_date
    AND (luat_tham_chieu.ngay_het_hieu_luc IS NULL
         OR luat_tham_chieu.ngay_het_hieu_luc > $target_date)
OPTIONAL MATCH (luat_tham_chieu)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_tham_chieu)
  WHERE chi_tiet_tham_chieu.ngay_co_hieu_luc <= $target_date
    AND (chi_tiet_tham_chieu.ngay_het_hieu_luc IS NULL
         OR chi_tiet_tham_chieu.ngay_het_hieu_luc > $target_date)

OPTIONAL MATCH (chi_tiet_huong_dan)-[:THAM_CHIEU_DEN]->(luat_tham_chieu_tu_hd)
  WHERE luat_tham_chieu_tu_hd.ngay_co_hieu_luc <= $target_date
    AND (luat_tham_chieu_tu_hd.ngay_het_hieu_luc IS NULL
         OR luat_tham_chieu_tu_hd.ngay_het_hieu_luc > $target_date)
OPTIONAL MATCH (luat_tham_chieu_tu_hd)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_tc_tu_hd)
  WHERE chi_tiet_tc_tu_hd.ngay_co_hieu_luc <= $target_date
    AND (chi_tiet_tc_tu_hd.ngay_het_hieu_luc IS NULL
         OR chi_tiet_tc_tu_hd.ngay_het_hieu_luc > $target_date)
""" + THAM_CHIEU_ANCESTOR_MATCH_KG + MAU_THUAN_MATCH_KG + FUTURE_EFFECTIVE_MATCH_CYPHER_KG + """
WITH n_goc, dieu_seed_ids, chi_tiet_ap_dung, van_ban_sua_doi,
     huong_dan, chi_tiet_huong_dan, luat_tham_chieu, chi_tiet_tham_chieu,
     luat_tham_chieu_tu_hd, chi_tiet_tc_tu_hd, hien_hanh, mau_thuan_rel, mau_thuan,
     sua_doi_sap, hd_sap, chi_tiet_hd_sap, sua_hd_sap, thay_the_sap, chi_tiet_thay_the_sap, bai_bo_sap,
     """ + tham_chieu_ancestor_with_vars() + """
WHERE NOT any(did IN dieu_seed_ids
  WHERE chi_tiet_ap_dung.id <> did
    AND chi_tiet_ap_dung.id STARTS WITH did + '_'
    AND n_goc.id <> did)

WITH dieu_seed_ids,
  collect(DISTINCT {
    id: huong_dan.id,
    noidung: huong_dan.noidung,
    cap_bac: huong_dan.cap_bac_phap_ly,
    ngay_hieu_luc: huong_dan.ngay_co_hieu_luc,
    ngay_het_hieu_luc: huong_dan.ngay_het_hieu_luc
  }) AS hd_van_ban_parts,
  collect(DISTINCT {
    id: chi_tiet_huong_dan.id,
    noidung: chi_tiet_huong_dan.noidung,
    cap_bac: chi_tiet_huong_dan.cap_bac_phap_ly,
    ngay_hieu_luc: chi_tiet_huong_dan.ngay_co_hieu_luc,
    ngay_het_hieu_luc: chi_tiet_huong_dan.ngay_het_hieu_luc
  }) AS hd_chi_tiet_parts,
  collect(DISTINCT {
    id: luat_tham_chieu.id,
    noidung: luat_tham_chieu.noidung,
    cap_bac: luat_tham_chieu.cap_bac_phap_ly,
    ngay_hieu_luc: luat_tham_chieu.ngay_co_hieu_luc,
    ngay_het_hieu_luc: luat_tham_chieu.ngay_het_hieu_luc
  }) AS tc_van_ban_parts,
  collect(DISTINCT {
    id: chi_tiet_tham_chieu.id,
    noidung: chi_tiet_tham_chieu.noidung,
    cap_bac: chi_tiet_tham_chieu.cap_bac_phap_ly,
    ngay_hieu_luc: chi_tiet_tham_chieu.ngay_co_hieu_luc,
    ngay_het_hieu_luc: chi_tiet_tham_chieu.ngay_het_hieu_luc
  }) AS tc_chi_tiet_parts,
  collect(DISTINCT {
    id: luat_tham_chieu_tu_hd.id,
    noidung: luat_tham_chieu_tu_hd.noidung,
    cap_bac: luat_tham_chieu_tu_hd.cap_bac_phap_ly,
    ngay_hieu_luc: luat_tham_chieu_tu_hd.ngay_co_hieu_luc,
    ngay_het_hieu_luc: luat_tham_chieu_tu_hd.ngay_het_hieu_luc
  }) AS tc_hd_van_ban_parts,
  collect(DISTINCT {
    id: chi_tiet_tc_tu_hd.id,
    noidung: chi_tiet_tc_tu_hd.noidung,
    cap_bac: chi_tiet_tc_tu_hd.cap_bac_phap_ly,
    ngay_hieu_luc: chi_tiet_tc_tu_hd.ngay_co_hieu_luc,
    ngay_het_hieu_luc: chi_tiet_tc_tu_hd.ngay_het_hieu_luc
  }) AS tc_hd_chi_tiet_parts,
  """ + tham_chieu_ancestor_collect_parts() + """ AS tc_ancestor_parts,
  collect(DISTINCT hien_hanh.id) AS hien_hanh_ids,
  collect(DISTINCT CASE WHEN hien_hanh IS NOT NULL AND hien_hanh.id IS NOT NULL AND chi_tiet_ap_dung.id IS NOT NULL THEN {
    id_hien_hanh: hien_hanh.id,
    id_duoc_thay_the: chi_tiet_ap_dung.id,
    loai_tac_dong: 'THAY_THE_BOI'
  } END) AS lien_ket_hien_hanh_raw,
  collect({
    provision_id: chi_tiet_ap_dung.id,
    seed_rank: CASE
      WHEN 'DieuKhoanDiemLuat' IN labels(n_goc) THEN 0
      WHEN 'DieuKhoanLuat' IN labels(n_goc) THEN 1
      WHEN 'DieuLuat' IN labels(n_goc) THEN 2
      ELSE 3
    END,
    n_goc: n_goc,
    chi_tiet_ap_dung: chi_tiet_ap_dung,
    van_ban_sua_doi: van_ban_sua_doi
  }) AS can_cu_raw,
  collect(DISTINCT CASE WHEN mau_thuan IS NOT NULL AND mau_thuan.id IS NOT NULL AND chi_tiet_ap_dung.id IS NOT NULL THEN {
    id_nguon: chi_tiet_ap_dung.id,
    id_dich: mau_thuan.id,
    noidung_giai_thich: coalesce(mau_thuan_rel.noidung, mau_thuan_rel.noi_dung, mau_thuan_rel.giai_thich),
    noidung_dich: mau_thuan.noidung,
    cap_bac: mau_thuan.cap_bac_phap_ly,
    ngay_hieu_luc: mau_thuan.ngay_co_hieu_luc,
    ngay_het_hieu_luc: mau_thuan.ngay_het_hieu_luc
  } END) AS can_cu_mau_thuan_raw,
  collect(DISTINCT {
    id_huong_dan: huong_dan.id,
    id_duoc_huong_dan: chi_tiet_ap_dung.id
  }) AS lien_ket_huong_dan_raw,
  [item IN (
    collect(DISTINCT {
      id: sua_doi_sap.id, noidung: sua_doi_sap.noidung, cap_bac: sua_doi_sap.cap_bac_phap_ly,
      ngay_ban_hanh: sua_doi_sap.ngay_ban_hanh, ngay_hieu_luc: sua_doi_sap.ngay_co_hieu_luc,
      ngay_het_hieu_luc: sua_doi_sap.ngay_het_hieu_luc, loai_tac_dong: 'SUA_DOI_BOI',
      id_duoc_tac_dong: chi_tiet_ap_dung.id
    })
    + collect(DISTINCT {
      id: coalesce(chi_tiet_hd_sap.id, hd_sap.id), noidung: coalesce(chi_tiet_hd_sap.noidung, hd_sap.noidung),
      cap_bac: coalesce(chi_tiet_hd_sap.cap_bac_phap_ly, hd_sap.cap_bac_phap_ly),
      ngay_ban_hanh: coalesce(chi_tiet_hd_sap.ngay_ban_hanh, hd_sap.ngay_ban_hanh),
      ngay_hieu_luc: coalesce(chi_tiet_hd_sap.ngay_co_hieu_luc, hd_sap.ngay_co_hieu_luc),
      ngay_het_hieu_luc: coalesce(chi_tiet_hd_sap.ngay_het_hieu_luc, hd_sap.ngay_het_hieu_luc),
      loai_tac_dong: 'HUONG_DAN_BOI', id_duoc_tac_dong: chi_tiet_ap_dung.id
    })
    + collect(DISTINCT {
      id: sua_hd_sap.id, noidung: sua_hd_sap.noidung, cap_bac: sua_hd_sap.cap_bac_phap_ly,
      ngay_ban_hanh: sua_hd_sap.ngay_ban_hanh, ngay_hieu_luc: sua_hd_sap.ngay_co_hieu_luc,
      ngay_het_hieu_luc: sua_hd_sap.ngay_het_hieu_luc, loai_tac_dong: 'SUA_DOI_HUONG_DAN',
      id_duoc_tac_dong: coalesce(chi_tiet_huong_dan.id, huong_dan.id, chi_tiet_ap_dung.id)
    })
    + collect(DISTINCT {
      id: thay_the_sap.id, noidung: thay_the_sap.noidung, cap_bac: thay_the_sap.cap_bac_phap_ly,
      ngay_ban_hanh: thay_the_sap.ngay_ban_hanh, ngay_hieu_luc: thay_the_sap.ngay_co_hieu_luc,
      ngay_het_hieu_luc: thay_the_sap.ngay_het_hieu_luc, loai_tac_dong: 'THAY_THE_BOI',
      id_duoc_tac_dong: chi_tiet_ap_dung.id
    })
    + collect(DISTINCT CASE WHEN chi_tiet_thay_the_sap IS NOT NULL THEN {
      id: chi_tiet_thay_the_sap.id, noidung: chi_tiet_thay_the_sap.noidung,
      cap_bac: chi_tiet_thay_the_sap.cap_bac_phap_ly, ngay_ban_hanh: chi_tiet_thay_the_sap.ngay_ban_hanh,
      ngay_hieu_luc: chi_tiet_thay_the_sap.ngay_co_hieu_luc, ngay_het_hieu_luc: chi_tiet_thay_the_sap.ngay_het_hieu_luc,
      loai_tac_dong: 'THAY_THE_BOI', id_duoc_tac_dong: chi_tiet_ap_dung.id
    } END)
    + collect(DISTINCT {
      id: bai_bo_sap.id, noidung: bai_bo_sap.noidung, cap_bac: bai_bo_sap.cap_bac_phap_ly,
      ngay_ban_hanh: bai_bo_sap.ngay_ban_hanh, ngay_hieu_luc: bai_bo_sap.ngay_co_hieu_luc,
      ngay_het_hieu_luc: bai_bo_sap.ngay_het_hieu_luc, loai_tac_dong: 'BAI_BO',
      id_duoc_tac_dong: chi_tiet_ap_dung.id
    })
    + collect(DISTINCT CASE WHEN chi_tiet_ap_dung.ngay_het_hieu_luc > $query_date THEN {
      id: chi_tiet_ap_dung.id, noidung: chi_tiet_ap_dung.noidung, cap_bac: chi_tiet_ap_dung.cap_bac_phap_ly,
      ngay_ban_hanh: chi_tiet_ap_dung.ngay_ban_hanh, ngay_hieu_luc: chi_tiet_ap_dung.ngay_co_hieu_luc,
      ngay_het_hieu_luc: chi_tiet_ap_dung.ngay_het_hieu_luc, loai_tac_dong: 'HET_HIEU_LUC',
      id_duoc_tac_dong: chi_tiet_ap_dung.id
    } END)
  ) WHERE item.id IS NOT NULL] AS can_cu_sap_hieu_luc_raw,
  [pair IN (
    collect(DISTINCT {id_van_ban: sua_doi_sap.id, id_duoc_tac_dong: chi_tiet_ap_dung.id, loai_tac_dong: 'SUA_DOI_BOI'})
    + collect(DISTINCT {id_van_ban: coalesce(chi_tiet_hd_sap.id, hd_sap.id), id_duoc_tac_dong: chi_tiet_ap_dung.id, loai_tac_dong: 'HUONG_DAN_BOI'})
    + collect(DISTINCT {id_van_ban: sua_hd_sap.id, id_duoc_tac_dong: coalesce(chi_tiet_huong_dan.id, huong_dan.id), loai_tac_dong: 'SUA_DOI_HUONG_DAN'})
    + collect(DISTINCT {id_van_ban: thay_the_sap.id, id_duoc_tac_dong: chi_tiet_ap_dung.id, loai_tac_dong: 'THAY_THE_BOI'})
    + collect(DISTINCT {id_van_ban: bai_bo_sap.id, id_duoc_tac_dong: chi_tiet_ap_dung.id, loai_tac_dong: 'BAI_BO'})
    + collect(DISTINCT CASE WHEN chi_tiet_ap_dung.ngay_het_hieu_luc > $query_date THEN {
      id_van_ban: chi_tiet_ap_dung.id, id_duoc_tac_dong: chi_tiet_ap_dung.id, loai_tac_dong: 'HET_HIEU_LUC'
    } END)
  ) WHERE pair.id_van_ban IS NOT NULL AND pair.id_duoc_tac_dong IS NOT NULL] AS lien_ket_sap_hieu_luc_raw

OPTIONAL CALL {
  WITH can_cu_raw
  UNWIND can_cu_raw AS row
  WITH row.provision_id AS provision_id, collect(row) AS rows
  WITH provision_id,
       reduce(best = rows[0], r IN rows |
         CASE WHEN r.seed_rank < best.seed_rank THEN r ELSE best END
       ) AS picked
  RETURN collect({
    id_goc_tu_router: picked.n_goc.id,
    id_thuc_te_ap_dung: picked.chi_tiet_ap_dung.id,
    noidung: picked.chi_tiet_ap_dung.noidung,
    cap_bac: picked.chi_tiet_ap_dung.cap_bac_phap_ly,
    het_hieu_luc: picked.chi_tiet_ap_dung.ngay_het_hieu_luc IS NOT NULL,
    ngay_hieu_luc: picked.chi_tiet_ap_dung.ngay_co_hieu_luc,
    ngay_het_hieu_luc: picked.chi_tiet_ap_dung.ngay_het_hieu_luc,
    id_sua_doi: picked.van_ban_sua_doi.id,
    noidung_sua_doi: picked.van_ban_sua_doi.noidung,
    ngay_hieu_luc_sua_doi: picked.van_ban_sua_doi.ngay_co_hieu_luc,
    ngay_het_hieu_luc_sua_doi: picked.van_ban_sua_doi.ngay_het_hieu_luc
  }) AS can_cu_chinh_inner
}
WITH hd_van_ban_parts + hd_chi_tiet_parts AS hd_all,
     tc_van_ban_parts + tc_chi_tiet_parts + tc_ancestor_parts
       + tc_hd_van_ban_parts + tc_hd_chi_tiet_parts AS tc_all,
     hien_hanh_ids, coalesce(can_cu_chinh_inner, []) AS can_cu_chinh,
     [x IN lien_ket_huong_dan_raw
      WHERE x.id_huong_dan IS NOT NULL AND x.id_duoc_huong_dan IS NOT NULL] AS lien_ket_huong_dan_inner,
     [x IN lien_ket_hien_hanh_raw
      WHERE x.id_hien_hanh IS NOT NULL AND x.id_duoc_thay_the IS NOT NULL] AS lien_ket_hien_hanh_inner,
     can_cu_mau_thuan_raw, can_cu_sap_hieu_luc_raw, lien_ket_sap_hieu_luc_raw

OPTIONAL CALL {
  WITH hd_all
  UNWIND [x IN hd_all WHERE x.id IS NOT NULL] AS hd_item
  WITH hd_item.id AS hid, hd_item
  WITH hid, head(collect(hd_item)) AS hd_one
  RETURN collect(hd_one) AS can_cu_huong_dan_inner
}
WITH tc_all, hien_hanh_ids, can_cu_chinh, can_cu_huong_dan_inner, lien_ket_huong_dan_inner,
     lien_ket_hien_hanh_inner, can_cu_mau_thuan_raw, can_cu_sap_hieu_luc_raw, lien_ket_sap_hieu_luc_raw

OPTIONAL CALL {
  WITH tc_all
  UNWIND [x IN tc_all WHERE x.id IS NOT NULL] AS tc_item
  WITH tc_item.id AS tid, tc_item
  WITH tid, head(collect(tc_item)) AS tc_one
  RETURN collect(tc_one) AS can_cu_bo_tro_inner
}
RETURN {
    can_cu_chinh: can_cu_chinh,
    can_cu_huong_dan: coalesce(can_cu_huong_dan_inner, []),
    can_cu_bo_tro: coalesce(can_cu_bo_tro_inner, []),
    can_cu_mau_thuan: [x IN can_cu_mau_thuan_raw WHERE x IS NOT NULL],
    lien_ket_huong_dan: coalesce(lien_ket_huong_dan_inner, []),
    quy_dinh_hien_hanh_doi_chieu: [x IN hien_hanh_ids WHERE x IS NOT NULL],
    lien_ket_hien_hanh: coalesce(lien_ket_hien_hanh_inner, []),
    can_cu_sap_hieu_luc: can_cu_sap_hieu_luc_raw,
    lien_ket_sap_hieu_luc: lien_ket_sap_hieu_luc_raw
} AS Context_Tho
"""


def assemble_graph_seed_cypher(seed_body: str) -> str:
    return (
        seed_body.rstrip()
        + "\n\n"
        + SEMANTIC_TO_LEGAL_TAIL.strip()
        + "\n\n"
        + EXPAND_AND_TIMEFILTER_CYPHER
    )


_SEMANTIC_VIZ_FROM_TRACE_TAIL = """
WITH wl, seed_nodes, leaf_seed_nodes
UNWIND [x IN seed_nodes WHERE x IS NOT NULL] AS n
OPTIONAL MATCH (n)-[r]-(m)
WHERE (m IN seed_nodes AND m IS NOT NULL) OR type(r) = 'CAN_CU_TAI'
WITH wl, seed_nodes, leaf_seed_nodes, n, r, m
WHERE r IS NOT NULL
  AND startNode(r).id IS NOT NULL
  AND endNode(r).id IS NOT NULL
WITH wl, seed_nodes, leaf_seed_nodes,
  [x IN collect(DISTINCT {id: n.id, labels: labels(n)})
        + collect(DISTINCT CASE WHEN m IS NOT NULL THEN {id: m.id, labels: labels(m)} END)
   WHERE x IS NOT NULL AND x.id IS NOT NULL | x] AS viz_nodes,
  [e IN collect(DISTINCT {src: startNode(r).id, dst: endNode(r).id, type: type(r)})
   WHERE e.src IS NOT NULL AND e.dst IS NOT NULL | e] AS viz_edges
RETURN {
  nodes: viz_nodes,
  edges: viz_edges,
  leaf_seed_ids: [x IN leaf_seed_nodes WHERE x IS NOT NULL | x.id]
} AS viz_graph
"""


def assemble_semantic_viz_from_trace_prefix(trace_prefix: str) -> str:
    body = trace_prefix.rstrip()
    if "AS leaf_seed_nodes" in trace_prefix and "AS seed_nodes" in trace_prefix:
        idx = trace_prefix.rfind("AS leaf_seed_nodes")
        if idx != -1:
            body = trace_prefix[: idx + len("AS leaf_seed_nodes")].rstrip()
        return body + "\n" + _SEMANTIC_VIZ_FROM_TRACE_TAIL
    return body + "\n" + _SEMANTIC_VIZ_FROM_TRACE_TAIL


BROAD_SCOPE_VALUES = frozenset({"tong_quat", "tat_ca", "khong_ro", "chua_ro"})


def should_keep_whitelist(params, router_fields: tuple[str, ...]) -> bool:
    if not router_fields:
        return False
    data = params.model_dump()
    return data.get(router_fields[0]) in BROAD_SCOPE_VALUES


__all__ = [
    "EXPAND_AND_TIMEFILTER_CYPHER",
    "SEMANTIC_TO_LEGAL_TAIL",
    "assemble_graph_seed_cypher",
    "assemble_semantic_viz_from_trace_prefix",
    "BROAD_SCOPE_VALUES",
    "should_keep_whitelist",
    "TOPIC",
    "TOPIC_LABEL",
]
