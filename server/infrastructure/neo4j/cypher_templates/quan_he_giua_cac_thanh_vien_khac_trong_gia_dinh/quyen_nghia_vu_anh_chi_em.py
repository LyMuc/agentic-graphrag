"""Template — quyền, nghĩa vụ chung anh chị em (Đ105)."""
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

_ROUTER_FIELDS = ("khia_canh_anh_chi_em",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_105"]


class QuyenNghiaVuAnhChiEmParams(BaseModel):
    chieu_anh_chi_em: Literal[
        "hai_chieu",
        "mot_nguoi_doi_voi_nguoi_kia",
        "khong_ro",
    ] = Field(description="chiều anh chị em.")
    noi_dung_anh_chi_em: Literal[
        "thuong_yeu",
        "cham_soc",
        "giup_do",
        "tong_hop",
    ] = Field(description="nội dung thương yêu, chăm sóc, giúp đỡ.")
    cung_song: Literal["co", "khong", "khong_ro"] = Field(
        description="cùng sống — dữ kiện tình huống, không gate seed."
    )
    khia_canh_anh_chi_em: Literal[
        "liet_ke",
        "co_nghia_vu_khong",
        "tong_quat",
    ] = Field(description="liệt kê / đánh giá nghĩa vụ.")


_SEED_BODY = f"""
WITH $whitelist_dieu_ids AS wl

MATCH (q:Quyen:{TOPIC_LABEL} {{
  id: 'quyen_anh_chi_em_thuong_yeu_cham_soc_giup_do_nhau', topic: '{TOPIC}'
}})
MATCH (nv:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_anh_chi_em_thuong_yeu_cham_soc_giup_do_nhau', topic: '{TOPIC}'
}})

OPTIONAL MATCH (qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'phan_biet_giup_do_thuong_xuyen_va_nuoi_duong_co_dieu_kien_anh_chi_em', topic: '{TOPIC}'
}})

WITH wl,
  collect(DISTINCT q) + collect(DISTINCT nv) + collect(DISTINCT qd) AS seed_nodes,
  [x IN collect(DISTINCT q) + collect(DISTINCT nv) + collect(DISTINCT qd)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: QuyenNghiaVuAnhChiEmParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {"whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else []}


quyen_nghia_vu_anh_chi_em = CypherTemplate(
    name="quyen_nghia_vu_anh_chi_em",
    description=(
        "Dùng cho quy tắc chung anh, chị, em có quyền và nghĩa vụ thương yêu, chăm sóc, giúp đỡ nhau. "
        "Việc có sống chung hay không không phải điều kiện Đ105 cho nghĩa vụ chung này. "
        "Ví dụ: Anh, chị, em có những quyền, nghĩa vụ gì đối với nhau?; "
        "Hai anh em cùng sống trong một hộ gia đình có nghĩa vụ thương yêu, chăm sóc, giúp đỡ nhau không?"
    ),
    params_schema=QuyenNghiaVuAnhChiEmParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
