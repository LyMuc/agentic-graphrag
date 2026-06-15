"""Template — nuôi dưỡng có điều kiện họ hàng mở rộng-cháu ruột (Đ106) + so sánh Đ104."""
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

_ROUTER_FIELDS = ("khia_canh_nuoi_duong_ho_hang",)
_DIEU_WHITELIST = [
    "Luat_HNGD_2014_Dieu_104",
    "Luat_HNGD_2014_Dieu_105",
    "Luat_HNGD_2014_Dieu_106",
]
_SO_SANH_WHITELIST = ["Luat_HNGD_2014_Dieu_104", "Luat_HNGD_2014_Dieu_106"]


class NuoiDuongGiuaHoHangVaChauParams(BaseModel):
    doi_tuong_ho_hang: Literal[
        "co",
        "di",
        "chu",
        "cau",
        "bac",
        "nhom_co_di_chu_cau_bac",
        "khong_ro",
    ] = Field(description="cô/dì/chú/cậu/bác ruột.")
    chieu_nuoi_duong_ho_hang: Literal[
        "ho_hang_nuoi_chau_ruot",
        "chau_ruot_nuoi_ho_hang",
        "hai_chieu",
        "khong_ro",
    ] = Field(description="chiều nuôi dưỡng họ hàng-cháu.")
    con_cha_me_cua_nguoi_can_nuoi_duong: Literal["co", "khong", "khong_ro"] = Field(
        description="người cần nuôi dưỡng còn cha mẹ không."
    )
    con_con_cua_nguoi_can_nuoi_duong: Literal["co", "khong", "khong_ro"] = Field(
        description="người cần nuôi dưỡng còn con không."
    )
    tinh_trang_nguoi_thuoc_dieu_104_105: Literal[
        "khong_con",
        "con_nhung_khong_co_dieu_kien",
        "khong_con_hoac_khong_co_dieu_kien",
        "con_co_dieu_kien",
        "chi_biet_mot_phan",
        "khong_ro",
    ] = Field(description="tuyến Đ104-105.")
    khia_canh_nuoi_duong_ho_hang: Literal[
        "dieu_kien_phat_sinh",
        "danh_gia_tinh_huong",
        "can_cu_phap_ly",
        "so_sanh_voi_ong_ba_chau",
        "tong_quat",
    ] = Field(description="điều kiện / so sánh với ông bà-cháu.")


_SEED_BODY = f"""
WITH $khia_canh AS kc, $con_cha_me AS ccm, $con_con AS cc,
     $tinh_trang_104_105 AS tt104105, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (nv106:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_ho_hang_va_chau_nuoi_duong_nhau', topic: '{TOPIC}'
}})
WHERE kc <> 'so_sanh_voi_ong_ba_chau' OR kc = 'so_sanh_voi_ong_ba_chau'
OPTIONAL MATCH (qd106:QuyDinh:{TOPIC_LABEL} {{
  id: 'dieu_106_la_tuyen_nuoi_duong_sau_cha_me_con_va_dieu_104_105', topic: '{TOPIC}'
}})
WHERE kc <> 'so_sanh_voi_ong_ba_chau' OR kc = 'so_sanh_voi_ong_ba_chau'

OPTIONAL MATCH (dk_cmc:DieuKien:{TOPIC_LABEL} {{
  id: 'nguoi_can_nuoi_duong_khong_con_cha_me_con', topic: '{TOPIC}'
}})
WHERE (ccm = 'khong' AND cc = 'khong')
  OR ccm = 'khong' OR cc = 'khong'
  OR kc IN ['dieu_kien_phat_sinh', 'danh_gia_tinh_huong', 'can_cu_phap_ly', 'tong_quat', 'so_sanh_voi_ong_ba_chau']

OPTIONAL MATCH (dk1:DieuKien:{TOPIC_LABEL} {{
  id: 'nguoi_thuoc_dieu_104_105_khong_con', topic: '{TOPIC}'
}})
WHERE tt104105 IN ['khong_con', 'khong_con_hoac_khong_co_dieu_kien', 'khong_ro']
  OR kc IN ['dieu_kien_phat_sinh', 'danh_gia_tinh_huong', 'can_cu_phap_ly', 'tong_quat', 'so_sanh_voi_ong_ba_chau']
OPTIONAL MATCH (dk2:DieuKien:{TOPIC_LABEL} {{
  id: 'nguoi_thuoc_dieu_104_105_khong_co_dieu_kien_nuoi_duong', topic: '{TOPIC}'
}})
WHERE tt104105 IN ['con_nhung_khong_co_dieu_kien', 'khong_con_hoac_khong_co_dieu_kien', 'khong_ro']
  OR kc IN ['dieu_kien_phat_sinh', 'danh_gia_tinh_huong', 'can_cu_phap_ly', 'tong_quat', 'so_sanh_voi_ong_ba_chau']

OPTIONAL MATCH (nv_ob:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_ong_ba_nuoi_duong_chau', topic: '{TOPIC}'
}})
WHERE kc = 'so_sanh_voi_ong_ba_chau'
OPTIONAL MATCH (nv_ch_ob:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_chau_thanh_nien_nuoi_duong_ong_ba', topic: '{TOPIC}'
}})
WHERE kc = 'so_sanh_voi_ong_ba_chau'
OPTIONAL MATCH (qd_ss:QuyDinh:{TOPIC_LABEL} {{
  id: 'phan_biet_dieu_kien_nuoi_duong_ong_ba_chau_va_ho_hang_mo_rong', topic: '{TOPIC}'
}})
WHERE kc = 'so_sanh_voi_ong_ba_chau'

WITH wl, kc,
  collect(DISTINCT nv106) + collect(DISTINCT qd106) + collect(DISTINCT dk_cmc)
    + collect(DISTINCT dk1) + collect(DISTINCT dk2)
    + collect(DISTINCT nv_ob) + collect(DISTINCT nv_ch_ob) + collect(DISTINCT qd_ss) AS seed_nodes,
  CASE
    WHEN kc = 'so_sanh_voi_ong_ba_chau' THEN
      [x IN collect(DISTINCT nv_ob) + collect(DISTINCT nv_ch_ob)
           + collect(DISTINCT nv106) + collect(DISTINCT qd_ss)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT nv106) + collect(DISTINCT qd106)
           + collect(DISTINCT dk_cmc) + collect(DISTINCT dk1) + collect(DISTINCT dk2)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: NuoiDuongGiuaHoHangVaChauParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    if params.khia_canh_nuoi_duong_ho_hang == "so_sanh_voi_ong_ba_chau":
        wl = [] if not use_wl else _SO_SANH_WHITELIST
    else:
        wl = _DIEU_WHITELIST if use_wl else []
    return {
        "khia_canh": params.khia_canh_nuoi_duong_ho_hang,
        "con_cha_me": params.con_cha_me_cua_nguoi_can_nuoi_duong,
        "con_con": params.con_con_cua_nguoi_can_nuoi_duong,
        "tinh_trang_104_105": params.tinh_trang_nguoi_thuoc_dieu_104_105,
        "whitelist_dieu_ids": wl,
    }


nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot = CypherTemplate(
    name="nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot",
    description=(
        "Dùng cho nghĩa vụ nuôi dưỡng có điều kiện tại Điều 106 và câu so sánh tuyến nuôi dưỡng "
        "với Điều 104. Kiểm tra riêng cha, mẹ, con của người cần nuôi dưỡng và tuyến Đ104-105. "
        "Ví dụ: Cháu mồ côi, ông bà đã mất, anh chị em không có điều kiện thì cô ruột có nghĩa vụ nuôi không?; "
        "Quyền, nghĩa vụ nuôi dưỡng giữa cô dì chú cậu bác và cháu khác gì so với ông bà và cháu?"
    ),
    params_schema=NuoiDuongGiuaHoHangVaChauParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
