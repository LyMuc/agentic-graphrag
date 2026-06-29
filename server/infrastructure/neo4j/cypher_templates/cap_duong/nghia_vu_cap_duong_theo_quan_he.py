"""Template — nghĩa vụ cấp dưỡng theo quan hệ gia đình (Đ107-115, Đ110)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.cap_duong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("quan_he",)
_TONG_QUAT_WHITELIST = [
    "Luat_HNGD_2014_Dieu_107",
    "Luat_HNGD_2014_Dieu_110",
    "Luat_HNGD_2014_Dieu_111",
    "Luat_HNGD_2014_Dieu_112",
    "Luat_HNGD_2014_Dieu_113",
    "Luat_HNGD_2014_Dieu_114",
    "Luat_HNGD_2014_Dieu_115",
]

_TINH_TRANG_TO_DK = {
    "chua_thanh_nien": "con_chua_thanh_nien",
    "thanh_nien_khong_kha_nang_lao_dong_khong_tai_san": "con_thanh_nien_khong_kha_nang_lao_dong_khong_tai_san",
    "kho_khan_tung_thieu": "ben_sau_ly_hon_kho_khan_tung_thieu",
    "khong_co_nguoi_khac_cap_duong": "khong_co_nguoi_khac_cap_duong",
}


class NghiaVuCapDuongTheoQuanHeParams(BaseModel):
    quan_he: Literal[
        "cha_me_cho_con",
        "con_cho_cha_me",
        "anh_chi_em_voi_nhau",
        "ong_ba_cho_chau",
        "chau_cho_ong_ba",
        "co_di_chu_cau_bac_cho_chau_ruot",
        "chau_ruot_cho_co_di_chu_cau_bac",
        "vo_chong_sau_ly_hon",
        "cha_me_khong_truc_tiep_nuoi_con_sau_ly_hon",
        "tong_quat",
    ] = Field(
        description=(
            "Quan hệ cấp dưỡng. Map: cha/mẹ cấp dưỡng con, con ngoài giá thú, "
            "không đăng ký kết hôn → cha_me_cho_con; người không trực tiếp nuôi con "
            "→ cha_me_khong_truc_tiep_nuoi_con_sau_ly_hon; ông bà nuôi/cấp dưỡng cháu "
            "→ ong_ba_cho_chau; cháu cấp dưỡng ông bà → chau_cho_ong_ba; vợ cũ/chồng cũ "
            "→ vo_chong_sau_ly_hon; không xác định → tong_quat."
        )
    )
    tinh_trang_nguoi_duoc_cap_duong: Literal[
        "chua_thanh_nien",
        "thanh_nien_khong_kha_nang_lao_dong_khong_tai_san",
        "kho_khan_tung_thieu",
        "khong_co_nguoi_khac_cap_duong",
        "khong_ro",
    ] = Field(
        description=(
            "Tình trạng người được cấp dưỡng. Map: trẻ em/đến bao nhiêu tuổi "
            "→ chua_thanh_nien; không lao động/không tự nuôi → thanh_nien_...; "
            "đau yếu/túng thiếu (vợ chồng cũ) → kho_khan_tung_thieu; cha không cấp dưỡng "
            "→ khong_co_nguoi_khac_cap_duong."
        )
    )
    boi_canh: Literal[
        "sau_ly_hon",
        "khong_dang_ky_ket_hon",
        "con_ngoai_gia_thu",
        "khong_song_chung",
        "song_chung_vi_pham_nuoi_duong",
        "khong_ro",
    ] = Field(description="Bối cảnh phát sinh nghĩa vụ.")
    khia_canh: Literal[
        "phat_sinh_nghia_vu",
        "dieu_kien",
        "thoi_han_theo_tinh_trang",
        "nguon_tai_san_thuc_hien",
        "tong_quat",
    ] = Field(
        description=(
            "Khía cạnh câu hỏi. Map: có phải cấp dưỡng → phat_sinh_nghia_vu; "
            "trường hợp nào → dieu_kien; đến bao nhiêu tuổi → thoi_han_theo_tinh_trang; "
            "lấy tài sản riêng → nguon_tai_san_thuc_hien."
        )
    )
    hoi_kem_muc: Literal["co", "khong"] = Field(
        description="co khi cùng câu hỏi có bao nhiêu/mức cấp dưỡng."
    )


_SEED_BODY = f"""
WITH $quan_he AS qh, $tinh_trang AS tt, $boi_canh AS bc, $khia_canh AS kc,
     $hoi_kem_muc AS hkm, $dk_id AS dk_id, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (anchor:QuanHeCapDuong:{TOPIC_LABEL} {{id: qh, topic: '{TOPIC}'}})
WHERE qh <> 'tong_quat'

OPTIONAL MATCH (anchor)-[:QUY_DINH_NGHIA_VU]->(nv:NghiaVu:{TOPIC_LABEL})
WHERE anchor IS NOT NULL

OPTIONAL MATCH (nv)-[:AP_DUNG_KHI]->(dk:DieuKien:{TOPIC_LABEL})
WHERE nv IS NOT NULL
  AND (tt = 'khong_ro' OR dk.id = dk_id
       OR (tt = 'chua_thanh_nien' AND dk.id IN [
             'con_chua_thanh_nien', 'cha_me_khong_song_chung_voi_con',
             'cha_me_song_chung_nhung_vi_pham_nghia_vu_nuoi_duong'
           ])
       OR (tt = 'thanh_nien_khong_kha_nang_lao_dong_khong_tai_san'
           AND dk.id = 'con_thanh_nien_khong_kha_nang_lao_dong_khong_tai_san'))

OPTIONAL MATCH (anchor)-[:QUY_DINH_NGHIA_VU]->(nv2:NghiaVu:{TOPIC_LABEL})
WHERE qh = 'cha_me_khong_truc_tiep_nuoi_con_sau_ly_hon'
  AND nv2.id = 'nghia_vu_cap_duong_cha_me_khong_truc_tiep_nuoi_con'

OPTIONAL MATCH (dk_bc:DieuKien:{TOPIC_LABEL})
WHERE bc = 'khong_song_chung' AND dk_bc.id = 'cha_me_khong_song_chung_voi_con'
OPTIONAL MATCH (dk_bc2:DieuKien:{TOPIC_LABEL})
WHERE bc = 'song_chung_vi_pham_nuoi_duong'
  AND dk_bc2.id = 'cha_me_song_chung_nhung_vi_pham_nghia_vu_nuoi_duong'

OPTIONAL MATCH (dk_tt:DieuKien:{TOPIC_LABEL})
WHERE tt = 'khong_co_nguoi_khac_cap_duong'
  AND dk_tt.id = 'chau_khong_co_nguoi_cap_duong_theo_dieu_112'

OPTIONAL MATCH (hq_tai_hon:HauQua:{TOPIC_LABEL} {{id: 'cham_dut_khi_ben_duoc_cap_duong_tai_hon'}})
WHERE qh = 'vo_chong_sau_ly_hon'

OPTIONAL MATCH (muc_tt:ThoaThuan:{TOPIC_LABEL})
WHERE (hkm = 'co' OR kc = 'nguon_tai_san_thuc_hien')
  AND muc_tt.id IN [
    'thoa_thuan_muc_cap_duong',
    'thoa_thuan_thay_doi_muc_cap_duong'
  ]
OPTIONAL MATCH (dk_muc:DieuKien:{TOPIC_LABEL})
WHERE (hkm = 'co' OR kc = 'nguon_tai_san_thuc_hien')
  AND dk_muc.id IN [
    'thu_nhap_kha_nang_thuc_te_nguoi_cap_duong',
    'nhu_cau_thiet_yeu_nguoi_duoc_cap_duong'
  ]

WITH wl, qh, tt, bc, kc, hkm,
  collect(DISTINCT anchor) AS anchors,
  collect(DISTINCT nv) AS nvs,
  collect(DISTINCT nv2) AS nv2s,
  collect(DISTINCT dk) AS dks,
  collect(DISTINCT dk_bc) AS dk_bc_list,
  collect(DISTINCT dk_bc2) AS dk_bc2_list,
  collect(DISTINCT dk_tt) AS dk_tt_list,
  collect(DISTINCT hq_tai_hon) AS hq_tai_hon_list,
  collect(DISTINCT muc_tt) AS muc_tt_list,
  collect(DISTINCT dk_muc) AS dk_muc_list

WITH wl, qh, tt, bc, kc, hkm,
  anchors, nvs, nv2s, dks, dk_bc_list, dk_bc2_list, dk_tt_list,
  hq_tai_hon_list, muc_tt_list, dk_muc_list,
  [x IN anchors + nvs + nv2s + dks + dk_bc_list + dk_bc2_list + dk_tt_list
       + hq_tai_hon_list + muc_tt_list + dk_muc_list
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN qh = 'tong_quat' THEN []
    WHEN tt <> 'khong_ro'
         AND size([x IN dks WHERE x IS NOT NULL]) > 0 THEN
      [x IN dks + dk_bc_list + dk_bc2_list + dk_tt_list WHERE x IS NOT NULL]
    WHEN qh = 'cha_me_khong_truc_tiep_nuoi_con_sau_ly_hon' THEN
      [x IN nv2s WHERE x IS NOT NULL]
    ELSE
      [x IN anchors + nvs WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: NghiaVuCapDuongTheoQuanHeParams) -> dict[str, Any]:
    dk_id = _TINH_TRANG_TO_DK.get(params.tinh_trang_nguoi_duoc_cap_duong, "")
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "quan_he": params.quan_he,
        "tinh_trang": params.tinh_trang_nguoi_duoc_cap_duong,
        "boi_canh": params.boi_canh,
        "khia_canh": params.khia_canh,
        "hoi_kem_muc": params.hoi_kem_muc,
        "dk_id": dk_id,
        "whitelist_dieu_ids": _TONG_QUAT_WHITELIST if use_wl else [],
    }


nghia_vu_cap_duong_theo_quan_he = CypherTemplate(
    name="nghia_vu_cap_duong_theo_quan_he",
    description=(
        "Xác định giữa những người nào có nghĩa vụ cấp dưỡng và điều kiện phát sinh: "
        "cha mẹ-con, con-cha mẹ, anh chị em, ông bà-cháu, cô dì chú cậu bác-cháu, "
        "vợ chồng sau ly hôn. Ví dụ: yêu cầu ông bà cấp dưỡng khi cha không chịu cấp dưỡng; "
        "đã ly hôn 5 năm có thể yêu cầu chồng cũ cấp dưỡng không; không đăng ký kết hôn "
        "người cha có nghĩa vụ cấp dưỡng cho con không."
    ),
    params_schema=NghiaVuCapDuongTheoQuanHeParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
