"""Template — người có yêu cầu xác định đã chết (Đ92)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.xac_dinh_cha_me_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
)

_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_92"]


class XacDinhKhiNguoiYeuCauDaChetParams(BaseModel):
    nguoi_co_yeu_cau_da_chet: Literal["co", "khong_ro"] = Field(default="co")
    nguoi_yeu_cau_thay: Literal["nguoi_than_thich", "gia_dinh", "khong_ro"] = Field(
        default="khong_ro"
    )
    doi_tuong_xac_dinh: Literal["cha", "me", "con", "cha_me_con", "khong_ro"] = Field(
        default="khong_ro"
    )


_SEED_BODY = f"""
WITH $use_whitelist AS uw, $whitelist_dieu_ids AS wl

MATCH (dk:DieuKien:{TOPIC_LABEL} {{
  id: 'nguoi_co_yeu_cau_xac_dinh_da_chet', topic: '{TOPIC}'
}})

MATCH (q:Quyen:{TOPIC_LABEL} {{
  id: 'nguoi_than_thich_yeu_cau_xac_dinh_thay', topic: '{TOPIC}'
}})

MATCH (tq:ThamQuyen:{TOPIC_LABEL} {{
  id: 'toa_an_xac_dinh_cho_nguoi_yeu_cau_da_chet', topic: '{TOPIC}'
}})

WITH wl, uw, collect(DISTINCT dk) + collect(DISTINCT q) + collect(DISTINCT tq) AS seed_nodes,
  CASE WHEN uw THEN [] ELSE [dk, q, tq] END AS leaf_seed_nodes
"""


def _params_builder(params: XacDinhKhiNguoiYeuCauDaChetParams) -> dict[str, Any]:
    use_wl = (
        params.nguoi_co_yeu_cau_da_chet == "khong_ro"
        and params.nguoi_yeu_cau_thay == "khong_ro"
        and params.doi_tuong_xac_dinh == "khong_ro"
    )
    return {
        "use_whitelist": use_wl,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


xac_dinh_khi_nguoi_yeu_cau_da_chet = CypherTemplate(
    name="xac_dinh_khi_nguoi_yeu_cau_da_chet",
    description=(
        "Người có yêu cầu xác định cha, mẹ, con đã chết; người thân thích yêu cầu "
        "Tòa án xác định thay (Đ92). "
        "Ví dụ: 'ai có quyền yêu cầu thay'; 'gia đình yêu cầu xác định con cho người anh đã mất'."
    ),
    params_schema=XacDinhKhiNguoiYeuCauDaChetParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
