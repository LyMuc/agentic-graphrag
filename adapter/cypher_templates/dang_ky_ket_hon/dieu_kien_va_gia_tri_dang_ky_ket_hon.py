"""Template — điều kiện và giá trị pháp lý đăng ký kết hôn (Đ8, Đ9, Đ13)."""
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

_ROUTER_FIELDS = ("khia_canh_dieu_kien_gia_tri",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_8", "Luat_HNGD_2014_Dieu_9"]


class DieuKienVaGiaTriDangKyKetHonParams(BaseModel):
    tinh_trang_dang_ky: Literal[
        "chua_dang_ky", "da_dang_ky", "sai_tham_quyen", "khong_ro"
    ] = Field(
        description=(
            "Chỉ cưới/chưa đăng ký -> chua_dang_ky; đã đăng ký -> da_dang_ky; "
            "đăng ký sai thẩm quyền -> sai_tham_quyen."
        )
    )
    khia_canh_dieu_kien_gia_tri: Literal[
        "dieu_kien_ket_hon",
        "gia_tri_khi_khong_dang_ky",
        "thoi_diem_so_voi_le_cuoi",
        "xu_ly_sai_tham_quyen",
        "tong_quat",
    ] = Field(
        description=(
            "Cần điều kiện gì -> dieu_kien_ket_hon; không đăng ký có giá trị không "
            "-> gia_tri_khi_khong_dang_ky; trước lễ cưới bao lâu -> thoi_diem_so_voi_le_cuoi; "
            "sai thẩm quyền -> xu_ly_sai_tham_quyen."
        )
    )


_SEED_BODY = f"""
WITH $kc AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{id: 'du_dieu_kien_ket_hon', topic: '{TOPIC}'}})
WHERE kc IN ['dieu_kien_ket_hon', 'tong_quat', 'thoi_diem_so_voi_le_cuoi']
OPTIONAL MATCH (dk)-[:LIEN_QUAN]->(dk_leaf:DieuKien:{TOPIC_LABEL})
WHERE dk IS NOT NULL AND dk_leaf.topic = '{TOPIC}'

OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_dang_ky_ket_hon', topic: '{TOPIC}'}})
WHERE kc IN ['dieu_kien_ket_hon', 'gia_tri_khi_khong_dang_ky', 'tong_quat', 'thoi_diem_so_voi_le_cuoi']

OPTIONAL MATCH (nv)-[:DAN_TOI]->(hq_xl:HauQua:{TOPIC_LABEL} {{id: 'quan_he_vo_chong_duoc_xac_lap_sau_dang_ky', topic: '{TOPIC}'}})
WHERE kc IN ['dieu_kien_ket_hon', 'thoi_diem_so_voi_le_cuoi', 'tong_quat']

OPTIONAL MATCH (nv)-[:DAN_TOI]->(hq_kxl:HauQua:{TOPIC_LABEL} {{id: 'ket_hon_khong_dang_ky_khong_co_gia_tri_phap_ly', topic: '{TOPIC}'}})
WHERE kc IN ['gia_tri_khi_khong_dang_ky', 'tong_quat']

OPTIONAL MATCH (hv_dk:HanhVi:{TOPIC_LABEL} {{id: 'thuc_hien_dang_ky_ket_hon', topic: '{TOPIC}'}})
WHERE kc IN ['thoi_diem_so_voi_le_cuoi', 'tong_quat']

OPTIONAL MATCH (dk_sq:DieuKien:{TOPIC_LABEL} {{id: 'dang_ky_ket_hon_khong_dung_tham_quyen', topic: '{TOPIC}'}})
WHERE kc IN ['xu_ly_sai_tham_quyen', 'tong_quat']
OPTIONAL MATCH (hv_th:HanhVi:{TOPIC_LABEL} {{id: 'thu_hoi_huy_giay_sai_tham_quyen', topic: '{TOPIC}'}})
WHERE kc IN ['xu_ly_sai_tham_quyen', 'tong_quat']
OPTIONAL MATCH (hv_th)-[:THUC_HIEN_LAI]->(hv_lai:HanhVi:{TOPIC_LABEL} {{id: 'thuc_hien_lai_dang_ky_dung_tham_quyen', topic: '{TOPIC}'}})
WHERE hv_th IS NOT NULL
OPTIONAL MATCH (hv_lai)-[:DAN_TOI]->(hq_sq:HauQua:{TOPIC_LABEL} {{id: 'quan_he_sai_tham_quyen_tinh_tu_ngay_dang_ky_truoc', topic: '{TOPIC}'}})
WHERE hv_lai IS NOT NULL

WITH wl, kc,
  [x IN collect(DISTINCT dk) + collect(DISTINCT dk_leaf) + collect(DISTINCT nv)
       + collect(DISTINCT hq_xl) + collect(DISTINCT hq_kxl) + collect(DISTINCT hv_dk)
       + collect(DISTINCT dk_sq) + collect(DISTINCT hv_th) + collect(DISTINCT hv_lai)
       + collect(DISTINCT hq_sq)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'dieu_kien_ket_hon' THEN
      [x IN collect(DISTINCT dk) + collect(DISTINCT dk_leaf) + collect(DISTINCT nv)
       WHERE x IS NOT NULL]
    WHEN 'gia_tri_khi_khong_dang_ky' THEN
      [x IN collect(DISTINCT nv) + collect(DISTINCT hq_kxl) WHERE x IS NOT NULL]
    WHEN 'xu_ly_sai_tham_quyen' THEN
      [x IN collect(DISTINCT dk_sq) + collect(DISTINCT hv_th) + collect(DISTINCT hv_lai)
           + collect(DISTINCT hq_sq)
       WHERE x IS NOT NULL]
    WHEN 'thoi_diem_so_voi_le_cuoi' THEN
      [x IN collect(DISTINCT dk) + collect(DISTINCT nv) + collect(DISTINCT hv_dk)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT dk) + collect(DISTINCT nv) + collect(DISTINCT hq_kxl)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: DieuKienVaGiaTriDangKyKetHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "kc": params.khia_canh_dieu_kien_gia_tri,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


dieu_kien_va_gia_tri_dang_ky_ket_hon = CypherTemplate(
    name="dieu_kien_va_gia_tri_dang_ky_ket_hon",
    description=(
        "Trả lời điều kiện nền để đăng ký, giá trị pháp lý khi không đăng ký, thời điểm "
        "đăng ký so với lễ cưới và xử lý đăng ký sai thẩm quyền (Đ8, Đ9, Đ13). "
        "Ví dụ: Cần đáp ứng điều kiện gì để đăng ký kết hôn?; "
        "Cưới mà không đăng ký có được công nhận là vợ chồng không?"
    ),
    params_schema=DieuKienVaGiaTriDangKyKetHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
