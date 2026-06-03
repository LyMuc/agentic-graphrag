"""Template 6 — TÀI SẢN CHUNG ĐƯA VÀO KINH DOANH KHI LY HÔN (Đ64).

Coverage feat_llm stt: 19,20.
Seed kiểu semantic graph: DAN_TOI từ HanhVi kinh doanh.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.chia_tai_san_sau_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("nguoi_dang_kinh_doanh",)
_DIEU_64_WHITELIST = ["Luat_HNGD_2014_Dieu_64"]


class TaiSanChungDuaVaoKinhDoanhParams(BaseModel):
    nguoi_dang_kinh_doanh: Literal["vo", "chong", "ca_hai", "khong_ro"] = Field(
        default="khong_ro"
    )
    tai_san_chung_lien_quan_kinh_doanh: Literal["co", "khong_ro"] = Field(
        default="khong_ro",
        description="Map 'đưa vào kinh doanh/góp vốn/làm ăn'→co.",
    )
    phap_luat_kinh_doanh_khac: Literal["co", "khong", "khong_ro"] = Field(
        default="khong_ro"
    )


_SEED_BODY = f"""
// ============================================================
// PHẦN 1 — SEED semantic graph (tài sản kinh doanh — Đ64)
// ============================================================
WITH $whitelist_dieu_ids AS wl

MATCH (anchor:HanhVi:{TOPIC_LABEL} {{
  id: 'chia_tai_san_chung_dua_vao_kinh_doanh',
  topic: '{TOPIC}'
}})

OPTIONAL MATCH (anchor)-[:DAN_TOI]->(hq:HauQua:{TOPIC_LABEL} {{
  id: 'nhan_tai_san_kinh_doanh_va_thanh_toan_gia_tri'
}})

WITH wl,
  collect(DISTINCT anchor) + collect(DISTINCT hq) AS seed_nodes,
  collect(DISTINCT anchor) + collect(DISTINCT hq) AS leaf_seed_nodes
"""


def _params_builder(params: TaiSanChungDuaVaoKinhDoanhParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "whitelist_dieu_ids": _DIEU_64_WHITELIST if use_wl else [],
        **params.model_dump(),
    }


tai_san_chung_dua_vao_kinh_doanh_khi_ly_hon = CypherTemplate(
    name="tai_san_chung_dua_vao_kinh_doanh_khi_ly_hon",
    description=(
        "Tài sản chung của vợ chồng đã đưa vào hoạt động kinh doanh khi ly hôn "
        "(Đ64): bên đang kinh doanh nhận tài sản và thanh toán giá trị cho bên kia. "
        "Phù hợp khi có 'đưa vào kinh doanh', 'tài sản kinh doanh', 'góp vốn', "
        "'làm ăn kinh doanh' và hỏi chia tài sản khi ly hôn."
    ),
    params_schema=TaiSanChungDuaVaoKinhDoanhParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
