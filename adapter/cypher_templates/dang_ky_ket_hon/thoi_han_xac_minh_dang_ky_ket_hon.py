"""Template — thời hạn xác minh/giải quyết hồ sơ đăng ký kết hôn."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.dang_ky_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("cap_dang_ky",)
_DIEU_18_WHITELIST = ["Luat_HoTich_2014_Dieu_18"]
_DIEU_38_WHITELIST = ["Luat_HoTich_2014_Dieu_38"]


class ThoiHanXacMinhDangKyKetHonParams(BaseModel):
    cap_dang_ky: Literal["cap_xa", "cap_huyen", "xa_bien_gioi", "khong_ro"] = Field(
        description="Phường/xã -> cap_xa; huyện/quận -> cap_huyen; xã biên giới -> xa_bien_gioi."
    )
    khia_canh_thoi_han: Literal[
        "xac_minh_dieu_kien", "giai_quyet_ho_so", "dang_ky_lai", "tong_quat"
    ] = Field(
        description=(
            "Xác minh điều kiện -> xac_minh_dieu_kien; giải quyết hồ sơ -> giai_quyet_ho_so; "
            "đăng ký lại -> dang_ky_lai."
        )
    )
    co_can_xac_minh: Literal["co", "khong", "khong_ro"] = Field(
        description="Cơ quan báo cần xác minh -> co."
    )


_SEED_BODY = f"""
WITH $cap AS cap, $kc AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{id: 'can_xac_minh_dieu_kien_ket_hon', topic: '{TOPIC}'}})
WHERE kc IN ['xac_minh_dieu_kien', 'tong_quat']

OPTIONAL MATCH (th_xa:ThoiHan:{TOPIC_LABEL} {{id: 'xac_minh_cap_xa_khong_qua_05_ngay_lam_viec', topic: '{TOPIC}'}})
WHERE cap IN ['cap_xa', 'khong_ro'] AND kc IN ['xac_minh_dieu_kien', 'tong_quat']

OPTIONAL MATCH (hv:HanhVi:{TOPIC_LABEL} {{id: 'kiem_tra_xac_minh_ho_so_ket_hon', topic: '{TOPIC}'}})
WHERE kc IN ['xac_minh_dieu_kien', 'giai_quyet_ho_so', 'tong_quat']
OPTIONAL MATCH (hv)-[:CO_THOI_HAN]->(th_hv:ThoiHan:{TOPIC_LABEL})
WHERE hv IS NOT NULL AND th_hv.topic = '{TOPIC}'

OPTIONAL MATCH (th_huyen:ThoiHan:{TOPIC_LABEL} {{id: 'giai_quyet_cap_huyen_15_ngay', topic: '{TOPIC}'}})
WHERE cap IN ['cap_huyen', 'khong_ro'] AND kc IN ['giai_quyet_ho_so', 'xac_minh_dieu_kien', 'tong_quat']

OPTIONAL MATCH (cq_bg:CoQuanDangKy:{TOPIC_LABEL} {{id: 'ubnd_xa_khu_vuc_bien_gioi', topic: '{TOPIC}'}})
WHERE cap = 'xa_bien_gioi'
OPTIONAL MATCH (cq_bg)-[:LIEN_QUAN]->(th_bg1:ThoiHan:{TOPIC_LABEL} {{id: 'giai_quyet_xa_bien_gioi_03_ngay_lam_viec', topic: '{TOPIC}'}})
WHERE cq_bg IS NOT NULL
OPTIONAL MATCH (cq_bg)-[:LIEN_QUAN]->(th_bg2:ThoiHan:{TOPIC_LABEL} {{id: 'xac_minh_xa_bien_gioi_khong_qua_08_ngay_lam_viec', topic: '{TOPIC}'}})
WHERE cq_bg IS NOT NULL

OPTIONAL MATCH (th_dkl:ThoiHan:{TOPIC_LABEL})
WHERE th_dkl.id IN [
  'kiem_tra_ho_so_dang_ky_lai_05_ngay_lam_viec',
  'noi_dang_ky_truoc_tra_loi_05_ngay_lam_viec',
  'hoan_tat_dang_ky_lai_03_ngay_sau_xac_minh'
] AND th_dkl.topic = '{TOPIC}' AND kc = 'dang_ky_lai'

WITH wl, cap, kc,
  [x IN collect(DISTINCT dk) + collect(DISTINCT th_xa) + collect(DISTINCT hv)
       + collect(DISTINCT th_hv) + collect(DISTINCT th_huyen) + collect(DISTINCT cq_bg)
       + collect(DISTINCT th_bg1) + collect(DISTINCT th_bg2) + collect(DISTINCT th_dkl)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'dang_ky_lai' THEN
      [x IN collect(DISTINCT th_dkl) WHERE x IS NOT NULL]
    WHEN 'xac_minh_dieu_kien' THEN
      [x IN collect(DISTINCT th_xa) + collect(DISTINCT th_hv) WHERE x IS NOT NULL]
    WHEN 'giai_quyet_ho_so' THEN
      [x IN collect(DISTINCT th_huyen) + collect(DISTINCT th_bg1) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT th_xa) + collect(DISTINCT th_huyen) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ThoiHanXacMinhDangKyKetHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    cap = params.cap_dang_ky
    if use_wl:
        wl = _DIEU_18_WHITELIST + _DIEU_38_WHITELIST
    elif cap == "cap_huyen":
        wl = _DIEU_38_WHITELIST
    else:
        wl = _DIEU_18_WHITELIST if cap in ("cap_xa", "xa_bien_gioi", "khong_ro") else []
    return {
        "cap": cap,
        "kc": params.khia_canh_thoi_han,
        "whitelist_dieu_ids": wl,
    }


thoi_han_xac_minh_dang_ky_ket_hon = CypherTemplate(
    name="thoi_han_xac_minh_dang_ky_ket_hon",
    description=(
        "Trả lời câu hỏi bao lâu/bao nhiêu ngày về xác minh hoặc giải quyết hồ sơ đăng ký kết hôn "
        "theo đúng cấp cơ quan (Đ18 K2, Đ38 K2, NĐ123 Đ18). "
        "Ví dụ: Xác minh điều kiện kết hôn mất bao nhiêu ngày?; "
        "Phường báo cần xác minh thì trong bao lâu?"
    ),
    params_schema=ThoiHanXacMinhDangKyKetHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
