"""Build KG ngữ nghĩa cho topic quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.py
    python scripts/build_kg_quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.py --reset
    python scripts/build_kg_quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.py --dry-run

Schema: docs/kg_quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh"
TOPIC_LABEL = "QuanHeGiuaCacThanhVienKhacTrongGiaDinh"

SEMANTIC_LABELS = [
    "ChuThe",
    "Quyen",
    "NghiaVu",
    "QuyDinh",
    "DieuKien",
    "QuanHe",
    "HauQua",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    (
        "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh",
        "Quan hệ quyền, nghĩa vụ giữa các thành viên khác trong gia đình",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_103"],
    ),
    (
        "quan_he_ong_ba_noi_ngoai_va_chau",
        "Quan hệ giữa ông bà nội, ông bà ngoại và cháu",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_104"],
    ),
    (
        "quan_he_anh_chi_em",
        "Quan hệ giữa anh, chị, em",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_105"],
    ),
    (
        "quan_he_co_di_chu_cau_bac_ruot_va_chau_ruot",
        "Quan hệ giữa cô, dì, chú, cậu, bác ruột và cháu ruột",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_106"],
    ),
    (
        "thanh_vien_gia_dinh",
        "Thành viên gia đình thuộc phạm vi Điều 103",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_103"],
    ),
    (
        "thanh_vien_gia_dinh_song_chung",
        "Thành viên gia đình đang sống chung",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_103_Khoan_2"],
    ),
    (
        "ong_ba_noi_ngoai",
        "Ông bà nội, ông bà ngoại",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_104"],
    ),
    (
        "chau",
        "Cháu trong quan hệ với ông bà nội, ông bà ngoại",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_104"],
    ),
    (
        "chau_da_thanh_nien",
        "Cháu đã thành niên",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_104_Khoan_2"],
    ),
    (
        "anh_chi_em",
        "Anh, chị, em trong gia đình",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_105"],
    ),
    (
        "co_di_chu_cau_bac_ruot",
        "Cô, dì, chú, cậu, bác ruột",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_106"],
    ),
    (
        "chau_ruot",
        "Cháu ruột của cô, dì, chú, cậu, bác ruột",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_106"],
    ),
    (
        "nguoi_can_duoc_nuoi_duong",
        "Người cần được nuôi dưỡng trong quan hệ gia đình mở rộng",
        "ChuThe",
        [
            "Luat_HNGD_2014_Dieu_104",
            "Luat_HNGD_2014_Dieu_105",
            "Luat_HNGD_2014_Dieu_106",
        ],
    ),
    (
        "quyen_duoc_quan_tam_cham_soc_giup_do_ton_trong",
        "Quyền được các thành viên gia đình quan tâm, chăm sóc, giúp đỡ, tôn trọng",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_103_Khoan_1"],
    ),
    (
        "quyen_loi_ich_nhan_than_va_tai_san_duoc_bao_ve",
        "Quyền, lợi ích hợp pháp về nhân thân và tài sản được pháp luật bảo vệ",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_103_Khoan_1"],
    ),
    (
        "quyen_ong_ba_trong_nom_cham_soc_giao_duc_chau",
        "Quyền của ông bà trông nom, chăm sóc, giáo dục cháu",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_104_Khoan_1"],
    ),
    (
        "quyen_anh_chi_em_thuong_yeu_cham_soc_giup_do_nhau",
        "Quyền của anh, chị, em được thương yêu, chăm sóc, giúp đỡ nhau",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_105"],
    ),
    (
        "quyen_ho_hang_va_chau_thuong_yeu_cham_soc_giup_do_nhau",
        "Quyền của cô, dì, chú, cậu, bác ruột và cháu ruột được thương yêu, chăm sóc, giúp đỡ nhau",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_106"],
    ),
    (
        "nghia_vu_quan_tam_cham_soc_giup_do_ton_trong_lan_nhau",
        "Nghĩa vụ các thành viên gia đình quan tâm, chăm sóc, giúp đỡ, tôn trọng nhau",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_103_Khoan_1"],
    ),
    (
        "nghia_vu_tham_gia_cong_viec_gia_dinh",
        "Nghĩa vụ tham gia công việc gia đình khi sống chung",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_103_Khoan_2"],
    ),
    (
        "nghia_vu_lao_dong_tao_thu_nhap",
        "Nghĩa vụ lao động tạo thu nhập khi sống chung",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_103_Khoan_2"],
    ),
    (
        "nghia_vu_dong_gop_cong_suc",
        "Nghĩa vụ đóng góp công sức để duy trì đời sống chung",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_103_Khoan_2"],
    ),
    (
        "nghia_vu_dong_gop_tien",
        "Nghĩa vụ đóng góp tiền để duy trì đời sống chung",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_103_Khoan_2"],
    ),
    (
        "nghia_vu_dong_gop_tai_san_khac",
        "Nghĩa vụ đóng góp tài sản khác để duy trì đời sống chung",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_103_Khoan_2"],
    ),
    (
        "nghia_vu_ong_ba_trong_nom_cham_soc_giao_duc_chau",
        "Nghĩa vụ của ông bà trông nom, chăm sóc, giáo dục cháu",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_104_Khoan_1"],
    ),
    (
        "nghia_vu_ong_ba_song_mau_muc_neu_guong",
        "Nghĩa vụ của ông bà sống mẫu mực và nêu gương tốt cho con cháu",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_104_Khoan_1"],
    ),
    (
        "nghia_vu_ong_ba_nuoi_duong_chau",
        "Nghĩa vụ của ông bà nội, ông bà ngoại nuôi dưỡng cháu khi đủ điều kiện luật định",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_104_Khoan_1"],
    ),
    (
        "nghia_vu_chau_kinh_trong_cham_soc_phung_duong_ong_ba",
        "Nghĩa vụ của cháu kính trọng, chăm sóc, phụng dưỡng ông bà",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_104_Khoan_2"],
    ),
    (
        "nghia_vu_chau_thanh_nien_nuoi_duong_ong_ba",
        "Nghĩa vụ của cháu đã thành niên nuôi dưỡng ông bà khi ông bà không có con nuôi dưỡng",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_104_Khoan_2"],
    ),
    (
        "nghia_vu_anh_chi_em_thuong_yeu_cham_soc_giup_do_nhau",
        "Nghĩa vụ anh, chị, em thương yêu, chăm sóc, giúp đỡ nhau",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_105"],
    ),
    (
        "nghia_vu_anh_chi_em_nuoi_duong_nhau",
        "Nghĩa vụ anh, chị, em nuôi dưỡng nhau khi đủ điều kiện luật định",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_105"],
    ),
    (
        "nghia_vu_ho_hang_va_chau_thuong_yeu_cham_soc_giup_do_nhau",
        "Nghĩa vụ cô, dì, chú, cậu, bác ruột và cháu ruột thương yêu, chăm sóc, giúp đỡ nhau",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_106"],
    ),
    (
        "nghia_vu_ho_hang_va_chau_nuoi_duong_nhau",
        "Nghĩa vụ cô, dì, chú, cậu, bác ruột và cháu ruột nuôi dưỡng nhau khi đủ điều kiện luật định",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_106"],
    ),
    (
        "cac_thanh_vien_dang_song_chung",
        "Các thành viên gia đình đang sống chung",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_103_Khoan_2"],
    ),
    (
        "dong_gop_phu_hop_kha_nang_thuc_te",
        "Mức đóng góp phù hợp với khả năng thực tế của từng thành viên",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_103_Khoan_2"],
    ),
    (
        "chau_chua_thanh_nien_can_nuoi_duong",
        "Cháu chưa thành niên thuộc nhóm có thể phát sinh nghĩa vụ nuôi dưỡng của ông bà",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_104_Khoan_1"],
    ),
    (
        "chau_thanh_nien_mat_nang_luc_hanh_vi_dan_su_can_nuoi_duong",
        "Cháu đã thành niên mất năng lực hành vi dân sự",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_104_Khoan_1"],
    ),
    (
        "chau_thanh_nien_khong_kha_nang_lao_dong_va_khong_co_tai_san_tu_nuoi",
        "Cháu đã thành niên không có khả năng lao động và không có tài sản để tự nuôi mình",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_104_Khoan_1"],
    ),
    (
        "khong_co_nguoi_nuoi_duong_theo_dieu_105",
        "Không có người nuôi dưỡng cháu theo Điều 105",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_104_Khoan_1", "Luat_HNGD_2014_Dieu_105"],
    ),
    (
        "ong_ba_khong_co_con_de_nuoi_duong",
        "Ông bà không có con để nuôi dưỡng mình",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_104_Khoan_2"],
    ),
    (
        "chau_phai_da_thanh_nien",
        "Cháu phải đã thành niên để phát sinh nghĩa vụ nuôi dưỡng ông bà",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_104_Khoan_2"],
    ),
    (
        "khong_con_cha_me",
        "Không còn cha mẹ",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_105"],
    ),
    (
        "cha_me_khong_co_dieu_kien_trong_nom_nuoi_duong_cham_soc_giao_duc_con",
        "Cha mẹ không có điều kiện trông nom, nuôi dưỡng, chăm sóc, giáo dục con",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_105"],
    ),
    (
        "nguoi_can_nuoi_duong_khong_con_cha_me_con",
        "Người cần nuôi dưỡng không còn cha, mẹ, con",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_106"],
    ),
    (
        "nguoi_thuoc_dieu_104_105_khong_con",
        "Những người thuộc Điều 104 và Điều 105 không còn",
        "DieuKien",
        [
            "Luat_HNGD_2014_Dieu_104",
            "Luat_HNGD_2014_Dieu_105",
            "Luat_HNGD_2014_Dieu_106",
        ],
    ),
    (
        "nguoi_thuoc_dieu_104_105_khong_co_dieu_kien_nuoi_duong",
        "Những người thuộc Điều 104 và Điều 105 còn nhưng không có điều kiện thực hiện nghĩa vụ nuôi dưỡng",
        "DieuKien",
        [
            "Luat_HNGD_2014_Dieu_104",
            "Luat_HNGD_2014_Dieu_105",
            "Luat_HNGD_2014_Dieu_106",
        ],
    ),
    (
        "quy_dinh_chung_quyen_nghia_vu_thanh_vien_gia_dinh",
        "Quy định chung về quyền, nghĩa vụ giữa các thành viên khác của gia đình",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_103"],
    ),
    (
        "nha_nuoc_tao_dieu_kien_cac_the_he_quan_tam_cham_soc_giup_do_nhau",
        "Nhà nước tạo điều kiện để các thế hệ trong gia đình quan tâm, chăm sóc, giúp đỡ nhau",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_103_Khoan_3"],
    ),
    (
        "nha_nuoc_khuyen_khich_xa_hoi_giu_gin_truyen_thong_gia_dinh",
        "Nhà nước khuyến khích cá nhân, tổ chức giữ gìn và phát huy truyền thống tốt đẹp của gia đình Việt Nam",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_103_Khoan_3"],
    ),
    (
        "phan_biet_cham_soc_thuong_xuyen_va_nuoi_duong_co_dieu_kien_ong_ba_chau",
        "Phân biệt nghĩa vụ chăm sóc thường xuyên với nghĩa vụ nuôi dưỡng có điều kiện giữa ông bà và cháu",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_104"],
    ),
    (
        "phan_biet_giup_do_thuong_xuyen_va_nuoi_duong_co_dieu_kien_anh_chi_em",
        "Phân biệt nghĩa vụ thương yêu, chăm sóc, giúp đỡ với nghĩa vụ nuôi dưỡng có điều kiện giữa anh chị em",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_105"],
    ),
    (
        "phan_biet_giup_do_thuong_xuyen_va_nuoi_duong_co_dieu_kien_ho_hang",
        "Phân biệt nghĩa vụ thương yêu, chăm sóc, giúp đỡ với nghĩa vụ nuôi dưỡng có điều kiện theo Điều 106",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_106"],
    ),
    (
        "dieu_104_chi_phat_sinh_khi_khong_co_nguoi_nuoi_duong_theo_dieu_105",
        "Nghĩa vụ ông bà nuôi dưỡng cháu chỉ phát sinh khi không có người nuôi dưỡng theo Điều 105",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_104_Khoan_1", "Luat_HNGD_2014_Dieu_105"],
    ),
    (
        "dieu_106_la_tuyen_nuoi_duong_sau_cha_me_con_va_dieu_104_105",
        "Nghĩa vụ Điều 106 là tuyến sau cha, mẹ, con và những người thuộc Điều 104, Điều 105",
        "QuyDinh",
        [
            "Luat_HNGD_2014_Dieu_104",
            "Luat_HNGD_2014_Dieu_105",
            "Luat_HNGD_2014_Dieu_106",
        ],
    ),
    (
        "phan_biet_dieu_kien_nuoi_duong_ong_ba_chau_va_ho_hang_mo_rong",
        "So sánh điều kiện nuôi dưỡng giữa ông bà-cháu tại Điều 104 và cô, dì, chú, cậu, bác ruột-cháu ruột tại Điều 106",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_104", "Luat_HNGD_2014_Dieu_106"],
    ),
    (
        "phat_sinh_nghia_vu_nuoi_duong_ong_ba_chau",
        "Phát sinh nghĩa vụ nuôi dưỡng giữa ông bà và cháu",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_104"],
    ),
    (
        "phat_sinh_nghia_vu_nuoi_duong_anh_chi_em",
        "Phát sinh nghĩa vụ nuôi dưỡng giữa anh, chị, em",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_105"],
    ),
    (
        "phat_sinh_nghia_vu_nuoi_duong_ho_hang_mo_rong",
        "Phát sinh nghĩa vụ nuôi dưỡng giữa cô, dì, chú, cậu, bác ruột và cháu ruột",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_106"],
    ),
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
    ("QuanHe", "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh", "BAO_GOM", "ChuThe", "thanh_vien_gia_dinh"),
    ("QuanHe", "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh", "CO_QUYEN", "Quyen", "quyen_duoc_quan_tam_cham_soc_giup_do_ton_trong"),
    ("QuanHe", "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh", "CO_QUYEN", "Quyen", "quyen_loi_ich_nhan_than_va_tai_san_duoc_bao_ve"),
    ("QuanHe", "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh", "CO_NGHIA_VU", "NghiaVu", "nghia_vu_quan_tam_cham_soc_giup_do_ton_trong_lan_nhau"),
    ("QuyDinh", "quy_dinh_chung_quyen_nghia_vu_thanh_vien_gia_dinh", "BAO_GOM", "Quyen", "quyen_duoc_quan_tam_cham_soc_giup_do_ton_trong"),
    ("QuyDinh", "quy_dinh_chung_quyen_nghia_vu_thanh_vien_gia_dinh", "BAO_GOM", "Quyen", "quyen_loi_ich_nhan_than_va_tai_san_duoc_bao_ve"),
    ("QuyDinh", "quy_dinh_chung_quyen_nghia_vu_thanh_vien_gia_dinh", "BAO_GOM", "NghiaVu", "nghia_vu_quan_tam_cham_soc_giup_do_ton_trong_lan_nhau"),
    ("ChuThe", "thanh_vien_gia_dinh_song_chung", "THUC_HIEN", "NghiaVu", "nghia_vu_tham_gia_cong_viec_gia_dinh"),
    ("ChuThe", "thanh_vien_gia_dinh_song_chung", "THUC_HIEN", "NghiaVu", "nghia_vu_lao_dong_tao_thu_nhap"),
    ("ChuThe", "thanh_vien_gia_dinh_song_chung", "THUC_HIEN", "NghiaVu", "nghia_vu_dong_gop_cong_suc"),
    ("ChuThe", "thanh_vien_gia_dinh_song_chung", "THUC_HIEN", "NghiaVu", "nghia_vu_dong_gop_tien"),
    ("ChuThe", "thanh_vien_gia_dinh_song_chung", "THUC_HIEN", "NghiaVu", "nghia_vu_dong_gop_tai_san_khac"),
    ("NghiaVu", "nghia_vu_tham_gia_cong_viec_gia_dinh", "PHAT_SINH_KHI", "DieuKien", "cac_thanh_vien_dang_song_chung"),
    ("NghiaVu", "nghia_vu_lao_dong_tao_thu_nhap", "PHAT_SINH_KHI", "DieuKien", "cac_thanh_vien_dang_song_chung"),
    ("NghiaVu", "nghia_vu_dong_gop_cong_suc", "PHAT_SINH_KHI", "DieuKien", "cac_thanh_vien_dang_song_chung"),
    ("NghiaVu", "nghia_vu_dong_gop_tien", "PHAT_SINH_KHI", "DieuKien", "cac_thanh_vien_dang_song_chung"),
    ("NghiaVu", "nghia_vu_dong_gop_tai_san_khac", "PHAT_SINH_KHI", "DieuKien", "cac_thanh_vien_dang_song_chung"),
    ("NghiaVu", "nghia_vu_dong_gop_cong_suc", "PHAT_SINH_KHI", "DieuKien", "dong_gop_phu_hop_kha_nang_thuc_te"),
    ("NghiaVu", "nghia_vu_dong_gop_tien", "PHAT_SINH_KHI", "DieuKien", "dong_gop_phu_hop_kha_nang_thuc_te"),
    ("NghiaVu", "nghia_vu_dong_gop_tai_san_khac", "PHAT_SINH_KHI", "DieuKien", "dong_gop_phu_hop_kha_nang_thuc_te"),
    ("QuanHe", "quan_he_ong_ba_noi_ngoai_va_chau", "BAO_GOM", "ChuThe", "ong_ba_noi_ngoai"),
    ("QuanHe", "quan_he_ong_ba_noi_ngoai_va_chau", "BAO_GOM", "ChuThe", "chau"),
    ("QuanHe", "quan_he_ong_ba_noi_ngoai_va_chau", "CO_QUYEN", "Quyen", "quyen_ong_ba_trong_nom_cham_soc_giao_duc_chau"),
    ("QuanHe", "quan_he_ong_ba_noi_ngoai_va_chau", "CO_NGHIA_VU", "NghiaVu", "nghia_vu_ong_ba_trong_nom_cham_soc_giao_duc_chau"),
    ("QuanHe", "quan_he_ong_ba_noi_ngoai_va_chau", "CO_NGHIA_VU", "NghiaVu", "nghia_vu_ong_ba_song_mau_muc_neu_guong"),
    ("QuanHe", "quan_he_ong_ba_noi_ngoai_va_chau", "CO_NGHIA_VU", "NghiaVu", "nghia_vu_ong_ba_nuoi_duong_chau"),
    ("QuanHe", "quan_he_ong_ba_noi_ngoai_va_chau", "CO_NGHIA_VU", "NghiaVu", "nghia_vu_chau_kinh_trong_cham_soc_phung_duong_ong_ba"),
    ("QuanHe", "quan_he_ong_ba_noi_ngoai_va_chau", "CO_NGHIA_VU", "NghiaVu", "nghia_vu_chau_thanh_nien_nuoi_duong_ong_ba"),
    ("ChuThe", "ong_ba_noi_ngoai", "THUC_HIEN", "NghiaVu", "nghia_vu_ong_ba_nuoi_duong_chau"),
    ("ChuThe", "chau_da_thanh_nien", "THUC_HIEN", "NghiaVu", "nghia_vu_chau_thanh_nien_nuoi_duong_ong_ba"),
    ("NghiaVu", "nghia_vu_ong_ba_nuoi_duong_chau", "PHAT_SINH_KHI", "DieuKien", "chau_chua_thanh_nien_can_nuoi_duong"),
    ("NghiaVu", "nghia_vu_ong_ba_nuoi_duong_chau", "PHAT_SINH_KHI", "DieuKien", "chau_thanh_nien_mat_nang_luc_hanh_vi_dan_su_can_nuoi_duong"),
    ("NghiaVu", "nghia_vu_ong_ba_nuoi_duong_chau", "PHAT_SINH_KHI", "DieuKien", "chau_thanh_nien_khong_kha_nang_lao_dong_va_khong_co_tai_san_tu_nuoi"),
    ("NghiaVu", "nghia_vu_ong_ba_nuoi_duong_chau", "PHAT_SINH_KHI", "DieuKien", "khong_co_nguoi_nuoi_duong_theo_dieu_105"),
    ("NghiaVu", "nghia_vu_chau_thanh_nien_nuoi_duong_ong_ba", "PHAT_SINH_KHI", "DieuKien", "ong_ba_khong_co_con_de_nuoi_duong"),
    ("NghiaVu", "nghia_vu_chau_thanh_nien_nuoi_duong_ong_ba", "PHAT_SINH_KHI", "DieuKien", "chau_phai_da_thanh_nien"),
    ("DieuKien", "khong_co_nguoi_nuoi_duong_theo_dieu_105", "DAN_TOI", "HauQua", "phat_sinh_nghia_vu_nuoi_duong_ong_ba_chau"),
    ("DieuKien", "ong_ba_khong_co_con_de_nuoi_duong", "DAN_TOI", "HauQua", "phat_sinh_nghia_vu_nuoi_duong_ong_ba_chau"),
    ("QuyDinh", "dieu_104_chi_phat_sinh_khi_khong_co_nguoi_nuoi_duong_theo_dieu_105", "DOI_CHIEU_VOI", "DieuKien", "khong_co_nguoi_nuoi_duong_theo_dieu_105"),
    ("QuanHe", "quan_he_anh_chi_em", "BAO_GOM", "ChuThe", "anh_chi_em"),
    ("QuanHe", "quan_he_anh_chi_em", "CO_QUYEN", "Quyen", "quyen_anh_chi_em_thuong_yeu_cham_soc_giup_do_nhau"),
    ("QuanHe", "quan_he_anh_chi_em", "CO_NGHIA_VU", "NghiaVu", "nghia_vu_anh_chi_em_thuong_yeu_cham_soc_giup_do_nhau"),
    ("QuanHe", "quan_he_anh_chi_em", "CO_NGHIA_VU", "NghiaVu", "nghia_vu_anh_chi_em_nuoi_duong_nhau"),
    ("ChuThe", "anh_chi_em", "THUC_HIEN", "NghiaVu", "nghia_vu_anh_chi_em_nuoi_duong_nhau"),
    ("NghiaVu", "nghia_vu_anh_chi_em_nuoi_duong_nhau", "PHAT_SINH_KHI", "DieuKien", "khong_con_cha_me"),
    ("NghiaVu", "nghia_vu_anh_chi_em_nuoi_duong_nhau", "PHAT_SINH_KHI", "DieuKien", "cha_me_khong_co_dieu_kien_trong_nom_nuoi_duong_cham_soc_giao_duc_con"),
    ("DieuKien", "khong_con_cha_me", "DAN_TOI", "HauQua", "phat_sinh_nghia_vu_nuoi_duong_anh_chi_em"),
    ("DieuKien", "cha_me_khong_co_dieu_kien_trong_nom_nuoi_duong_cham_soc_giao_duc_con", "DAN_TOI", "HauQua", "phat_sinh_nghia_vu_nuoi_duong_anh_chi_em"),
    ("QuanHe", "quan_he_co_di_chu_cau_bac_ruot_va_chau_ruot", "BAO_GOM", "ChuThe", "co_di_chu_cau_bac_ruot"),
    ("QuanHe", "quan_he_co_di_chu_cau_bac_ruot_va_chau_ruot", "BAO_GOM", "ChuThe", "chau_ruot"),
    ("QuanHe", "quan_he_co_di_chu_cau_bac_ruot_va_chau_ruot", "CO_QUYEN", "Quyen", "quyen_ho_hang_va_chau_thuong_yeu_cham_soc_giup_do_nhau"),
    ("QuanHe", "quan_he_co_di_chu_cau_bac_ruot_va_chau_ruot", "CO_NGHIA_VU", "NghiaVu", "nghia_vu_ho_hang_va_chau_thuong_yeu_cham_soc_giup_do_nhau"),
    ("QuanHe", "quan_he_co_di_chu_cau_bac_ruot_va_chau_ruot", "CO_NGHIA_VU", "NghiaVu", "nghia_vu_ho_hang_va_chau_nuoi_duong_nhau"),
    ("ChuThe", "co_di_chu_cau_bac_ruot", "THUC_HIEN", "NghiaVu", "nghia_vu_ho_hang_va_chau_nuoi_duong_nhau"),
    ("ChuThe", "chau_ruot", "THUC_HIEN", "NghiaVu", "nghia_vu_ho_hang_va_chau_nuoi_duong_nhau"),
    ("NghiaVu", "nghia_vu_ho_hang_va_chau_nuoi_duong_nhau", "PHAT_SINH_KHI", "DieuKien", "nguoi_can_nuoi_duong_khong_con_cha_me_con"),
    ("NghiaVu", "nghia_vu_ho_hang_va_chau_nuoi_duong_nhau", "PHAT_SINH_KHI", "DieuKien", "nguoi_thuoc_dieu_104_105_khong_con"),
    ("NghiaVu", "nghia_vu_ho_hang_va_chau_nuoi_duong_nhau", "PHAT_SINH_KHI", "DieuKien", "nguoi_thuoc_dieu_104_105_khong_co_dieu_kien_nuoi_duong"),
    ("DieuKien", "nguoi_thuoc_dieu_104_105_khong_con", "DAN_TOI", "HauQua", "phat_sinh_nghia_vu_nuoi_duong_ho_hang_mo_rong"),
    ("DieuKien", "nguoi_thuoc_dieu_104_105_khong_co_dieu_kien_nuoi_duong", "DAN_TOI", "HauQua", "phat_sinh_nghia_vu_nuoi_duong_ho_hang_mo_rong"),
    ("QuyDinh", "dieu_106_la_tuyen_nuoi_duong_sau_cha_me_con_va_dieu_104_105", "DOI_CHIEU_VOI", "DieuKien", "nguoi_can_nuoi_duong_khong_con_cha_me_con"),
    ("QuyDinh", "dieu_106_la_tuyen_nuoi_duong_sau_cha_me_con_va_dieu_104_105", "DOI_CHIEU_VOI", "DieuKien", "nguoi_thuoc_dieu_104_105_khong_con"),
    ("QuyDinh", "dieu_106_la_tuyen_nuoi_duong_sau_cha_me_con_va_dieu_104_105", "DOI_CHIEU_VOI", "DieuKien", "nguoi_thuoc_dieu_104_105_khong_co_dieu_kien_nuoi_duong"),
    ("QuyDinh", "phan_biet_dieu_kien_nuoi_duong_ong_ba_chau_va_ho_hang_mo_rong", "LIEN_QUAN", "NghiaVu", "nghia_vu_ong_ba_nuoi_duong_chau"),
    ("QuyDinh", "phan_biet_dieu_kien_nuoi_duong_ong_ba_chau_va_ho_hang_mo_rong", "LIEN_QUAN", "NghiaVu", "nghia_vu_chau_thanh_nien_nuoi_duong_ong_ba"),
    ("QuyDinh", "phan_biet_dieu_kien_nuoi_duong_ong_ba_chau_va_ho_hang_mo_rong", "LIEN_QUAN", "NghiaVu", "nghia_vu_ho_hang_va_chau_nuoi_duong_nhau"),
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
