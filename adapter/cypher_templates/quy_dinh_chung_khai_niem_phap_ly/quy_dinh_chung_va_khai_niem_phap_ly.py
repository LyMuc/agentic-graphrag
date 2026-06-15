"""Template — quy định chung và khái niệm pháp lý (Đ1, Đ3, Đ6, Đ7)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("noi_dung_phap_ly",)
_DIEU_WHITELIST = [
    "Luat_HNGD_2014_Dieu_1",
    "Luat_HNGD_2014_Dieu_3",
    "Luat_HNGD_2014_Dieu_6",
    "Luat_HNGD_2014_Dieu_7",
]

_NOI_DUNG_MAP: dict[str, tuple[str, str]] = {
    "pham_vi_dieu_chinh": ("QuyDinh", "pham_vi_dieu_chinh_luat_hngd"),
    "hon_nhan": ("QuanHe", "khai_niem_hon_nhan"),
    "gia_dinh": ("QuanHe", "khai_niem_gia_dinh"),
    "che_do_hon_nhan_gia_dinh": ("QuyDinh", "khai_niem_che_do_hon_nhan_gia_dinh"),
    "tap_quan_hon_nhan_gia_dinh": ("QuyDinh", "khai_niem_tap_quan_hon_nhan_gia_dinh"),
    "ket_hon": ("HanhVi", "khai_niem_ket_hon"),
    "ket_hon_trai_phap_luat": ("HanhVi", "khai_niem_ket_hon_trai_phap_luat"),
    "chung_song_nhu_vo_chong": ("HanhVi", "khai_niem_chung_song_nhu_vo_chong"),
    "tao_hon": ("HanhVi", "khai_niem_tao_hon"),
    "cuong_ep_ket_hon_ly_hon": ("HanhVi", "khai_niem_cuong_ep_ket_hon_ly_hon"),
    "can_tro_ket_hon_ly_hon": ("HanhVi", "khai_niem_can_tro_ket_hon_ly_hon"),
    "ket_hon_gia_tao": ("HanhVi", "khai_niem_ket_hon_gia_tao"),
    "yeu_sach_cua_cai_trong_ket_hon": ("HanhVi", "khai_niem_yeu_sach_cua_cai_trong_ket_hon"),
    "thoi_ky_hon_nhan": ("QuanHe", "khai_niem_thoi_ky_hon_nhan"),
    "ly_hon": ("HanhVi", "khai_niem_ly_hon"),
    "ly_hon_gia_tao": ("HanhVi", "khai_niem_ly_hon_gia_tao"),
    "thanh_vien_gia_dinh": ("ChuThe", "khai_niem_thanh_vien_gia_dinh"),
    "cung_dong_mau_ve_truc_he": ("QuanHe", "khai_niem_cung_dong_mau_ve_truc_he"),
    "ho_trong_pham_vi_ba_doi": ("QuanHe", "khai_niem_ho_trong_pham_vi_ba_doi"),
    "nguoi_than_thich": ("QuanHe", "khai_niem_nguoi_than_thich"),
    "nhu_cau_thiet_yeu": ("DieuKien", "khai_niem_nhu_cau_thiet_yeu"),
    "sinh_con_bang_ky_thuat_ho_tro_sinh_san": (
        "HanhVi",
        "khai_niem_sinh_con_bang_ky_thuat_ho_tro_sinh_san",
    ),
    "mang_thai_ho_vi_muc_dich_nhan_dao": (
        "HanhVi",
        "khai_niem_mang_thai_ho_vi_muc_dich_nhan_dao",
    ),
    "mang_thai_ho_vi_muc_dich_thuong_mai": (
        "HanhVi",
        "khai_niem_mang_thai_ho_vi_muc_dich_thuong_mai",
    ),
    "cap_duong": ("NghiaVu", "khai_niem_cap_duong"),
    "quan_he_hngd_co_yeu_to_nuoc_ngoai": (
        "QuanHe",
        "khai_niem_quan_he_hngd_co_yeu_to_nuoc_ngoai",
    ),
    "ap_dung_phap_luat_lien_quan": ("QuyDinh", "ap_dung_bo_luat_dan_su_va_luat_lien_quan"),
    "ap_dung_tap_quan": ("QuyDinh", "ap_dung_tap_quan_hon_nhan_gia_dinh"),
}


class QuyDinhChungVaKhaiNiemPhapLyParams(BaseModel):
    noi_dung_phap_ly: Literal[
        "pham_vi_dieu_chinh",
        "hon_nhan",
        "gia_dinh",
        "che_do_hon_nhan_gia_dinh",
        "tap_quan_hon_nhan_gia_dinh",
        "ket_hon",
        "ket_hon_trai_phap_luat",
        "chung_song_nhu_vo_chong",
        "tao_hon",
        "cuong_ep_ket_hon_ly_hon",
        "can_tro_ket_hon_ly_hon",
        "ket_hon_gia_tao",
        "yeu_sach_cua_cai_trong_ket_hon",
        "thoi_ky_hon_nhan",
        "ly_hon",
        "ly_hon_gia_tao",
        "thanh_vien_gia_dinh",
        "cung_dong_mau_ve_truc_he",
        "ho_trong_pham_vi_ba_doi",
        "nguoi_than_thich",
        "nhu_cau_thiet_yeu",
        "sinh_con_bang_ky_thuat_ho_tro_sinh_san",
        "mang_thai_ho_vi_muc_dich_nhan_dao",
        "mang_thai_ho_vi_muc_dich_thuong_mai",
        "cap_duong",
        "quan_he_hngd_co_yeu_to_nuoc_ngoai",
        "ap_dung_phap_luat_lien_quan",
        "ap_dung_tap_quan",
        "khong_ro",
    ] = Field(description="Khái niệm hoặc quy định chung cần truy xuất.")
    khia_canh_khai_niem: Literal[
        "dinh_nghia",
        "thoi_diem_bat_dau",
        "thoi_diem_ket_thuc",
        "pham_vi",
        "dieu_kien_ap_dung",
        "tong_quat",
    ] = Field(description="Định nghĩa, mốc thời gian, phạm vi hoặc điều kiện áp dụng.")


_SEED_BODY = f"""
WITH $label AS label, $sid AS sid, $nd AS nd, $seed_ap_dung AS seed_ap_dung,
     $seed_tap_quan AS seed_tap_quan, $use_root AS use_root,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (root:QuyDinh:{TOPIC_LABEL} {{
  id: 'quy_dinh_chung_khai_niem_phap_ly', topic: '{TOPIC}'
}})
WHERE use_root = true

OPTIONAL MATCH (node)
WHERE sid <> '' AND label <> ''
  AND node.id = sid AND node.topic = '{TOPIC}'
  AND label IN labels(node)

OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{
  id: 'dieu_kien_luat_hngd_khong_quy_dinh', topic: '{TOPIC}'
}})
WHERE seed_ap_dung = true AND nd = 'ap_dung_phap_luat_lien_quan'

OPTIONAL MATCH (tq:QuyDinh:{TOPIC_LABEL} {{
  id: 'ap_dung_tap_quan_hon_nhan_gia_dinh', topic: '{TOPIC}'
}})
WHERE seed_tap_quan = true
OPTIONAL MATCH (tq)-[:AP_DUNG_KHI]->(dk_tq:DieuKien:{TOPIC_LABEL})
WHERE seed_tap_quan = true AND dk_tq.topic = '{TOPIC}'
OPTIONAL MATCH (dk_tq2:DieuKien:{TOPIC_LABEL} {{
  id: 'tap_quan_tot_dep_khong_trai_nguyen_tac_va_dieu_cam', topic: '{TOPIC}'
}})
WHERE seed_tap_quan = true

WITH wl, nd,
  collect(DISTINCT root) + collect(DISTINCT node)
    + collect(DISTINCT dk) + collect(DISTINCT tq)
    + collect(DISTINCT dk_tq) + collect(DISTINCT dk_tq2)
    AS seed_nodes,
  [x IN collect(DISTINCT node) + collect(DISTINCT dk)
       + collect(DISTINCT tq) + collect(DISTINCT dk_tq) + collect(DISTINCT dk_tq2)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: QuyDinhChungVaKhaiNiemPhapLyParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    nd = params.noi_dung_phap_ly
    use_root = nd == "khong_ro"
    label, sid = _NOI_DUNG_MAP.get(nd, ("", ""))
    seed_ap_dung = nd == "ap_dung_phap_luat_lien_quan"
    seed_tap_quan = nd == "ap_dung_tap_quan"
    return {
        "label": label,
        "sid": sid,
        "nd": nd,
        "seed_ap_dung": seed_ap_dung,
        "seed_tap_quan": seed_tap_quan,
        "use_root": use_root,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


quy_dinh_chung_va_khai_niem_phap_ly = CypherTemplate(
    name="quy_dinh_chung_va_khai_niem_phap_ly",
    description=(
        "Truy xuất một khái niệm cụ thể tại Điều 3 hoặc quy tắc chung tại Điều 1, 6, 7. "
        "Ưu tiên semantic leaf đúng khoản; kết hôn, cấp dưỡng, thời kỳ hôn nhân không seed "
        "toàn bộ Điều 3. Fallback an toàn cho câu hỏi là gì trong topic. "
        "Ví dụ: Kết hôn là gì?; Kết hôn trái pháp luật là gì?; "
        "Cấp dưỡng là gì?; Thời kỳ hôn nhân bắt đầu từ khi nào?"
    ),
    params_schema=QuyDinhChungVaKhaiNiemPhapLyParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
