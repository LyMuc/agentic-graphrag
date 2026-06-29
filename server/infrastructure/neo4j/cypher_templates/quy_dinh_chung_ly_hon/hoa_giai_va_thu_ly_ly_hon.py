"""Template — hòa giải và thụ lý ly hôn (Đ52-54, Đ53)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.quy_dinh_chung_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("giai_doan",)
_DIEU_52_54_WHITELIST = [
    "Luat_HNGD_2014_Dieu_52",
    "Luat_HNGD_2014_Dieu_53",
    "Luat_HNGD_2014_Dieu_54",
]


class HoaGiaiVaThuLyLyHonParams(BaseModel):
    giai_doan: Literal[
        "hoa_giai_o_co_so",
        "thu_ly_don",
        "hoa_giai_tai_toa",
        "phan_biet_co_so_va_tai_toa",
        "da_nop_don_cham_giai_quyet",
        "tong_quat",
    ] = Field(
        description=(
            "Giai đoạn thủ tục. Map: hòa giải xã/phường → hoa_giai_o_co_so; "
            "Tòa thụ lý đơn → thu_ly_don; hòa giải sau thụ lý → hoa_giai_tai_toa; "
            "hỏi bắt buộc → phan_biet_co_so_va_tai_toa; nộp lâu chưa xử lý "
            "→ da_nop_don_cham_giai_quyet."
        )
    )
    hinh_thuc_ly_hon: Literal["thuan_tinh", "don_phuong", "khong_ro"] = Field(
        description="Hai bên đồng ý → thuan_tinh; một bên → don_phuong."
    )
    dang_ky_ket_hon: Literal["co", "khong", "khong_ro"] = Field(
        description="Không đăng ký/không có giấy kết hôn → khong."
    )
    khia_canh_hoa_giai: Literal[
        "co_bat_buoc_hay_khong",
        "tham_quyen_thu_ly",
        "tinh_trang_cham_giai_quyet",
        "tong_quat",
    ] = Field(
        description=(
            "Có bắt buộc hòa giải → co_bat_buoc_hay_khong; Tòa nhận đơn "
            "→ tham_quyen_thu_ly; chậm giải quyết → tinh_trang_cham_giai_quyet."
        )
    )


_SEED_BODY = f"""
WITH $gd AS gd, $dang_ky AS dk, $hinh_thuc AS ht, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (gd_cs:GiaiDoanLyHon:{TOPIC_LABEL} {{id: 'hoa_giai_o_co_so', topic: '{TOPIC}'}})
WHERE gd IN ['hoa_giai_o_co_so', 'phan_biet_co_so_va_tai_toa', 'tong_quat', 'da_nop_don_cham_giai_quyet']

OPTIONAL MATCH (gd_tt:GiaiDoanLyHon:{TOPIC_LABEL} {{id: 'hoa_giai_tai_toa_sau_thu_ly', topic: '{TOPIC}'}})
WHERE gd IN ['hoa_giai_tai_toa', 'phan_biet_co_so_va_tai_toa', 'tong_quat', 'da_nop_don_cham_giai_quyet']
OPTIONAL MATCH (hv_hg:HanhVi:{TOPIC_LABEL} {{id: 'toa_an_tien_hanh_hoa_giai', topic: '{TOPIC}'}})
WHERE gd_tt IS NOT NULL

OPTIONAL MATCH (gd_tl:GiaiDoanLyHon:{TOPIC_LABEL} {{id: 'thu_ly_don_yeu_cau_ly_hon', topic: '{TOPIC}'}})
WHERE gd IN ['thu_ly_don', 'da_nop_don_cham_giai_quyet', 'tong_quat']
OPTIONAL MATCH (hv_tl:HanhVi:{TOPIC_LABEL} {{id: 'toa_an_thu_ly_don_ly_hon', topic: '{TOPIC}'}})
WHERE gd_tl IS NOT NULL

OPTIONAL MATCH (gd_kdk:GiaiDoanLyHon:{TOPIC_LABEL} {{id: 'thu_ly_yeu_cau_khi_khong_dang_ky_ket_hon', topic: '{TOPIC}'}})
WHERE gd IN ['thu_ly_don', 'tong_quat'] AND dk = 'khong'

OPTIONAL MATCH (ht:HinhThucLyHon:{TOPIC_LABEL} {{id: 'thuan_tinh_ly_hon', topic: '{TOPIC}'}})
WHERE ht = 'thuan_tinh' AND gd IN ['phan_biet_co_so_va_tai_toa', 'da_nop_don_cham_giai_quyet']

OPTIONAL MATCH (ht_dp:HinhThucLyHon:{TOPIC_LABEL} {{id: 'ly_hon_theo_yeu_cau_mot_ben', topic: '{TOPIC}'}})
WHERE ht = 'don_phuong' AND gd = 'da_nop_don_cham_giai_quyet'

WITH wl, gd,
  [x IN collect(DISTINCT gd_cs) + collect(DISTINCT gd_tt) + collect(DISTINCT hv_hg)
       + collect(DISTINCT gd_tl) + collect(DISTINCT hv_tl) + collect(DISTINCT gd_kdk)
       + collect(DISTINCT ht) + collect(DISTINCT ht_dp)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE gd
    WHEN 'hoa_giai_o_co_so' THEN [x IN collect(DISTINCT gd_cs) WHERE x IS NOT NULL]
    WHEN 'hoa_giai_tai_toa' THEN
      [x IN collect(DISTINCT gd_tt) + collect(DISTINCT hv_hg) WHERE x IS NOT NULL]
    WHEN 'thu_ly_don' THEN
      CASE WHEN dk = 'khong'
        THEN [x IN collect(DISTINCT gd_kdk) WHERE x IS NOT NULL]
        ELSE [x IN collect(DISTINCT gd_tl) + collect(DISTINCT hv_tl) WHERE x IS NOT NULL]
      END
    WHEN 'phan_biet_co_so_va_tai_toa' THEN
      [x IN collect(DISTINCT gd_cs) + collect(DISTINCT gd_tt) + collect(DISTINCT ht)
       WHERE x IS NOT NULL]
    WHEN 'da_nop_don_cham_giai_quyet' THEN
      [x IN collect(DISTINCT gd_tl) + collect(DISTINCT gd_tt) + collect(DISTINCT ht)
           + collect(DISTINCT ht_dp)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT gd_cs) + collect(DISTINCT gd_tt) + collect(DISTINCT gd_tl)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: HoaGiaiVaThuLyLyHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "gd": params.giai_doan,
        "dang_ky": params.dang_ky_ket_hon,
        "hinh_thuc": params.hinh_thuc_ly_hon,
        "whitelist_dieu_ids": _DIEU_52_54_WHITELIST if use_wl else [],
    }


hoa_giai_va_thu_ly_ly_hon = CypherTemplate(
    name="hoa_giai_va_thu_ly_ly_hon",
    description=(
        "Phân biệt hòa giải ở cơ sở (Đ52) với hòa giải tại Tòa án sau thụ lý (Đ54), "
        "và trả căn cứ thụ lý đơn (Đ53). "
        "Ví dụ: Thủ tục hòa giải có bắt buộc không; "
        "Phân biệt hòa giải cơ sở và hòa giải tại Tòa án; "
        "Đã nộp đơn hơn một năm nhưng Tòa án chưa giải quyết."
    ),
    params_schema=HoaGiaiVaThuLyLyHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
