"""Template — nuôi dưỡng có điều kiện giữa anh chị em (Đ105)."""
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

_ROUTER_FIELDS = ("khia_canh_nuoi_duong_anh_chi_em",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_105"]


class NuoiDuongGiuaAnhChiEmParams(BaseModel):
    tinh_trang_cha_me: Literal[
        "khong_con",
        "khong_co_dieu_kien",
        "co_va_co_dieu_kien",
        "khong_ro",
    ] = Field(description="tình trạng cha mẹ.")
    nguoi_duoc_nuoi_duong: Literal[
        "em_chua_thanh_nien",
        "anh_chi_em_can_nuoi_duong",
        "khong_ro",
    ] = Field(description="người cần nuôi dưỡng.")
    nguoi_thuc_hien_da_thanh_nien: Literal["co", "khong", "khong_ro"] = Field(
        description="dữ kiện tình huống — không gate legal seed."
    )
    khia_canh_nuoi_duong_anh_chi_em: Literal[
        "dieu_kien_phat_sinh",
        "danh_gia_tinh_huong",
        "tong_quat",
    ] = Field(description="điều kiện phát sinh / đánh giá tình huống.")


_SEED_BODY = f"""
WITH $tinh_trang_cha_me AS tcm, $whitelist_dieu_ids AS wl

MATCH (nv:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_anh_chi_em_nuoi_duong_nhau', topic: '{TOPIC}'
}})

OPTIONAL MATCH (dk1:DieuKien:{TOPIC_LABEL} {{
  id: 'khong_con_cha_me', topic: '{TOPIC}'
}})
WHERE tcm IN ['khong_con', 'khong_ro']
OPTIONAL MATCH (dk2:DieuKien:{TOPIC_LABEL} {{
  id: 'cha_me_khong_co_dieu_kien_trong_nom_nuoi_duong_cham_soc_giao_duc_con', topic: '{TOPIC}'
}})
WHERE tcm IN ['khong_co_dieu_kien', 'khong_ro']

WITH wl,
  collect(DISTINCT nv) + collect(DISTINCT dk1) + collect(DISTINCT dk2) AS seed_nodes,
  [x IN collect(DISTINCT nv) + collect(DISTINCT dk1) + collect(DISTINCT dk2)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: NuoiDuongGiuaAnhChiEmParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "tinh_trang_cha_me": params.tinh_trang_cha_me,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


nuoi_duong_giua_anh_chi_em = CypherTemplate(
    name="nuoi_duong_giua_anh_chi_em",
    description=(
        "Dùng khi trọng tâm là nghĩa vụ anh, chị, em nuôi dưỡng nhau vì không còn cha mẹ "
        "hoặc cha mẹ không có điều kiện trông nom, nuôi dưỡng, chăm sóc, giáo dục con. "
        "Ví dụ: Khi không còn cha mẹ thì anh chị em có nghĩa vụ nuôi dưỡng em út chưa thành niên không?; "
        "Bố mẹ bị tù, anh trai 25 tuổi có nghĩa vụ nuôi em 11 tuổi không?"
    ),
    params_schema=NuoiDuongGiuaAnhChiEmParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
