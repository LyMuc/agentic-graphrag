"""Template — bồi thường thiệt hại do con gây ra (Đ74)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_cha_me_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
)

_DIEU_WHITELIST: list[str] = []


class BoiThuongThietHaiDoConGayRaParams(BaseModel):
    tinh_trang_cua_con_gay_thiet_hai: Literal[
        "chua_thanh_nien",
        "da_thanh_nien_mat_nang_luc_hanh_vi",
        "khong_ro",
    ] = Field(description="Tuổi dưới 18 -> chua_thanh_nien.")
    khia_canh_boi_thuong: Literal[
        "co_phai_boi_thuong",
        "can_cu_trach_nhiem",
        "pham_vi_boi_thuong",
        "tong_quat",
    ] = Field(description="có phải bồi thường -> co_phai_boi_thuong.")


_SEED_BODY = f"""
WITH $whitelist_dieu_ids AS wl

OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{
  id: 'con_thuoc_dien_luat_dinh_gay_thiet_hai', topic: '{TOPIC}'
}})

OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL} {{
  id: 'cha_me_boi_thuong_thiet_hai_do_con_gay_ra', topic: '{TOPIC}'
}})

WITH wl,
  collect(DISTINCT dk) + collect(DISTINCT nv) AS seed_nodes,
  [x IN collect(DISTINCT dk) + collect(DISTINCT nv) WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: BoiThuongThietHaiDoConGayRaParams) -> dict[str, Any]:
    return {
        "whitelist_dieu_ids": _DIEU_WHITELIST,
    }


boi_thuong_thiet_hai_do_con_gay_ra = CypherTemplate(
    name="boi_thuong_thiet_hai_do_con_gay_ra",
    description=(
        "Trả lời nghĩa vụ cha mẹ bồi thường thiệt hại do con chưa thành niên hoặc con đã thành niên "
        "mất năng lực hành vi dân sự gây ra theo Điều 74. "
        "Dùng khi hỏi nguyên tắc chung cha mẹ có phải bồi thường, "
        "hoặc con cụ thể (vd. 12 tuổi) làm vỡ/hỏng tài sản người khác."
    ),
    params_schema=BoiThuongThietHaiDoConGayRaParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
