"""Template — đưa tài sản chung vào kinh doanh (Đ25 k2 + Đ36)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh",)
_DIEU_25_WHITELIST = ["Luat_HNGD_2014_Dieu_25"]


class DuaTaiSanChungVaoKinhDoanhParams(BaseModel):
    khia_canh: Literal["hinh_thuc_thoa_thuan", "quy_dinh_ap_dung", "tong_quat"] = Field(
        default="tong_quat"
    )
    hinh_thuc_thoa_thuan: Literal["van_ban", "loi_noi", "khong_ro"] = Field(
        default="khong_ro"
    )
    loai_tai_san: Literal["tai_san_chung", "khong_ro"] = Field(default="tai_san_chung")


_SEED_BODY = f"""
WITH $khia_canh AS kc, $hinh_thuc_thoa_thuan AS htt, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (hv:HanhVi:{TOPIC_LABEL} {{
  id: 'dua_tai_san_chung_vao_kinh_doanh', topic: '{TOPIC}'
}})
OPTIONAL MATCH (lts:LoaiTaiSan:{TOPIC_LABEL} {{
  id: 'tai_san_chung_dua_vao_kinh_doanh', topic: '{TOPIC}'
}})
OPTIONAL MATCH (tt:ThoaThuan:{TOPIC_LABEL} {{
  id: 'thoa_thuan_kinh_doanh', topic: '{TOPIC}'
}})

WITH wl, kc, htt,
  [x IN collect(DISTINCT hv) + collect(DISTINCT lts) + collect(DISTINCT tt)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN kc = 'hinh_thuc_thoa_thuan' OR htt = 'loi_noi' THEN
      [x IN collect(DISTINCT tt) WHERE x IS NOT NULL]
    WHEN kc = 'quy_dinh_ap_dung' THEN
      [x IN collect(DISTINCT hv) + collect(DISTINCT tt) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hv) + collect(DISTINCT lts) + collect(DISTINCT tt)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: DuaTaiSanChungVaoKinhDoanhParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "whitelist_dieu_ids": _DIEU_25_WHITELIST if use_wl else [],
        **params.model_dump(),
    }


dua_tai_san_chung_vao_kinh_doanh = CypherTemplate(
    name="dua_tai_san_chung_vao_kinh_doanh",
    description=(
        "Thỏa thuận và quy định khi đưa tài sản chung vào kinh doanh (Đ25 k2, "
        "tham chiếu Đ36). Phù hợp khi hỏi 'đưa tài sản chung vào kinh doanh', "
        "'thỏa thuận bằng lời nói/văn bản' — KHÔNG dùng khi chỉ hỏi ai đại diện "
        "trong quan hệ kinh doanh (Đ25 k1)."
    ),
    params_schema=DuaTaiSanChungVaoKinhDoanhParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
