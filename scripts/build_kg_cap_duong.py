"""Build KG ngữ nghĩa cho topic 'Cấp dưỡng' (Điều 107-120, Đ82 K2 Luật HN&GĐ 2014).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_cap_duong.py           # MERGE idempotent
    python scripts/build_kg_cap_duong.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_cap_duong.py --dry-run # chỉ in summary

Schema: docs/kg_cap_duong_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "cap_duong"
TOPIC_LABEL = "CapDuong"

SEMANTIC_LABELS = [
    "NghiaVu",
    "Quyen",
    "ChuThe",
    "DieuKien",
    "HauQua",
    "HanhVi",
    "ThoaThuan",
    "QuanHeCapDuong",
    "PhuongThucCapDuong",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("cha_me_cho_con", "Quan hệ cấp dưỡng của cha, mẹ đối với con", "QuanHeCapDuong", ["Luat_HNGD_2014_Dieu_107_Khoan_1", "Luat_HNGD_2014_Dieu_110"]),
    ("con_cho_cha_me", "Quan hệ cấp dưỡng của con đối với cha, mẹ", "QuanHeCapDuong", ["Luat_HNGD_2014_Dieu_107_Khoan_1", "Luat_HNGD_2014_Dieu_111"]),
    ("anh_chi_em_voi_nhau", "Quan hệ cấp dưỡng giữa anh, chị, em", "QuanHeCapDuong", ["Luat_HNGD_2014_Dieu_107_Khoan_1", "Luat_HNGD_2014_Dieu_112"]),
    ("ong_ba_cho_chau", "Quan hệ cấp dưỡng của ông bà đối với cháu", "QuanHeCapDuong", ["Luat_HNGD_2014_Dieu_107_Khoan_1", "Luat_HNGD_2014_Dieu_113_Khoan_1"]),
    ("chau_cho_ong_ba", "Quan hệ cấp dưỡng của cháu đối với ông bà", "QuanHeCapDuong", ["Luat_HNGD_2014_Dieu_107_Khoan_1", "Luat_HNGD_2014_Dieu_113_Khoan_2"]),
    ("co_di_chu_cau_bac_cho_chau_ruot", "Quan hệ cấp dưỡng của cô, dì, chú, cậu, bác ruột đối với cháu ruột", "QuanHeCapDuong", ["Luat_HNGD_2014_Dieu_107_Khoan_1", "Luat_HNGD_2014_Dieu_114_Khoan_1"]),
    ("chau_ruot_cho_co_di_chu_cau_bac", "Quan hệ cấp dưỡng của cháu ruột đối với cô, dì, chú, cậu, bác ruột", "QuanHeCapDuong", ["Luat_HNGD_2014_Dieu_107_Khoan_1", "Luat_HNGD_2014_Dieu_114_Khoan_2"]),
    ("vo_chong_sau_ly_hon", "Quan hệ cấp dưỡng giữa vợ và chồng sau ly hôn", "QuanHeCapDuong", ["Luat_HNGD_2014_Dieu_107_Khoan_1", "Luat_HNGD_2014_Dieu_115"]),
    ("cha_me_khong_truc_tiep_nuoi_con_sau_ly_hon", "Cha, mẹ không trực tiếp nuôi con cấp dưỡng cho con sau ly hôn", "QuanHeCapDuong", ["Luat_HNGD_2014_Dieu_82_Khoan_2", "Luat_HNGD_2014_Dieu_110"]),
    ("nghia_vu_cap_duong", "Nghĩa vụ cấp dưỡng theo Luật Hôn nhân và gia đình", "NghiaVu", ["Luat_HNGD_2014_Dieu_107"]),
    ("nghia_vu_cap_duong_khong_the_thay_the_chuyen_giao", "Nghĩa vụ cấp dưỡng không thể thay thế bằng nghĩa vụ khác và không thể chuyển giao", "NghiaVu", ["Luat_HNGD_2014_Dieu_107_Khoan_1"]),
    ("mot_nguoi_cap_duong_nhieu_nguoi", "Một người có nghĩa vụ cấp dưỡng cho nhiều người", "NghiaVu", ["Luat_HNGD_2014_Dieu_108"]),
    ("nhieu_nguoi_cung_cap_duong", "Nhiều người cùng cấp dưỡng cho một hoặc nhiều người", "NghiaVu", ["Luat_HNGD_2014_Dieu_109"]),
    ("nghia_vu_cha_me_cap_duong_con", "Nghĩa vụ cấp dưỡng của cha, mẹ đối với con", "NghiaVu", ["Luat_HNGD_2014_Dieu_110"]),
    ("nghia_vu_con_cap_duong_cha_me", "Nghĩa vụ cấp dưỡng của con đối với cha, mẹ", "NghiaVu", ["Luat_HNGD_2014_Dieu_111"]),
    ("nghia_vu_cap_duong_giua_anh_chi_em", "Nghĩa vụ cấp dưỡng giữa anh, chị, em", "NghiaVu", ["Luat_HNGD_2014_Dieu_112"]),
    ("nghia_vu_cap_duong_giua_ong_ba_chau", "Nghĩa vụ cấp dưỡng giữa ông bà và cháu", "NghiaVu", ["Luat_HNGD_2014_Dieu_113"]),
    ("nghia_vu_cap_duong_giua_co_di_chu_cau_bac_chau", "Nghĩa vụ cấp dưỡng giữa cô, dì, chú, cậu, bác ruột và cháu ruột", "NghiaVu", ["Luat_HNGD_2014_Dieu_114"]),
    ("nghia_vu_cap_duong_vo_chong_sau_ly_hon", "Nghĩa vụ cấp dưỡng giữa vợ và chồng khi ly hôn", "NghiaVu", ["Luat_HNGD_2014_Dieu_115"]),
    ("nghia_vu_cap_duong_cha_me_khong_truc_tiep_nuoi_con", "Nghĩa vụ cấp dưỡng của cha, mẹ không trực tiếp nuôi con", "NghiaVu", ["Luat_HNGD_2014_Dieu_82_Khoan_2"]),
    ("thuc_hien_nghia_vu_cap_duong", "Thực hiện nghĩa vụ cấp dưỡng", "HanhVi", ["Luat_HNGD_2014_Dieu_107"]),
    ("tron_tranh_nghia_vu_nuoi_duong", "Trốn tránh nghĩa vụ nuôi dưỡng làm phát sinh yêu cầu buộc cấp dưỡng", "HanhVi", ["Luat_HNGD_2014_Dieu_107_Khoan_2"]),
    ("yeu_cau_toa_an_buoc_thuc_hien_cap_duong", "Yêu cầu Tòa án buộc thực hiện nghĩa vụ cấp dưỡng", "HanhVi", ["Luat_HNGD_2014_Dieu_107_Khoan_2", "Luat_HNGD_2014_Dieu_119"]),
    ("thay_doi_muc_cap_duong", "Thay đổi mức cấp dưỡng khi có lý do chính đáng", "HanhVi", ["Luat_HNGD_2014_Dieu_116_Khoan_2"]),
    ("thay_doi_phuong_thuc_cap_duong", "Thay đổi phương thức cấp dưỡng", "HanhVi", ["Luat_HNGD_2014_Dieu_117"]),
    ("tam_ngung_cap_duong", "Tạm ngừng cấp dưỡng do khó khăn kinh tế và không có khả năng thực hiện", "HanhVi", ["Luat_HNGD_2014_Dieu_117"]),
    ("cham_dut_nghia_vu_cap_duong", "Chấm dứt nghĩa vụ cấp dưỡng", "HanhVi", ["Luat_HNGD_2014_Dieu_118"]),
    ("de_nghi_co_quan_to_chuc_yeu_cau_toa_an", "Đề nghị cơ quan, tổ chức có thẩm quyền yêu cầu Tòa án", "HanhVi", ["Luat_HNGD_2014_Dieu_119_Khoan_3"]),
    ("tro_giup_tu_nguyen_cho_nguoi_kho_khan", "Tổ chức, cá nhân trợ giúp tự nguyện bằng tiền hoặc tài sản khác", "HanhVi", ["Luat_HNGD_2014_Dieu_120"]),
    ("thoa_thuan_muc_phuong_thuc_mot_nguoi_nhieu_nguoi", "Thỏa thuận mức và phương thức khi một người cấp dưỡng cho nhiều người", "ThoaThuan", ["Luat_HNGD_2014_Dieu_108"]),
    ("thoa_thuan_muc_dong_gop_nhieu_nguoi", "Thỏa thuận mức đóng góp khi nhiều người cùng cấp dưỡng", "ThoaThuan", ["Luat_HNGD_2014_Dieu_109"]),
    ("thoa_thuan_muc_cap_duong", "Thỏa thuận mức cấp dưỡng", "ThoaThuan", ["Luat_HNGD_2014_Dieu_116_Khoan_1"]),
    ("thoa_thuan_thay_doi_muc_cap_duong", "Thỏa thuận thay đổi mức cấp dưỡng", "ThoaThuan", ["Luat_HNGD_2014_Dieu_116_Khoan_2"]),
    ("thoa_thuan_phuong_thuc_cap_duong", "Thỏa thuận phương thức cấp dưỡng", "ThoaThuan", ["Luat_HNGD_2014_Dieu_117"]),
    ("thoa_thuan_thay_doi_phuong_thuc_cap_duong", "Thỏa thuận thay đổi phương thức cấp dưỡng", "ThoaThuan", ["Luat_HNGD_2014_Dieu_117"]),
    ("thoa_thuan_tam_ngung_cap_duong", "Thỏa thuận tạm ngừng cấp dưỡng", "ThoaThuan", ["Luat_HNGD_2014_Dieu_117"]),
    ("cap_duong_hang_thang", "Cấp dưỡng định kỳ hàng tháng", "PhuongThucCapDuong", ["Luat_HNGD_2014_Dieu_117"]),
    ("cap_duong_hang_quy", "Cấp dưỡng định kỳ hàng quý", "PhuongThucCapDuong", ["Luat_HNGD_2014_Dieu_117"]),
    ("cap_duong_nua_nam", "Cấp dưỡng định kỳ nửa năm", "PhuongThucCapDuong", ["Luat_HNGD_2014_Dieu_117"]),
    ("cap_duong_hang_nam", "Cấp dưỡng định kỳ hàng năm", "PhuongThucCapDuong", ["Luat_HNGD_2014_Dieu_117"]),
    ("cap_duong_mot_lan", "Cấp dưỡng một lần", "PhuongThucCapDuong", ["Luat_HNGD_2014_Dieu_117"]),
    ("con_chua_thanh_nien", "Con chưa thành niên", "DieuKien", ["Luat_HNGD_2014_Dieu_110"]),
    ("con_thanh_nien_khong_kha_nang_lao_dong_khong_tai_san", "Con đã thành niên không có khả năng lao động và không có tài sản để tự nuôi mình", "DieuKien", ["Luat_HNGD_2014_Dieu_110"]),
    ("cha_me_khong_song_chung_voi_con", "Cha, mẹ không sống chung với con", "DieuKien", ["Luat_HNGD_2014_Dieu_110"]),
    ("cha_me_song_chung_nhung_vi_pham_nghia_vu_nuoi_duong", "Cha, mẹ sống chung nhưng vi phạm nghĩa vụ nuôi dưỡng con", "DieuKien", ["Luat_HNGD_2014_Dieu_110"]),
    ("cha_me_khong_kha_nang_lao_dong_khong_tai_san", "Cha, mẹ không có khả năng lao động và không có tài sản để tự nuôi mình", "DieuKien", ["Luat_HNGD_2014_Dieu_111"]),
    ("khong_con_cha_me_hoac_cha_me_khong_the_cap_duong", "Không còn cha mẹ hoặc cha mẹ không có khả năng lao động, không có tài sản để cấp dưỡng", "DieuKien", ["Luat_HNGD_2014_Dieu_112"]),
    ("anh_chi_em_can_cap_duong_khong_tu_nuoi_minh", "Anh, chị, em thuộc trường hợp không thể tự nuôi mình theo Điều 112", "DieuKien", ["Luat_HNGD_2014_Dieu_112"]),
    ("chau_khong_co_nguoi_cap_duong_theo_dieu_112", "Cháu không có người cấp dưỡng theo Điều 112", "DieuKien", ["Luat_HNGD_2014_Dieu_113_Khoan_1"]),
    ("khong_co_nguoi_khac_cap_duong", "Không có người khác cấp dưỡng theo quy định của Luật", "DieuKien", ["Luat_HNGD_2014_Dieu_113_Khoan_2", "Luat_HNGD_2014_Dieu_114"]),
    ("khong_song_chung_voi_nguoi_duoc_cap_duong", "Người có nghĩa vụ không sống chung với người được cấp dưỡng", "DieuKien", ["Luat_HNGD_2014_Dieu_111", "Luat_HNGD_2014_Dieu_112", "Luat_HNGD_2014_Dieu_113", "Luat_HNGD_2014_Dieu_114"]),
    ("ben_sau_ly_hon_kho_khan_tung_thieu", "Bên sau ly hôn khó khăn, túng thiếu", "DieuKien", ["Luat_HNGD_2014_Dieu_115"]),
    ("yeu_cau_cap_duong_co_ly_do_chinh_dang", "Có yêu cầu cấp dưỡng và lý do chính đáng", "DieuKien", ["Luat_HNGD_2014_Dieu_115"]),
    ("thu_nhap_kha_nang_thuc_te_nguoi_cap_duong", "Thu nhập và khả năng thực tế của người có nghĩa vụ cấp dưỡng", "DieuKien", ["Luat_HNGD_2014_Dieu_108", "Luat_HNGD_2014_Dieu_109", "Luat_HNGD_2014_Dieu_116_Khoan_1"]),
    ("nhu_cau_thiet_yeu_nguoi_duoc_cap_duong", "Nhu cầu thiết yếu của người được cấp dưỡng", "DieuKien", ["Luat_HNGD_2014_Dieu_108", "Luat_HNGD_2014_Dieu_109", "Luat_HNGD_2014_Dieu_116_Khoan_1"]),
    ("ly_do_chinh_dang_thay_doi_muc", "Có lý do chính đáng để thay đổi mức cấp dưỡng", "DieuKien", ["Luat_HNGD_2014_Dieu_116_Khoan_2"]),
    ("kho_khan_kinh_te_khong_co_kha_nang_thuc_hien", "Người có nghĩa vụ khó khăn về kinh tế và không có khả năng thực hiện", "DieuKien", ["Luat_HNGD_2014_Dieu_117"]),
    ("quyen_yeu_cau_cua_nguoi_duoc_cap_duong", "Người được cấp dưỡng có quyền yêu cầu Tòa án", "Quyen", ["Luat_HNGD_2014_Dieu_119_Khoan_1"]),
    ("quyen_yeu_cau_cua_cha_me_nguoi_giam_ho", "Cha, mẹ hoặc người giám hộ có quyền yêu cầu Tòa án", "Quyen", ["Luat_HNGD_2014_Dieu_119_Khoan_1"]),
    ("quyen_yeu_cau_cua_nguoi_than_thich", "Người thân thích có quyền yêu cầu Tòa án", "Quyen", ["Luat_HNGD_2014_Dieu_119_Khoan_2_Diem_a"]),
    ("quyen_yeu_cau_cua_co_quan_quan_ly_gia_dinh", "Cơ quan quản lý nhà nước về gia đình có quyền yêu cầu Tòa án", "Quyen", ["Luat_HNGD_2014_Dieu_119_Khoan_2_Diem_b"]),
    ("quyen_yeu_cau_cua_co_quan_quan_ly_tre_em", "Cơ quan quản lý nhà nước về trẻ em có quyền yêu cầu Tòa án", "Quyen", ["Luat_HNGD_2014_Dieu_119_Khoan_2_Diem_c"]),
    ("quyen_yeu_cau_cua_hoi_lien_hiep_phu_nu", "Hội liên hiệp phụ nữ có quyền yêu cầu Tòa án", "Quyen", ["Luat_HNGD_2014_Dieu_119_Khoan_2_Diem_d"]),
    ("quyen_de_nghi_khi_phat_hien_tron_tranh", "Cá nhân, cơ quan, tổ chức khác có quyền đề nghị khi phát hiện trốn tránh", "Quyen", ["Luat_HNGD_2014_Dieu_119_Khoan_3"]),
    ("nguoi_co_nghia_vu_cap_duong", "Người có nghĩa vụ cấp dưỡng", "ChuThe", ["Luat_HNGD_2014_Dieu_107"]),
    ("nguoi_duoc_cap_duong", "Người được cấp dưỡng", "ChuThe", ["Luat_HNGD_2014_Dieu_107", "Luat_HNGD_2014_Dieu_119_Khoan_1"]),
    ("toa_an_giai_quyet_cap_duong", "Tòa án giải quyết yêu cầu về cấp dưỡng", "ChuThe", ["Luat_HNGD_2014_Dieu_107_Khoan_2", "Luat_HNGD_2014_Dieu_108", "Luat_HNGD_2014_Dieu_109", "Luat_HNGD_2014_Dieu_116", "Luat_HNGD_2014_Dieu_117", "Luat_HNGD_2014_Dieu_119"]),
    ("ca_nhan_co_quan_to_chuc_yeu_cau", "Cá nhân, cơ quan, tổ chức có quyền yêu cầu hoặc đề nghị", "ChuThe", ["Luat_HNGD_2014_Dieu_119"]),
    ("toa_an_buoc_thuc_hien_nghia_vu", "Tòa án buộc người trốn tránh hoặc không tự nguyện phải thực hiện nghĩa vụ", "HauQua", ["Luat_HNGD_2014_Dieu_107_Khoan_2", "Luat_HNGD_2014_Dieu_119"]),
    ("toa_an_quyet_dinh_muc_phuong_thuc", "Tòa án giải quyết mức, phương thức hoặc mức đóng góp khi không thỏa thuận được", "HauQua", ["Luat_HNGD_2014_Dieu_108", "Luat_HNGD_2014_Dieu_109", "Luat_HNGD_2014_Dieu_116_Khoan_1", "Luat_HNGD_2014_Dieu_117"]),
    ("muc_cap_duong_duoc_thay_doi", "Mức cấp dưỡng có thể được thay đổi", "HauQua", ["Luat_HNGD_2014_Dieu_116_Khoan_2"]),
    ("tam_ngung_cap_duong_do_kho_khan", "Tạm ngừng cấp dưỡng khi đủ điều kiện khó khăn kinh tế", "HauQua", ["Luat_HNGD_2014_Dieu_117"]),
    ("cham_dut_khi_nguoi_duoc_cap_duong_tu_nuoi_minh", "Chấm dứt khi người được cấp dưỡng đã thành niên và có khả năng lao động hoặc có tài sản tự nuôi mình", "HauQua", ["Luat_HNGD_2014_Dieu_118_Khoan_1"]),
    ("cham_dut_khi_duoc_nhan_lam_con_nuoi", "Chấm dứt khi người được cấp dưỡng được nhận làm con nuôi", "HauQua", ["Luat_HNGD_2014_Dieu_118_Khoan_2"]),
    ("cham_dut_khi_nguoi_cap_duong_truc_tiep_nuoi", "Chấm dứt khi người cấp dưỡng đã trực tiếp nuôi dưỡng người được cấp dưỡng", "HauQua", ["Luat_HNGD_2014_Dieu_118_Khoan_3"]),
    ("cham_dut_khi_mot_ben_chet", "Chấm dứt khi người cấp dưỡng hoặc người được cấp dưỡng chết", "HauQua", ["Luat_HNGD_2014_Dieu_118_Khoan_4"]),
    ("cham_dut_khi_ben_duoc_cap_duong_tai_hon", "Chấm dứt khi bên được cấp dưỡng sau ly hôn đã kết hôn", "HauQua", ["Luat_HNGD_2014_Dieu_118_Khoan_5"]),
    ("cham_dut_theo_truong_hop_khac_cua_luat", "Chấm dứt trong trường hợp khác theo quy định của luật", "HauQua", ["Luat_HNGD_2014_Dieu_118_Khoan_6"]),
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
    ("QuanHeCapDuong", "cha_me_cho_con", "QUY_DINH_NGHIA_VU", "NghiaVu", "nghia_vu_cha_me_cap_duong_con", {}),
    ("QuanHeCapDuong", "con_cho_cha_me", "QUY_DINH_NGHIA_VU", "NghiaVu", "nghia_vu_con_cap_duong_cha_me", {}),
    ("QuanHeCapDuong", "anh_chi_em_voi_nhau", "QUY_DINH_NGHIA_VU", "NghiaVu", "nghia_vu_cap_duong_giua_anh_chi_em", {}),
    ("QuanHeCapDuong", "ong_ba_cho_chau", "QUY_DINH_NGHIA_VU", "NghiaVu", "nghia_vu_cap_duong_giua_ong_ba_chau", {}),
    ("QuanHeCapDuong", "chau_cho_ong_ba", "QUY_DINH_NGHIA_VU", "NghiaVu", "nghia_vu_cap_duong_giua_ong_ba_chau", {}),
    ("QuanHeCapDuong", "co_di_chu_cau_bac_cho_chau_ruot", "QUY_DINH_NGHIA_VU", "NghiaVu", "nghia_vu_cap_duong_giua_co_di_chu_cau_bac_chau", {}),
    ("QuanHeCapDuong", "chau_ruot_cho_co_di_chu_cau_bac", "QUY_DINH_NGHIA_VU", "NghiaVu", "nghia_vu_cap_duong_giua_co_di_chu_cau_bac_chau", {}),
    ("QuanHeCapDuong", "vo_chong_sau_ly_hon", "QUY_DINH_NGHIA_VU", "NghiaVu", "nghia_vu_cap_duong_vo_chong_sau_ly_hon", {}),
    ("QuanHeCapDuong", "cha_me_khong_truc_tiep_nuoi_con_sau_ly_hon", "QUY_DINH_NGHIA_VU", "NghiaVu", "nghia_vu_cap_duong_cha_me_khong_truc_tiep_nuoi_con", {}),
    ("NghiaVu", "nghia_vu_cha_me_cap_duong_con", "AP_DUNG_KHI", "DieuKien", "con_chua_thanh_nien", {}),
    ("NghiaVu", "nghia_vu_cha_me_cap_duong_con", "AP_DUNG_KHI", "DieuKien", "con_thanh_nien_khong_kha_nang_lao_dong_khong_tai_san", {}),
    ("NghiaVu", "nghia_vu_cha_me_cap_duong_con", "AP_DUNG_KHI", "DieuKien", "cha_me_khong_song_chung_voi_con", {}),
    ("NghiaVu", "nghia_vu_cha_me_cap_duong_con", "AP_DUNG_KHI", "DieuKien", "cha_me_song_chung_nhung_vi_pham_nghia_vu_nuoi_duong", {}),
    ("NghiaVu", "nghia_vu_con_cap_duong_cha_me", "AP_DUNG_KHI", "DieuKien", "cha_me_khong_kha_nang_lao_dong_khong_tai_san", {}),
    ("NghiaVu", "nghia_vu_cap_duong_giua_anh_chi_em", "AP_DUNG_KHI", "DieuKien", "khong_con_cha_me_hoac_cha_me_khong_the_cap_duong", {}),
    ("NghiaVu", "nghia_vu_cap_duong_giua_anh_chi_em", "AP_DUNG_KHI", "DieuKien", "anh_chi_em_can_cap_duong_khong_tu_nuoi_minh", {}),
    ("NghiaVu", "nghia_vu_cap_duong_giua_ong_ba_chau", "AP_DUNG_KHI", "DieuKien", "chau_khong_co_nguoi_cap_duong_theo_dieu_112", {}),
    ("NghiaVu", "nghia_vu_cap_duong_giua_ong_ba_chau", "AP_DUNG_KHI", "DieuKien", "khong_co_nguoi_khac_cap_duong", {}),
    ("NghiaVu", "nghia_vu_cap_duong_giua_co_di_chu_cau_bac_chau", "AP_DUNG_KHI", "DieuKien", "khong_co_nguoi_khac_cap_duong", {}),
    ("NghiaVu", "nghia_vu_cap_duong_vo_chong_sau_ly_hon", "AP_DUNG_KHI", "DieuKien", "ben_sau_ly_hon_kho_khan_tung_thieu", {}),
    ("NghiaVu", "nghia_vu_cap_duong_vo_chong_sau_ly_hon", "AP_DUNG_KHI", "DieuKien", "yeu_cau_cap_duong_co_ly_do_chinh_dang", {}),
    ("NghiaVu", "nghia_vu_cap_duong", "THUC_HIEN_BANG", "PhuongThucCapDuong", "cap_duong_hang_thang", {}),
    ("NghiaVu", "nghia_vu_cap_duong", "THUC_HIEN_BANG", "PhuongThucCapDuong", "cap_duong_hang_quy", {}),
    ("NghiaVu", "nghia_vu_cap_duong", "THUC_HIEN_BANG", "PhuongThucCapDuong", "cap_duong_nua_nam", {}),
    ("NghiaVu", "nghia_vu_cap_duong", "THUC_HIEN_BANG", "PhuongThucCapDuong", "cap_duong_hang_nam", {}),
    ("NghiaVu", "nghia_vu_cap_duong", "THUC_HIEN_BANG", "PhuongThucCapDuong", "cap_duong_mot_lan", {}),
    ("ThoaThuan", "thoa_thuan_muc_cap_duong", "DIEU_CHINH", "NghiaVu", "nghia_vu_cap_duong", {}),
    ("ThoaThuan", "thoa_thuan_thay_doi_muc_cap_duong", "DIEU_CHINH", "HanhVi", "thay_doi_muc_cap_duong", {}),
    ("ThoaThuan", "thoa_thuan_phuong_thuc_cap_duong", "DIEU_CHINH", "NghiaVu", "nghia_vu_cap_duong", {}),
    ("ThoaThuan", "thoa_thuan_thay_doi_phuong_thuc_cap_duong", "DIEU_CHINH", "HanhVi", "thay_doi_phuong_thuc_cap_duong", {}),
    ("ThoaThuan", "thoa_thuan_tam_ngung_cap_duong", "DIEU_CHINH", "HanhVi", "tam_ngung_cap_duong", {}),
    ("HanhVi", "thay_doi_muc_cap_duong", "AP_DUNG_KHI", "DieuKien", "ly_do_chinh_dang_thay_doi_muc", {}),
    ("HanhVi", "tam_ngung_cap_duong", "AP_DUNG_KHI", "DieuKien", "kho_khan_kinh_te_khong_co_kha_nang_thuc_hien", {}),
    ("HanhVi", "tron_tranh_nghia_vu_nuoi_duong", "DAN_TOI", "HauQua", "toa_an_buoc_thuc_hien_nghia_vu", {}),
    ("HanhVi", "yeu_cau_toa_an_buoc_thuc_hien_cap_duong", "DAN_TOI", "HauQua", "toa_an_buoc_thuc_hien_nghia_vu", {}),
    ("HanhVi", "cham_dut_nghia_vu_cap_duong", "DAN_TOI", "HauQua", "cham_dut_khi_nguoi_duoc_cap_duong_tu_nuoi_minh", {}),
    ("HanhVi", "cham_dut_nghia_vu_cap_duong", "DAN_TOI", "HauQua", "cham_dut_khi_duoc_nhan_lam_con_nuoi", {}),
    ("HanhVi", "cham_dut_nghia_vu_cap_duong", "DAN_TOI", "HauQua", "cham_dut_khi_nguoi_cap_duong_truc_tiep_nuoi", {}),
    ("HanhVi", "cham_dut_nghia_vu_cap_duong", "DAN_TOI", "HauQua", "cham_dut_khi_mot_ben_chet", {}),
    ("HanhVi", "cham_dut_nghia_vu_cap_duong", "DAN_TOI", "HauQua", "cham_dut_khi_ben_duoc_cap_duong_tai_hon", {}),
    ("HanhVi", "cham_dut_nghia_vu_cap_duong", "DAN_TOI", "HauQua", "cham_dut_theo_truong_hop_khac_cua_luat", {}),
    ("ChuThe", "nguoi_duoc_cap_duong", "CO_QUYEN", "Quyen", "quyen_yeu_cau_cua_nguoi_duoc_cap_duong", {}),
    ("ChuThe", "ca_nhan_co_quan_to_chuc_yeu_cau", "CO_QUYEN", "Quyen", "quyen_yeu_cau_cua_cha_me_nguoi_giam_ho", {}),
    ("ChuThe", "ca_nhan_co_quan_to_chuc_yeu_cau", "CO_QUYEN", "Quyen", "quyen_yeu_cau_cua_nguoi_than_thich", {}),
    ("ChuThe", "ca_nhan_co_quan_to_chuc_yeu_cau", "CO_QUYEN", "Quyen", "quyen_yeu_cau_cua_co_quan_quan_ly_gia_dinh", {}),
    ("ChuThe", "ca_nhan_co_quan_to_chuc_yeu_cau", "CO_QUYEN", "Quyen", "quyen_yeu_cau_cua_co_quan_quan_ly_tre_em", {}),
    ("ChuThe", "ca_nhan_co_quan_to_chuc_yeu_cau", "CO_QUYEN", "Quyen", "quyen_yeu_cau_cua_hoi_lien_hiep_phu_nu", {}),
    ("ChuThe", "ca_nhan_co_quan_to_chuc_yeu_cau", "CO_QUYEN", "Quyen", "quyen_de_nghi_khi_phat_hien_tron_tranh", {}),
    ("Quyen", "quyen_yeu_cau_cua_nguoi_duoc_cap_duong", "THUC_HIEN", "HanhVi", "yeu_cau_toa_an_buoc_thuc_hien_cap_duong", {}),
    ("Quyen", "quyen_yeu_cau_cua_cha_me_nguoi_giam_ho", "THUC_HIEN", "HanhVi", "yeu_cau_toa_an_buoc_thuc_hien_cap_duong", {}),
    ("Quyen", "quyen_yeu_cau_cua_nguoi_than_thich", "THUC_HIEN", "HanhVi", "yeu_cau_toa_an_buoc_thuc_hien_cap_duong", {}),
    ("Quyen", "quyen_de_nghi_khi_phat_hien_tron_tranh", "THUC_HIEN", "HanhVi", "de_nghi_co_quan_to_chuc_yeu_cau_toa_an", {}),
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
