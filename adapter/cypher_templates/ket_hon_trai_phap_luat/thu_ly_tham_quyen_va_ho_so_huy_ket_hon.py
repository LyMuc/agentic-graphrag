"""Template — thẩm quyền, hồ sơ và phân loại vụ việc hủy (Đ11, TTLT Đ3)."""
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

_ROUTER_FIELDS = ("khia_canh_thu_tuc",)
_TONG_QUAT_WHITELIST = [
    "Luat_HNGD_2014_Dieu_11_Khoan_1",
    "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3",
]


class ThuLyThamQuyenVaHoSoHuyKetHonParams(BaseModel):
    khia_canh_thu_tuc: Literal[
        "tham_quyen_giai_quyet",
        "ho_so_chung_cu",
        "that_lac_giay_chung_nhan",
        "xac_dinh_dang_ky_dung_tham_quyen",
        "phan_biet_khong_dang_ky_sai_tham_quyen",
        "tong_quat",
    ] = Field(
        description=(
            "Khía cạnh thủ tục. Map: cơ quan/thẩm quyền hủy → tham_quyen_giai_quyet; "
            "hồ sơ/giấy tờ → ho_so_chung_cu; mất giấy → that_lac_giay_chung_nhan; "
            "chưa đăng ký/sai thẩm quyền → phan_biet_khong_dang_ky_sai_tham_quyen."
        )
    )
    tinh_trang_dang_ky: Literal[
        "dung_tham_quyen",
        "sai_tham_quyen",
        "khong_dang_ky",
        "khong_ro",
    ] = Field(description="Tình trạng đăng ký kết hôn được nêu.")
    tinh_trang_giay_chung_nhan: Literal[
        "co",
        "that_lac",
        "khong_co_vi_khong_dang_ky",
        "khong_ro",
    ] = Field(description="Tình trạng giấy chứng nhận kết hôn.")
    co_chung_cu_vi_pham: Literal["co", "chua_co", "khong_ro"] = Field(
        description="Đã có hay cần chuẩn bị chứng cứ vi phạm điều kiện kết hôn."
    )
    co_yeu_cau_giai_quyet_con_tai_san: Literal["co", "khong", "khong_ro"] = Field(
        description="Có hỏi thêm con, tài sản, nghĩa vụ hay hợp đồng."
    )


_SEED_BODY = f"""
WITH $khia_canh_thu_tuc AS kctt, $tinh_trang_dang_ky AS ttdk,
     $tinh_trang_giay_chung_nhan AS ttgcn, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (toa:ChuThe:{TOPIC_LABEL} {{
  id: 'toa_an_giai_quyet_yeu_cau_huy_ket_hon_trai_phap_luat', topic: '{TOPIC}'
}})
WHERE kctt IN ['tham_quyen_giai_quyet', 'tong_quat']
OPTIONAL MATCH (toa)-[:THUC_HIEN]->(hv_thu_ly:HanhVi:{TOPIC_LABEL} {{
  id: 'toa_an_thu_ly_giai_quyet_yeu_cau_huy', topic: '{TOPIC}'
}})
WHERE kctt IN ['tham_quyen_giai_quyet', 'tong_quat']
OPTIONAL MATCH (hv_thu_ly)-[:AP_DUNG_KHI]->(dk_thu_ly:DieuKien:{TOPIC_LABEL})
WHERE kctt IN ['tham_quyen_giai_quyet', 'tong_quat']

OPTIONAL MATCH (hv_nop:HanhVi:{TOPIC_LABEL} {{
  id: 'nop_ho_so_yeu_cau_huy_ket_hon_trai_phap_luat', topic: '{TOPIC}'
}})
WHERE kctt IN ['ho_so_chung_cu', 'that_lac_giay_chung_nhan', 'tong_quat']
OPTIONAL MATCH (hv_nop)-[:YEU_CAU]->(tl:TaiLieu:{TOPIC_LABEL})
WHERE kctt IN ['ho_so_chung_cu', 'that_lac_giay_chung_nhan', 'tong_quat']
OPTIONAL MATCH (hv_nop)-[:AP_DUNG_KHI]->(dk_tl:DieuKien:{TOPIC_LABEL})
WHERE kctt IN ['that_lac_giay_chung_nhan', 'tong_quat'] AND ttgcn = 'that_lac'

OPTIONAL MATCH (hv_kcn:HanhVi:{TOPIC_LABEL} {{
  id: 'toa_an_tuyen_khong_cong_nhan_quan_he_hon_nhan', topic: '{TOPIC}'
}})
WHERE kctt = 'phan_biet_khong_dang_ky_sai_tham_quyen'
   OR ttdk IN ['sai_tham_quyen', 'khong_dang_ky']
OPTIONAL MATCH (hv_kcn)-[:AP_DUNG_KHI]->(dk_kcn:DieuKien:{TOPIC_LABEL})
WHERE kctt = 'phan_biet_khong_dang_ky_sai_tham_quyen'
   OR ttdk IN ['sai_tham_quyen', 'khong_dang_ky']
  AND (ttdk = 'sai_tham_quyen' AND dk_kcn.id = 'dang_ky_ket_hon_sai_co_quan_co_tham_quyen'
       OR ttdk = 'khong_dang_ky' AND dk_kcn.id = 'chung_song_nhu_vo_chong_khong_dang_ky_ket_hon'
       OR ttdk = 'khong_ro')
OPTIONAL MATCH (hv_kcn)-[:DAN_TOI]->(hq_kcn:HauQua:{TOPIC_LABEL})
WHERE kctt = 'phan_biet_khong_dang_ky_sai_tham_quyen'
   OR ttdk IN ['sai_tham_quyen', 'khong_dang_ky']

OPTIONAL MATCH (dk_dung:DieuKien:{TOPIC_LABEL} {{
  id: 'da_dang_ky_ket_hon_dung_co_quan_co_tham_quyen', topic: '{TOPIC}'
}})
WHERE kctt = 'xac_dinh_dang_ky_dung_tham_quyen' OR ttdk = 'dung_tham_quyen'

WITH wl, kctt, ttdk,
  collect(DISTINCT toa) + collect(DISTINCT hv_thu_ly) + collect(DISTINCT dk_thu_ly)
    + collect(DISTINCT hv_nop) + collect(DISTINCT tl) + collect(DISTINCT dk_tl)
    + collect(DISTINCT hv_kcn) + collect(DISTINCT dk_kcn) + collect(DISTINCT hq_kcn)
    + collect(DISTINCT dk_dung) AS seed_nodes,
  CASE
    WHEN kctt = 'tham_quyen_giai_quyet' THEN
      [x IN collect(DISTINCT toa) + collect(DISTINCT hv_thu_ly) + collect(DISTINCT dk_thu_ly)
       WHERE x IS NOT NULL]
    WHEN kctt IN ['ho_so_chung_cu', 'that_lac_giay_chung_nhan'] THEN
      [x IN collect(DISTINCT hv_nop) + collect(DISTINCT tl) + collect(DISTINCT dk_tl)
       WHERE x IS NOT NULL]
    WHEN kctt = 'xac_dinh_dang_ky_dung_tham_quyen' THEN
      [x IN collect(DISTINCT dk_dung) WHERE x IS NOT NULL]
    WHEN kctt = 'phan_biet_khong_dang_ky_sai_tham_quyen' THEN
      [x IN collect(DISTINCT hv_kcn) + collect(DISTINCT dk_kcn) + collect(DISTINCT hq_kcn)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT toa) + collect(DISTINCT hv_thu_ly)
           + collect(DISTINCT hv_nop) + collect(DISTINCT tl)
           + collect(DISTINCT hv_kcn) + collect(DISTINCT dk_kcn)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ThuLyThamQuyenVaHoSoHuyKetHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "khia_canh_thu_tuc": params.khia_canh_thu_tuc,
        "tinh_trang_dang_ky": params.tinh_trang_dang_ky,
        "tinh_trang_giay_chung_nhan": params.tinh_trang_giay_chung_nhan,
        "whitelist_dieu_ids": _TONG_QUAT_WHITELIST if use_wl else [],
    }


thu_ly_tham_quyen_va_ho_so_huy_ket_hon = CypherTemplate(
    name="thu_ly_tham_quyen_va_ho_so_huy_ket_hon",
    description=(
        "Trả lời cơ quan giải quyết, tài liệu phải nộp và cách phân loại vụ việc theo "
        "tình trạng đăng ký. Safety-net cho câu không đăng ký hoặc đăng ký sai thẩm quyền "
        "(không công nhận quan hệ hôn nhân, không phải nhánh hủy hẹp). "
        "Ví dụ: Cơ quan nào có thẩm quyền hủy?; Cần chuẩn bị giấy tờ gì khi yêu cầu hủy?"
    ),
    params_schema=ThuLyThamQuyenVaHoSoHuyKetHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
