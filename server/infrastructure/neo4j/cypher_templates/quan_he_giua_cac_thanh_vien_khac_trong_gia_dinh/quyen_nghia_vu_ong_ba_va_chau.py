"""Template — quyền, nghĩa vụ chung ông bà và cháu (Đ104)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_ong_ba_chau",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_104"]


class QuyenNghiaVuOngBaVaChauParams(BaseModel):
    chieu_ong_ba_chau: Literal[
        "ong_ba_doi_voi_chau",
        "chau_doi_voi_ong_ba",
        "hai_chieu",
        "khong_ro",
    ] = Field(description="chiều ông bà-cháu.")
    noi_dung_ong_ba_chau: Literal[
        "trong_nom_cham_soc_giao_duc",
        "song_mau_muc_neu_guong",
        "kinh_trong_cham_soc_phung_duong",
        "tong_hop",
    ] = Field(description="nội dung quyền nghĩa vụ chăm sóc thường xuyên.")
    khia_canh_ong_ba_chau: Literal[
        "liet_ke",
        "co_nghia_vu_khong",
        "tong_quat",
    ] = Field(description="liệt kê / đánh giá có nghĩa vụ không.")


_SEED_BODY = f"""
WITH $chieu AS ch, $noi_dung AS nd, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (q_ob:Quyen:{TOPIC_LABEL} {{
  id: 'quyen_ong_ba_trong_nom_cham_soc_giao_duc_chau', topic: '{TOPIC}'
}})
WHERE ch IN ['ong_ba_doi_voi_chau', 'hai_chieu', 'khong_ro']
OPTIONAL MATCH (nv_tn:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_ong_ba_trong_nom_cham_soc_giao_duc_chau', topic: '{TOPIC}'
}})
WHERE ch IN ['ong_ba_doi_voi_chau', 'hai_chieu', 'khong_ro']
  OR nd IN ['trong_nom_cham_soc_giao_duc', 'tong_hop']
OPTIONAL MATCH (nv_sm:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_ong_ba_song_mau_muc_neu_guong', topic: '{TOPIC}'
}})
WHERE ch IN ['ong_ba_doi_voi_chau', 'hai_chieu', 'khong_ro']
  AND nd IN ['song_mau_muc_neu_guong', 'tong_hop']

OPTIONAL MATCH (nv_ch:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_chau_kinh_trong_cham_soc_phung_duong_ong_ba', topic: '{TOPIC}'
}})
WHERE ch IN ['chau_doi_voi_ong_ba', 'hai_chieu', 'khong_ro']
  OR nd IN ['kinh_trong_cham_soc_phung_duong', 'tong_hop']

WITH wl,
  collect(DISTINCT q_ob) + collect(DISTINCT nv_tn) + collect(DISTINCT nv_sm)
    + collect(DISTINCT nv_ch) AS seed_nodes,
  [x IN collect(DISTINCT q_ob) + collect(DISTINCT nv_tn) + collect(DISTINCT nv_sm)
       + collect(DISTINCT nv_ch)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: QuyenNghiaVuOngBaVaChauParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "chieu": params.chieu_ong_ba_chau,
        "noi_dung": params.noi_dung_ong_ba_chau,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


quyen_nghia_vu_ong_ba_va_chau = CypherTemplate(
    name="quyen_nghia_vu_ong_ba_va_chau",
    description=(
        "Dùng cho quyền, nghĩa vụ chăm sóc thường xuyên giữa ông bà nội/ngoại và cháu: "
        "trông nom, chăm sóc, giáo dục, nêu gương, kính trọng, phụng dưỡng. "
        "Không dùng khi trọng tâm là điều kiện nuôi dưỡng. "
        "Ví dụ: Ông bà nội, ông bà ngoại có những quyền, nghĩa vụ gì đối với cháu?; "
        "Cháu có những nghĩa vụ gì đối với ông bà?"
    ),
    params_schema=QuyenNghiaVuOngBaVaChauParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
