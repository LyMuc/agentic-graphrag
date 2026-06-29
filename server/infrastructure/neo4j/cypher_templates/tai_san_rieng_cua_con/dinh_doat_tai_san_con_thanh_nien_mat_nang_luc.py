"""Template — định đoạt tài sản con đã thành niên mất năng lực (Đ77 k3)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.tai_san_rieng_cua_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_dinh_doat",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_77"]


class DinhDoatTaiSanConThanhNienMatNangLucParams(BaseModel):
    nguoi_thuc_hien: Literal["nguoi_giam_ho", "cha_me", "khong_ro"] = Field(
        description="người thực hiện định đoạt; quy tắc luật là người giám hộ."
    )
    khia_canh_dinh_doat: Literal[
        "ai_thuc_hien",
        "nguoi_giam_ho_co_quyen_khong",
        "tong_quat",
    ] = Field(description="ai có quyền định đoạt tài sản con đã thành niên mất năng lực.")


_SEED_BODY = f"""
WITH $leaf_ids AS leaf_ids, $trace_ids AS trace_ids, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (leaf)
WHERE leaf.id IN leaf_ids AND leaf.topic = '{TOPIC}' AND '{TOPIC_LABEL}' IN labels(leaf)

OPTIONAL MATCH (trace)
WHERE trace.id IN trace_ids AND trace.topic = '{TOPIC}' AND '{TOPIC_LABEL}' IN labels(trace)

WITH wl,
  collect(DISTINCT leaf) + collect(DISTINCT trace) AS seed_nodes,
  [x IN collect(DISTINCT leaf) WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _resolve_ids(
    params: DinhDoatTaiSanConThanhNienMatNangLucParams,
) -> tuple[list[str], list[str]]:
    leaf_ids = ["quyen_dinh_doat_tai_san_con_thanh_nien_mat_nang_luc_cua_nguoi_giam_ho"]
    trace_ids = ["con_mat_nang_luc_hanh_vi_dan_su", "nguoi_giam_ho"]
    return leaf_ids, trace_ids


def _params_builder(params: DinhDoatTaiSanConThanhNienMatNangLucParams) -> dict[str, Any]:
    leaf_ids, trace_ids = _resolve_ids(params)
    use_wl = not leaf_ids and should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "leaf_ids": leaf_ids,
        "trace_ids": trace_ids,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


dinh_doat_tai_san_con_thanh_nien_mat_nang_luc = CypherTemplate(
    name="dinh_doat_tai_san_con_thanh_nien_mat_nang_luc",
    description=(
        "Trả lời việc định đoạt tài sản của con đã thành niên mất năng lực hành vi dân sự "
        "do người giám hộ thực hiện theo khoản 3 Điều 77. "
        "Ví dụ: Ai có quyền định đoạt tài sản riêng của con đã thành niên mất năng lực hành vi dân sự?; "
        "Người giám hộ có quyền định đoạt tài sản riêng của con đã thành niên mất năng lực không?"
    ),
    params_schema=DinhDoatTaiSanConThanhNienMatNangLucParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
