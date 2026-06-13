"""Template — giải quyết tài sản khi người bị tuyên bố đã chết trở về (Đ67 k2)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.hon_nhan_cham_dut_do_vo_chong_chet._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_tai_san", "tinh_trang_khoi_phuc_hon_nhan")
_DIEU_67_K2_WHITELIST = ["Luat_HNGD_2014_Dieu_67_Khoan_2"]


class GiaiQuyetTaiSanKhiTroVeParams(BaseModel):
    loai_quyet_dinh_truoc_khi_tro_ve: Literal[
        "tuyen_bo_da_chet",
        "tuyen_bo_mat_tich",
        "khong_ro",
    ] = Field(description="Giữ nguyên dữ kiện để phát hiện mismatch Điều 67.")
    tinh_trang_khoi_phuc_hon_nhan: Literal[
        "duoc_khoi_phuc",
        "khong_duoc_khoi_phuc",
        "khong_ro",
    ] = Field(description="Quyết định seed điểm a, điểm b hoặc cả hai.")
    khia_canh_tai_san: Literal[
        "khoi_phuc_quan_he_tai_san",
        "tai_san_trong_thoi_gian_bi_tuyen_bo_da_chet",
        "tai_san_truoc_tuyen_bo_chua_chia",
        "co_duoc_chia_lai_hay_khong",
        "tong_quat",
    ] = Field(description="Chọn leaf tài sản/hậu quả cụ thể.")


_SEED_BODY = f"""
WITH $loai AS loai, $kp AS kp, $kc AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (dk_xm:DieuKien:{TOPIC_LABEL} {{id: 'can_xac_minh_quyet_dinh_mat_tich_hay_tuyen_bo_da_chet', topic: '{TOPIC}'}})
WHERE loai = 'tuyen_bo_mat_tich'

OPTIONAL MATCH (dk_kp:DieuKien:{TOPIC_LABEL} {{id: 'hon_nhan_duoc_khoi_phuc', topic: '{TOPIC}'}})
WHERE kp IN ['duoc_khoi_phuc', 'tong_quat', 'khong_ro'] OR kc IN ['khoi_phuc_quan_he_tai_san', 'tai_san_trong_thoi_gian_bi_tuyen_bo_da_chet', 'tong_quat']
OPTIONAL MATCH (hv_kp:HanhVi:{TOPIC_LABEL} {{id: 'khoi_phuc_quan_he_tai_san_sau_khi_huy_bo_tuyen_bo_da_chet', topic: '{TOPIC}'}})
WHERE dk_kp IS NOT NULL
OPTIONAL MATCH (hq_kp:HauQua:{TOPIC_LABEL} {{id: 'quan_he_tai_san_duoc_khoi_phuc_tu_ngay_huy_bo_co_hieu_luc', topic: '{TOPIC}'}})
WHERE hv_kp IS NOT NULL
OPTIONAL MATCH (ts_kp:LoaiTaiSan:{TOPIC_LABEL} {{id: 'tai_san_co_duoc_trong_thoi_gian_bi_tuyen_bo_da_chet', topic: '{TOPIC}'}})
WHERE hv_kp IS NOT NULL OR kc = 'tai_san_trong_thoi_gian_bi_tuyen_bo_da_chet'
OPTIONAL MATCH (hq_rieng:HauQua:{TOPIC_LABEL} {{id: 'tai_san_trong_thoi_gian_tuyen_bo_la_tai_san_rieng', topic: '{TOPIC}'}})
WHERE ts_kp IS NOT NULL

OPTIONAL MATCH (dk_khong:DieuKien:{TOPIC_LABEL} {{id: 'hon_nhan_khong_duoc_khoi_phuc', topic: '{TOPIC}'}})
WHERE kp IN ['khong_duoc_khoi_phuc', 'tong_quat', 'khong_ro'] OR kc IN ['tai_san_truoc_tuyen_bo_chua_chia', 'co_duoc_chia_lai_hay_khong', 'tong_quat']
OPTIONAL MATCH (hv_ly:HanhVi:{TOPIC_LABEL} {{id: 'giai_quyet_tai_san_nhu_chia_tai_san_khi_ly_hon', topic: '{TOPIC}'}})
WHERE dk_khong IS NOT NULL
OPTIONAL MATCH (ts_truoc:LoaiTaiSan:{TOPIC_LABEL} {{id: 'tai_san_co_truoc_tuyen_bo_da_chet_chua_chia', topic: '{TOPIC}'}})
WHERE hv_ly IS NOT NULL OR kc = 'tai_san_truoc_tuyen_bo_chua_chia'
OPTIONAL MATCH (hq_ly:HauQua:{TOPIC_LABEL} {{id: 'tai_san_truoc_tuyen_bo_chua_chia_duoc_giai_quyet_nhu_ly_hon', topic: '{TOPIC}'}})
WHERE hv_ly IS NOT NULL

WITH wl, loai, kp, kc,
  [x IN collect(DISTINCT dk_xm) + collect(DISTINCT dk_kp) + collect(DISTINCT hv_kp)
       + collect(DISTINCT hq_kp) + collect(DISTINCT ts_kp) + collect(DISTINCT hq_rieng)
       + collect(DISTINCT dk_khong) + collect(DISTINCT hv_ly) + collect(DISTINCT ts_truoc)
       + collect(DISTINCT hq_ly)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN loai = 'tuyen_bo_mat_tich' THEN
      [x IN collect(DISTINCT dk_xm) WHERE x IS NOT NULL]
    WHEN kp = 'duoc_khoi_phuc' THEN
      [x IN collect(DISTINCT hv_kp) + collect(DISTINCT hq_kp) + collect(DISTINCT ts_kp)
           + collect(DISTINCT hq_rieng)
       WHERE x IS NOT NULL]
    WHEN kp = 'khong_duoc_khoi_phuc' THEN
      [x IN collect(DISTINCT hv_ly) + collect(DISTINCT ts_truoc) + collect(DISTINCT hq_ly)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hv_kp) + collect(DISTINCT hq_kp) + collect(DISTINCT hv_ly)
           + collect(DISTINCT hq_ly)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: GiaiQuyetTaiSanKhiTroVeParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    wl = _DIEU_67_K2_WHITELIST if use_wl or params.loai_quyet_dinh_truoc_khi_tro_ve == "tuyen_bo_mat_tich" else []
    return {
        "loai": params.loai_quyet_dinh_truoc_khi_tro_ve,
        "kp": params.tinh_trang_khoi_phuc_hon_nhan,
        "kc": params.khia_canh_tai_san,
        "whitelist_dieu_ids": wl,
    }


giai_quyet_tai_san_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve = CypherTemplate(
    name="giai_quyet_tai_san_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve",
    description=(
        "Truy xuất Điều 67 khoản 2 để phân biệt tài sản khi hôn nhân được khôi phục "
        "và khi hôn nhân không được khôi phục. Nhánh khôi phục seed điểm a; "
        "nhánh không khôi phục seed điểm b. "
        "Ví dụ: Chồng bị tuyên bố đã chết trở về có được lại chia tài sản không?; "
        "Tài sản chung trước đó được giải quyết thế nào nếu hôn nhân không được khôi phục?"
    ),
    params_schema=GiaiQuyetTaiSanKhiTroVeParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
