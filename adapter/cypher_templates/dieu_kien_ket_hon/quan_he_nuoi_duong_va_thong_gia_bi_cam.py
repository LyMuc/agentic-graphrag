"""Template — quan hệ nuôi dưỡng và thông gia bị cấm đích danh (Đ5 K2 điểm d)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.dieu_kien_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_quan_he_bi_cam",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_5", "Luat_HNGD_2014_Dieu_8"]

_RELATION_IDS: dict[str, str] = {
    "cha_me_nuoi_con_nuoi": "cha_me_nuoi_voi_con_nuoi",
    "nguoi_tung_la_cha_me_nuoi_con_nuoi": "nguoi_tung_la_cha_me_nuoi_voi_con_nuoi",
    "cha_chong_con_dau": "cha_chong_voi_con_dau",
    "me_vo_con_re": "me_vo_voi_con_re",
    "cha_duong_con_rieng_cua_vo": "cha_duong_voi_con_rieng_cua_vo",
    "me_ke_con_rieng_cua_chong": "me_ke_voi_con_rieng_cua_chong",
}


class QuanHeNuoiDuongVaThongGiaBiCamParams(BaseModel):
    loai_quan_he_bi_cam: Literal[
        "cha_me_nuoi_con_nuoi",
        "nguoi_tung_la_cha_me_nuoi_con_nuoi",
        "cha_chong_con_dau",
        "me_vo_con_re",
        "cha_duong_con_rieng_cua_vo",
        "me_ke_con_rieng_cua_chong",
        "khong_ro",
    ] = Field(
        description=(
            "cha dượng-con riêng -> cha_duong_con_rieng_cua_vo; "
            "cha chồng-con dâu -> cha_chong_con_dau; các cụm còn lại map tương ứng."
        )
    )
    khia_canh_quan_he_bi_cam: Literal[
        "co_duoc_ket_hon",
        "co_bi_cam",
        "xac_dinh_can_cu",
        "tong_quat",
    ] = Field(
        description=(
            "được không -> co_duoc_ket_hon; "
            "có bị cấm -> co_bi_cam; căn cứ nào -> xac_dinh_can_cu."
        )
    )


_SEED_BODY = f"""
WITH $lqh AS lqh, $lrh AS lrh, $kc AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (qh:QuanHe:{TOPIC_LABEL} {{id: lqh, topic: '{TOPIC}'}})
WHERE lqh <> '' AND lrh <> 'khong_ro'

OPTIONAL MATCH (qh_nd:QuanHe:{TOPIC_LABEL} {{id: 'cha_me_nuoi_voi_con_nuoi', topic: '{TOPIC}'}})
WHERE lrh = 'khong_ro'
OPTIONAL MATCH (qh_nt:QuanHe:{TOPIC_LABEL} {{
  id: 'nguoi_tung_la_cha_me_nuoi_voi_con_nuoi', topic: '{TOPIC}'
}})
WHERE lrh = 'khong_ro'
OPTIONAL MATCH (qh_cc:QuanHe:{TOPIC_LABEL} {{id: 'cha_chong_voi_con_dau', topic: '{TOPIC}'}})
WHERE lrh = 'khong_ro'
OPTIONAL MATCH (qh_mv:QuanHe:{TOPIC_LABEL} {{id: 'me_vo_voi_con_re', topic: '{TOPIC}'}})
WHERE lrh = 'khong_ro'
OPTIONAL MATCH (qh_cd:QuanHe:{TOPIC_LABEL} {{id: 'cha_duong_voi_con_rieng_cua_vo', topic: '{TOPIC}'}})
WHERE lrh = 'khong_ro'
OPTIONAL MATCH (qh_mk:QuanHe:{TOPIC_LABEL} {{id: 'me_ke_voi_con_rieng_cua_chong', topic: '{TOPIC}'}})
WHERE lrh = 'khong_ro'

OPTIONAL MATCH (hv_cam:HanhVi:{TOPIC_LABEL} {{
  id: 'ket_hon_trong_quan_he_than_thich_bi_cam', topic: '{TOPIC}'
}})

WITH wl, kc,
  [x IN collect(DISTINCT qh)
       + collect(DISTINCT qh_nd) + collect(DISTINCT qh_nt) + collect(DISTINCT qh_cc)
       + collect(DISTINCT qh_mv) + collect(DISTINCT qh_cd) + collect(DISTINCT qh_mk)
       + collect(DISTINCT hv_cam)
   WHERE x IS NOT NULL] AS seed_nodes,
  [x IN collect(DISTINCT qh)
       + collect(DISTINCT qh_nd) + collect(DISTINCT qh_nt) + collect(DISTINCT qh_cc)
       + collect(DISTINCT qh_mv) + collect(DISTINCT qh_cd) + collect(DISTINCT qh_mk)
       + collect(DISTINCT hv_cam)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: QuanHeNuoiDuongVaThongGiaBiCamParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    lrh = params.loai_quan_he_bi_cam
    lqh = _RELATION_IDS.get(lrh, "")
    return {
        "lqh": lqh,
        "lrh": lrh,
        "kc": params.khia_canh_quan_he_bi_cam,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


quan_he_nuoi_duong_va_thong_gia_bi_cam = CypherTemplate(
    name="quan_he_nuoi_duong_va_thong_gia_bi_cam",
    description=(
        "Xử lý các quan hệ không nhất thiết có huyết thống nhưng được điểm d khoản 2 "
        "Điều 5 liệt kê đích danh là bị cấm, như cha dượng-con riêng của vợ hoặc "
        "cha chồng-con dâu. Không dùng cho em chồng-anh vợ/em trai chồng-em gái vợ. "
        "Ví dụ: Cha dượng có được kết hôn với con riêng của vợ không?; "
        "Cha chồng có được kết hôn với con dâu không?"
    ),
    params_schema=QuanHeNuoiDuongVaThongGiaBiCamParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
