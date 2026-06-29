"""Template — kết hôn lại sau ly hôn (Đ9 K2 Luật HNGD)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_ket_hon_lai",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_9"]


class KetHonLaiSauLyHonParams(BaseModel):
    tinh_trang_truoc_do: Literal["da_ly_hon", "chua_ly_hon", "khong_ro"] = Field(
        description="Đã ly hôn/có bản án ly hôn -> da_ly_hon."
    )
    khia_canh_ket_hon_lai: Literal[
        "co_duoc_ket_hon_lai",
        "co_phai_dang_ky",
        "xac_lap_lai_quan_he",
        "tong_quat",
    ] = Field(
        description=(
            "Có được kết hôn lại -> co_duoc_ket_hon_lai; có phải đăng ký -> co_phai_dang_ky; "
            "xác lập lại quan hệ vợ chồng -> xac_lap_lai_quan_he."
        )
    )


_SEED_BODY = f"""
WITH $kc AS kc, $whitelist_dieu_ids AS wl

MATCH (hv:HanhVi:{TOPIC_LABEL} {{id: 'ket_hon_lai_sau_khi_da_ly_hon', topic: '{TOPIC}'}})

OPTIONAL MATCH (hv)-[:DAN_TOI]->(hq:HauQua:{TOPIC_LABEL} {{id: 'phai_dang_ky_khi_xac_lap_lai_quan_he_sau_ly_hon', topic: '{TOPIC}'}})
WHERE kc IN ['co_phai_dang_ky', 'xac_lap_lai_quan_he', 'tong_quat']

OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{id: 'du_dieu_kien_ket_hon', topic: '{TOPIC}'}})
WHERE kc IN ['co_duoc_ket_hon_lai', 'tong_quat']
OPTIONAL MATCH (dk)-[:LIEN_QUAN]->(dk_leaf:DieuKien:{TOPIC_LABEL})
WHERE dk IS NOT NULL AND dk_leaf.topic = '{TOPIC}'

WITH wl, kc,
  [x IN collect(DISTINCT hv) + collect(DISTINCT hq)
       + collect(DISTINCT dk) + collect(DISTINCT dk_leaf)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'co_phai_dang_ky' THEN
      [x IN collect(DISTINCT hq) WHERE x IS NOT NULL]
    WHEN 'xac_lap_lai_quan_he' THEN
      [x IN collect(DISTINCT hq) + collect(DISTINCT hv) WHERE x IS NOT NULL]
    WHEN 'co_duoc_ket_hon_lai' THEN
      [x IN collect(DISTINCT hv) + collect(DISTINCT dk) + collect(DISTINCT dk_leaf)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hv) + collect(DISTINCT hq) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: KetHonLaiSauLyHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "kc": params.khia_canh_ket_hon_lai,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


ket_hon_lai_sau_ly_hon = CypherTemplate(
    name="ket_hon_lai_sau_ly_hon",
    description=(
        "Xử lý việc hai người từng là vợ chồng, đã ly hôn, muốn xác lập lại quan hệ vợ chồng "
        "— phải đăng ký kết hôn lại theo Đ9 K2 và vẫn phải đáp ứng điều kiện kết hôn. "
        "Ví dụ: Hai người đã ly hôn có được kết hôn lại không?; "
        "Quay lại sau ly hôn có phải đăng ký không?"
    ),
    params_schema=KetHonLaiSauLyHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
