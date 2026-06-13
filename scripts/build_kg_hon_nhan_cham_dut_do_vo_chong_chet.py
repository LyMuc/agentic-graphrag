"""Build KG ngữ nghĩa cho topic 'Hôn nhân chấm dứt do vợ/chồng chết' (Điều 65-67 Luật HN&GĐ 2014).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_hon_nhan_cham_dut_do_vo_chong_chet.py           # MERGE idempotent
    python scripts/build_kg_hon_nhan_cham_dut_do_vo_chong_chet.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_hon_nhan_cham_dut_do_vo_chong_chet.py --dry-run # chỉ in summary

Schema: docs/kg_hon_nhan_cham_dut_do_vo_chong_chet_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "hon_nhan_cham_dut_do_vo_chong_chet"
TOPIC_LABEL = "HonNhanChamDutDoVoChongChet"

SEMANTIC_LABELS = [
    "ChuThe",
    "DieuKien",
    "HauQua",
    "HanhVi",
    "TinhTrangHonNhan",
    "Quyen",
    "ThoaThuan",
    "LoaiTaiSan",
    "QuyTrinhPhapLy",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("vo_hoac_chong_chet_trong_hon_nhan", "Vợ hoặc chồng chết trong thời kỳ hôn nhân", "ChuThe", ["Luat_HNGD_2014_Dieu_65"]),
    ("vo_hoac_chong_con_song_sau_khi_ben_kia_chet", "Vợ hoặc chồng còn sống sau khi bên kia chết hoặc bị tuyên bố là đã chết", "ChuThe", ["Luat_HNGD_2014_Dieu_66_Khoan_1", "Luat_HNGD_2014_Dieu_66_Khoan_3"]),
    ("nguoi_bi_tuyen_bo_da_chet_tro_ve", "Người vợ hoặc chồng bị tuyên bố là đã chết nhưng trở về", "ChuThe", ["Luat_HNGD_2014_Dieu_67_Khoan_1", "Luat_HNGD_2014_Dieu_67_Khoan_2"]),
    ("vo_hoac_chong_cua_nguoi_bi_tuyen_bo_da_chet_tro_ve", "Vợ hoặc chồng của người bị tuyên bố là đã chết trở về", "ChuThe", ["Luat_HNGD_2014_Dieu_67_Khoan_1", "Luat_HNGD_2014_Dieu_67_Khoan_2"]),
    ("nguoi_thua_ke_cua_nguoi_chet", "Những người thừa kế của người chết hoặc bị tuyên bố là đã chết", "ChuThe", ["Luat_HNGD_2014_Dieu_66_Khoan_1", "Luat_HNGD_2014_Dieu_66_Khoan_2"]),
    ("toa_an_tuyen_bo_vo_hoac_chong_da_chet", "Tòa án tuyên bố vợ hoặc chồng là đã chết", "QuyTrinhPhapLy", ["Luat_HNGD_2014_Dieu_65"]),
    ("toa_an_huy_bo_tuyen_bo_vo_hoac_chong_da_chet", "Tòa án hủy bỏ quyết định tuyên bố vợ hoặc chồng là đã chết", "QuyTrinhPhapLy", ["Luat_HNGD_2014_Dieu_67_Khoan_1"]),
    ("quyet_dinh_cho_ly_hon_voi_nguoi_bi_tuyen_bo_mat_tich", "Quyết định cho ly hôn với người bị tuyên bố mất tích được Điều 67 khoản 1 nhắc tới", "QuyTrinhPhapLy", ["Luat_HNGD_2014_Dieu_67_Khoan_1"]),
    ("mot_ben_chet_thuc_te", "Một bên vợ hoặc chồng chết trên thực tế", "DieuKien", ["Luat_HNGD_2014_Dieu_65"]),
    ("mot_ben_bi_toa_an_tuyen_bo_da_chet", "Một bên vợ hoặc chồng bị Tòa án tuyên bố là đã chết", "DieuKien", ["Luat_HNGD_2014_Dieu_65"]),
    ("chi_biet_tich_chua_co_tuyen_bo_da_chet", "Mới có dữ kiện biệt tích hoặc mất liên lạc, chưa xác định có quyết định tuyên bố đã chết", "DieuKien", ["Luat_HNGD_2014_Dieu_65"]),
    ("can_xac_minh_quyet_dinh_mat_tich_hay_tuyen_bo_da_chet", "Cần phân biệt quyết định tuyên bố mất tích với quyết định tuyên bố đã chết trước khi áp dụng Điều 67", "DieuKien", ["Luat_HNGD_2014_Dieu_67_Khoan_1"]),
    ("di_chuc_chi_dinh_nguoi_khac_quan_ly_di_san", "Di chúc chỉ định người khác quản lý di sản", "DieuKien", ["Luat_HNGD_2014_Dieu_66_Khoan_1"]),
    ("nguoi_thua_ke_thoa_thuan_cu_nguoi_khac_quan_ly_di_san", "Những người thừa kế thỏa thuận cử người khác quản lý di sản", "DieuKien", ["Luat_HNGD_2014_Dieu_66_Khoan_1"]),
    ("co_yeu_cau_chia_di_san", "Có yêu cầu chia di sản", "DieuKien", ["Luat_HNGD_2014_Dieu_66_Khoan_2"]),
    ("co_thoa_thuan_ve_che_do_tai_san_khi_chia_di_san", "Vợ chồng có thỏa thuận về chế độ tài sản chi phối việc chia", "DieuKien", ["Luat_HNGD_2014_Dieu_66_Khoan_2"]),
    ("chia_di_san_anh_huong_nghiem_trong_den_doi_song", "Việc chia di sản ảnh hưởng nghiêm trọng đến đời sống của bên còn sống hoặc gia đình", "DieuKien", ["Luat_HNGD_2014_Dieu_66_Khoan_3"]),
    ("ben_con_lai_chua_ket_hon_voi_nguoi_khac", "Vợ hoặc chồng của người trở về chưa kết hôn với người khác", "DieuKien", ["Luat_HNGD_2014_Dieu_67_Khoan_1"]),
    ("da_co_quyet_dinh_cho_ly_hon", "Đã có quyết định cho ly hôn của Tòa án theo trường hợp được Điều 67 khoản 1 dẫn chiếu", "DieuKien", ["Luat_HNGD_2014_Dieu_67_Khoan_1"]),
    ("ben_con_lai_da_ket_hon_voi_nguoi_khac", "Vợ hoặc chồng của người trở về đã kết hôn với người khác", "DieuKien", ["Luat_HNGD_2014_Dieu_67_Khoan_1"]),
    ("hon_nhan_duoc_khoi_phuc", "Quan hệ hôn nhân thuộc nhánh được khôi phục", "DieuKien", ["Luat_HNGD_2014_Dieu_67_Khoan_2_Diem_a"]),
    ("hon_nhan_khong_duoc_khoi_phuc", "Quan hệ hôn nhân thuộc nhánh không được khôi phục", "DieuKien", ["Luat_HNGD_2014_Dieu_67_Khoan_2_Diem_b"]),
    ("quyen_ben_con_song_quan_ly_tai_san_chung", "Quyền của bên còn sống quản lý tài sản chung theo quy tắc mặc định", "Quyen", ["Luat_HNGD_2014_Dieu_66_Khoan_1"]),
    ("quyen_yeu_cau_toa_an_han_che_phan_chia_di_san", "Quyền yêu cầu Tòa án hạn chế phân chia di sản khi đời sống bị ảnh hưởng nghiêm trọng", "Quyen", ["Luat_HNGD_2014_Dieu_66_Khoan_3"]),
    ("thoa_thuan_che_do_tai_san_ap_dung_khi_chia_di_san", "Thỏa thuận về chế độ tài sản được ưu tiên khi chia tài sản chung", "ThoaThuan", ["Luat_HNGD_2014_Dieu_66_Khoan_2"]),
    ("thoa_thuan_cu_nguoi_khac_quan_ly_di_san", "Thỏa thuận của những người thừa kế cử người khác quản lý di sản", "ThoaThuan", ["Luat_HNGD_2014_Dieu_66_Khoan_1"]),
    ("ben_con_song_quan_ly_tai_san_chung", "Bên còn sống quản lý tài sản chung của vợ chồng", "HanhVi", ["Luat_HNGD_2014_Dieu_66_Khoan_1"]),
    ("chia_tai_san_chung_khi_co_yeu_cau_chia_di_san", "Chia tài sản chung của vợ chồng khi có yêu cầu chia di sản", "HanhVi", ["Luat_HNGD_2014_Dieu_66_Khoan_2"]),
    ("chia_phan_tai_san_cua_nguoi_chet_theo_phap_luat_thua_ke", "Chia phần tài sản của người chết theo pháp luật về thừa kế", "HanhVi", ["Luat_HNGD_2014_Dieu_66_Khoan_2"]),
    ("yeu_cau_toa_an_han_che_phan_chia_di_san", "Bên còn sống yêu cầu Tòa án hạn chế phân chia di sản", "HanhVi", ["Luat_HNGD_2014_Dieu_66_Khoan_3"]),
    ("giai_quyet_tai_san_vo_chong_trong_kinh_doanh", "Giải quyết tài sản của vợ chồng trong kinh doanh khi một bên chết", "HanhVi", ["Luat_HNGD_2014_Dieu_66_Khoan_4"]),
    ("khoi_phuc_quan_he_tai_san_sau_khi_huy_bo_tuyen_bo_da_chet", "Khôi phục quan hệ tài sản khi quan hệ hôn nhân được khôi phục", "HanhVi", ["Luat_HNGD_2014_Dieu_67_Khoan_2_Diem_a"]),
    ("giai_quyet_tai_san_nhu_chia_tai_san_khi_ly_hon", "Giải quyết tài sản chưa chia như chia tài sản khi ly hôn nếu hôn nhân không được khôi phục", "HanhVi", ["Luat_HNGD_2014_Dieu_67_Khoan_2_Diem_b"]),
    ("tai_san_chung_khi_mot_ben_chet", "Tài sản chung của vợ chồng tại thời điểm một bên chết hoặc bị tuyên bố là đã chết", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_66_Khoan_1", "Luat_HNGD_2014_Dieu_66_Khoan_2"]),
    ("phan_tai_san_cua_nguoi_chet_trong_tai_san_chung", "Phần tài sản của người chết sau khi xác định phần trong tài sản chung", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_66_Khoan_2"]),
    ("tai_san_vo_chong_trong_kinh_doanh_khi_mot_ben_chet", "Tài sản của vợ chồng đang dùng trong kinh doanh khi một bên chết", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_66_Khoan_4"]),
    ("tai_san_co_duoc_trong_thoi_gian_bi_tuyen_bo_da_chet", "Tài sản có được từ khi quyết định tuyên bố đã chết có hiệu lực đến khi quyết định hủy bỏ có hiệu lực", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_67_Khoan_2_Diem_a"]),
    ("tai_san_co_truoc_tuyen_bo_da_chet_chua_chia", "Tài sản có trước khi quyết định tuyên bố đã chết có hiệu lực mà chưa chia", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_67_Khoan_2_Diem_b"]),
    ("hon_nhan_cham_dut_do_mot_ben_chet_hoac_bi_tuyen_bo_da_chet", "Hôn nhân đã chấm dứt do một bên chết hoặc bị Tòa án tuyên bố là đã chết", "TinhTrangHonNhan", ["Luat_HNGD_2014_Dieu_65"]),
    ("biet_tich_chua_tu_lam_cham_dut_hon_nhan", "Biệt tích hoặc mất liên lạc chưa tự làm chấm dứt hôn nhân nếu chưa có căn cứ pháp lý tương ứng", "TinhTrangHonNhan", ["Luat_HNGD_2014_Dieu_65"]),
    ("hon_nhan_duoc_khoi_phuc_tu_thoi_diem_ket_hon", "Hôn nhân được khôi phục từ thời điểm kết hôn khi đủ điều kiện Điều 67 khoản 1", "TinhTrangHonNhan", ["Luat_HNGD_2014_Dieu_67_Khoan_1"]),
    ("hon_nhan_xac_lap_sau_co_hieu_luc", "Quan hệ hôn nhân được xác lập sau có hiệu lực khi bên còn lại đã kết hôn với người khác", "TinhTrangHonNhan", ["Luat_HNGD_2014_Dieu_67_Khoan_1"]),
    ("hon_nhan_cham_dut_tai_thoi_diem_vo_hoac_chong_chet", "Hôn nhân chấm dứt kể từ thời điểm vợ hoặc chồng chết", "HauQua", ["Luat_HNGD_2014_Dieu_65"]),
    ("hon_nhan_cham_dut_theo_ngay_chet_ghi_trong_ban_an_quyet_dinh", "Khi bị tuyên bố đã chết, hôn nhân chấm dứt theo ngày chết ghi trong bản án hoặc quyết định", "HauQua", ["Luat_HNGD_2014_Dieu_65"]),
    ("tai_san_chung_duoc_chia_doi_tru_thoa_thuan", "Tài sản chung được chia đôi khi có yêu cầu chia di sản, trừ thỏa thuận về chế độ tài sản", "HauQua", ["Luat_HNGD_2014_Dieu_66_Khoan_2"]),
    ("phan_tai_san_nguoi_chet_duoc_chia_theo_phap_luat_thua_ke", "Phần tài sản của người chết được chia theo pháp luật về thừa kế", "HauQua", ["Luat_HNGD_2014_Dieu_66_Khoan_2"]),
    ("toa_an_co_the_han_che_phan_chia_di_san", "Tòa án có thể hạn chế phân chia di sản theo pháp luật dân sự khi đủ điều kiện", "HauQua", ["Luat_HNGD_2014_Dieu_66_Khoan_3"]),
    ("quan_he_hon_nhan_duoc_khoi_phuc", "Quan hệ hôn nhân được khôi phục nếu có quyết định hủy bỏ tuyên bố đã chết và bên còn lại chưa kết hôn với người khác", "HauQua", ["Luat_HNGD_2014_Dieu_67_Khoan_1"]),
    ("quyet_dinh_cho_ly_hon_van_co_hieu_luc", "Quyết định cho ly hôn đã có vẫn có hiệu lực pháp luật", "HauQua", ["Luat_HNGD_2014_Dieu_67_Khoan_1"]),
    ("quan_he_hon_nhan_xac_lap_sau_co_hieu_luc", "Quan hệ hôn nhân được xác lập sau có hiệu lực pháp luật", "HauQua", ["Luat_HNGD_2014_Dieu_67_Khoan_1"]),
    ("quan_he_tai_san_duoc_khoi_phuc_tu_ngay_huy_bo_co_hieu_luc", "Quan hệ tài sản được khôi phục từ khi quyết định hủy bỏ tuyên bố đã chết có hiệu lực", "HauQua", ["Luat_HNGD_2014_Dieu_67_Khoan_2_Diem_a"]),
    ("tai_san_trong_thoi_gian_tuyen_bo_la_tai_san_rieng", "Tài sản có được trong khoảng thời gian luật định là tài sản riêng của người có được tài sản", "HauQua", ["Luat_HNGD_2014_Dieu_67_Khoan_2_Diem_a"]),
    ("tai_san_truoc_tuyen_bo_chua_chia_duoc_giai_quyet_nhu_ly_hon", "Nếu hôn nhân không được khôi phục, tài sản có trước quyết định tuyên bố đã chết mà chưa chia được giải quyết như chia tài sản khi ly hôn", "HauQua", ["Luat_HNGD_2014_Dieu_67_Khoan_2_Diem_b"]),
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
    ("DieuKien", "mot_ben_chet_thuc_te", "DAN_TOI", "HauQua", "hon_nhan_cham_dut_tai_thoi_diem_vo_hoac_chong_chet", {}),
    ("HauQua", "hon_nhan_cham_dut_tai_thoi_diem_vo_hoac_chong_chet", "XAC_LAP", "TinhTrangHonNhan", "hon_nhan_cham_dut_do_mot_ben_chet_hoac_bi_tuyen_bo_da_chet", {}),
    ("QuyTrinhPhapLy", "toa_an_tuyen_bo_vo_hoac_chong_da_chet", "AP_DUNG_KHI", "DieuKien", "mot_ben_bi_toa_an_tuyen_bo_da_chet", {}),
    ("QuyTrinhPhapLy", "toa_an_tuyen_bo_vo_hoac_chong_da_chet", "DAN_TOI", "HauQua", "hon_nhan_cham_dut_theo_ngay_chet_ghi_trong_ban_an_quyet_dinh", {}),
    ("HauQua", "hon_nhan_cham_dut_theo_ngay_chet_ghi_trong_ban_an_quyet_dinh", "XAC_LAP", "TinhTrangHonNhan", "hon_nhan_cham_dut_do_mot_ben_chet_hoac_bi_tuyen_bo_da_chet", {}),
    ("DieuKien", "chi_biet_tich_chua_co_tuyen_bo_da_chet", "LIEN_QUAN", "TinhTrangHonNhan", "biet_tich_chua_tu_lam_cham_dut_hon_nhan", {}),
    ("ChuThe", "vo_hoac_chong_con_song_sau_khi_ben_kia_chet", "CO_QUYEN", "Quyen", "quyen_ben_con_song_quan_ly_tai_san_chung", {}),
    ("Quyen", "quyen_ben_con_song_quan_ly_tai_san_chung", "THUC_HIEN", "HanhVi", "ben_con_song_quan_ly_tai_san_chung", {}),
    ("HanhVi", "ben_con_song_quan_ly_tai_san_chung", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_chung_khi_mot_ben_chet", {}),
    ("HanhVi", "ben_con_song_quan_ly_tai_san_chung", "CO_NGOAI_LE", "DieuKien", "di_chuc_chi_dinh_nguoi_khac_quan_ly_di_san", {}),
    ("HanhVi", "ben_con_song_quan_ly_tai_san_chung", "CO_NGOAI_LE", "DieuKien", "nguoi_thua_ke_thoa_thuan_cu_nguoi_khac_quan_ly_di_san", {}),
    ("ThoaThuan", "thoa_thuan_cu_nguoi_khac_quan_ly_di_san", "DIEU_CHINH", "HanhVi", "ben_con_song_quan_ly_tai_san_chung", {}),
    ("HanhVi", "chia_tai_san_chung_khi_co_yeu_cau_chia_di_san", "AP_DUNG_KHI", "DieuKien", "co_yeu_cau_chia_di_san", {}),
    ("HanhVi", "chia_tai_san_chung_khi_co_yeu_cau_chia_di_san", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_chung_khi_mot_ben_chet", {}),
    ("HanhVi", "chia_tai_san_chung_khi_co_yeu_cau_chia_di_san", "DAN_TOI", "HauQua", "tai_san_chung_duoc_chia_doi_tru_thoa_thuan", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san_ap_dung_khi_chia_di_san", "DIEU_CHINH", "HauQua", "tai_san_chung_duoc_chia_doi_tru_thoa_thuan", {}),
    ("DieuKien", "co_thoa_thuan_ve_che_do_tai_san_khi_chia_di_san", "LIEN_QUAN", "ThoaThuan", "thoa_thuan_che_do_tai_san_ap_dung_khi_chia_di_san", {}),
    ("HanhVi", "chia_phan_tai_san_cua_nguoi_chet_theo_phap_luat_thua_ke", "TAC_DONG_LEN", "LoaiTaiSan", "phan_tai_san_cua_nguoi_chet_trong_tai_san_chung", {}),
    ("HanhVi", "chia_phan_tai_san_cua_nguoi_chet_theo_phap_luat_thua_ke", "DAN_TOI", "HauQua", "phan_tai_san_nguoi_chet_duoc_chia_theo_phap_luat_thua_ke", {}),
    ("ChuThe", "vo_hoac_chong_con_song_sau_khi_ben_kia_chet", "CO_QUYEN", "Quyen", "quyen_yeu_cau_toa_an_han_che_phan_chia_di_san", {}),
    ("Quyen", "quyen_yeu_cau_toa_an_han_che_phan_chia_di_san", "AP_DUNG_KHI", "DieuKien", "chia_di_san_anh_huong_nghiem_trong_den_doi_song", {}),
    ("Quyen", "quyen_yeu_cau_toa_an_han_che_phan_chia_di_san", "THUC_HIEN", "HanhVi", "yeu_cau_toa_an_han_che_phan_chia_di_san", {}),
    ("HanhVi", "yeu_cau_toa_an_han_che_phan_chia_di_san", "DAN_TOI", "HauQua", "toa_an_co_the_han_che_phan_chia_di_san", {}),
    ("HanhVi", "giai_quyet_tai_san_vo_chong_trong_kinh_doanh", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_vo_chong_trong_kinh_doanh_khi_mot_ben_chet", {}),
    ("QuyTrinhPhapLy", "toa_an_huy_bo_tuyen_bo_vo_hoac_chong_da_chet", "AP_DUNG_KHI", "DieuKien", "ben_con_lai_chua_ket_hon_voi_nguoi_khac", {}),
    ("DieuKien", "ben_con_lai_chua_ket_hon_voi_nguoi_khac", "DAN_TOI", "HauQua", "quan_he_hon_nhan_duoc_khoi_phuc", {}),
    ("HauQua", "quan_he_hon_nhan_duoc_khoi_phuc", "XAC_LAP", "TinhTrangHonNhan", "hon_nhan_duoc_khoi_phuc_tu_thoi_diem_ket_hon", {}),
    ("QuyTrinhPhapLy", "quyet_dinh_cho_ly_hon_voi_nguoi_bi_tuyen_bo_mat_tich", "AP_DUNG_KHI", "DieuKien", "da_co_quyet_dinh_cho_ly_hon", {}),
    ("DieuKien", "da_co_quyet_dinh_cho_ly_hon", "DAN_TOI", "HauQua", "quyet_dinh_cho_ly_hon_van_co_hieu_luc", {}),
    ("DieuKien", "ben_con_lai_da_ket_hon_voi_nguoi_khac", "DAN_TOI", "HauQua", "quan_he_hon_nhan_xac_lap_sau_co_hieu_luc", {}),
    ("HauQua", "quan_he_hon_nhan_xac_lap_sau_co_hieu_luc", "XAC_LAP", "TinhTrangHonNhan", "hon_nhan_xac_lap_sau_co_hieu_luc", {}),
    ("DieuKien", "can_xac_minh_quyet_dinh_mat_tich_hay_tuyen_bo_da_chet", "LIEN_QUAN", "QuyTrinhPhapLy", "toa_an_huy_bo_tuyen_bo_vo_hoac_chong_da_chet", {}),
    ("HauQua", "quan_he_hon_nhan_duoc_khoi_phuc", "CHI_PHOI", "HanhVi", "khoi_phuc_quan_he_tai_san_sau_khi_huy_bo_tuyen_bo_da_chet", {}),
    ("HanhVi", "khoi_phuc_quan_he_tai_san_sau_khi_huy_bo_tuyen_bo_da_chet", "AP_DUNG_KHI", "DieuKien", "hon_nhan_duoc_khoi_phuc", {}),
    ("HanhVi", "khoi_phuc_quan_he_tai_san_sau_khi_huy_bo_tuyen_bo_da_chet", "DAN_TOI", "HauQua", "quan_he_tai_san_duoc_khoi_phuc_tu_ngay_huy_bo_co_hieu_luc", {}),
    ("HanhVi", "khoi_phuc_quan_he_tai_san_sau_khi_huy_bo_tuyen_bo_da_chet", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_co_duoc_trong_thoi_gian_bi_tuyen_bo_da_chet", {}),
    ("LoaiTaiSan", "tai_san_co_duoc_trong_thoi_gian_bi_tuyen_bo_da_chet", "DAN_TOI", "HauQua", "tai_san_trong_thoi_gian_tuyen_bo_la_tai_san_rieng", {}),
    ("HauQua", "quyet_dinh_cho_ly_hon_van_co_hieu_luc", "CHI_PHOI", "HanhVi", "giai_quyet_tai_san_nhu_chia_tai_san_khi_ly_hon", {}),
    ("HauQua", "quan_he_hon_nhan_xac_lap_sau_co_hieu_luc", "CHI_PHOI", "HanhVi", "giai_quyet_tai_san_nhu_chia_tai_san_khi_ly_hon", {}),
    ("HanhVi", "giai_quyet_tai_san_nhu_chia_tai_san_khi_ly_hon", "AP_DUNG_KHI", "DieuKien", "hon_nhan_khong_duoc_khoi_phuc", {}),
    ("HanhVi", "giai_quyet_tai_san_nhu_chia_tai_san_khi_ly_hon", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_co_truoc_tuyen_bo_da_chet_chua_chia", {}),
    ("HanhVi", "giai_quyet_tai_san_nhu_chia_tai_san_khi_ly_hon", "DAN_TOI", "HauQua", "tai_san_truoc_tuyen_bo_chua_chia_duoc_giai_quyet_nhu_ly_hon", {}),
]

RELATIONSHIPS = EDGES


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
