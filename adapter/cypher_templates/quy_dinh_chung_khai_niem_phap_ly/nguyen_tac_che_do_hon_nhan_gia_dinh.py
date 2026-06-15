"""Template — nguyên tắc cơ bản chế độ hôn nhân và gia đình (Đ2)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_nguyen_tac",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_2"]

_NGUYEN_TAC_MAP: dict[str, str] = {
    "tu_nguyen_tien_bo": "hon_nhan_tu_nguyen_tien_bo",
    "mot_vo_mot_chong": "hon_nhan_mot_vo_mot_chong",
    "vo_chong_binh_dang": "vo_chong_binh_dang",
    "ton_trong_da_dan_toc_ton_giao_quoc_te": "ton_trong_hon_nhan_da_dan_toc_ton_giao_quoc_te",
    "ke_thua_truyen_thong_tot_dep": "ke_thua_phat_huy_truyen_thong_tot_dep",
}


class NguyenTacCheDoHonNhanGiaDinhParams(BaseModel):
    khia_canh_nguyen_tac: Literal[
        "liet_ke_tat_ca",
        "tu_nguyen_tien_bo",
        "mot_vo_mot_chong",
        "vo_chong_binh_dang",
        "ton_trong_da_dan_toc_ton_giao_quoc_te",
        "xay_dung_gia_dinh_va_bao_ve_nhom_yeu_the",
        "ke_thua_truyen_thong_tot_dep",
        "tong_quat",
    ] = Field(
        description=(
            "liet_ke_tat_ca: liệt kê toàn bộ nguyên tắc; "
            "mot_vo_mot_chong: một vợ một chồng; "
            "tu_nguyen_tien_bo: tự nguyện tiến bộ."
        )
    )
    muc_do_chi_tiet: Literal["tom_tat", "day_du_khoan_1_den_5"] = Field(
        description="day_du_khoan_1_den_5 khi liệt kê đủ khoản 1-5 Điều 2."
    )


_SEED_BODY = f"""
WITH $kc AS kc, $md AS md, $sid AS sid, $expand_all AS expand_all,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (root:QuyDinh:{TOPIC_LABEL} {{
  id: 'nguyen_tac_co_ban_che_do_hngd', topic: '{TOPIC}'
}})
WHERE expand_all = true OR kc IN ['liet_ke_tat_ca', 'tong_quat', 'khong_ro']

OPTIONAL MATCH (root)-[:BAO_GOM]->(leaf:QuyDinh:{TOPIC_LABEL})
WHERE expand_all = true
  AND leaf.topic = '{TOPIC}'

OPTIONAL MATCH (leaf_nv:NghiaVu:{TOPIC_LABEL})
WHERE expand_all = true
  AND leaf_nv.id IN [
    'thanh_vien_gia_dinh_ton_trong_cham_soc_giup_do',
    'bao_ve_ho_tro_nhom_yeu_the_va_ba_me',
    'thuc_hien_ke_hoach_hoa_gia_dinh'
  ]
  AND leaf_nv.topic = '{TOPIC}'

OPTIONAL MATCH (spec:QuyDinh:{TOPIC_LABEL} {{id: sid, topic: '{TOPIC}'}})
WHERE sid <> '' AND expand_all = false

OPTIONAL MATCH (spec_nv:NghiaVu:{TOPIC_LABEL})
WHERE kc = 'xay_dung_gia_dinh_va_bao_ve_nhom_yeu_the'
  AND spec_nv.id IN [
    'thanh_vien_gia_dinh_ton_trong_cham_soc_giup_do',
    'bao_ve_ho_tro_nhom_yeu_the_va_ba_me',
    'thuc_hien_ke_hoach_hoa_gia_dinh'
  ]
  AND spec_nv.topic = '{TOPIC}'

OPTIONAL MATCH (spec_qd2:QuyDinh:{TOPIC_LABEL})
WHERE kc = 'xay_dung_gia_dinh_va_bao_ve_nhom_yeu_the'
  AND spec_qd2.id IN [
    'xay_dung_gia_dinh_am_no_tien_bo_hanh_phuc',
    'khong_phan_biet_doi_xu_giua_cac_con'
  ]
  AND spec_qd2.topic = '{TOPIC}'

WITH wl, kc, expand_all,
  collect(DISTINCT root) + collect(DISTINCT leaf) + collect(DISTINCT leaf_nv)
    + collect(DISTINCT spec) + collect(DISTINCT spec_nv) + collect(DISTINCT spec_qd2)
    AS seed_nodes,
  CASE
    WHEN expand_all = true THEN
      [x IN collect(DISTINCT leaf) + collect(DISTINCT leaf_nv) WHERE x IS NOT NULL]
    WHEN kc = 'xay_dung_gia_dinh_va_bao_ve_nhom_yeu_the' THEN
      [x IN collect(DISTINCT spec_qd2) + collect(DISTINCT spec_nv) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT spec) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: NguyenTacCheDoHonNhanGiaDinhParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    kc = params.khia_canh_nguyen_tac
    expand_all = kc in ("liet_ke_tat_ca", "tong_quat")
    sid = _NGUYEN_TAC_MAP.get(kc, "")
    return {
        "kc": kc,
        "md": params.muc_do_chi_tiet,
        "sid": sid,
        "expand_all": expand_all,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


nguyen_tac_che_do_hon_nhan_gia_dinh = CypherTemplate(
    name="nguyen_tac_che_do_hon_nhan_gia_dinh",
    description=(
        "Truy xuất toàn bộ năm nhóm nguyên tắc tại Điều 2 hoặc giải thích một nguyên tắc cụ thể "
        "như tự nguyện, một vợ một chồng, bình đẳng. Không dùng cho câu hỏi về hành vi vi phạm "
        "nguyên tắc; các câu có ngoại tình, đang có vợ/chồng hoặc chung sống với người khác "
        "phải chuyển sang template hành vi bị cấm. "
        "Ví dụ: Chế độ hôn nhân và gia đình có những nguyên tắc cơ bản nào?; "
        "Nguyên tắc hôn nhân một vợ một chồng là gì?"
    ),
    params_schema=NguyenTacCheDoHonNhanGiaDinhParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
