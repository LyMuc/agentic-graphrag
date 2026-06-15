"""Template — đại diện trong quan hệ kinh doanh chung (Đ25 k1)."""
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

_ROUTER_FIELDS = ("boi_canh_kinh_doanh",)
_DIEU_25_WHITELIST = ["Luat_HNGD_2014_Dieu_25"]


class DaiDienTrongQuanHeKinhDoanhParams(BaseModel):
    boi_canh_kinh_doanh: Literal[
        "kinh_doanh_chung",
        "mot_ben_ky_giao_dich",
        "co_thoa_thuan_dai_dien",
        "khong_ro",
    ] = Field(default="khong_ro")
    co_thoa_thuan_khac: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    nguoi_truc_tiep_tham_gia: Literal["vo", "chong", "ca_hai", "khong_ro"] = Field(
        default="khong_ro"
    )


_SEED_BODY = f"""
WITH $co_thoa_thuan_khac AS ctt, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (hv_kd:HanhVi:{TOPIC_LABEL} {{
  id: 'kinh_doanh_chung_cua_vo_chong', topic: '{TOPIC}'
}})
OPTIONAL MATCH (hv_tt:HanhVi:{TOPIC_LABEL} {{
  id: 'truc_tiep_tham_gia_quan_he_kinh_doanh', topic: '{TOPIC}'
}})
OPTIONAL MATCH (tt:ThoaThuan:{TOPIC_LABEL} {{
  id: 'thoa_thuan_nguoi_dai_dien_truoc_khi_kinh_doanh', topic: '{TOPIC}'
}})
OPTIONAL MATCH (nl:TruongHopNgoaiLe:{TOPIC_LABEL} {{
  id: 'co_thoa_thuan_hoac_luat_quy_dinh_khac_ve_dai_dien_kinh_doanh', topic: '{TOPIC}'
}})
OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{
  id: 'dai_dien_hop_phap_trong_kinh_doanh_chung', topic: '{TOPIC}'
}})
OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{
  id: 'co_thoa_thuan_khac_truoc_khi_kinh_doanh', topic: '{TOPIC}'
}})

WITH wl, ctt,
  [x IN collect(DISTINCT hv_kd) + collect(DISTINCT hv_tt) + collect(DISTINCT tt)
      + collect(DISTINCT nl) + collect(DISTINCT hq) + collect(DISTINCT dk)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN ctt = 'co' THEN
      [x IN collect(DISTINCT tt) + collect(DISTINCT nl) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hv_tt) + collect(DISTINCT hq)
          + collect(DISTINCT tt) + collect(DISTINCT nl)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: DaiDienTrongQuanHeKinhDoanhParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "whitelist_dieu_ids": _DIEU_25_WHITELIST if use_wl else [],
        **params.model_dump(),
    }


dai_dien_trong_quan_he_kinh_doanh = CypherTemplate(
    name="dai_dien_trong_quan_he_kinh_doanh",
    description=(
        "Ai là đại diện hợp pháp khi vợ chồng kinh doanh chung và thỏa thuận "
        "người đại diện trước khi tham gia (Đ25 k1). KHÔNG dùng cho câu hỏi "
        "đưa tài sản chung vào kinh doanh (Đ25 k2)."
    ),
    params_schema=DaiDienTrongQuanHeKinhDoanhParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
