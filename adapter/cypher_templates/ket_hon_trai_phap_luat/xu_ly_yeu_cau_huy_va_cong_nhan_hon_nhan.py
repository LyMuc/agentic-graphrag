"""Template — xử lý yêu cầu hủy và công nhận hôn nhân (Đ11 K2, TTLT Đ4 K2-3)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.ket_hon_trai_phap_luat._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("ket_qua_nguoi_dung_hoi",)
_TONG_QUAT_WHITELIST = [
    "Luat_HNGD_2014_Dieu_11_Khoan_2",
    "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2",
    "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_3",
]

_YEU_CAU_TO_DK = {
    "cung_yeu_cau_cong_nhan": "hai_ben_cung_yeu_cau_cong_nhan_quan_he_hon_nhan",
    "co_yeu_cau_huy": "mot_hoac_hai_ben_yeu_cau_huy",
    "mot_ben_cong_nhan_ben_kia_khong_yeu_cau": "mot_ben_yeu_cau_cong_nhan_ben_kia_khong_yeu_cau",
    "cung_yeu_cau_ly_hon": "hai_ben_cung_yeu_cau_ly_hon",
    "mot_ben_ly_hon_ben_kia_cong_nhan": "mot_ben_yeu_cau_ly_hon_ben_kia_yeu_cau_cong_nhan",
}


class XuLyYeuCauHuyVaCongNhanHonNhanParams(BaseModel):
    trang_thai_dieu_kien_hien_tai: Literal[
        "ca_hai_da_du_dieu_kien",
        "van_co_ben_chua_du_dieu_kien",
        "khong_ro",
    ] = Field(
        description=(
            "Tình trạng điều kiện tại thời điểm giải quyết. Map: nay đủ điều kiện "
            "→ ca_hai_da_du_dieu_kien; vẫn thiếu điều kiện → van_co_ben_chua_du_dieu_kien."
        )
    )
    yeu_cau_cua_hai_ben: Literal[
        "cung_yeu_cau_cong_nhan",
        "co_yeu_cau_huy",
        "mot_ben_cong_nhan_ben_kia_khong_yeu_cau",
        "cung_yeu_cau_ly_hon",
        "mot_ben_ly_hon_ben_kia_cong_nhan",
        "khong_ro",
    ] = Field(description="Cấu hình yêu cầu của hai bên.")
    vi_pham_ban_dau: Literal[
        "chua_du_tuoi",
        "khong_tu_nguyen_cuong_ep",
        "lua_doi",
        "dang_co_vo_chong",
        "mat_nang_luc_hanh_vi",
        "quan_he_bi_cam",
        "khong_ro",
    ] = Field(description="Vi phạm tại thời điểm đăng ký.")
    co_tai_lieu_xac_dinh_thoi_diem_du_dieu_kien: Literal["co", "khong", "khong_ro"] = Field(
        description="Có tài liệu xác định thời điểm đủ điều kiện kết hôn."
    )
    ket_qua_nguoi_dung_hoi: Literal["cong_nhan", "huy", "ly_hon", "tong_quat"] = Field(
        description=(
            "Kết quả người hỏi quan tâm. Map: được công nhận không → cong_nhan; "
            "có bị hủy không → huy; giải quyết ly hôn → ly_hon."
        )
    )


_SEED_BODY = f"""
WITH $trang_thai_dieu_kien AS ttdk, $yeu_cau_cua_hai_ben AS yc, $dk_yeu_cau_id AS dk_yc_id,
     $ket_qua AS kq, $co_tai_lieu AS ctl, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'nguyen_tac_xu_ly_yeu_cau_huy_ket_hon_trai_phap_luat', topic: '{TOPIC}'
}})
OPTIONAL MATCH (hv_xd:HanhVi:{TOPIC_LABEL} {{
  id: 'toa_an_xac_dinh_thoi_diem_hai_ben_du_dieu_kien_ket_hon', topic: '{TOPIC}'
}})
WHERE ttdk = 'ca_hai_da_du_dieu_kien' OR ctl = 'co'
OPTIONAL MATCH (hv_xd)-[:YEU_CAU]->(tl_xd:TaiLieu:{TOPIC_LABEL})
WHERE ctl = 'co'

OPTIONAL MATCH (hv_cn:HanhVi:{TOPIC_LABEL} {{
  id: 'toa_an_cong_nhan_quan_he_hon_nhan', topic: '{TOPIC}'
}})
WHERE ttdk = 'ca_hai_da_du_dieu_kien'
   OR kq IN ['cong_nhan', 'tong_quat']
OPTIONAL MATCH (hv_cn)-[:AP_DUNG_KHI]->(dk_cn:DieuKien:{TOPIC_LABEL})
WHERE ttdk = 'ca_hai_da_du_dieu_kien'
   OR kq IN ['cong_nhan', 'tong_quat']
OPTIONAL MATCH (hv_cn)-[:DAN_TOI]->(hq_cn:HauQua:{TOPIC_LABEL})
OPTIONAL MATCH (hq_cn)-[:XAC_LAP]->(tt_cn:TinhTrangHonNhan:{TOPIC_LABEL})

OPTIONAL MATCH (hv_huy:HanhVi:{TOPIC_LABEL} {{
  id: 'toa_an_quyet_dinh_huy_ket_hon_trai_phap_luat', topic: '{TOPIC}'
}})
WHERE ttdk IN ['ca_hai_da_du_dieu_kien', 'van_co_ben_chua_du_dieu_kien', 'khong_ro']
   OR kq IN ['huy', 'tong_quat']
OPTIONAL MATCH (hv_huy)-[:AP_DUNG_KHI]->(dk_huy:DieuKien:{TOPIC_LABEL})
WHERE (ttdk = 'van_co_ben_chua_du_dieu_kien' AND dk_huy.id = 'tai_thoi_diem_giai_quyet_van_chua_du_dieu_kien'
       OR yc <> 'khong_ro' AND dk_huy.id = dk_yc_id
       OR yc = 'khong_ro' AND dk_huy IS NOT NULL)
OPTIONAL MATCH (hv_huy)-[:DAN_TOI]->(hq_huy:HauQua:{TOPIC_LABEL})
OPTIONAL MATCH (hq_huy)-[:XAC_LAP]->(tt_huy:TinhTrangHonNhan:{TOPIC_LABEL})

OPTIONAL MATCH (hv_lh:HanhVi:{TOPIC_LABEL} {{
  id: 'toa_an_giai_quyet_cho_ly_hon', topic: '{TOPIC}'
}})
WHERE kq = 'ly_hon' OR yc IN ['cung_yeu_cau_ly_hon', 'mot_ben_ly_hon_ben_kia_cong_nhan']
OPTIONAL MATCH (hv_lh)-[:AP_DUNG_KHI]->(dk_lh:DieuKien:{TOPIC_LABEL})
WHERE kq = 'ly_hon' OR yc IN ['cung_yeu_cau_ly_hon', 'mot_ben_ly_hon_ben_kia_cong_nhan']
OPTIONAL MATCH (hv_lh)-[:DAN_TOI]->(hq_lh:HauQua:{TOPIC_LABEL})
OPTIONAL MATCH (hq_lh)-[:XAC_LAP]->(tt_lh:TinhTrangHonNhan:{TOPIC_LABEL})

WITH wl, ttdk, yc, kq,
  collect(DISTINCT qd) + collect(DISTINCT hv_xd) + collect(DISTINCT tl_xd)
    + collect(DISTINCT hv_cn) + collect(DISTINCT dk_cn) + collect(DISTINCT hq_cn) + collect(DISTINCT tt_cn)
    + collect(DISTINCT hv_huy) + collect(DISTINCT dk_huy) + collect(DISTINCT hq_huy) + collect(DISTINCT tt_huy)
    + collect(DISTINCT hv_lh) + collect(DISTINCT dk_lh) + collect(DISTINCT hq_lh) + collect(DISTINCT tt_lh)
    AS seed_nodes,
  CASE
    WHEN ttdk = 'van_co_ben_chua_du_dieu_kien' THEN
      [x IN collect(DISTINCT hv_huy) + collect(DISTINCT dk_huy)
           + collect(DISTINCT hq_huy) + collect(DISTINCT tt_huy)
       WHERE x IS NOT NULL]
    WHEN kq = 'cong_nhan' OR (ttdk = 'ca_hai_da_du_dieu_kien' AND yc = 'cung_yeu_cau_cong_nhan') THEN
      [x IN collect(DISTINCT hv_cn) + collect(DISTINCT dk_cn)
           + collect(DISTINCT hq_cn) + collect(DISTINCT tt_cn)
           + collect(DISTINCT hv_xd) + collect(DISTINCT tl_xd)
       WHERE x IS NOT NULL]
    WHEN kq = 'ly_hon' THEN
      [x IN collect(DISTINCT hv_lh) + collect(DISTINCT dk_lh)
           + collect(DISTINCT hq_lh) + collect(DISTINCT tt_lh)
       WHERE x IS NOT NULL]
    WHEN kq = 'huy' THEN
      [x IN collect(DISTINCT hv_huy) + collect(DISTINCT dk_huy)
           + collect(DISTINCT hq_huy) + collect(DISTINCT tt_huy)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT qd) + collect(DISTINCT hv_cn) + collect(DISTINCT dk_cn)
           + collect(DISTINCT hv_huy) + collect(DISTINCT dk_huy)
           + collect(DISTINCT hv_lh) + collect(DISTINCT dk_lh)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: XuLyYeuCauHuyVaCongNhanHonNhanParams) -> dict[str, Any]:
    dk_yc_id = _YEU_CAU_TO_DK.get(params.yeu_cau_cua_hai_ben, "")
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS) or params.yeu_cau_cua_hai_ben == "khong_ro"
    return {
        "trang_thai_dieu_kien": params.trang_thai_dieu_kien_hien_tai,
        "yeu_cau_cua_hai_ben": params.yeu_cau_cua_hai_ben,
        "dk_yeu_cau_id": dk_yc_id,
        "ket_qua": params.ket_qua_nguoi_dung_hoi,
        "co_tai_lieu": params.co_tai_lieu_xac_dinh_thoi_diem_du_dieu_kien,
        "whitelist_dieu_ids": _TONG_QUAT_WHITELIST if use_wl else [],
    }


xu_ly_yeu_cau_huy_va_cong_nhan_hon_nhan = CypherTemplate(
    name="xu_ly_yeu_cau_huy_va_cong_nhan_hon_nhan",
    description=(
        "Xử lý trường hợp vi phạm tại thời điểm kết hôn nhưng điều kiện có thể đã thay đổi "
        "khi Tòa án giải quyết: công nhận, hủy hoặc giải quyết ly hôn tùy cấu hình yêu cầu. "
        "Ví dụ: Kết hôn chưa đủ tuổi nhưng nay đủ tuổi có được công nhận không?; "
        "Hai bên nay 22 tuổi và đều đồng ý duy trì hôn nhân."
    ),
    params_schema=XuLyYeuCauHuyVaCongNhanHonNhanParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
