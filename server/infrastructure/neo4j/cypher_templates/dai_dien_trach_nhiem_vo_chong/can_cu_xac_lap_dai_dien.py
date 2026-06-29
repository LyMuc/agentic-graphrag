"""Template — căn cứ xác lập đại diện giữa vợ và chồng (Đ24 k1)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.dai_dien_trach_nhiem_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("pham_vi_giao_dich",)
_DIEU_24_WHITELIST = ["Luat_HNGD_2014_Dieu_24"]


class CanCuXacLapDaiDienParams(BaseModel):
    pham_vi_giao_dich: Literal[
        "xac_lap", "thuc_hien", "cham_dut", "tai_san_chung", "tat_ca"
    ] = Field(
        default="tat_ca",
        description="Khía cạnh giao dịch được hỏi; mặc định tat_ca cho câu tổng quát.",
    )


_SEED_BODY = f"""
WITH $whitelist_dieu_ids AS wl

OPTIONAL MATCH (hv:HanhVi:{TOPIC_LABEL} {{
  id: 'xac_lap_thuc_hien_cham_dut_giao_dich', topic: '{TOPIC}'
}})
OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{
  id: 'can_cu_dai_dien_theo_luat_hngd_blds_luat_lien_quan', topic: '{TOPIC}'
}})

WITH wl,
  [x IN collect(DISTINCT hv) + collect(DISTINCT dk) WHERE x IS NOT NULL] AS seed_nodes,
  [x IN collect(DISTINCT hv) + collect(DISTINCT dk) WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: CanCuXacLapDaiDienParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "whitelist_dieu_ids": _DIEU_24_WHITELIST if use_wl else [],
        **params.model_dump(),
    }


can_cu_xac_lap_dai_dien = CypherTemplate(
    name="can_cu_xac_lap_dai_dien",
    description=(
        "Căn cứ xác lập đại diện giữa vợ và chồng trong xác lập, thực hiện hoặc "
        "chấm dứt giao dịch (Đ24 k1). Phù hợp khi hỏi 'căn cứ xác lập đại diện', "
        "'theo quy định pháp luật nào', 'đại diện thực hiện giao dịch tài sản chung'."
    ),
    params_schema=CanCuXacLapDaiDienParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
