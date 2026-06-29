"""Template — quan hệ huyết thống và phạm vi ba đời (Đ3 K17-18, Đ5 K2 điểm d)."""
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

_ROUTER_FIELDS = ("khia_canh_ba_doi",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_5", "Luat_HNGD_2014_Dieu_8"]

_RELATION_IDS: dict[str, str] = {
    "cung_dong_mau_truc_he": "cung_dong_mau_ve_truc_he",
    "ho_trong_pham_vi_ba_doi": "co_ho_trong_pham_vi_ba_doi",
    "anh_chi_em_cung_cha_me": "anh_chi_em_cung_cha_me",
    "anh_chi_em_cung_cha_khac_me": "anh_chi_em_cung_cha_khac_me",
    "anh_chi_em_cung_me_khac_cha": "anh_chi_em_cung_me_khac_cha",
    "anh_chi_em_con_chu_bac_co_cau_di": "anh_chi_em_con_chu_bac_co_cau_di",
    "con_rieng_cua_bo": "con_rieng_cua_bo_cung_cha_khac_me",
    "hai_chau_noi_cung_goc": "hai_chau_noi_cung_mot_goc_sinh_ra",
    "can_huyet_khong_ro": "co_ho_trong_pham_vi_ba_doi",
}


class QuanHeHuyetThongVaBaDoiParams(BaseModel):
    loai_quan_he_huyet_thong: Literal[
        "cung_dong_mau_truc_he",
        "ho_trong_pham_vi_ba_doi",
        "anh_chi_em_cung_cha_me",
        "anh_chi_em_cung_cha_khac_me",
        "anh_chi_em_cung_me_khac_cha",
        "anh_chi_em_con_chu_bac_co_cau_di",
        "con_rieng_cua_bo",
        "hai_chau_noi_cung_goc",
        "can_huyet_khong_ro",
        "khong_ro",
    ] = Field(
        description=(
            "trực hệ -> cung_dong_mau_truc_he; ba đời/cận huyết -> ho_trong_pham_vi_ba_doi "
            "hoặc can_huyet_khong_ro; cùng cha khác mẹ/con riêng của bố -> "
            "anh_chi_em_cung_cha_khac_me/con_rieng_cua_bo."
        )
    )
    khia_canh_ba_doi: Literal[
        "co_duoc_ket_hon",
        "cach_tinh_ba_doi",
        "phai_qua_may_doi",
        "xac_dinh_quan_he",
        "tong_quat",
    ] = Field(
        description=(
            "có được không -> co_duoc_ket_hon; "
            "ba đời tính thế nào -> cach_tinh_ba_doi; "
            "qua mấy đời -> phai_qua_may_doi; mô tả cây gia đình -> xac_dinh_quan_he."
        )
    )
    co_chung_goc_sinh_ra: Literal["co", "khong", "khong_ro"] = Field(
        description=(
            "cùng ông/bà/cùng một gốc -> co; "
            "quan hệ chỉ do hôn nhân -> khong; không đủ dữ kiện -> khong_ro."
        )
    )


_SEED_BODY = f"""
WITH $lqh AS lqh, $lrh AS lrh, $kc AS kc, $seed_cam AS seed_cam,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (qh:QuanHe:{TOPIC_LABEL} {{id: lqh, topic: '{TOPIC}'}})
WHERE lqh <> '' AND NOT lrh IN ['khong_ro', 'can_huyet_khong_ro']

OPTIONAL MATCH (qh_truc:QuanHe:{TOPIC_LABEL} {{
  id: 'cung_dong_mau_ve_truc_he', topic: '{TOPIC}'
}})
WHERE lrh IN ['cung_dong_mau_truc_he', 'can_huyet_khong_ro', 'khong_ro']
   OR kc IN ['cach_tinh_ba_doi', 'phai_qua_may_doi', 'tong_quat']

OPTIONAL MATCH (qh_ba:QuanHe:{TOPIC_LABEL} {{
  id: 'co_ho_trong_pham_vi_ba_doi', topic: '{TOPIC}'
}})
WHERE lrh IN [
  'ho_trong_pham_vi_ba_doi', 'can_huyet_khong_ro', 'hai_chau_noi_cung_goc', 'khong_ro'
] OR kc IN ['cach_tinh_ba_doi', 'phai_qua_may_doi', 'tong_quat']

OPTIONAL MATCH (hv_cam:HanhVi:{TOPIC_LABEL} {{
  id: 'ket_hon_trong_quan_he_than_thich_bi_cam', topic: '{TOPIC}'
}})
WHERE seed_cam = true

WITH wl, kc, lrh, seed_cam,
  [x IN collect(DISTINCT qh) + collect(DISTINCT qh_truc) + collect(DISTINCT qh_ba)
       + collect(DISTINCT hv_cam)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN kc IN ['cach_tinh_ba_doi', 'phai_qua_may_doi'] THEN
      [x IN collect(DISTINCT qh_ba) + collect(DISTINCT qh_truc) WHERE x IS NOT NULL]
    WHEN seed_cam = true THEN
      [x IN collect(DISTINCT qh) + collect(DISTINCT qh_truc) + collect(DISTINCT qh_ba)
           + collect(DISTINCT hv_cam)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT qh) + collect(DISTINCT qh_truc) + collect(DISTINCT qh_ba)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: QuanHeHuyetThongVaBaDoiParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    lrh = params.loai_quan_he_huyet_thong
    lqh = _RELATION_IDS.get(lrh, "")
    seed_cam = params.khia_canh_ba_doi == "co_duoc_ket_hon"
    return {
        "lqh": lqh,
        "lrh": lrh,
        "kc": params.khia_canh_ba_doi,
        "seed_cam": seed_cam,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


quan_he_huyet_thong_va_ba_doi = CypherTemplate(
    name="quan_he_huyet_thong_va_ba_doi",
    description=(
        "Đánh giá quan hệ cùng dòng máu trực hệ, họ trong phạm vi ba đời, anh chị em "
        "cùng cha khác mẹ, anh em họ và các mô tả cây gia đình tương đương. Template phải "
        "seed định nghĩa Điều 3 khoản 17/18 trước khi seed điều cấm tại Điều 5 khoản 2 điểm d. "
        "Ví dụ: Có được đăng ký kết hôn trong phạm vi ba đời không?; "
        "Có được kết hôn với nhau khi là anh em cùng cha khác mẹ hay không?"
    ),
    params_schema=QuanHeHuyetThongVaBaDoiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
