"""Template — định đoạt tài sản con dưới 15 tuổi (Đ77 k1)."""
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


class DinhDoatTaiSanConDuoi15TuoiParams(BaseModel):
    nguoi_dang_quan_ly: Literal["cha_me", "nguoi_giam_ho", "khong_ro"] = Field(
        description="cha mẹ hoặc người giám hộ đang quản lý tài sản."
    )
    tuoi_con: int | None = Field(description="Tuổi con; từ 9 trở lên kích hoạt xem xét nguyện vọng.")
    khia_canh_dinh_doat: Literal[
        "co_quyen_dinh_doat",
        "vi_loi_ich_cua_con",
        "xem_xet_nguyen_vong",
        "tong_quat",
    ] = Field(description="quyền định đoạt vì lợi ích con, xem xét nguyện vọng từ 9 tuổi.")
    loai_tai_san: Literal[
        "tai_san_rieng_cua_con",
        "bat_dong_san",
        "dong_san_phai_dang_ky",
        "khong_ro",
    ] = Field(description="loại tài sản; con dưới 15 không chuyển sang ngoại lệ Đ77 k2.")


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


def _resolve_ids(params: DinhDoatTaiSanConDuoi15TuoiParams) -> tuple[list[str], list[str]]:
    leaf_ids = [
        "quyen_dinh_doat_tai_san_con_duoi_15_cua_nguoi_quan_ly",
        "quan_ly_vi_loi_ich_cua_con",
    ]
    trace_ids: list[str] = []
    if params.khia_canh_dinh_doat == "xem_xet_nguyen_vong" or (
        params.tuoi_con is not None and params.tuoi_con >= 9
    ):
        leaf_ids.append("nghia_vu_xem_xet_nguyen_vong_con_tu_du_09_tuoi")
        trace_ids.append("con_tu_du_09_tuoi")
    return leaf_ids, trace_ids


def _params_builder(params: DinhDoatTaiSanConDuoi15TuoiParams) -> dict[str, Any]:
    leaf_ids, trace_ids = _resolve_ids(params)
    use_wl = not leaf_ids and should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "leaf_ids": leaf_ids,
        "trace_ids": trace_ids,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


dinh_doat_tai_san_con_duoi_15_tuoi = CypherTemplate(
    name="dinh_doat_tai_san_con_duoi_15_tuoi",
    description=(
        "Trả lời quyền định đoạt của cha mẹ hoặc người giám hộ đối với tài sản con dưới 15 tuổi "
        "vì lợi ích của con; xem xét nguyện vọng từ đủ 09 tuổi (Đ77 k1). "
        "Ví dụ: Cha mẹ quản lý tài sản con dưới 15 tuổi có quyền định đoạt vì lợi ích con không?; "
        "Cha mẹ muốn bán xe đứng tên con 10 tuổi có phải xem xét nguyện vọng của con không?"
    ),
    params_schema=DinhDoatTaiSanConDuoi15TuoiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
