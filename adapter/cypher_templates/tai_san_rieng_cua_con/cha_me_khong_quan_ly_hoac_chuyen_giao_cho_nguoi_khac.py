"""Template — cha mẹ không quản lý hoặc chuyển giao cho người khác (Đ76 k3-k4)."""
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

_ROUTER_FIELDS = ("truong_hop_quan_ly",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_76"]


class ChaMeKhongQuanLyHoacChuyenGiaoParams(BaseModel):
    truong_hop_quan_ly: Literal[
        "con_dang_duoc_nguoi_khac_giam_ho",
        "nguoi_tang_cho_hoac_de_lai_di_chuc_chi_dinh",
        "chuyen_giao_sang_nguoi_giam_ho",
        "truong_hop_khac_theo_luat",
        "khong_ro",
    ] = Field(description="con có người giám hộ khác, người chỉ định quản lý, hoặc chuyển giao.")
    khia_canh_quan_ly: Literal[
        "cha_me_co_quan_ly_khong",
        "ai_quan_ly",
        "co_the_chi_dinh_nguoi_quan_ly",
        "giao_lai_cho_nguoi_giam_ho",
        "tong_quat",
    ] = Field(description="cha mẹ có quản lý không, ai quản lý thay.")


_SEED_BODY = f"""
WITH $leaf_ids AS leaf_ids, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (leaf)
WHERE leaf.id IN leaf_ids AND leaf.topic = '{TOPIC}' AND '{TOPIC_LABEL}' IN labels(leaf)

WITH wl,
  collect(DISTINCT leaf) AS seed_nodes,
  [x IN collect(DISTINCT leaf) WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _resolve_leaf_ids(params: ChaMeKhongQuanLyHoacChuyenGiaoParams) -> list[str]:
    th = params.truong_hop_quan_ly
    if th == "chuyen_giao_sang_nguoi_giam_ho":
        return ["giao_tai_san_cho_nguoi_giam_ho_quan_ly"]
    if th == "nguoi_tang_cho_hoac_de_lai_di_chuc_chi_dinh":
        return ["chi_dinh_nguoi_khac_quan_ly_tai_san"]
    if th == "con_dang_duoc_nguoi_khac_giam_ho":
        return ["cha_me_khong_quan_ly_tai_san_cua_con"]
    return []


def _params_builder(params: ChaMeKhongQuanLyHoacChuyenGiaoParams) -> dict[str, Any]:
    leaf_ids = _resolve_leaf_ids(params)
    use_wl = not leaf_ids and should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "leaf_ids": leaf_ids,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


cha_me_khong_quan_ly_hoac_chuyen_giao_cho_nguoi_khac = CypherTemplate(
    name="cha_me_khong_quan_ly_hoac_chuyen_giao_cho_nguoi_khac",
    description=(
        "Xử lý trường hợp cha mẹ không quản lý vì con có người giám hộ khác hoặc người tặng cho/"
        "di chúc chỉ định người quản lý (Đ76 k3), và chuyển giao cho người giám hộ (Đ76 k4). "
        "Ví dụ: Cha mẹ có phải quản lý tài sản khi con đang do người khác giám hộ không?; "
        "Con chưa thành niên được Tòa án giao cho ông bà giám hộ thì ai quản lý tài sản riêng?"
    ),
    params_schema=ChaMeKhongQuanLyHoacChuyenGiaoParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
