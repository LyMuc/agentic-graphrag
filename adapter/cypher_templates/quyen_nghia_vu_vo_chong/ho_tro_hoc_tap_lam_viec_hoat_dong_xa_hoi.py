"""Template — hỗ trợ học tập, làm việc và hoạt động xã hội (Đ23)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quyen_nghia_vu_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
)

_LINH_VUC_QUYEN: dict[str, list[str]] = {
    "chon_nghe_nghiep": ["quyen_chon_nghe_nghiep", "nghia_vu_tao_dieu_kien_giup_do_chon_nghe_nghiep"],
    "lam_viec_kiem_tien": ["quyen_chon_nghe_nghiep", "nghia_vu_tao_dieu_kien_giup_do_chon_nghe_nghiep"],
    "hoc_tap_nang_cao_trinh_do": [
        "quyen_hoc_tap_nang_cao_trinh_do",
        "nghia_vu_tao_dieu_kien_giup_do_hoc_tap_nang_cao_trinh_do",
    ],
    "hoat_dong_chinh_tri": [
        "quyen_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "nghia_vu_tao_dieu_kien_giup_do_tham_gia_hoat_dong_xa_hoi",
    ],
    "hoat_dong_kinh_te": [
        "quyen_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "nghia_vu_tao_dieu_kien_giup_do_tham_gia_hoat_dong_xa_hoi",
    ],
    "hoat_dong_van_hoa": [
        "quyen_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "nghia_vu_tao_dieu_kien_giup_do_tham_gia_hoat_dong_xa_hoi",
    ],
    "hoat_dong_xa_hoi": [
        "quyen_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "nghia_vu_tao_dieu_kien_giup_do_tham_gia_hoat_dong_xa_hoi",
    ],
    "hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi": [
        "quyen_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "nghia_vu_tao_dieu_kien_giup_do_tham_gia_hoat_dong_xa_hoi",
    ],
}

_NHIEU_LINH_VUC_IDS = [
    "quyen_chon_nghe_nghiep",
    "nghia_vu_tao_dieu_kien_giup_do_chon_nghe_nghiep",
    "quyen_hoc_tap_nang_cao_trinh_do",
    "nghia_vu_tao_dieu_kien_giup_do_hoc_tap_nang_cao_trinh_do",
    "quyen_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
    "nghia_vu_tao_dieu_kien_giup_do_tham_gia_hoat_dong_xa_hoi",
]


class HoTroHocTapLamViecHoatDongXaHoiParams(BaseModel):
    linh_vuc_hoat_dong: Literal[
        "chon_nghe_nghiep",
        "lam_viec_kiem_tien",
        "hoc_tap_nang_cao_trinh_do",
        "hoat_dong_chinh_tri",
        "hoat_dong_kinh_te",
        "hoat_dong_van_hoa",
        "hoat_dong_xa_hoi",
        "hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "nhieu_linh_vuc",
        "khong_ro",
    ] = Field(description="chọn nghề nghiệp -> chon_nghe_nghiep; đi làm/kiếm tiền -> lam_viec_kiem_tien.")
    dang_hanh_vi: Literal[
        "tao_dieu_kien_giup_do",
        "cam_can_han_che",
        "khong_dong_y",
        "hoi_quyen_nghia_vu",
        "tong_quat",
        "khong_ro",
    ] = Field(description="cấm đi làm -> cam_can_han_che; chồng không đồng ý -> khong_dong_y.")


_SEED_BODY = f"""
WITH $lv AS lv, $dh AS dh, $seed_nhieu AS seed_nhieu, $seed_cam AS seed_cam,
     $ids AS ids, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (node)
WHERE (node:Quyen:{TOPIC_LABEL} OR node:NghiaVu:{TOPIC_LABEL})
  AND node.topic = '{TOPIC}'
  AND node.id IN ids

OPTIONAL MATCH (hv_l:HanhVi:{TOPIC_LABEL} {{
  id: 'cam_can_di_lam_kiem_tien', topic: '{TOPIC}'
}})
WHERE seed_cam = true AND lv IN ['lam_viec_kiem_tien', 'chon_nghe_nghiep']

OPTIONAL MATCH (hv_x:HanhVi:{TOPIC_LABEL} {{
  id: 'can_tro_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi', topic: '{TOPIC}'
}})
WHERE seed_cam = true AND lv IN [
  'hoat_dong_chinh_tri', 'hoat_dong_kinh_te', 'hoat_dong_van_hoa',
  'hoat_dong_xa_hoi', 'hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi'
]

OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{
  id: 'dau_hieu_can_tro_quyen_hoc_tap_lam_viec_hoat_dong_xa_hoi', topic: '{TOPIC}'
}})
WHERE seed_cam = true

WITH wl, lv,
  collect(DISTINCT node) + collect(DISTINCT hv_l)
    + collect(DISTINCT hv_x) + collect(DISTINCT hq)
    AS seed_nodes,
  [x IN collect(DISTINCT node) + collect(DISTINCT hv_l)
       + collect(DISTINCT hv_x) + collect(DISTINCT hq)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: HoTroHocTapLamViecHoatDongXaHoiParams) -> dict[str, Any]:
    lv = params.linh_vuc_hoat_dong
    dh = params.dang_hanh_vi
    if lv == "nhieu_linh_vuc" or dh in ("hoi_quyen_nghia_vu", "tong_quat"):
        ids = _NHIEU_LINH_VUC_IDS
    elif lv in _LINH_VUC_QUYEN:
        ids = _LINH_VUC_QUYEN[lv]
    else:
        ids = _NHIEU_LINH_VUC_IDS
    seed_cam = dh in ("cam_can_han_che", "khong_dong_y")
    return {
        "lv": lv,
        "dh": dh,
        "seed_nhieu": lv == "nhieu_linh_vuc",
        "seed_cam": seed_cam,
        "ids": ids,
        "whitelist_dieu_ids": [],
    }


ho_tro_hoc_tap_lam_viec_hoat_dong_xa_hoi = CypherTemplate(
    name="ho_tro_hoc_tap_lam_viec_hoat_dong_xa_hoi",
    description=(
        "Trả lời quyền, nghĩa vụ tạo điều kiện và giúp đỡ nhau chọn nghề nghiệp, học tập, "
        "nâng cao trình độ và tham gia hoạt động chính trị, kinh tế, văn hóa, xã hội theo Điều 23. "
        "Dùng cho cả câu hỏi quyền chủ động và hành vi cấm cản từ bên kia. "
        "Ví dụ: Quyền, nghĩa vụ về nghề nghiệp và học tập của vợ chồng?; "
        "Chồng cấm vợ đi làm kiếm tiền có vi phạm?; "
        "Vợ tham gia hoạt động xã hội khi chồng không đồng ý?"
    ),
    params_schema=HoTroHocTapLamViecHoatDongXaHoiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
