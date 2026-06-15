"""Template — con từ đủ 15 tuổi tự quản lý hoặc nhờ cha mẹ (Đ76 k1)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.tai_san_rieng_cua_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_quan_ly",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_76"]


class QuanLyTaiSanConTuDu15TuoiParams(BaseModel):
    tuoi_con: int | None = Field(description="Tuổi con nếu câu hỏi nêu rõ.")
    lua_chon_quan_ly: Literal[
        "tu_quan_ly",
        "nho_cha_me_quan_ly",
        "ca_hai_lua_chon",
        "khong_ro",
    ] = Field(description="tự quản lý -> tu_quan_ly; nhờ cha mẹ -> nho_cha_me_quan_ly.")
    khia_canh_quan_ly: Literal[
        "co_quyen_tu_quan_ly",
        "co_the_nho_cha_me",
        "liet_ke_lua_chon",
        "tong_quat",
    ] = Field(description="hỏi quyền tự quản lý hoặc nhờ cha mẹ quản lý.")


_SEED_BODY = f"""
WITH $leaf_ids AS leaf_ids, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (leaf)
WHERE leaf.id IN leaf_ids AND leaf.topic = '{TOPIC}' AND '{TOPIC_LABEL}' IN labels(leaf)

WITH wl,
  collect(DISTINCT leaf) AS seed_nodes,
  [x IN collect(DISTINCT leaf) WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _resolve_leaf_ids(params: QuanLyTaiSanConTuDu15TuoiParams) -> list[str]:
    lua_chon = params.lua_chon_quan_ly
    kc = params.khia_canh_quan_ly
    if lua_chon == "tu_quan_ly" or kc == "co_quyen_tu_quan_ly":
        return ["quyen_tu_quan_ly_tai_san_tu_du_15_tuoi"]
    if lua_chon == "nho_cha_me_quan_ly" or kc == "co_the_nho_cha_me":
        return ["quyen_nho_cha_me_quan_ly_tai_san"]
    if lua_chon in ("ca_hai_lua_chon", "khong_ro") or kc == "liet_ke_lua_chon":
        return [
            "quyen_tu_quan_ly_tai_san_tu_du_15_tuoi",
            "quyen_nho_cha_me_quan_ly_tai_san",
        ]
    return []


def _params_builder(params: QuanLyTaiSanConTuDu15TuoiParams) -> dict[str, Any]:
    leaf_ids = _resolve_leaf_ids(params)
    use_wl = not leaf_ids and should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "leaf_ids": leaf_ids,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


quan_ly_tai_san_con_tu_du_15_tuoi = CypherTemplate(
    name="quan_ly_tai_san_con_tu_du_15_tuoi",
    description=(
        "Trả lời hai lựa chọn tại khoản 1 Điều 76: con từ đủ 15 tuổi có thể tự quản lý hoặc "
        "nhờ cha mẹ quản lý tài sản riêng. Không xử lý định đoạt tài sản 15-17 tuổi. "
        "Ví dụ: Con từ đủ 15 tuổi có thể tự quản lý tài sản riêng của mình không?; "
        "Con 17 tuổi không muốn tự quản lý tài sản có thể nhờ cha mẹ quản lý giúp không?"
    ),
    params_schema=QuanLyTaiSanConTuDu15TuoiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
