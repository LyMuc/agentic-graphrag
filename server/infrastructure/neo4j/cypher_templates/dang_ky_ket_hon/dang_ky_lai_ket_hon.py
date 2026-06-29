"""Template — đăng ký lại kết hôn (NĐ123 Đ24, Đ27)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_dang_ky_lai",)
_DIEU_WHITELIST = [
    "NghiDinh_123_2015_ND_CP_Dieu_24",
    "NghiDinh_123_2015_ND_CP_Dieu_27",
]


class DangKyLaiKetHonParams(BaseModel):
    khia_canh_dang_ky_lai: Literal[
        "dieu_kien", "ho_so", "thu_tuc_thoi_han", "hieu_luc_quan_he", "tong_quat"
    ] = Field(
        description=(
            "Khi nào/điều kiện cấp lại -> dieu_kien; cần giấy tờ gì -> ho_so; "
            "mất bao lâu/trình tự -> thu_tuc_thoi_han; hôn nhân tính từ ngày nào "
            "-> hieu_luc_quan_he."
        )
    )
    tinh_trang_luu_tru: Literal[
        "so_va_ban_chinh_deu_mat", "chi_mat_ban_chinh", "chi_mat_so", "khong_ro"
    ] = Field(
        description=(
            "Mất cả Sổ hộ tịch và bản chính -> so_va_ban_chinh_deu_mat; "
            "chỉ mất giấy/bản chính -> chi_mat_ban_chinh; chỉ mất sổ -> chi_mat_so."
        )
    )
    thoi_diem_dang_ky_truoc: Literal["truoc_2016", "tu_2016_tro_di", "khong_ro"] = Field(
        description="Đăng ký trước 01/01/2016 -> truoc_2016."
    )
    nguoi_yeu_cau_con_song: Literal["co", "khong", "khong_ro"] = Field(
        description="Người yêu cầu còn sống -> co."
    )


_SEED_BODY = f"""
WITH $kc AS kc, $luu_tru AS luu_tru, $whitelist_dieu_ids AS wl

MATCH (hv:HanhVi:{TOPIC_LABEL} {{id: 'dang_ky_lai_ket_hon', topic: '{TOPIC}'}})

OPTIONAL MATCH (dk1:DieuKien:{TOPIC_LABEL} {{id: 'da_dang_ky_truoc_ngay_01_01_2016', topic: '{TOPIC}'}})
WHERE kc IN ['dieu_kien', 'tong_quat']
OPTIONAL MATCH (dk2:DieuKien:{TOPIC_LABEL} {{id: 'so_ho_tich_va_ban_chinh_deu_bi_mat', topic: '{TOPIC}'}})
WHERE kc IN ['dieu_kien', 'tong_quat'] AND luu_tru IN ['so_va_ban_chinh_deu_mat', 'khong_ro']
OPTIONAL MATCH (dk3:DieuKien:{TOPIC_LABEL} {{id: 'nguoi_yeu_cau_dang_ky_lai_con_song', topic: '{TOPIC}'}})
WHERE kc IN ['dieu_kien', 'tong_quat']
OPTIONAL MATCH (dk4:DieuKien:{TOPIC_LABEL} {{id: 'ho_so_dang_ky_lai_day_du_chinh_xac', topic: '{TOPIC}'}})
WHERE kc IN ['dieu_kien', 'ho_so', 'thu_tuc_thoi_han', 'tong_quat']

OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_nop_tai_lieu_dang_ky_lai', topic: '{TOPIC}'}})
WHERE kc IN ['ho_so', 'tong_quat']
OPTIONAL MATCH (gt:GiayToHoTich:{TOPIC_LABEL} {{id: 'to_khai_dang_ky_ket_hon', topic: '{TOPIC}'}})
WHERE kc IN ['ho_so', 'tong_quat']

OPTIONAL MATCH (hv_xm:HanhVi:{TOPIC_LABEL} {{id: 'xac_minh_viec_luu_giu_so_ho_tich', topic: '{TOPIC}'}})
WHERE kc IN ['thu_tuc_thoi_han', 'tong_quat']
OPTIONAL MATCH (th:ThoiHan:{TOPIC_LABEL})
WHERE th.id IN [
  'kiem_tra_ho_so_dang_ky_lai_05_ngay_lam_viec',
  'noi_dang_ky_truoc_tra_loi_05_ngay_lam_viec',
  'hoan_tat_dang_ky_lai_03_ngay_sau_xac_minh'
] AND th.topic = '{TOPIC}' AND kc IN ['thu_tuc_thoi_han', 'tong_quat']

OPTIONAL MATCH (hq1:HauQua:{TOPIC_LABEL} {{id: 'quan_he_dang_ky_lai_cong_nhan_tu_ngay_truoc', topic: '{TOPIC}'}})
WHERE kc IN ['hieu_luc_quan_he', 'tong_quat']
OPTIONAL MATCH (hq1)-[:LIEN_QUAN]->(hq2:HauQua:{TOPIC_LABEL} {{id: 'khong_xac_dinh_ngay_thang_thi_tinh_tu_01_01', topic: '{TOPIC}'}})
WHERE hq1 IS NOT NULL

WITH wl, kc, luu_tru,
  [x IN collect(DISTINCT hv) + collect(DISTINCT dk1) + collect(DISTINCT dk2)
       + collect(DISTINCT dk3) + collect(DISTINCT dk4) + collect(DISTINCT nv)
       + collect(DISTINCT gt) + collect(DISTINCT hv_xm) + collect(DISTINCT th)
       + collect(DISTINCT hq1) + collect(DISTINCT hq2)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'dieu_kien' THEN
      [x IN collect(DISTINCT dk1) + collect(DISTINCT dk2) + collect(DISTINCT dk3)
       WHERE x IS NOT NULL]
    WHEN 'ho_so' THEN
      [x IN collect(DISTINCT nv) + collect(DISTINCT gt) + collect(DISTINCT dk4)
       WHERE x IS NOT NULL]
    WHEN 'thu_tuc_thoi_han' THEN
      [x IN collect(DISTINCT hv) + collect(DISTINCT hv_xm) + collect(DISTINCT th)
       WHERE x IS NOT NULL]
    WHEN 'hieu_luc_quan_he' THEN
      [x IN collect(DISTINCT hq1) + collect(DISTINCT hq2) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT dk1) + collect(DISTINCT dk2) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: DangKyLaiKetHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "kc": params.khia_canh_dang_ky_lai,
        "luu_tru": params.tinh_trang_luu_tru,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


dang_ky_lai_ket_hon = CypherTemplate(
    name="dang_ky_lai_ket_hon",
    description=(
        "Xử lý điều kiện, hồ sơ, thời hạn và hiệu lực đăng ký lại khi Sổ hộ tịch và bản chính "
        "đều bị mất (NĐ123 Đ24, Đ27). Không dùng cho kết hôn lại sau ly hôn. "
        "Ví dụ: Khi nào được xin cấp lại giấy đăng ký kết hôn? "
        "Khác với: đã ly hôn muốn quay lại -> ket_hon_lai_sau_ly_hon."
    ),
    params_schema=DangKyLaiKetHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
