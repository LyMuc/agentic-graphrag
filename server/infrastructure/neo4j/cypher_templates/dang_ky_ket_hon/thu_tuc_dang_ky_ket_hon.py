"""Template — thủ tục đăng ký kết hôn (Đ18, Đ38, Đ11 Luật Hộ tịch)."""
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

_ROUTER_FIELDS = ("cap_dang_ky",)
_DIEU_XA_WHITELIST = ["Luat_HoTich_2014_Dieu_18"]
_DIEU_HUYEN_WHITELIST = ["Luat_HoTich_2014_Dieu_38"]

_XA_CHAIN = [
    "nop_to_khai_va_cung_co_mat",
    "kiem_tra_xac_minh_ho_so_ket_hon",
    "ghi_viec_ket_hon_vao_so_ho_tich",
    "hai_ben_ky_so_va_giay_chung_nhan",
    "cap_giay_chung_nhan_ket_hon",
]


class ThuTucDangKyKetHonParams(BaseModel):
    cap_dang_ky: Literal["cap_xa", "cap_huyen", "xa_bien_gioi", "khong_ro"] = Field(
        description=(
            "Phường/xã/thị trấn -> cap_xa; quận/huyện -> cap_huyen; "
            "xã biên giới -> xa_bien_gioi."
        )
    )
    boi_canh_chu_the: Literal["trong_nuoc", "co_yeu_to_nuoc_ngoai", "khong_ro"] = Field(
        description="Hai người Việt Nam trong nước -> trong_nuoc; có yếu tố nước ngoài -> co_yeu_to_nuoc_ngoai."
    )
    khia_canh_thu_tuc: Literal[
        "ho_so_nop", "trinh_tu_xu_ly", "su_co_mat_va_uy_quyen", "tong_quat"
    ] = Field(
        description=(
            "Hồ sơ/giấy tờ -> ho_so_nop; quy trình/trình tự -> trinh_tu_xu_ly; "
            "nhờ người khác/ủy quyền/cùng có mặt -> su_co_mat_va_uy_quyen."
        )
    )


_SEED_BODY = f"""
WITH $cap AS cap, $bc AS bc, $kc AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (hv_xa:HanhVi:{TOPIC_LABEL})
WHERE hv_xa.id IN $xa_chain AND hv_xa.topic = '{TOPIC}'
  AND (cap IN ['cap_xa', 'khong_ro', 'xa_bien_gioi'] OR kc IN ['tong_quat', 'trinh_tu_xu_ly', 'ho_so_nop', 'su_co_mat_va_uy_quyen'])

OPTIONAL MATCH (hv_huyen:HanhVi:{TOPIC_LABEL})
WHERE hv_huyen.id IN [
  'nop_to_khai_va_cung_co_mat', 'kiem_tra_xac_minh_ho_so_ket_hon',
  'cap_giay_chung_nhan_ket_hon', 'to_chuc_trao_giay_chung_nhan_ket_hon'
] AND hv_huyen.topic = '{TOPIC}' AND (cap IN ['cap_huyen', 'khong_ro'] OR bc = 'co_yeu_to_nuoc_ngoai')

OPTIONAL MATCH (dk_nn:DieuKien:{TOPIC_LABEL} {{id: 'co_yeu_to_nuoc_ngoai', topic: '{TOPIC}'}})
WHERE cap IN ['cap_huyen', 'co_yeu_to_nuoc_ngoai', 'khong_ro']
OPTIONAL MATCH (dk_nn)-[:LIEN_QUAN]->(dk_doc:DieuKien:{TOPIC_LABEL})
WHERE dk_nn IS NOT NULL AND dk_doc.topic = '{TOPIC}'

OPTIONAL MATCH (gt:GiayToHoTich:{TOPIC_LABEL})
WHERE gt.id IN [
  'to_khai_dang_ky_ket_hon', 'giay_xac_nhan_y_te',
  'giay_chung_minh_tinh_trang_hon_nhan', 'ho_chieu_hoac_giay_thay_ho_chieu'
] AND gt.topic = '{TOPIC}' AND kc IN ['ho_so_nop', 'tong_quat', 'trinh_tu_xu_ly']

OPTIONAL MATCH (nv_cm:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_hai_ben_cung_co_mat', topic: '{TOPIC}'}})
WHERE kc IN ['su_co_mat_va_uy_quyen', 'tong_quat', 'trinh_tu_xu_ly']
OPTIONAL MATCH (hv_uq:HanhVi:{TOPIC_LABEL} {{id: 'uy_quyen_nguoi_khac_dang_ky_ket_hon', topic: '{TOPIC}'}})
WHERE kc IN ['su_co_mat_va_uy_quyen', 'tong_quat']

OPTIONAL MATCH (cq_bg:CoQuanDangKy:{TOPIC_LABEL} {{id: 'ubnd_xa_khu_vuc_bien_gioi', topic: '{TOPIC}'}})
WHERE cap = 'xa_bien_gioi'

OPTIONAL MATCH (ct:ChuThe:{TOPIC_LABEL} {{id: 'cong_dan_viet_nam_cu_tru_trong_nuoc', topic: '{TOPIC}'}})
WHERE bc = 'trong_nuoc' AND kc IN ['tong_quat', 'trinh_tu_xu_ly', 'ho_so_nop']
OPTIONAL MATCH (ct)-[:CO_QUYEN]->(q:Quyen:{TOPIC_LABEL} {{id: 'quyen_mien_le_phi_ket_hon_trong_nuoc', topic: '{TOPIC}'}})
WHERE ct IS NOT NULL

WITH wl, cap, kc,
  [x IN collect(DISTINCT hv_xa) + collect(DISTINCT hv_huyen)
       + collect(DISTINCT dk_nn) + collect(DISTINCT dk_doc) + collect(DISTINCT gt)
       + collect(DISTINCT nv_cm) + collect(DISTINCT hv_uq) + collect(DISTINCT cq_bg)
       + collect(DISTINCT ct) + collect(DISTINCT q)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'su_co_mat_va_uy_quyen' THEN
      [x IN collect(DISTINCT nv_cm) + collect(DISTINCT hv_uq) WHERE x IS NOT NULL]
    WHEN 'ho_so_nop' THEN
      [x IN collect(DISTINCT gt) + collect(DISTINCT hv_xa) WHERE x IS NOT NULL]
    WHEN 'trinh_tu_xu_ly' THEN
      [x IN collect(DISTINCT hv_xa) + collect(DISTINCT hv_huyen) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hv_xa) + collect(DISTINCT hv_huyen) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ThuTucDangKyKetHonParams) -> dict[str, Any]:
    cap = params.cap_dang_ky
    if cap == "khong_ro" and params.boi_canh_chu_the == "co_yeu_to_nuoc_ngoai":
        cap = "cap_huyen"
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    if use_wl:
        wl = _DIEU_XA_WHITELIST + _DIEU_HUYEN_WHITELIST
    elif cap == "cap_huyen":
        wl = _DIEU_HUYEN_WHITELIST
    elif cap == "cap_xa":
        wl = _DIEU_XA_WHITELIST
    else:
        wl = []
    return {
        "cap": cap,
        "bc": params.boi_canh_chu_the,
        "kc": params.khia_canh_thu_tuc,
        "xa_chain": _XA_CHAIN,
        "whitelist_dieu_ids": wl,
    }


thu_tuc_dang_ky_ket_hon = CypherTemplate(
    name="thu_tuc_dang_ky_ket_hon",
    description=(
        "Trả lời hồ sơ và trình tự đăng ký tại cấp xã/cấp huyện: nộp tờ khai, cùng có mặt, "
        "kiểm tra, ghi Sổ hộ tịch, ký và cấp/trao Giấy chứng nhận (Đ18, Đ38). "
        "Ví dụ: Quy trình đăng ký kết hôn tại cấp xã thế nào?; "
        "Có được nhờ người khác đăng ký giùm không?"
    ),
    params_schema=ThuTucDangKyKetHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
