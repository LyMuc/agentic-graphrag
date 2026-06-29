"""Template — liệt kê các trường hợp cấm kết hôn (Đ5 K2, Đ8 K1 điểm d)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("pham_vi_liet_ke",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_5", "Luat_HNGD_2014_Dieu_8"]


class CacTruongHopCamKetHonParams(BaseModel):
    pham_vi_liet_ke: Literal[
        "tat_ca_a_den_d",
        "khong_huyet_thong",
        "gia_tao",
        "tao_hon_cuong_ep_lua_doi_can_tro",
        "dang_co_vo_chong",
        "quan_he_than_thich",
        "khong_ro",
    ] = Field(
        description=(
            "trường hợp nào bị cấm -> tat_ca_a_den_d; "
            "dù không huyết thống -> khong_huyet_thong; "
            "đã có vợ/chồng -> dang_co_vo_chong; "
            "tảo hôn/cưỡng ép/lừa dối/cản trở -> tao_hon_cuong_ep_lua_doi_can_tro."
        )
    )
    khia_canh_cam: Literal["liet_ke", "co_bi_cam", "giai_thich", "tong_quat"] = Field(
        description=(
            "trường hợp nào/liệt kê -> liet_ke; "
            "có bị cấm không -> co_bi_cam; tại sao -> giai_thich."
        )
    )


_SEED_BODY = f"""
WITH $pv AS pv, $kc AS kc, $whitelist_dieu_ids AS wl

MATCH (qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'cac_truong_hop_cam_ket_hon_diem_a_den_d', topic: '{TOPIC}'
}})

OPTIONAL MATCH (hv_gt:HanhVi:{TOPIC_LABEL} {{id: 'ket_hon_gia_tao', topic: '{TOPIC}'}})
WHERE pv IN ['tat_ca_a_den_d', 'khong_huyet_thong', 'gia_tao', 'khong_ro']

OPTIONAL MATCH (hv_th:HanhVi:{TOPIC_LABEL} {{id: 'tao_hon', topic: '{TOPIC}'}})
WHERE pv IN [
  'tat_ca_a_den_d', 'khong_huyet_thong', 'tao_hon_cuong_ep_lua_doi_can_tro', 'khong_ro'
]

OPTIONAL MATCH (hv_ce:HanhVi:{TOPIC_LABEL} {{id: 'cuong_ep_ket_hon', topic: '{TOPIC}'}})
WHERE pv IN [
  'tat_ca_a_den_d', 'khong_huyet_thong', 'tao_hon_cuong_ep_lua_doi_can_tro', 'khong_ro'
]

OPTIONAL MATCH (hv_ld:HanhVi:{TOPIC_LABEL} {{id: 'lua_doi_ket_hon', topic: '{TOPIC}'}})
WHERE pv IN [
  'tat_ca_a_den_d', 'khong_huyet_thong', 'tao_hon_cuong_ep_lua_doi_can_tro', 'khong_ro'
]

OPTIONAL MATCH (hv_ct:HanhVi:{TOPIC_LABEL} {{id: 'can_tro_ket_hon', topic: '{TOPIC}'}})
WHERE pv IN [
  'tat_ca_a_den_d', 'khong_huyet_thong', 'tao_hon_cuong_ep_lua_doi_can_tro', 'khong_ro'
]

OPTIONAL MATCH (hv_vc:HanhVi:{TOPIC_LABEL} {{
  id: 'ket_hon_khi_mot_ben_dang_co_vo_hoac_chong', topic: '{TOPIC}'
}})
WHERE pv IN ['tat_ca_a_den_d', 'khong_huyet_thong', 'dang_co_vo_chong', 'khong_ro']

OPTIONAL MATCH (hv_qh:HanhVi:{TOPIC_LABEL} {{
  id: 'ket_hon_trong_quan_he_than_thich_bi_cam', topic: '{TOPIC}'
}})
WHERE pv IN ['tat_ca_a_den_d', 'quan_he_than_thich', 'khong_ro']

OPTIONAL MATCH (qh_nd:QuanHe:{TOPIC_LABEL} {{id: 'cha_me_nuoi_voi_con_nuoi', topic: '{TOPIC}'}})
WHERE pv IN ['tat_ca_a_den_d', 'khong_huyet_thong', 'quan_he_than_thich', 'khong_ro']
OPTIONAL MATCH (qh_nt:QuanHe:{TOPIC_LABEL} {{
  id: 'nguoi_tung_la_cha_me_nuoi_voi_con_nuoi', topic: '{TOPIC}'
}})
WHERE pv IN ['tat_ca_a_den_d', 'khong_huyet_thong', 'quan_he_than_thich', 'khong_ro']
OPTIONAL MATCH (qh_cc:QuanHe:{TOPIC_LABEL} {{id: 'cha_chong_voi_con_dau', topic: '{TOPIC}'}})
WHERE pv IN ['tat_ca_a_den_d', 'khong_huyet_thong', 'quan_he_than_thich', 'khong_ro']
OPTIONAL MATCH (qh_mv:QuanHe:{TOPIC_LABEL} {{id: 'me_vo_voi_con_re', topic: '{TOPIC}'}})
WHERE pv IN ['tat_ca_a_den_d', 'khong_huyet_thong', 'quan_he_than_thich', 'khong_ro']
OPTIONAL MATCH (qh_cd:QuanHe:{TOPIC_LABEL} {{id: 'cha_duong_voi_con_rieng_cua_vo', topic: '{TOPIC}'}})
WHERE pv IN ['tat_ca_a_den_d', 'khong_huyet_thong', 'quan_he_than_thich', 'khong_ro']
OPTIONAL MATCH (qh_mk:QuanHe:{TOPIC_LABEL} {{id: 'me_ke_voi_con_rieng_cua_chong', topic: '{TOPIC}'}})
WHERE pv IN ['tat_ca_a_den_d', 'khong_huyet_thong', 'quan_he_than_thich', 'khong_ro']

WITH wl, kc, pv,
  [x IN collect(DISTINCT qd)
       + collect(DISTINCT hv_gt) + collect(DISTINCT hv_th) + collect(DISTINCT hv_ce)
       + collect(DISTINCT hv_ld) + collect(DISTINCT hv_ct) + collect(DISTINCT hv_vc)
       + collect(DISTINCT hv_qh)
       + collect(DISTINCT qh_nd) + collect(DISTINCT qh_nt) + collect(DISTINCT qh_cc)
       + collect(DISTINCT qh_mv) + collect(DISTINCT qh_cd) + collect(DISTINCT qh_mk)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE pv
    WHEN 'gia_tao' THEN [x IN collect(DISTINCT hv_gt) WHERE x IS NOT NULL]
    WHEN 'dang_co_vo_chong' THEN [x IN collect(DISTINCT hv_vc) WHERE x IS NOT NULL]
    WHEN 'tao_hon_cuong_ep_lua_doi_can_tro' THEN
      [x IN collect(DISTINCT hv_th) + collect(DISTINCT hv_ce)
           + collect(DISTINCT hv_ld) + collect(DISTINCT hv_ct)
       WHERE x IS NOT NULL]
    WHEN 'quan_he_than_thich' THEN
      [x IN collect(DISTINCT hv_qh) + collect(DISTINCT qh_nd) + collect(DISTINCT qh_nt)
           + collect(DISTINCT qh_cc) + collect(DISTINCT qh_mv)
           + collect(DISTINCT qh_cd) + collect(DISTINCT qh_mk)
       WHERE x IS NOT NULL]
    WHEN 'khong_huyet_thong' THEN
      [x IN collect(DISTINCT hv_gt) + collect(DISTINCT hv_th) + collect(DISTINCT hv_ce)
           + collect(DISTINCT hv_ld) + collect(DISTINCT hv_ct) + collect(DISTINCT hv_vc)
           + collect(DISTINCT qh_nd) + collect(DISTINCT qh_nt) + collect(DISTINCT qh_cc)
           + collect(DISTINCT qh_mv) + collect(DISTINCT qh_cd) + collect(DISTINCT qh_mk)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hv_gt) + collect(DISTINCT hv_th) + collect(DISTINCT hv_ce)
           + collect(DISTINCT hv_ld) + collect(DISTINCT hv_ct) + collect(DISTINCT hv_vc)
           + collect(DISTINCT hv_qh)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: CacTruongHopCamKetHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "pv": params.pham_vi_liet_ke,
        "kc": params.khia_canh_cam,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


cac_truong_hop_cam_ket_hon = CypherTemplate(
    name="cac_truong_hop_cam_ket_hon",
    description=(
        "Liệt kê hoặc chọn nhóm trường hợp cấm làm không đạt điểm d khoản 1 Điều 8, "
        "gồm điểm a-d khoản 2 Điều 5. Dùng cho câu hỏi tổng quát, không dùng khi câu đã "
        "nêu một quan hệ huyết thống/nuôi dưỡng/thông gia cụ thể. "
        "Ví dụ: Những trường hợp bị cấm kết hôn dù không có quan hệ huyết thống?; "
        "Trường hợp nào bị cấm kết hôn theo Luật hôn nhân gia đình năm 2014?"
    ),
    params_schema=CacTruongHopCamKetHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
