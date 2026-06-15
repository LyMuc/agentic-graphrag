"""Build KG ngữ nghĩa cho topic 'xac_dinh_cha_me_con' (Đ88-93, 99, 101-102 LHNGD 2014).

Cách chạy:
    python scripts/build_kg_xac_dinh_cha_me_con.py           # MERGE idempotent
    python scripts/build_kg_xac_dinh_cha_me_con.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_xac_dinh_cha_me_con.py --dry-run # chỉ in summary

Schema: docs/kg_xac_dinh_cha_me_con_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "xac_dinh_cha_me_con"
TOPIC_LABEL = "XacDinhChaMeCon"

SEMANTIC_LABELS = [
    "ChuThe",
    "QuyDinh",
    "Quyen",
    "HanhVi",
    "QuanHe",
    "DieuKien",
    "HauQua",
    "ThamQuyen",
    "CoQuan",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (semantic_id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("xac_dinh_quan_he_cha_me_con", "Xác định quan hệ cha, mẹ, con", "HanhVi", []),
    ("quan_he_cha_me_con", "Quan hệ cha, mẹ, con", "QuanHe", []),
    ("quan_he_con_chung_cua_vo_chong", "Quan hệ con chung của vợ chồng", "QuanHe", ["Luat_HNGD_2014_Dieu_88"]),
    ("toa_an", "Tòa án", "CoQuan", []),
    ("co_quan_dang_ky_ho_tich", "Cơ quan đăng ký hộ tịch", "CoQuan", []),
    ("xac_dinh_con_chung_cua_vo_chong", "Xác định con chung của vợ chồng", "QuyDinh", ["Luat_HNGD_2014_Dieu_88"]),
    ("con_sinh_trong_thoi_ky_hon_nhan", "Con sinh ra trong thời kỳ hôn nhân", "DieuKien", ["Luat_HNGD_2014_Dieu_88_Khoan_1"]),
    ("nguoi_vo_co_thai_trong_thoi_ky_hon_nhan", "Người vợ có thai trong thời kỳ hôn nhân", "DieuKien", ["Luat_HNGD_2014_Dieu_88_Khoan_1"]),
    ("con_sinh_trong_300_ngay_sau_cham_dut_hon_nhan", "Con sinh trong 300 ngày kể từ khi chấm dứt hôn nhân", "DieuKien", ["Luat_HNGD_2014_Dieu_88_Khoan_1"]),
    ("con_sinh_truoc_dang_ky_ket_hon_duoc_cha_me_thua_nhan", "Con sinh trước đăng ký kết hôn và được cha mẹ thừa nhận", "DieuKien", ["Luat_HNGD_2014_Dieu_88_Khoan_1"]),
    ("duoc_coi_la_con_chung_cua_vo_chong", "Được coi là con chung của vợ chồng", "HauQua", ["Luat_HNGD_2014_Dieu_88_Khoan_1"]),
    ("cha_me_khong_thua_nhan_con", "Cha, mẹ không thừa nhận con", "HanhVi", ["Luat_HNGD_2014_Dieu_88_Khoan_2"]),
    ("khong_thua_nhan_con_phai_co_chung_cu", "Không thừa nhận con phải có chứng cứ", "DieuKien", ["Luat_HNGD_2014_Dieu_88_Khoan_2"]),
    ("toa_an_xac_dinh_khi_cha_me_khong_thua_nhan_con", "Tòa án xác định khi cha, mẹ không thừa nhận con", "ThamQuyen", ["Luat_HNGD_2014_Dieu_88_Khoan_2"]),
    ("nguoi_khong_duoc_nhan_la_cha_me", "Người không được nhận là cha, mẹ", "ChuThe", ["Luat_HNGD_2014_Dieu_89_Khoan_1"]),
    ("yeu_cau_toa_an_xac_dinh_mot_nguoi_la_con_minh", "Yêu cầu Tòa án xác định một người là con mình", "Quyen", ["Luat_HNGD_2014_Dieu_89_Khoan_1"]),
    ("nguoi_dang_duoc_nhan_la_cha_me", "Người đang được nhận là cha, mẹ", "ChuThe", ["Luat_HNGD_2014_Dieu_89_Khoan_2"]),
    ("yeu_cau_toa_an_xac_dinh_khong_phai_la_con_minh", "Yêu cầu Tòa án xác định một người không phải là con mình", "Quyen", ["Luat_HNGD_2014_Dieu_89_Khoan_2"]),
    ("con", "Người con", "ChuThe", []),
    ("cha_me", "Cha, mẹ", "ChuThe", []),
    ("con_co_quyen_nhan_cha_me", "Con có quyền nhận cha, mẹ", "Quyen", ["Luat_HNGD_2014_Dieu_90_Khoan_1"]),
    ("cha_me_da_chet", "Cha, mẹ đã chết", "DieuKien", ["Luat_HNGD_2014_Dieu_90_Khoan_1"]),
    ("con_thanh_nien_nhan_cha_khong_can_me_dong_y", "Con thành niên nhận cha không cần mẹ đồng ý", "Quyen", ["Luat_HNGD_2014_Dieu_90_Khoan_2"]),
    ("con_thanh_nien_nhan_me_khong_can_cha_dong_y", "Con thành niên nhận mẹ không cần cha đồng ý", "Quyen", ["Luat_HNGD_2014_Dieu_90_Khoan_2"]),
    ("cha_me_co_quyen_nhan_con", "Cha, mẹ có quyền nhận con", "Quyen", ["Luat_HNGD_2014_Dieu_91_Khoan_1"]),
    ("con_da_chet", "Con đã chết", "DieuKien", ["Luat_HNGD_2014_Dieu_91_Khoan_1"]),
    ("nguoi_dang_co_vo_chong_nhan_con", "Người đang có vợ, chồng nhận con", "HanhVi", ["Luat_HNGD_2014_Dieu_91_Khoan_2"]),
    ("nhan_con_khong_can_vo_chong_dong_y", "Nhận con không cần sự đồng ý của người vợ hoặc chồng", "HauQua", ["Luat_HNGD_2014_Dieu_91_Khoan_2"]),
    ("nguoi_co_yeu_cau_xac_dinh_da_chet", "Người có yêu cầu xác định cha, mẹ, con đã chết", "DieuKien", ["Luat_HNGD_2014_Dieu_92"]),
    ("nguoi_than_thich_yeu_cau_xac_dinh_thay", "Người thân thích có quyền yêu cầu xác định thay", "Quyen", ["Luat_HNGD_2014_Dieu_92"]),
    ("toa_an_xac_dinh_cho_nguoi_yeu_cau_da_chet", "Tòa án xác định cho người yêu cầu đã chết", "ThamQuyen", ["Luat_HNGD_2014_Dieu_92"]),
    ("vo_chong_sinh_con_bang_ky_thuat_ho_tro_sinh_san", "Vợ chồng sinh con bằng kỹ thuật hỗ trợ sinh sản", "HanhVi", ["Luat_HNGD_2014_Dieu_93_Khoan_1"]),
    ("ap_dung_dieu_88_khi_vo_sinh_con_bang_ho_tro_sinh_san", "Áp dụng Điều 88 khi người vợ sinh con bằng kỹ thuật hỗ trợ sinh sản", "QuyDinh", ["Luat_HNGD_2014_Dieu_93_Khoan_1", "Luat_HNGD_2014_Dieu_88"]),
    ("phu_nu_doc_than_sinh_con_bang_ky_thuat_ho_tro_sinh_san", "Phụ nữ độc thân sinh con bằng kỹ thuật hỗ trợ sinh sản", "HanhVi", ["Luat_HNGD_2014_Dieu_93_Khoan_2"]),
    ("phu_nu_doc_than_la_me_cua_con_duoc_sinh_ra", "Phụ nữ độc thân là mẹ của con được sinh ra", "QuanHe", ["Luat_HNGD_2014_Dieu_93_Khoan_2"]),
    ("nguoi_cho_tinh_trung_noan_phoi", "Người cho tinh trùng, noãn hoặc phôi", "ChuThe", ["Luat_HNGD_2014_Dieu_93_Khoan_3"]),
    ("sinh_con_ho_tro_khong_phat_sinh_quan_he_voi_nguoi_cho", "Không phát sinh quan hệ cha, mẹ, con với người cho", "HauQua", ["Luat_HNGD_2014_Dieu_93_Khoan_3"]),
    ("mang_thai_ho_vi_muc_dich_nhan_dao", "Mang thai hộ vì mục đích nhân đạo", "HanhVi", ["Luat_HNGD_2014_Dieu_93_Khoan_4"]),
    ("xac_dinh_cha_me_mang_thai_ho_ap_dung_dieu_94", "Xác định cha, mẹ trong mang thai hộ áp dụng Điều 94", "QuyDinh", ["Luat_HNGD_2014_Dieu_93_Khoan_4"]),
    ("tranh_chap_ho_tro_sinh_san_hoac_mang_thai_ho", "Tranh chấp về hỗ trợ sinh sản hoặc mang thai hộ", "DieuKien", ["Luat_HNGD_2014_Dieu_99_Khoan_1"]),
    ("toa_an_giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho", "Tòa án giải quyết tranh chấp hỗ trợ sinh sản, mang thai hộ", "ThamQuyen", ["Luat_HNGD_2014_Dieu_99_Khoan_1"]),
    ("chua_giao_tre_va_ben_nho_mang_thai_ho_cung_chet_hoac_mat_nang_luc", "Chưa giao trẻ và bên nhờ mang thai hộ cùng chết hoặc mất năng lực hành vi dân sự", "DieuKien", ["Luat_HNGD_2014_Dieu_99_Khoan_2"]),
    ("ben_mang_thai_ho_co_quyen_nhan_nuoi_tre", "Bên mang thai hộ có quyền nhận nuôi trẻ", "Quyen", ["Luat_HNGD_2014_Dieu_99_Khoan_2"]),
    ("ben_mang_thai_ho_khong_nhan_nuoi_tre", "Bên mang thai hộ không nhận nuôi trẻ", "DieuKien", ["Luat_HNGD_2014_Dieu_99_Khoan_2"]),
    ("giam_ho_va_cap_duong_cho_tre_theo_quy_dinh", "Giám hộ và cấp dưỡng cho trẻ theo quy định", "HauQua", ["Luat_HNGD_2014_Dieu_99_Khoan_2"]),
    ("xac_dinh_cha_me_con_khong_co_tranh_chap", "Xác định cha, mẹ, con không có tranh chấp", "DieuKien", ["Luat_HNGD_2014_Dieu_101_Khoan_1"]),
    ("tham_quyen_co_quan_dang_ky_ho_tich", "Thẩm quyền của cơ quan đăng ký hộ tịch", "ThamQuyen", ["Luat_HNGD_2014_Dieu_101_Khoan_1"]),
    ("xac_dinh_cha_me_con_co_tranh_chap", "Xác định cha, mẹ, con có tranh chấp", "DieuKien", ["Luat_HNGD_2014_Dieu_101_Khoan_2"]),
    ("nguoi_duoc_yeu_cau_xac_dinh_da_chet", "Người được yêu cầu xác định là cha, mẹ, con đã chết", "DieuKien", ["Luat_HNGD_2014_Dieu_101_Khoan_2"]),
    ("tham_quyen_toa_an_xac_dinh_cha_me_con", "Thẩm quyền của Tòa án xác định cha, mẹ, con", "ThamQuyen", ["Luat_HNGD_2014_Dieu_101_Khoan_2"]),
    ("quyet_dinh_toa_an_duoc_gui_de_ghi_chu_ho_tich", "Quyết định của Tòa án được gửi để ghi chú hộ tịch", "HauQua", ["Luat_HNGD_2014_Dieu_101_Khoan_2"]),
    ("cha_me_con_thanh_nien_khong_mat_nang_luc_hanh_vi", "Cha, mẹ, con thành niên không mất năng lực hành vi dân sự", "ChuThe", ["Luat_HNGD_2014_Dieu_102_Khoan_1"]),
    ("yeu_cau_ho_tich_xac_dinh_cho_minh", "Yêu cầu cơ quan đăng ký hộ tịch xác định cho mình", "Quyen", ["Luat_HNGD_2014_Dieu_102_Khoan_1"]),
    ("cha_me_con_yeu_cau_toa_an_xac_dinh_cho_minh", "Cha, mẹ, con yêu cầu Tòa án xác định cho mình", "Quyen", ["Luat_HNGD_2014_Dieu_102_Khoan_2"]),
    ("con_chua_thanh_nien_hoac_thanh_nien_mat_nang_luc", "Con chưa thành niên hoặc thành niên mất năng lực hành vi dân sự", "ChuThe", ["Luat_HNGD_2014_Dieu_102_Khoan_3"]),
    ("cha_me_chua_thanh_nien_hoac_mat_nang_luc", "Cha, mẹ chưa thành niên hoặc mất năng lực hành vi dân sự", "ChuThe", ["Luat_HNGD_2014_Dieu_102_Khoan_3"]),
    ("yeu_cau_toa_an_xac_dinh_cho_nguoi_duoc_bao_ve", "Yêu cầu Tòa án xác định cho người được bảo vệ", "Quyen", ["Luat_HNGD_2014_Dieu_102_Khoan_3"]),
    ("cha_me_con_hoac_nguoi_giam_ho", "Cha, mẹ, con hoặc người giám hộ", "ChuThe", ["Luat_HNGD_2014_Dieu_102_Khoan_3_Diem_a"]),
    ("co_quan_quan_ly_nha_nuoc_ve_gia_dinh", "Cơ quan quản lý nhà nước về gia đình", "CoQuan", ["Luat_HNGD_2014_Dieu_102_Khoan_3_Diem_b"]),
    ("co_quan_quan_ly_nha_nuoc_ve_tre_em", "Cơ quan quản lý nhà nước về trẻ em", "CoQuan", ["Luat_HNGD_2014_Dieu_102_Khoan_3_Diem_c"]),
    ("hoi_lien_hiep_phu_nu", "Hội Liên hiệp Phụ nữ", "CoQuan", ["Luat_HNGD_2014_Dieu_102_Khoan_3_Diem_d"]),
]


def _build_nodes() -> dict[str, list[dict[str, Any]]]:
    nodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sid, ten, label, _ in _SEMANTIC_ROWS:
        nodes[label].append({"id": sid, "ten": ten, "topic": TOPIC})
    return dict(nodes)


def _build_can_cu_tai() -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for sid, _, label, legal_ids in _SEMANTIC_ROWS:
        for lid in legal_ids:
            out.append((label, sid, lid))
    return out


NODES = _build_nodes()
CAN_CU_TAI = _build_can_cu_tai()

EDGES: list[tuple] = [
    ("HanhVi", "xac_dinh_quan_he_cha_me_con", "XAC_DINH", "QuanHe", "quan_he_cha_me_con", {}),
    ("QuyDinh", "xac_dinh_con_chung_cua_vo_chong", "DIEU_CHINH", "QuanHe", "quan_he_con_chung_cua_vo_chong", {}),
    ("QuyDinh", "xac_dinh_con_chung_cua_vo_chong", "AP_DUNG_KHI", "DieuKien", "con_sinh_trong_thoi_ky_hon_nhan", {}),
    ("QuyDinh", "xac_dinh_con_chung_cua_vo_chong", "AP_DUNG_KHI", "DieuKien", "nguoi_vo_co_thai_trong_thoi_ky_hon_nhan", {}),
    ("QuyDinh", "xac_dinh_con_chung_cua_vo_chong", "AP_DUNG_KHI", "DieuKien", "con_sinh_trong_300_ngay_sau_cham_dut_hon_nhan", {}),
    ("QuyDinh", "xac_dinh_con_chung_cua_vo_chong", "AP_DUNG_KHI", "DieuKien", "con_sinh_truoc_dang_ky_ket_hon_duoc_cha_me_thua_nhan", {}),
    ("QuyDinh", "xac_dinh_con_chung_cua_vo_chong", "DAN_TOI", "HauQua", "duoc_coi_la_con_chung_cua_vo_chong", {}),
    ("HanhVi", "cha_me_khong_thua_nhan_con", "AP_DUNG_KHI", "DieuKien", "khong_thua_nhan_con_phai_co_chung_cu", {}),
    ("HanhVi", "cha_me_khong_thua_nhan_con", "YEU_CAU", "ThamQuyen", "toa_an_xac_dinh_khi_cha_me_khong_thua_nhan_con", {}),
    ("ThamQuyen", "toa_an_xac_dinh_khi_cha_me_khong_thua_nhan_con", "THUC_HIEN_BOI", "CoQuan", "toa_an", {}),
    ("ChuThe", "nguoi_khong_duoc_nhan_la_cha_me", "CO_QUYEN", "Quyen", "yeu_cau_toa_an_xac_dinh_mot_nguoi_la_con_minh", {}),
    ("Quyen", "yeu_cau_toa_an_xac_dinh_mot_nguoi_la_con_minh", "XAC_DINH", "QuanHe", "quan_he_cha_me_con", {}),
    ("ChuThe", "nguoi_dang_duoc_nhan_la_cha_me", "CO_QUYEN", "Quyen", "yeu_cau_toa_an_xac_dinh_khong_phai_la_con_minh", {}),
    ("Quyen", "yeu_cau_toa_an_xac_dinh_khong_phai_la_con_minh", "XAC_DINH", "QuanHe", "quan_he_cha_me_con", {}),
    ("ChuThe", "con", "CO_QUYEN", "Quyen", "con_co_quyen_nhan_cha_me", {}),
    ("Quyen", "con_co_quyen_nhan_cha_me", "AP_DUNG_KHI", "DieuKien", "cha_me_da_chet", {}),
    ("ChuThe", "con", "CO_QUYEN", "Quyen", "con_thanh_nien_nhan_cha_khong_can_me_dong_y", {}),
    ("ChuThe", "con", "CO_QUYEN", "Quyen", "con_thanh_nien_nhan_me_khong_can_cha_dong_y", {}),
    ("ChuThe", "cha_me", "CO_QUYEN", "Quyen", "cha_me_co_quyen_nhan_con", {}),
    ("Quyen", "cha_me_co_quyen_nhan_con", "AP_DUNG_KHI", "DieuKien", "con_da_chet", {}),
    ("HanhVi", "nguoi_dang_co_vo_chong_nhan_con", "DAN_TOI", "HauQua", "nhan_con_khong_can_vo_chong_dong_y", {}),
    ("Quyen", "nguoi_than_thich_yeu_cau_xac_dinh_thay", "AP_DUNG_KHI", "DieuKien", "nguoi_co_yeu_cau_xac_dinh_da_chet", {}),
    ("Quyen", "nguoi_than_thich_yeu_cau_xac_dinh_thay", "YEU_CAU", "ThamQuyen", "toa_an_xac_dinh_cho_nguoi_yeu_cau_da_chet", {}),
    ("ThamQuyen", "toa_an_xac_dinh_cho_nguoi_yeu_cau_da_chet", "THUC_HIEN_BOI", "CoQuan", "toa_an", {}),
    ("HanhVi", "vo_chong_sinh_con_bang_ky_thuat_ho_tro_sinh_san", "DAN_TOI", "QuyDinh", "ap_dung_dieu_88_khi_vo_sinh_con_bang_ho_tro_sinh_san", {}),
    ("HanhVi", "phu_nu_doc_than_sinh_con_bang_ky_thuat_ho_tro_sinh_san", "DAN_TOI", "QuanHe", "phu_nu_doc_than_la_me_cua_con_duoc_sinh_ra", {}),
    ("ChuThe", "nguoi_cho_tinh_trung_noan_phoi", "KHONG_PHAT_SINH", "QuanHe", "quan_he_cha_me_con", {}),
    ("ChuThe", "nguoi_cho_tinh_trung_noan_phoi", "DAN_TOI", "HauQua", "sinh_con_ho_tro_khong_phat_sinh_quan_he_voi_nguoi_cho", {}),
    ("HanhVi", "mang_thai_ho_vi_muc_dich_nhan_dao", "DAN_TOI", "QuyDinh", "xac_dinh_cha_me_mang_thai_ho_ap_dung_dieu_94", {}),
    ("ThamQuyen", "toa_an_giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho", "AP_DUNG_KHI", "DieuKien", "tranh_chap_ho_tro_sinh_san_hoac_mang_thai_ho", {}),
    ("ThamQuyen", "toa_an_giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho", "THUC_HIEN_BOI", "CoQuan", "toa_an", {}),
    ("Quyen", "ben_mang_thai_ho_co_quyen_nhan_nuoi_tre", "AP_DUNG_KHI", "DieuKien", "chua_giao_tre_va_ben_nho_mang_thai_ho_cung_chet_hoac_mat_nang_luc", {}),
    ("DieuKien", "ben_mang_thai_ho_khong_nhan_nuoi_tre", "DAN_TOI", "HauQua", "giam_ho_va_cap_duong_cho_tre_theo_quy_dinh", {}),
    ("ThamQuyen", "tham_quyen_co_quan_dang_ky_ho_tich", "AP_DUNG_KHI", "DieuKien", "xac_dinh_cha_me_con_khong_co_tranh_chap", {}),
    ("ThamQuyen", "tham_quyen_co_quan_dang_ky_ho_tich", "THUC_HIEN_BOI", "CoQuan", "co_quan_dang_ky_ho_tich", {}),
    ("ThamQuyen", "tham_quyen_toa_an_xac_dinh_cha_me_con", "AP_DUNG_KHI", "DieuKien", "xac_dinh_cha_me_con_co_tranh_chap", {}),
    ("ThamQuyen", "tham_quyen_toa_an_xac_dinh_cha_me_con", "AP_DUNG_KHI", "DieuKien", "nguoi_duoc_yeu_cau_xac_dinh_da_chet", {}),
    ("ThamQuyen", "tham_quyen_toa_an_xac_dinh_cha_me_con", "THUC_HIEN_BOI", "CoQuan", "toa_an", {}),
    ("ThamQuyen", "tham_quyen_toa_an_xac_dinh_cha_me_con", "DAN_TOI", "HauQua", "quyet_dinh_toa_an_duoc_gui_de_ghi_chu_ho_tich", {}),
    ("ChuThe", "cha_me_con_thanh_nien_khong_mat_nang_luc_hanh_vi", "CO_QUYEN", "Quyen", "yeu_cau_ho_tich_xac_dinh_cho_minh", {}),
    ("Quyen", "yeu_cau_ho_tich_xac_dinh_cho_minh", "YEU_CAU", "ThamQuyen", "tham_quyen_co_quan_dang_ky_ho_tich", {}),
    ("Quyen", "cha_me_con_yeu_cau_toa_an_xac_dinh_cho_minh", "YEU_CAU", "ThamQuyen", "tham_quyen_toa_an_xac_dinh_cha_me_con", {}),
    ("Quyen", "yeu_cau_toa_an_xac_dinh_cho_nguoi_duoc_bao_ve", "XAC_DINH", "QuanHe", "quan_he_cha_me_con", {}),
    ("ChuThe", "cha_me_con_hoac_nguoi_giam_ho", "CO_QUYEN", "Quyen", "yeu_cau_toa_an_xac_dinh_cho_nguoi_duoc_bao_ve", {}),
    ("CoQuan", "co_quan_quan_ly_nha_nuoc_ve_gia_dinh", "CO_QUYEN", "Quyen", "yeu_cau_toa_an_xac_dinh_cho_nguoi_duoc_bao_ve", {}),
    ("CoQuan", "co_quan_quan_ly_nha_nuoc_ve_tre_em", "CO_QUYEN", "Quyen", "yeu_cau_toa_an_xac_dinh_cho_nguoi_duoc_bao_ve", {}),
    ("CoQuan", "hoi_lien_hiep_phu_nu", "CO_QUYEN", "Quyen", "yeu_cau_toa_an_xac_dinh_cho_nguoi_duoc_bao_ve", {}),
    ("Quyen", "yeu_cau_toa_an_xac_dinh_cho_nguoi_duoc_bao_ve", "AP_DUNG_KHI", "ChuThe", "con_chua_thanh_nien_hoac_thanh_nien_mat_nang_luc", {}),
    ("Quyen", "yeu_cau_toa_an_xac_dinh_cho_nguoi_duoc_bao_ve", "AP_DUNG_KHI", "ChuThe", "cha_me_chua_thanh_nien_hoac_mat_nang_luc", {}),
]


def infer_legal_label(legal_id: str) -> str:
    if "_Diem_" in legal_id:
        return "DieuKhoanDiemLuat"
    if "_Khoan_" in legal_id:
        return "DieuKhoanLuat"
    return "DieuLuat"


def chunk_summary() -> dict[str, int]:
    return {
        "topic": TOPIC,
        "nodes_total": sum(len(v) for v in NODES.values()),
        "edges_total": len(EDGES),
        "can_cu_tai_total": len(CAN_CU_TAI),
    }


def create_indexes(session) -> None:
    for label in SEMANTIC_LABELS:
        session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.id)")
    session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{TOPIC_LABEL}) ON (n.id)")
    session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{TOPIC_LABEL}) ON (n.topic)")


def reset_semantic_layer(session) -> None:
    print(f"[reset] Xoá node có label :{TOPIC_LABEL} hoặc topic = {TOPIC!r}...")
    session.run(
        f"MATCH (n) WHERE n:{TOPIC_LABEL} OR n.topic = $topic DETACH DELETE n",
        topic=TOPIC,
    )


def merge_nodes(session) -> int:
    total = 0
    for label, items in NODES.items():
        if not items:
            continue
        query = (
            f"UNWIND $rows AS row "
            f"MERGE (n:{label} {{id: row.id, topic: $topic}}) "
            f"SET n += row "
            f"SET n:{TOPIC_LABEL} "
        )
        result = session.run(query, rows=items, topic=TOPIC).consume()
        total += result.counters.nodes_created
    return total


def merge_edges(session) -> int:
    total = 0
    grouped: dict[tuple[str, str, str], list[dict]] = {}
    for edge in EDGES:
        if len(edge) == 5:
            src_label, src_id, rel, dst_label, dst_id = edge
            props: dict = {}
        else:
            src_label, src_id, rel, dst_label, dst_id, props = edge
        key = (src_label, rel, dst_label)
        grouped.setdefault(key, []).append(
            {"src_id": src_id, "dst_id": dst_id, "props": props or {}}
        )
    for (src_label, rel, dst_label), rows in grouped.items():
        query = (
            f"UNWIND $rows AS row "
            f"MATCH (s:{src_label}:{TOPIC_LABEL} {{id: row.src_id, topic: $topic}}) "
            f"MATCH (d:{dst_label}:{TOPIC_LABEL} {{id: row.dst_id, topic: $topic}}) "
            f"MERGE (s)-[r:{rel}]->(d) "
            f"SET r += row.props"
        )
        result = session.run(query, rows=rows, topic=TOPIC).consume()
        total += result.counters.relationships_created
    return total


def merge_can_cu_tai(session) -> tuple[int, int]:
    grouped: dict[tuple[str, str], list[dict]] = {}
    for src_label, src_id, legal_id in CAN_CU_TAI:
        legal_label = infer_legal_label(legal_id)
        grouped.setdefault((src_label, legal_label), []).append(
            {"src_id": src_id, "dst_id": legal_id}
        )
    total_created = 0
    total_missing = 0
    for (src_label, legal_label), rows in grouped.items():
        query = (
            f"UNWIND $rows AS row "
            f"MATCH (s:{src_label}:{TOPIC_LABEL} {{id: row.src_id, topic: $topic}}) "
            f"OPTIONAL MATCH (d:{legal_label} {{id: row.dst_id}}) "
            f"WITH s, d, row "
            f"WHERE d IS NOT NULL "
            f"MERGE (s)-[r:CAN_CU_TAI]->(d) "
            f"RETURN count(r) AS created"
        )
        result = session.run(query, rows=rows, topic=TOPIC)
        record = result.single()
        if record:
            total_created += record["created"]
        missing_query = (
            f"UNWIND $rows AS row "
            f"MATCH (s:{src_label}:{TOPIC_LABEL} {{id: row.src_id, topic: $topic}}) "
            f"OPTIONAL MATCH (d:{legal_label} {{id: row.dst_id}}) "
            f"WITH row, d WHERE d IS NULL "
            f"RETURN collect(row.dst_id) AS missing"
        )
        missing_record = session.run(missing_query, rows=rows, topic=TOPIC).single()
        if missing_record and missing_record["missing"]:
            print(
                f"[WARN] CAN_CU_TAI: legal node không tồn tại cho "
                f"{src_label} → {legal_label}: {missing_record['missing']}"
            )
            total_missing += len(missing_record["missing"])
    return total_created, total_missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help=f"Xoá node :{TOPIC_LABEL} / topic={TOPIC} trước khi build.",
    )
    parser.add_argument("--dry-run", action="store_true", help="In summary, không ghi DB.")
    args = parser.parse_args()

    summary = chunk_summary()
    print("[summary] Sẽ build:")
    for k, v in summary.items():
        print(f"  - {k}: {v}")

    if args.dry_run:
        print("[dry-run] Không ghi DB. Kết thúc.")
        return

    with driver.session() as session:
        if args.reset:
            reset_semantic_layer(session)

        print("[step 1/4] Tạo indexes...")
        create_indexes(session)

        print("[step 2/4] MERGE nodes...")
        nodes_created = merge_nodes(session)
        print(f"  -> Đã tạo {nodes_created} node mới (số còn lại đã tồn tại).")

        print("[step 3/4] MERGE semantic edges...")
        edges_created = merge_edges(session)
        print(f"  -> Đã tạo {edges_created} edge ngữ nghĩa mới.")

        print("[step 4/4] MERGE CAN_CU_TAI tới legal layer...")
        cct_created, cct_missing = merge_can_cu_tai(session)
        print(
            f"  -> Đã tạo {cct_created} CAN_CU_TAI mới; "
            f"{cct_missing} legal node thiếu (xem WARN ở trên)."
        )

    print(f"[done] Build KG semantic layer cho '{TOPIC}' hoàn tất.")


if __name__ == "__main__":
    main()
