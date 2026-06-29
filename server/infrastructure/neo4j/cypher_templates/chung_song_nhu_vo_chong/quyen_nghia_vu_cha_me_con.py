"""Template — quyền nghĩa vụ cha mẹ con khi không đăng ký (Đ14 K1, Đ15)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.chung_song_nhu_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_con",)
_DIEU_14_15_WHITELIST = [
    "Luat_HNGD_2014_Dieu_14",
    "Luat_HNGD_2014_Dieu_15",
]


class QuyenNghiaVuChaMeConParams(BaseModel):
    khia_canh_con: Literal[
        "nuoi_con",
        "cham_soc_giao_duc",
        "cap_duong",
        "quyen",
        "nghia_vu",
        "tong_quat",
    ] = Field(
        description=(
            "Ai nuôi con -> nuoi_con; chăm sóc/giáo dục -> cham_soc_giao_duc; "
            "cấp dưỡng -> cap_duong; quyền -> quyen; nghĩa vụ -> nghia_vu."
        )
    )
    chu_the_quan_tam: Literal[
        "cha", "me", "ca_hai", "con", "khong_ro"
    ] = Field(description="Cha/mẹ/cả hai/con; hỏi ai nuôi không rõ -> khong_ro.")


_SEED_BODY = f"""
WITH $kc AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (cm:ChuThe:{TOPIC_LABEL} {{id: 'cha_me_khong_dang_ky_ket_hon', topic: '{TOPIC}'}})
OPTIONAL MATCH (con:ChuThe:{TOPIC_LABEL} {{id: 'con_cua_nam_nu_chung_song', topic: '{TOPIC}'}})
OPTIONAL MATCH (q:Quyen:{TOPIC_LABEL} {{id: 'quyen_cua_cha_me_va_con_theo_quy_dinh_chung', topic: '{TOPIC}'}})
OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_cua_cha_me_va_con_theo_quy_dinh_chung', topic: '{TOPIC}'}})
OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{id: 'quyen_nghia_vu_voi_con_giai_quyet_theo_quy_dinh_cha_me_con', topic: '{TOPIC}'}})

WITH wl, kc,
  [x IN collect(DISTINCT cm) + collect(DISTINCT con)
       + collect(DISTINCT q) + collect(DISTINCT nv) + collect(DISTINCT hq)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'quyen' THEN
      [x IN collect(DISTINCT q) + collect(DISTINCT hq) WHERE x IS NOT NULL]
    WHEN 'nghia_vu' THEN
      [x IN collect(DISTINCT nv) + collect(DISTINCT hq) WHERE x IS NOT NULL]
    WHEN 'cap_duong' THEN
      [x IN collect(DISTINCT nv) + collect(DISTINCT hq) WHERE x IS NOT NULL]
    WHEN 'nuoi_con' THEN
      [x IN collect(DISTINCT q) + collect(DISTINCT nv) + collect(DISTINCT hq)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT q) + collect(DISTINCT nv) + collect(DISTINCT hq)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: QuyenNghiaVuChaMeConParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "kc": params.khia_canh_con,
        "whitelist_dieu_ids": _DIEU_14_15_WHITELIST if use_wl else [],
    }


quyen_nghia_vu_cha_me_con = CypherTemplate(
    name="quyen_nghia_vu_cha_me_con",
    description=(
        "Quyền, nghĩa vụ cha mẹ và con khi cha mẹ chung sống không đăng ký kết hôn "
        "(Đ15; gateway Đ14 K1). Không kết luận mẹ hoặc cha mặc nhiên được nuôi con. "
        "Ví dụ: Con được sinh ra khi cha mẹ không đăng ký kết hôn thì ai được "
        "quyền nuôi con?"
    ),
    params_schema=QuyenNghiaVuChaMeConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
