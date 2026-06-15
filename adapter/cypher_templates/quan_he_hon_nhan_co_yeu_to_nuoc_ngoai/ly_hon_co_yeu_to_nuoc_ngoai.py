"""Template — ly hôn có yếu tố nước ngoài (Đ127, Đ51 K1)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_ly_hon",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_127", "Luat_HNGD_2014_Dieu_51_Khoan_1"]


class LyHonYeuToNuocNgoaiParams(BaseModel):
    nhom_chu_the: Literal[
        "cong_dan_viet_nam_voi_nguoi_nuoc_ngoai",
        "hai_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam",
        "cong_dan_viet_nam_khong_thuong_tru_tai_viet_nam",
        "hai_cong_dan_viet_nam_o_nuoc_ngoai",
        "khong_ro",
    ] = Field(description="Nhóm chủ thể trong vụ ly hôn.")
    hinh_thuc_ly_hon: Literal["thuan_tinh", "don_phuong", "khong_ro"] = Field(
        description="thuận tình / đơn phương ly hôn."
    )
    tinh_trang_noi_thuong_tru_chung: Literal["co", "khong", "khong_ro"] = Field(
        description="có/không nơi thường trú chung của vợ chồng."
    )
    nuoc_thuong_tru_chung: str | None = Field(default=None, description="Quốc gia thường trú chung nếu có.")
    loai_tai_san: Literal["bat_dong_san_o_nuoc_ngoai", "tai_san_khac", "khong_de_cap"] = Field(
        description="bất động sản ở nước ngoài → bat_dong_san_o_nuoc_ngoai."
    )
    nuoc_co_bat_dong_san: str | None = Field(default=None, description="Quốc gia có bất động sản.")
    khia_canh_ly_hon: Literal[
        "tham_quyen_giai_quyet",
        "phap_luat_ap_dung",
        "quyen_yeu_cau_ly_hon",
        "tai_san",
        "tong_hop",
        "tong_quat",
    ] = Field(description="Khía cạnh câu hỏi về ly hôn.")


_SEED_BODY = f"""
WITH $nhom_chu_the AS nc, $hinh_thuc_ly_hon AS ht, $tinh_trang_noi_thuong_tru_chung AS tt,
     $loai_tai_san AS ts, $khia_canh_ly_hon AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (l_cq:CoQuan:{TOPIC_LABEL} {{
  id: 'co_quan_co_tham_quyen_viet_nam_giai_quyet_ly_hon', topic: '{TOPIC}'
}})
WHERE kc IN ['tham_quyen_giai_quyet', 'tong_hop', 'tong_quat', 'khong_ro']
OPTIONAL MATCH (l_vn:QuanHe:{TOPIC_LABEL} {{
  id: 'ly_hon_cong_dan_viet_nam_voi_nguoi_nuoc_ngoai', topic: '{TOPIC}'
}})
WHERE nc IN ['cong_dan_viet_nam_voi_nguoi_nuoc_ngoai', 'khong_ro']
OPTIONAL MATCH (l_nn:QuanHe:{TOPIC_LABEL} {{
  id: 'ly_hon_giua_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam', topic: '{TOPIC}'
}})
WHERE nc IN ['hai_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam', 'khong_ro']

OPTIONAL MATCH (l_tt:HanhVi:{TOPIC_LABEL} {{
  id: 'thuan_tinh_ly_hon_co_yeu_to_nuoc_ngoai', topic: '{TOPIC}'
}})
WHERE ht = 'thuan_tinh'
OPTIONAL MATCH (l_dp:HanhVi:{TOPIC_LABEL} {{
  id: 'don_phuong_ly_hon_co_yeu_to_nuoc_ngoai', topic: '{TOPIC}'
}})
WHERE ht IN ['don_phuong', 'khong_ro'] OR kc IN ['quyen_yeu_cau_ly_hon', 'tong_hop']

OPTIONAL MATCH (l_co_tt:QuyDinh:{TOPIC_LABEL} {{
  id: 'phap_luat_noi_thuong_tru_chung_cua_vo_chong', topic: '{TOPIC}'
}})
WHERE nc IN ['cong_dan_viet_nam_khong_thuong_tru_tai_viet_nam', 'hai_cong_dan_viet_nam_o_nuoc_ngoai', 'khong_ro']
  AND tt = 'co'
OPTIONAL MATCH (l_khong_tt:QuyDinh:{TOPIC_LABEL} {{
  id: 'khong_co_noi_thuong_tru_chung_ap_dung_phap_luat_viet_nam', topic: '{TOPIC}'
}})
WHERE nc IN ['cong_dan_viet_nam_khong_thuong_tru_tai_viet_nam', 'hai_cong_dan_viet_nam_o_nuoc_ngoai', 'khong_ro']
  AND tt IN ['khong', 'khong_ro']

OPTIONAL MATCH (l_bds:TaiSan:{TOPIC_LABEL} {{id: 'bat_dong_san_o_nuoc_ngoai', topic: '{TOPIC}'}})
WHERE ts = 'bat_dong_san_o_nuoc_ngoai' OR kc IN ['tai_san', 'tong_hop']
OPTIONAL MATCH (l_bds_qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'phap_luat_noi_co_bat_dong_san', topic: '{TOPIC}'
}})
WHERE ts = 'bat_dong_san_o_nuoc_ngoai' OR kc IN ['tai_san', 'tong_hop']

WITH wl, nc, ht, tt, ts, kc,
  collect(DISTINCT l_cq) + collect(DISTINCT l_vn) + collect(DISTINCT l_nn)
    + collect(DISTINCT l_tt) + collect(DISTINCT l_dp)
    + collect(DISTINCT l_co_tt) + collect(DISTINCT l_khong_tt)
    + collect(DISTINCT l_bds) + collect(DISTINCT l_bds_qd) AS seed_nodes,
  CASE
    WHEN ts = 'bat_dong_san_o_nuoc_ngoai' OR kc = 'tai_san' THEN
      [x IN collect(DISTINCT l_bds) + collect(DISTINCT l_bds_qd) WHERE x IS NOT NULL]
    WHEN kc = 'tong_hop' THEN
      [x IN collect(DISTINCT l_dp) + collect(DISTINCT l_bds) + collect(DISTINCT l_bds_qd)
       WHERE x IS NOT NULL]
    WHEN ht = 'thuan_tinh' THEN
      [x IN collect(DISTINCT l_tt) WHERE x IS NOT NULL]
    WHEN ht = 'don_phuong' THEN
      [x IN collect(DISTINCT l_dp) WHERE x IS NOT NULL]
    WHEN kc = 'tham_quyen_giai_quyet' THEN
      [x IN collect(DISTINCT l_cq) + collect(DISTINCT l_vn) + collect(DISTINCT l_nn)
       WHERE x IS NOT NULL]
    WHEN tt = 'co' THEN
      [x IN collect(DISTINCT l_co_tt) WHERE x IS NOT NULL]
    WHEN tt = 'khong' THEN
      [x IN collect(DISTINCT l_khong_tt) WHERE x IS NOT NULL]
    WHEN kc = 'phap_luat_ap_dung' THEN
      [x IN collect(DISTINCT l_co_tt) + collect(DISTINCT l_khong_tt) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT l_cq) + collect(DISTINCT l_vn) + collect(DISTINCT l_nn)
           + collect(DISTINCT l_co_tt) + collect(DISTINCT l_khong_tt)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: LyHonYeuToNuocNgoaiParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS) and params.loai_tai_san != "bat_dong_san_o_nuoc_ngoai"
    if params.khia_canh_ly_hon in ("tai_san", "tong_hop") and params.loai_tai_san == "bat_dong_san_o_nuoc_ngoai":
        use_wl = False
    return {
        "nhom_chu_the": params.nhom_chu_the,
        "hinh_thuc_ly_hon": params.hinh_thuc_ly_hon,
        "tinh_trang_noi_thuong_tru_chung": params.tinh_trang_noi_thuong_tru_chung,
        "loai_tai_san": params.loai_tai_san,
        "khia_canh_ly_hon": params.khia_canh_ly_hon,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


ly_hon_co_yeu_to_nuoc_ngoai = CypherTemplate(
    name="ly_hon_co_yeu_to_nuoc_ngoai",
    description=(
        "Dùng cho thẩm quyền và luật áp dụng khi ly hôn có yếu tố nước ngoài, gồm nơi "
        "thường trú chung và bất động sản ở nước ngoài. Seed nhánh thuận tình/đơn phương "
        "cho câu tổng hợp. "
        "Ví dụ: Hai công dân Việt Nam ở Singapore không có nơi thường trú chung ly hôn "
        "theo luật nào?; Đơn phương ly hôn và có nhà tại Thụy Điển xử lý thế nào?"
    ),
    params_schema=LyHonYeuToNuocNgoaiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
