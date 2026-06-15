"""Template — ủy quyền giao dịch cần sự đồng ý của cả hai (Đ24 k2)."""
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

_ROUTER_FIELDS = ("co_uy_quyen_hoac_dong_y",)
_DIEU_24_WHITELIST = ["Luat_HNGD_2014_Dieu_24"]


class UyQuyenGiaoDichCanDongYParams(BaseModel):
    hanh_vi_giao_dich: Literal[
        "xac_lap", "thuc_hien", "cham_dut", "ban_chuyen_nhuong", "tat_ca"
    ] = Field(default="tat_ca")
    doi_tuong_giao_dich: Literal[
        "giao_dich_can_dong_y_ca_hai", "tai_san_chung", "khong_ro"
    ] = Field(default="khong_ro")
    co_uy_quyen_hoac_dong_y: Literal["co", "khong", "khong_ro"] = Field(
        default="khong_ro"
    )


_SEED_BODY = f"""
WITH $co_uy_quyen_hoac_dong_y AS cu, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (hv_uq:HanhVi:{TOPIC_LABEL} {{
  id: 'uy_quyen_giua_vo_chong', topic: '{TOPIC}'
}})
OPTIONAL MATCH (tt:ThoaThuan:{TOPIC_LABEL} {{
  id: 'thoa_thuan_uy_quyen_giua_vo_chong', topic: '{TOPIC}'
}})
OPTIONAL MATCH (q:Quyen:{TOPIC_LABEL} {{
  id: 'quyen_uy_quyen_cho_nhau', topic: '{TOPIC}'
}})
OPTIONAL MATCH (gd: GiaoDich:{TOPIC_LABEL} {{
  id: 'giao_dich_can_su_dong_y_cua_ca_hai', topic: '{TOPIC}'
}})
OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{
  id: 'dai_dien_hop_phap_trong_giao_dich', topic: '{TOPIC}'
}})

WITH wl, cu,
  [x IN collect(DISTINCT hv_uq) + collect(DISTINCT tt) + collect(DISTINCT q)
      + collect(DISTINCT gd) + collect(DISTINCT hq)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE cu
    WHEN 'co' THEN
      [x IN collect(DISTINCT q) + collect(DISTINCT tt) WHERE x IS NOT NULL]
    WHEN 'khong' THEN
      [x IN collect(DISTINCT gd) + collect(DISTINCT hv_uq) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT q) + collect(DISTINCT tt) + collect(DISTINCT gd)
          + collect(DISTINCT hv_uq)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: UyQuyenGiaoDichCanDongYParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "whitelist_dieu_ids": _DIEU_24_WHITELIST if use_wl else [],
        **params.model_dump(),
    }


uy_quyen_giao_dich_can_dong_y = CypherTemplate(
    name="uy_quyen_giao_dich_can_dong_y",
    description=(
        "Ủy quyền cho nhau hoặc một bên tự ký giao dịch cần sự đồng ý của cả hai "
        "(Đ24 k2). Phù hợp khi hỏi 'ủy quyền', 'một mình ký', 'không đồng ý' — "
        "KHÔNG dùng khi hỏi hiệu lực/vô hiệu theo Đ26 k2."
    ),
    params_schema=UyQuyenGiaoDichCanDongYParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
