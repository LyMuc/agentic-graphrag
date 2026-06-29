"""Template — nuôi dưỡng có điều kiện giữa ông bà và cháu (Đ104)."""
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

_ROUTER_FIELDS = ("khia_canh_nuoi_duong_ong_ba_chau",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_104", "Luat_HNGD_2014_Dieu_105"]


class NuoiDuongGiuaOngBaVaChauParams(BaseModel):
    chieu_nuoi_duong_ong_ba_chau: Literal[
        "ong_ba_nuoi_chau",
        "chau_thanh_nien_nuoi_ong_ba",
        "hai_chieu",
        "khong_ro",
    ] = Field(description="chiều nuôi dưỡng ông bà-cháu.")
    tinh_trang_chau: Literal[
        "chua_thanh_nien",
        "thanh_nien_mat_nang_luc_hanh_vi_dan_su",
        "thanh_nien_khong_kha_nang_lao_dong_va_khong_co_tai_san",
        "ca_hai_nhom_thanh_nien_can_nuoi_duong",
        "khong_ro",
    ] = Field(description="tình trạng cháu cần nuôi dưỡng.")
    nguoi_nuoi_duong_theo_dieu_105: Literal[
        "khong_co",
        "co_nhung_khong_co_dieu_kien",
        "co_du_dieu_kien",
        "khong_ro",
    ] = Field(description="người nuôi dưỡng theo Đ105.")
    tinh_trang_con_cua_ong_ba: Literal[
        "khong_co_con",
        "co_con",
        "khong_ro",
    ] = Field(description="ông bà có con nuôi dưỡng hay không.")
    chau_da_thanh_nien: Literal["co", "khong", "khong_ro"]
    khia_canh_nuoi_duong_ong_ba_chau: Literal[
        "dieu_kien_phat_sinh",
        "danh_gia_tinh_huong",
        "tong_quat",
    ] = Field(description="điều kiện phát sinh / đánh giá tình huống.")


_SEED_BODY = f"""
WITH $chieu AS ch, $tinh_trang_chau AS tt, $nguoi_d105 AS nd105,
     $tinh_trang_con_ob AS tco, $chau_tn AS ctn, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (nv_ob:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_ong_ba_nuoi_duong_chau', topic: '{TOPIC}'
}})
WHERE ch IN ['ong_ba_nuoi_chau', 'hai_chieu', 'khong_ro']

OPTIONAL MATCH (dk1:DieuKien:{TOPIC_LABEL} {{
  id: 'chau_chua_thanh_nien_can_nuoi_duong', topic: '{TOPIC}'
}})
WHERE ch IN ['ong_ba_nuoi_chau', 'hai_chieu', 'khong_ro']
  AND tt IN ['chua_thanh_nien', 'khong_ro']
OPTIONAL MATCH (dk2:DieuKien:{TOPIC_LABEL} {{
  id: 'chau_thanh_nien_mat_nang_luc_hanh_vi_dan_su_can_nuoi_duong', topic: '{TOPIC}'
}})
WHERE ch IN ['ong_ba_nuoi_chau', 'hai_chieu', 'khong_ro']
  AND tt IN ['thanh_nien_mat_nang_luc_hanh_vi_dan_su', 'ca_hai_nhom_thanh_nien_can_nuoi_duong', 'khong_ro']
OPTIONAL MATCH (dk3:DieuKien:{TOPIC_LABEL} {{
  id: 'chau_thanh_nien_khong_kha_nang_lao_dong_va_khong_co_tai_san_tu_nuoi', topic: '{TOPIC}'
}})
WHERE ch IN ['ong_ba_nuoi_chau', 'hai_chieu', 'khong_ro']
  AND tt IN ['thanh_nien_khong_kha_nang_lao_dong_va_khong_co_tai_san', 'ca_hai_nhom_thanh_nien_can_nuoi_duong', 'khong_ro']

OPTIONAL MATCH (dk105:DieuKien:{TOPIC_LABEL} {{
  id: 'khong_co_nguoi_nuoi_duong_theo_dieu_105', topic: '{TOPIC}'
}})
WHERE ch IN ['ong_ba_nuoi_chau', 'hai_chieu', 'khong_ro']
  AND nd105 IN ['khong_co', 'co_nhung_khong_co_dieu_kien', 'khong_ro']
OPTIONAL MATCH (qd105:QuyDinh:{TOPIC_LABEL} {{
  id: 'dieu_104_chi_phat_sinh_khi_khong_co_nguoi_nuoi_duong_theo_dieu_105', topic: '{TOPIC}'
}})
WHERE ch IN ['ong_ba_nuoi_chau', 'hai_chieu', 'khong_ro']
  AND nd105 IN ['khong_co', 'co_nhung_khong_co_dieu_kien', 'khong_ro']

OPTIONAL MATCH (nv_ch:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_chau_thanh_nien_nuoi_duong_ong_ba', topic: '{TOPIC}'
}})
WHERE ch IN ['chau_thanh_nien_nuoi_ong_ba', 'hai_chieu', 'khong_ro']
OPTIONAL MATCH (dk_ob:DieuKien:{TOPIC_LABEL} {{
  id: 'ong_ba_khong_co_con_de_nuoi_duong', topic: '{TOPIC}'
}})
WHERE ch IN ['chau_thanh_nien_nuoi_ong_ba', 'hai_chieu', 'khong_ro']
  AND tco IN ['khong_co_con', 'khong_ro']
OPTIONAL MATCH (dk_ctn:DieuKien:{TOPIC_LABEL} {{
  id: 'chau_phai_da_thanh_nien', topic: '{TOPIC}'
}})
WHERE ch IN ['chau_thanh_nien_nuoi_ong_ba', 'hai_chieu', 'khong_ro']
  AND ctn IN ['co', 'khong_ro']

WITH wl,
  collect(DISTINCT nv_ob) + collect(DISTINCT dk1) + collect(DISTINCT dk2)
    + collect(DISTINCT dk3) + collect(DISTINCT dk105) + collect(DISTINCT qd105)
    + collect(DISTINCT nv_ch) + collect(DISTINCT dk_ob) + collect(DISTINCT dk_ctn) AS seed_nodes,
  [x IN collect(DISTINCT nv_ob) + collect(DISTINCT dk1) + collect(DISTINCT dk2)
       + collect(DISTINCT dk3) + collect(DISTINCT dk105) + collect(DISTINCT qd105)
       + collect(DISTINCT nv_ch) + collect(DISTINCT dk_ob) + collect(DISTINCT dk_ctn)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: NuoiDuongGiuaOngBaVaChauParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "chieu": params.chieu_nuoi_duong_ong_ba_chau,
        "tinh_trang_chau": params.tinh_trang_chau,
        "nguoi_d105": params.nguoi_nuoi_duong_theo_dieu_105,
        "tinh_trang_con_ob": params.tinh_trang_con_cua_ong_ba,
        "chau_tn": params.chau_da_thanh_nien,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


nuoi_duong_giua_ong_ba_va_chau = CypherTemplate(
    name="nuoi_duong_giua_ong_ba_va_chau",
    description=(
        "Dùng riêng cho nghĩa vụ nuôi dưỡng có điều kiện tại Điều 104. "
        "Nhánh ông bà nuôi cháu kiểm tra tình trạng cháu và không có người nuôi dưỡng theo Đ105; "
        "nhánh cháu nuôi ông bà kiểm tra cháu thành niên và ông bà không có con nuôi dưỡng. "
        "Ví dụ: Cháu 16 tuổi mồ côi, không có anh chị em đủ điều kiện, ông bà có nghĩa vụ nuôi không?; "
        "Ông bà không có con, cháu đã thành niên có nghĩa vụ nuôi dưỡng không?"
    ),
    params_schema=NuoiDuongGiuaOngBaVaChauParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
