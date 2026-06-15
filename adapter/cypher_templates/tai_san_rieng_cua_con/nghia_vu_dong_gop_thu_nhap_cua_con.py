"""Template — nghĩa vụ đóng góp thu nhập của con (Đ75 k2-k3)."""
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

_ROUTER_FIELDS = ("khia_canh_dong_gop",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_75"]


class NghiaVuDongGopThuNhapCuaConParams(BaseModel):
    nhom_tuoi: Literal["tu_du_15_chua_thanh_nien", "da_thanh_nien", "khong_ro"] = Field(
        description="15-17 tuổi -> tu_du_15_chua_thanh_nien; đã thành niên -> da_thanh_nien."
    )
    song_chung_voi_cha_me: Literal["co", "khong", "khong_ro"] = Field(
        description="sống chung với cha mẹ -> co."
    )
    co_thu_nhap: Literal["co", "khong", "khong_ro"] = Field(
        description="có thu nhập để đóng góp -> co (chỉ áp dụng khoản 2 nếu câu nêu rõ)."
    )
    khia_canh_dong_gop: Literal[
        "cham_lo_doi_song_chung",
        "dong_gop_nhu_cau_thiet_yeu",
        "dong_gop_nhu_cau_gia_dinh",
        "tong_quat",
    ] = Field(
        description=(
            "chăm lo đời sống chung -> cham_lo_doi_song_chung; "
            "nhu cầu thiết yếu -> dong_gop_nhu_cau_thiet_yeu; "
            "nhu cầu gia đình (Đ75 k3) -> dong_gop_nhu_cau_gia_dinh."
        )
    )


_SEED_BODY = f"""
WITH $leaf_ids AS leaf_ids, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (leaf)
WHERE leaf.id IN leaf_ids AND leaf.topic = '{TOPIC}' AND '{TOPIC_LABEL}' IN labels(leaf)

WITH wl,
  collect(DISTINCT leaf) AS seed_nodes,
  [x IN collect(DISTINCT leaf) WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _resolve_leaf_ids(params: NghiaVuDongGopThuNhapCuaConParams) -> list[str]:
    if params.nhom_tuoi == "da_thanh_nien" or params.khia_canh_dong_gop == "dong_gop_nhu_cau_gia_dinh":
        return ["nghia_vu_dong_gop_thu_nhap_cua_con_thanh_nien"]
    if params.khia_canh_dong_gop == "cham_lo_doi_song_chung":
        return ["nghia_vu_cham_lo_doi_song_chung_cua_gia_dinh"]
    if params.khia_canh_dong_gop == "dong_gop_nhu_cau_thiet_yeu":
        return ["nghia_vu_dong_gop_nhu_cau_thiet_yeu_khi_co_thu_nhap"]
    return []


def _params_builder(params: NghiaVuDongGopThuNhapCuaConParams) -> dict[str, Any]:
    leaf_ids = _resolve_leaf_ids(params)
    use_wl = not leaf_ids and should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "leaf_ids": leaf_ids,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


nghia_vu_dong_gop_thu_nhap_cua_con = CypherTemplate(
    name="nghia_vu_dong_gop_thu_nhap_cua_con",
    description=(
        "Phân biệt nghĩa vụ của con từ đủ 15 tuổi sống chung với cha mẹ (Đ75 k2) và nghĩa vụ "
        "của con đã thành niên (Đ75 k3). "
        "Ví dụ: Con 16 tuổi sống chung với cha mẹ có phải đóng góp thu nhập lao động vào "
        "chi tiêu gia đình không?; "
        "Con đã thành niên sống chung với cha mẹ có nghĩa vụ đóng góp thu nhập vào nhu cầu "
        "của gia đình không?"
    ),
    params_schema=NghiaVuDongGopThuNhapCuaConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
