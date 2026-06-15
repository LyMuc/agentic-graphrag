"""Template — trách nhiệm Nhà nước và xã hội (Đ4)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("chu_the_trach_nhiem", "khia_canh_trach_nhiem")
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_4"]

_CHU_THE_MAP: dict[str, str] = {
    "nha_nuoc": "chu_the_nha_nuoc",
    "chinh_phu": "chu_the_chinh_phu",
    "bo_co_quan_ngang_bo": "chu_the_bo_co_quan_ngang_bo",
    "uy_ban_nhan_dan_va_co_quan_khac": "chu_the_uy_ban_nhan_dan_va_co_quan_khac",
    "co_quan_to_chuc": "chu_the_co_quan_to_chuc",
    "nha_truong_va_gia_dinh": "chu_the_nha_truong",
}

_NGHIA_VU_MAP: dict[str, str] = {
    "bao_ho_tao_dieu_kien": "bao_ho_va_tao_dieu_kien_xac_lap_hon_nhan",
    "tuyen_truyen_xoa_bo_tap_quan_lac_hau": "tuyen_truyen_pho_bien_giao_duc_phap_luat_hngd",
    "thong_nhat_quan_ly_nha_nuoc": "thong_nhat_quan_ly_nha_nuoc_ve_hngd",
    "quan_ly_theo_phan_cong": "quan_ly_nha_nuoc_theo_phan_cong",
    "giao_duc_hoa_giai_bao_ve": "giao_duc_van_dong_xay_dung_gia_dinh_van_hoa",
    "phoi_hop_giao_duc_the_he_tre": "phoi_hop_gia_dinh_giao_duc_the_he_tre",
}


class TrachNhiemNhaNuocXaHoiParams(BaseModel):
    chu_the_trach_nhiem: Literal[
        "nha_nuoc",
        "chinh_phu",
        "bo_co_quan_ngang_bo",
        "uy_ban_nhan_dan_va_co_quan_khac",
        "co_quan_to_chuc",
        "nha_truong_va_gia_dinh",
        "tat_ca",
        "khong_ro",
    ] = Field(description="Chủ thể có trách nhiệm tại Điều 4.")
    khia_canh_trach_nhiem: Literal[
        "bao_ho_tao_dieu_kien",
        "tuyen_truyen_xoa_bo_tap_quan_lac_hau",
        "thong_nhat_quan_ly_nha_nuoc",
        "quan_ly_theo_phan_cong",
        "giao_duc_hoa_giai_bao_ve",
        "phoi_hop_giao_duc_the_he_tre",
        "tong_quat",
    ] = Field(description="Khía cạnh trách nhiệm cần truy xuất.")


_SEED_BODY = f"""
WITH $ct AS ct, $kc AS kc, $chu_the_id AS chu_the_id, $nghia_vu_id AS nghia_vu_id,
     $expand_all AS expand_all, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (root:QuyDinh:{TOPIC_LABEL} {{
  id: 'trach_nhiem_nha_nuoc_xa_hoi_ve_hngd', topic: '{TOPIC}'
}})
WHERE expand_all = true

OPTIONAL MATCH (root)-[:BAO_GOM]->(child)
WHERE expand_all = true AND child.topic = '{TOPIC}'

OPTIONAL MATCH (ct_node:ChuThe:{TOPIC_LABEL} {{id: chu_the_id, topic: '{TOPIC}'}})
WHERE chu_the_id <> ''

OPTIONAL MATCH (ct_gd:ChuThe:{TOPIC_LABEL} {{
  id: 'chu_the_gia_dinh_trong_giao_duc', topic: '{TOPIC}'
}})
WHERE ct = 'nha_truong_va_gia_dinh'

OPTIONAL MATCH (ct_node)-[:CO_TRACH_NHIEM]->(nv_ct:NghiaVu:{TOPIC_LABEL})
WHERE chu_the_id <> '' AND nv_ct.topic = '{TOPIC}'

OPTIONAL MATCH (ct_gd)-[:CO_TRACH_NHIEM]->(nv_gd:NghiaVu:{TOPIC_LABEL})
WHERE ct = 'nha_truong_va_gia_dinh' AND nv_gd.topic = '{TOPIC}'

OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL} {{id: nghia_vu_id, topic: '{TOPIC}'}})
WHERE nghia_vu_id <> '' AND expand_all = false AND chu_the_id = ''

WITH wl, kc, expand_all, ct, chu_the_id,
  collect(DISTINCT root) + collect(DISTINCT child)
    + collect(DISTINCT ct_node) + collect(DISTINCT ct_gd)
    + collect(DISTINCT nv_ct) + collect(DISTINCT nv_gd) + collect(DISTINCT nv)
    AS seed_nodes,
  CASE
    WHEN expand_all = true THEN
      [x IN collect(DISTINCT child) WHERE x IS NOT NULL]
    WHEN ct = 'nha_truong_va_gia_dinh' THEN
      [x IN collect(DISTINCT ct_node) + collect(DISTINCT ct_gd)
           + collect(DISTINCT nv_gd) + collect(DISTINCT nv)
       WHERE x IS NOT NULL]
    WHEN chu_the_id <> '' THEN
      [x IN collect(DISTINCT ct_node) + collect(DISTINCT nv_ct) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT nv) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: TrachNhiemNhaNuocXaHoiParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    ct = params.chu_the_trach_nhiem
    kc = params.khia_canh_trach_nhiem
    expand_all = ct in ("tat_ca", "khong_ro") or kc == "tong_quat"
    chu_the_id = _CHU_THE_MAP.get(ct, "")
    if ct == "nha_truong_va_gia_dinh":
        chu_the_id = "chu_the_nha_truong"
    nghia_vu_id = _NGHIA_VU_MAP.get(kc, "")
    if expand_all:
        chu_the_id = ""
        nghia_vu_id = ""
    elif ct == "nha_truong_va_gia_dinh":
        if kc == "tong_quat":
            nghia_vu_id = "phoi_hop_gia_dinh_giao_duc_the_he_tre"
    elif chu_the_id and kc == "thong_nhat_quan_ly_nha_nuoc":
        nghia_vu_id = "thong_nhat_quan_ly_nha_nuoc_ve_hngd"
    elif chu_the_id and kc == "quan_ly_theo_phan_cong":
        nghia_vu_id = "quan_ly_nha_nuoc_theo_phan_cong"
    elif chu_the_id:
        nghia_vu_id = ""
    return {
        "ct": ct,
        "kc": kc,
        "chu_the_id": chu_the_id,
        "nghia_vu_id": nghia_vu_id,
        "expand_all": expand_all,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


trach_nhiem_nha_nuoc_xa_hoi = CypherTemplate(
    name="trach_nhiem_nha_nuoc_xa_hoi",
    description=(
        "Truy xuất chính sách, biện pháp bảo hộ, tuyên truyền, quản lý nhà nước và trách nhiệm "
        "giáo dục, hòa giải, bảo vệ tại Điều 4. Phân biệt Chính phủ thống nhất quản lý với bộ, "
        "UBND thực hiện theo phân công. "
        "Ví dụ: Nhà nước và xã hội có trách nhiệm gì đối với hôn nhân và gia đình?; "
        "Cơ quan nào thống nhất quản lý nhà nước về hôn nhân và gia đình?"
    ),
    params_schema=TrachNhiemNhaNuocXaHoiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
