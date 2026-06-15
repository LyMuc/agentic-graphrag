"""Template — quyền, nghĩa vụ chung họ hàng mở rộng và cháu ruột (Đ106)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_ho_hang",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_106"]


class QuyenNghiaVuHoHangVaChauParams(BaseModel):
    doi_tuong_ho_hang: Literal[
        "co",
        "di",
        "chu",
        "cau",
        "bac",
        "nhom_co_di_chu_cau_bac",
        "khong_ro",
    ] = Field(description="cô/dì/chú/cậu/bác ruột.")
    chieu_ho_hang_chau: Literal[
        "ho_hang_doi_voi_chau",
        "chau_doi_voi_ho_hang",
        "hai_chieu",
        "khong_ro",
    ] = Field(description="chiều họ hàng-cháu.")
    noi_dung_ho_hang_chau: Literal[
        "thuong_yeu",
        "cham_soc",
        "giup_do",
        "tong_hop",
    ] = Field(description="nội dung thương yêu, chăm sóc, giúp đỡ.")
    con_cha_me_cua_chau: Literal["co", "khong", "khong_ro"] = Field(
        description="cha mẹ cháu còn hay không."
    )
    khia_canh_ho_hang: Literal[
        "liet_ke",
        "co_nghia_vu_khong",
        "phan_biet_voi_nuoi_duong",
        "tong_quat",
    ] = Field(description="liệt kê / phân biệt với nuôi dưỡng.")


_SEED_BODY = f"""
WITH $con_cha_me AS ccm, $khia_canh AS kc, $whitelist_dieu_ids AS wl

MATCH (q:Quyen:{TOPIC_LABEL} {{
  id: 'quyen_ho_hang_va_chau_thuong_yeu_cham_soc_giup_do_nhau', topic: '{TOPIC}'
}})
MATCH (nv:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_ho_hang_va_chau_thuong_yeu_cham_soc_giup_do_nhau', topic: '{TOPIC}'
}})

OPTIONAL MATCH (qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'phan_biet_giup_do_thuong_xuyen_va_nuoi_duong_co_dieu_kien_ho_hang', topic: '{TOPIC}'
}})
WHERE ccm = 'co' OR kc = 'phan_biet_voi_nuoi_duong'

WITH wl,
  collect(DISTINCT q) + collect(DISTINCT nv) + collect(DISTINCT qd) AS seed_nodes,
  [x IN collect(DISTINCT q) + collect(DISTINCT nv) + collect(DISTINCT qd)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: QuyenNghiaVuHoHangVaChauParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "con_cha_me": params.con_cha_me_cua_chau,
        "khia_canh": params.khia_canh_ho_hang,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


quyen_nghia_vu_co_di_chu_cau_bac_ruot_va_chau_ruot = CypherTemplate(
    name="quyen_nghia_vu_co_di_chu_cau_bac_ruot_va_chau_ruot",
    description=(
        "Dùng cho quyền, nghĩa vụ thương yêu, chăm sóc, giúp đỡ nhau giữa cô, dì, chú, cậu, bác ruột "
        "và cháu ruột — nghĩa vụ chung, không phụ thuộc cha mẹ cháu còn hay không. "
        "Ví dụ: Cô, dì, chú, cậu, bác ruột và cháu ruột có những quyền, nghĩa vụ gì?; "
        "Bác ruột và cháu ruột có quyền, nghĩa vụ chăm sóc, giúp đỡ nhau khi cha mẹ cháu còn không?"
    ),
    params_schema=QuyenNghiaVuHoHangVaChauParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
