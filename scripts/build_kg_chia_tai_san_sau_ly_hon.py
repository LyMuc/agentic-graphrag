"""Build KG ngữ nghĩa cho 'Chia tài sản sau ly hôn' (Điều 59-64 Luật HN&GĐ 2014).

Script này build / refresh lớp semantic ĐỘC LẬP với Knowledge-Graph-Builder cũ.
Chỉ MERGE node ngữ nghĩa và relationship nội bộ + CAN_CU_TAI sang layer luật
(DieuLuat / DieuKhoanLuat / DieuKhoanDiemLuat) đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_chia_tai_san_sau_ly_hon.py           # MERGE idempotent
    python scripts/build_kg_chia_tai_san_sau_ly_hon.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_chia_tai_san_sau_ly_hon.py --dry-run # chỉ in summary, không ghi DB

Schema đầy đủ: docs/cypher_semantic_graph_chia_tai_san_sau_ly_hon.md
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "chia_tai_san_sau_ly_hon"
TOPIC_LABEL = "ChiaTaiSanSauLyHon"

# =============================================================================
# 1. SEMANTIC LABELS (reuse từ KG tai_san + label topic ChiaTaiSanSauLyHon)
# =============================================================================
SEMANTIC_LABELS = [
    "LoaiTaiSan",
    "HanhVi",
    "NghiaVu",
    "DieuKien",
    "HauQua",
    "ThoaThuan",
    "ChuThe",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}


# =============================================================================
# 2. NODES (semantic layer — mỗi node có topic)
# =============================================================================
NODES: dict[str, list[dict[str, Any]]] = {
    "HanhVi": [
        {"id": "giai_quyet_tai_san_khi_ly_hon", "ten": "Giải quyết tài sản của vợ chồng khi ly hôn", "loai": "giai_quyet", "topic": TOPIC},
        {"id": "toa_an_giai_quyet_tai_san_ly_hon", "ten": "Tòa án giải quyết khi không thỏa thuận hoặc thỏa thuận không rõ", "loai": "giai_quyet", "topic": TOPIC},
        {"id": "chia_tai_san_chung_khi_ly_hon", "ten": "Chia tài sản chung khi ly hôn", "loai": "chia", "topic": TOPIC},
        {"id": "chia_bang_hien_vat", "ten": "Chia tài sản bằng hiện vật", "loai": "chia", "topic": TOPIC},
        {"id": "xac_dinh_tai_san_rieng_khi_ly_hon", "ten": "Xác định tài sản riêng khi ly hôn", "loai": "xac_dinh", "topic": TOPIC},
        {"id": "giai_quyet_quyen_nghia_vu_nguoi_thu_ba_khi_ly_hon", "ten": "Giải quyết quyền, nghĩa vụ tài sản với người thứ ba khi ly hôn", "loai": "giai_quyet", "topic": TOPIC},
        {"id": "chia_tai_san_song_chung_voi_gia_dinh", "ten": "Chia tài sản khi vợ chồng sống chung với gia đình", "loai": "chia", "topic": TOPIC},
        {"id": "chia_quyen_su_dung_dat_khi_ly_hon", "ten": "Chia quyền sử dụng đất khi ly hôn", "loai": "chia", "topic": TOPIC},
        {"id": "chia_tai_san_chung_dua_vao_kinh_doanh", "ten": "Chia tài sản chung đưa vào kinh doanh", "loai": "kinh_doanh", "topic": TOPIC},
    ],
    "ThoaThuan": [
        {"id": "thoa_thuan_giai_quyet_tai_san_ly_hon", "ten": "Thỏa thuận giải quyết tài sản khi ly hôn", "doi_tuong_thoa_thuan": "vo_chong", "topic": TOPIC},
    ],
    "DieuKien": [
        {"id": "hoan_canh_gia_dinh_vo_chong", "ten": "Hoàn cảnh gia đình và vợ chồng", "nhom": "yeu_to_chia", "topic": TOPIC},
        {"id": "cong_suc_dong_gop_tao_lap_duy_tri_phat_trien", "ten": "Công sức đóng góp tạo lập, duy trì, phát triển tài sản chung", "nhom": "yeu_to_chia", "topic": TOPIC},
        {"id": "lao_dong_gia_dinh_duoc_coi_nhu_lao_dong_co_thu_nhap", "ten": "Lao động nội trợ/chăm sóc gia đình được coi như lao động có thu nhập", "nhom": "yeu_to_chia", "topic": TOPIC},
        {"id": "bao_ve_loi_ich_san_xuat_kinh_doanh_nghe_nghiep", "ten": "Bảo vệ lợi ích chính đáng trong sản xuất, kinh doanh, nghề nghiệp", "nhom": "yeu_to_chia", "topic": TOPIC},
        {"id": "loi_vi_pham_quyen_nghia_vu_vo_chong", "ten": "Lỗi vi phạm quyền, nghĩa vụ của vợ chồng", "nhom": "yeu_to_chia", "topic": TOPIC},
        {"id": "co_tranh_chap_quyen_nghia_vu_tai_san", "ten": "Có tranh chấp quyền, nghĩa vụ tài sản", "nhom": "tranh_chap", "topic": TOPIC},
        {"id": "tai_san_vo_chong_trong_khoi_gia_dinh_khong_xac_dinh_duoc", "ten": "Phần tài sản trong khối tài sản gia đình không xác định được", "nhom": "song_chung_gia_dinh", "topic": TOPIC},
        {"id": "tai_san_vo_chong_trong_khoi_gia_dinh_xac_dinh_duoc_theo_phan", "ten": "Phần tài sản trong khối tài sản gia đình xác định được theo phần", "nhom": "song_chung_gia_dinh", "topic": TOPIC},
        {"id": "kho_khan_ve_cho_o", "ten": "Một bên khó khăn về chỗ ở", "nhom": "luu_cu", "topic": TOPIC},
    ],
    "HauQua": [
        {"id": "thanh_toan_chenh_lech_gia_tri", "ten": "Thanh toán phần chênh lệch giá trị", "loai": "thanh_toan", "topic": TOPIC},
        {"id": "chia_gia_tri_tai_san_rieng_da_sap_nhap", "ten": "Thanh toán giá trị tài sản riêng đã sáp nhập/trộn lẫn", "loai": "thanh_toan", "topic": TOPIC},
        {"id": "bao_ve_vo_con_yeu_the", "ten": "Bảo vệ quyền lợi của vợ, con chưa thành niên hoặc con yếu thế", "loai": "bao_ve", "topic": TOPIC},
        {"id": "quyen_nghia_vu_voi_nguoi_thu_ba_van_hieu_luc", "ten": "Quyền, nghĩa vụ với người thứ ba vẫn có hiệu lực sau ly hôn", "loai": "hieu_luc", "topic": TOPIC},
        {"id": "giai_quyet_quyen_loi_ben_khong_co_qsd_dat", "ten": "Quyền lợi của bên không có QSDĐ và không tiếp tục sống chung", "loai": "quyen_loi", "topic": TOPIC},
        {"id": "luu_cu_sau_ly_hon", "ten": "Quyền lưu cư sau ly hôn", "loai": "luu_cu", "topic": TOPIC},
        {"id": "thoi_han_luu_cu_06_thang", "ten": "Thời hạn lưu cư 06 tháng", "loai": "luu_cu", "topic": TOPIC},
        {"id": "nhan_tai_san_kinh_doanh_va_thanh_toan_gia_tri", "ten": "Người đang kinh doanh nhận tài sản và thanh toán giá trị cho bên kia", "loai": "kinh_doanh", "topic": TOPIC},
    ],
    "LoaiTaiSan": [
        {"id": "qsd_dat_la_tai_san_rieng", "ten": "Quyền sử dụng đất là tài sản riêng", "tinh_chat": "rieng", "loai_tai_san": "quyen_su_dung_dat", "topic": TOPIC},
        {"id": "qsd_dat_la_tai_san_chung", "ten": "Quyền sử dụng đất là tài sản chung", "tinh_chat": "chung", "loai_tai_san": "quyen_su_dung_dat", "topic": TOPIC},
        {"id": "dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san", "ten": "Đất nông nghiệp trồng cây hằng năm, nuôi trồng thủy sản", "tinh_chat": "chung", "loai_tai_san": "dat_nong_nghiep", "topic": TOPIC},
        {"id": "qsd_dat_chung_voi_ho_gia_dinh", "ten": "Quyền sử dụng đất chung với hộ gia đình", "tinh_chat": "chung", "loai_tai_san": "quyen_su_dung_dat", "topic": TOPIC},
        {"id": "dat_cay_lau_nam_dat_lam_nghiep_dat_o", "ten": "Đất cây lâu năm, đất lâm nghiệp, đất ở", "tinh_chat": "chung", "loai_tai_san": "dat_khac", "topic": TOPIC},
        {"id": "loai_dat_khac", "ten": "Loại đất khác", "tinh_chat": "chung", "loai_tai_san": "dat_khac", "topic": TOPIC},
        {"id": "nha_o_rieng_da_dua_vao_su_dung_chung", "ten": "Nhà riêng đã đưa vào sử dụng chung", "tinh_chat": "rieng", "loai_tai_san": "nha_o", "topic": TOPIC},
        {"id": "bat_dong_san_chung", "ten": "Bất động sản là tài sản chung", "tinh_chat": "chung", "loai_tai_san": "bat_dong_san", "topic": TOPIC},
        {"id": "bat_dong_san_rieng", "ten": "Bất động sản là tài sản riêng", "tinh_chat": "rieng", "loai_tai_san": "bat_dong_san", "topic": TOPIC},
        {"id": "dong_san_phai_dang_ky_chung", "ten": "Động sản phải đăng ký là tài sản chung", "tinh_chat": "chung", "loai_tai_san": "dong_san_phai_dang_ky", "topic": TOPIC},
        {"id": "dong_san_phai_dang_ky_rieng", "ten": "Động sản phải đăng ký là tài sản riêng", "tinh_chat": "rieng", "loai_tai_san": "dong_san_phai_dang_ky", "topic": TOPIC},
        {"id": "tai_khoan_tiet_kiem_tro_cap_chung", "ten": "Tài khoản tiết kiệm/trợ cấp là tài sản chung", "tinh_chat": "chung", "loai_tai_san": "tai_khoan_tiet_kiem_tro_cap", "topic": TOPIC},
        {"id": "tai_san_duoc_tang_cho", "ten": "Tài sản được tặng cho", "tinh_chat": "rieng", "loai_tai_san": "tai_san_tang_cho", "topic": TOPIC},
    ],
}


# =============================================================================
# 3. EDGES (semantic ↔ semantic)
# =============================================================================
EDGES: list[tuple] = [
    ("HanhVi", "giai_quyet_tai_san_khi_ly_hon", "DAN_TOI", "HanhVi", "chia_tai_san_chung_khi_ly_hon", {}),
    ("ThoaThuan", "thoa_thuan_giai_quyet_tai_san_ly_hon", "DIEU_CHINH", "HanhVi", "giai_quyet_tai_san_khi_ly_hon", {}),
    ("HanhVi", "toa_an_giai_quyet_tai_san_ly_hon", "THUC_HIEN", "HanhVi", "giai_quyet_tai_san_khi_ly_hon", {}),
    ("HanhVi", "chia_tai_san_chung_khi_ly_hon", "AP_DUNG_KHI", "DieuKien", "hoan_canh_gia_dinh_vo_chong", {}),
    ("HanhVi", "chia_tai_san_chung_khi_ly_hon", "AP_DUNG_KHI", "DieuKien", "cong_suc_dong_gop_tao_lap_duy_tri_phat_trien", {}),
    ("HanhVi", "chia_tai_san_chung_khi_ly_hon", "AP_DUNG_KHI", "DieuKien", "lao_dong_gia_dinh_duoc_coi_nhu_lao_dong_co_thu_nhap", {}),
    ("HanhVi", "chia_tai_san_chung_khi_ly_hon", "AP_DUNG_KHI", "DieuKien", "bao_ve_loi_ich_san_xuat_kinh_doanh_nghe_nghiep", {}),
    ("HanhVi", "chia_tai_san_chung_khi_ly_hon", "AP_DUNG_KHI", "DieuKien", "loi_vi_pham_quyen_nghia_vu_vo_chong", {}),
    ("HanhVi", "chia_tai_san_chung_khi_ly_hon", "DAN_TOI", "HanhVi", "chia_bang_hien_vat", {}),
    ("HanhVi", "chia_bang_hien_vat", "DAN_TOI", "HauQua", "thanh_toan_chenh_lech_gia_tri", {}),
    ("HanhVi", "xac_dinh_tai_san_rieng_khi_ly_hon", "DAN_TOI", "HauQua", "chia_gia_tri_tai_san_rieng_da_sap_nhap", {}),
    ("HanhVi", "giai_quyet_quyen_nghia_vu_nguoi_thu_ba_khi_ly_hon", "DAN_TOI", "HauQua", "quyen_nghia_vu_voi_nguoi_thu_ba_van_hieu_luc", {}),
    ("DieuKien", "co_tranh_chap_quyen_nghia_vu_tai_san", "AP_DUNG_KHI", "HanhVi", "giai_quyet_quyen_nghia_vu_nguoi_thu_ba_khi_ly_hon", {}),
    ("HanhVi", "chia_tai_san_song_chung_voi_gia_dinh", "AP_DUNG_KHI", "DieuKien", "tai_san_vo_chong_trong_khoi_gia_dinh_khong_xac_dinh_duoc", {}),
    ("HanhVi", "chia_tai_san_song_chung_voi_gia_dinh", "AP_DUNG_KHI", "DieuKien", "tai_san_vo_chong_trong_khoi_gia_dinh_xac_dinh_duoc_theo_phan", {}),
    ("HanhVi", "chia_quyen_su_dung_dat_khi_ly_hon", "TAC_DONG_LEN", "LoaiTaiSan", "qsd_dat_la_tai_san_rieng", {}),
    ("HanhVi", "chia_quyen_su_dung_dat_khi_ly_hon", "TAC_DONG_LEN", "LoaiTaiSan", "qsd_dat_la_tai_san_chung", {}),
    ("LoaiTaiSan", "qsd_dat_la_tai_san_chung", "AP_DUNG_KHI", "LoaiTaiSan", "dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san", {}),
    ("LoaiTaiSan", "qsd_dat_la_tai_san_chung", "AP_DUNG_KHI", "LoaiTaiSan", "qsd_dat_chung_voi_ho_gia_dinh", {}),
    ("LoaiTaiSan", "qsd_dat_la_tai_san_chung", "AP_DUNG_KHI", "LoaiTaiSan", "dat_cay_lau_nam_dat_lam_nghiep_dat_o", {}),
    ("LoaiTaiSan", "qsd_dat_la_tai_san_chung", "AP_DUNG_KHI", "LoaiTaiSan", "loai_dat_khac", {}),
    ("HauQua", "luu_cu_sau_ly_hon", "AP_DUNG_KHI", "LoaiTaiSan", "nha_o_rieng_da_dua_vao_su_dung_chung", {}),
    ("HauQua", "luu_cu_sau_ly_hon", "AP_DUNG_KHI", "DieuKien", "kho_khan_ve_cho_o", {}),
    ("HauQua", "luu_cu_sau_ly_hon", "DAN_TOI", "HauQua", "thoi_han_luu_cu_06_thang", {}),
    ("HanhVi", "chia_tai_san_chung_dua_vao_kinh_doanh", "DAN_TOI", "HauQua", "nhan_tai_san_kinh_doanh_va_thanh_toan_gia_tri", {}),
    ("HanhVi", "giai_quyet_tai_san_khi_ly_hon", "DAN_TOI", "HauQua", "bao_ve_vo_con_yeu_the", {}),
    ("HanhVi", "chia_tai_san_chung_khi_ly_hon", "DAN_TOI", "HanhVi", "xac_dinh_tai_san_rieng_khi_ly_hon", {}),
    ("HanhVi", "chia_tai_san_chung_khi_ly_hon", "TAC_DONG_LEN", "LoaiTaiSan", "bat_dong_san_chung", {}),
    ("HanhVi", "chia_tai_san_chung_khi_ly_hon", "TAC_DONG_LEN", "LoaiTaiSan", "dong_san_phai_dang_ky_chung", {}),
    ("HanhVi", "chia_tai_san_chung_khi_ly_hon", "TAC_DONG_LEN", "LoaiTaiSan", "tai_khoan_tiet_kiem_tro_cap_chung", {}),
    ("HanhVi", "xac_dinh_tai_san_rieng_khi_ly_hon", "TAC_DONG_LEN", "LoaiTaiSan", "bat_dong_san_rieng", {}),
    ("HanhVi", "xac_dinh_tai_san_rieng_khi_ly_hon", "TAC_DONG_LEN", "LoaiTaiSan", "dong_san_phai_dang_ky_rieng", {}),
    ("HanhVi", "xac_dinh_tai_san_rieng_khi_ly_hon", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_duoc_tang_cho", {}),
    ("HanhVi", "xac_dinh_tai_san_rieng_khi_ly_hon", "TAC_DONG_LEN", "LoaiTaiSan", "qsd_dat_la_tai_san_rieng", {}),
]


# =============================================================================
# 4. CAN_CU_TAI — bridge tới legal layer (Đ59-64)
# =============================================================================
CAN_CU_TAI: list[tuple[str, str, str]] = [
    ("HanhVi", "giai_quyet_tai_san_khi_ly_hon", "Luat_HNGD_2014_Dieu_59"),
    ("ThoaThuan", "thoa_thuan_giai_quyet_tai_san_ly_hon", "Luat_HNGD_2014_Dieu_59_Khoan_1"),
    ("HanhVi", "toa_an_giai_quyet_tai_san_ly_hon", "Luat_HNGD_2014_Dieu_59_Khoan_1"),
    ("HanhVi", "chia_tai_san_chung_khi_ly_hon", "Luat_HNGD_2014_Dieu_59_Khoan_2"),
    ("HanhVi", "chia_tai_san_chung_khi_ly_hon", "Luat_HNGD_2014_Dieu_59_Khoan_3"),
    ("HanhVi", "chia_bang_hien_vat", "Luat_HNGD_2014_Dieu_59_Khoan_3"),
    ("HauQua", "thanh_toan_chenh_lech_gia_tri", "Luat_HNGD_2014_Dieu_59_Khoan_3"),
    ("HanhVi", "xac_dinh_tai_san_rieng_khi_ly_hon", "Luat_HNGD_2014_Dieu_59_Khoan_4"),
    ("HauQua", "chia_gia_tri_tai_san_rieng_da_sap_nhap", "Luat_HNGD_2014_Dieu_59_Khoan_4"),
    ("DieuKien", "hoan_canh_gia_dinh_vo_chong", "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_a"),
    ("DieuKien", "cong_suc_dong_gop_tao_lap_duy_tri_phat_trien", "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_b"),
    ("DieuKien", "lao_dong_gia_dinh_duoc_coi_nhu_lao_dong_co_thu_nhap", "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_b"),
    ("DieuKien", "bao_ve_loi_ich_san_xuat_kinh_doanh_nghe_nghiep", "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_c"),
    ("DieuKien", "loi_vi_pham_quyen_nghia_vu_vo_chong", "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_d"),
    ("HauQua", "bao_ve_vo_con_yeu_the", "Luat_HNGD_2014_Dieu_59_Khoan_5"),
    ("HanhVi", "giai_quyet_quyen_nghia_vu_nguoi_thu_ba_khi_ly_hon", "Luat_HNGD_2014_Dieu_60"),
    ("HauQua", "quyen_nghia_vu_voi_nguoi_thu_ba_van_hieu_luc", "Luat_HNGD_2014_Dieu_60_Khoan_1"),
    ("DieuKien", "co_tranh_chap_quyen_nghia_vu_tai_san", "Luat_HNGD_2014_Dieu_60_Khoan_2"),
    ("HanhVi", "chia_tai_san_song_chung_voi_gia_dinh", "Luat_HNGD_2014_Dieu_61"),
    ("DieuKien", "tai_san_vo_chong_trong_khoi_gia_dinh_khong_xac_dinh_duoc", "Luat_HNGD_2014_Dieu_61_Khoan_1"),
    ("DieuKien", "tai_san_vo_chong_trong_khoi_gia_dinh_xac_dinh_duoc_theo_phan", "Luat_HNGD_2014_Dieu_61_Khoan_2"),
    ("HanhVi", "chia_quyen_su_dung_dat_khi_ly_hon", "Luat_HNGD_2014_Dieu_62"),
    ("LoaiTaiSan", "qsd_dat_la_tai_san_rieng", "Luat_HNGD_2014_Dieu_62_Khoan_1"),
    ("LoaiTaiSan", "qsd_dat_la_tai_san_chung", "Luat_HNGD_2014_Dieu_62_Khoan_2"),
    ("LoaiTaiSan", "dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san", "Luat_HNGD_2014_Dieu_62_Khoan_2_Diem_a"),
    ("LoaiTaiSan", "qsd_dat_chung_voi_ho_gia_dinh", "Luat_HNGD_2014_Dieu_62_Khoan_2_Diem_b"),
    ("LoaiTaiSan", "dat_cay_lau_nam_dat_lam_nghiep_dat_o", "Luat_HNGD_2014_Dieu_62_Khoan_2_Diem_c"),
    ("LoaiTaiSan", "loai_dat_khac", "Luat_HNGD_2014_Dieu_62_Khoan_2_Diem_d"),
    ("HauQua", "giai_quyet_quyen_loi_ben_khong_co_qsd_dat", "Luat_HNGD_2014_Dieu_62_Khoan_3"),
    ("HauQua", "luu_cu_sau_ly_hon", "Luat_HNGD_2014_Dieu_63"),
    ("LoaiTaiSan", "nha_o_rieng_da_dua_vao_su_dung_chung", "Luat_HNGD_2014_Dieu_63"),
    ("DieuKien", "kho_khan_ve_cho_o", "Luat_HNGD_2014_Dieu_63"),
    ("HauQua", "thoi_han_luu_cu_06_thang", "Luat_HNGD_2014_Dieu_63"),
    ("HanhVi", "chia_tai_san_chung_dua_vao_kinh_doanh", "Luat_HNGD_2014_Dieu_64"),
    ("HauQua", "nhan_tai_san_kinh_doanh_va_thanh_toan_gia_tri", "Luat_HNGD_2014_Dieu_64"),
]


# =============================================================================
# 5. Helpers
# =============================================================================
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
    print(f"[reset] Xoá node có label :{TOPIC_LABEL}...")
    query = f"MATCH (n:{TOPIC_LABEL}) DETACH DELETE n"
    session.run(query)


def merge_nodes(session) -> int:
    total = 0
    for label, items in NODES.items():
        if not items:
            continue
        query = (
            f"UNWIND $rows AS row "
            f"MERGE (n:{label} {{id: row.id}}) "
            f"SET n += row "
            f"SET n:{TOPIC_LABEL} "
        )
        result = session.run(query, rows=items).consume()
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
        help=f"Xoá node có label :{TOPIC_LABEL} trước khi build.",
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
