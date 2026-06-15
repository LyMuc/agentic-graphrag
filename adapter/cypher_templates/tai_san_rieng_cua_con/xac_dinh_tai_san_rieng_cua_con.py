"""Template — xác định tài sản riêng của con (Đ75 khoản 1)."""
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

_ROUTER_FIELDS = ("khia_canh_tai_san",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_75"]

_LOAI_TAI_SAN_LEAVES = [
    "tai_san_thua_ke_rieng",
    "tai_san_tang_cho_rieng",
    "thu_nhap_lao_dong",
    "hoa_loi_loi_tuc",
    "thu_nhap_hop_phap_khac",
    "tai_san_hinh_thanh_tu_tai_san_rieng",
]


class XacDinhTaiSanRiengCuaConParams(BaseModel):
    khia_canh_tai_san: Literal[
        "quyen_co_tai_san_rieng",
        "liet_ke_thanh_phan",
        "xac_dinh_co_phai_tai_san_rieng",
        "tong_quat",
    ] = Field(
        description=(
            "có tài sản riêng -> quyen_co_tai_san_rieng; "
            "gồm những gì -> liet_ke_thanh_phan; "
            "có phải tài sản riêng -> xac_dinh_co_phai_tai_san_rieng."
        )
    )
    loai_tai_san: Literal[
        "tai_san_thua_ke_rieng",
        "tai_san_tang_cho_rieng",
        "thu_nhap_lao_dong",
        "hoa_loi_loi_tuc",
        "thu_nhap_hop_phap_khac",
        "tai_san_hinh_thanh_tu_tai_san_rieng",
        "tat_ca",
        "khong_ro",
    ] = Field(description="Loại tài sản cụ thể theo khoản 1 Điều 75.")


_SEED_BODY = f"""
WITH $leaf_ids AS leaf_ids, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (leaf)
WHERE leaf.id IN leaf_ids AND leaf.topic = '{TOPIC}' AND '{TOPIC_LABEL}' IN labels(leaf)

WITH wl,
  collect(DISTINCT leaf) AS seed_nodes,
  [x IN collect(DISTINCT leaf) WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _resolve_leaf_ids(kc: str, loai: str) -> list[str]:
    if kc == "quyen_co_tai_san_rieng":
        return ["quyen_co_tai_san_rieng"]
    if kc == "liet_ke_thanh_phan" or loai == "tat_ca":
        return list(_LOAI_TAI_SAN_LEAVES)
    if loai not in ("khong_ro", "tat_ca"):
        return [loai]
    return []


def _params_builder(params: XacDinhTaiSanRiengCuaConParams) -> dict[str, Any]:
    leaf_ids = _resolve_leaf_ids(params.khia_canh_tai_san, params.loai_tai_san)
    use_wl = not leaf_ids and should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "leaf_ids": leaf_ids,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


xac_dinh_tai_san_rieng_cua_con = CypherTemplate(
    name="xac_dinh_tai_san_rieng_cua_con",
    description=(
        "Trả lời quyền có tài sản riêng, liệt kê thành phần tài sản riêng, hoặc xác định một "
        "tài sản theo nguồn gốc có thuộc tài sản riêng của con hay không (Đ75 k1). "
        "Ví dụ: Con có quyền có tài sản riêng theo Luật Hôn nhân và gia đình không?; "
        "Hoa lợi, lợi tức phát sinh từ tài sản riêng của con thuộc loại tài sản gì?"
    ),
    params_schema=XacDinhTaiSanRiengCuaConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
