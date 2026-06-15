"""Build KG ngữ nghĩa cho topic 'Tài sản riêng của con' (tai_san_rieng_cua_con).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_tai_san_rieng_cua_con.py           # MERGE idempotent
    python scripts/build_kg_tai_san_rieng_cua_con.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_tai_san_rieng_cua_con.py --dry-run # chỉ in summary

Schema: docs/kg_tai_san_rieng_cua_con_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "tai_san_rieng_cua_con"
TOPIC_LABEL = "TaiSanRiengCuaCon"

SEMANTIC_LABELS = [
    "ChuThe",
    "QuyDinh",
    "Quyen",
    "NghiaVu",
    "HanhVi",
    "LoaiTaiSan",
    "NguonGocTaiSan",
    "DieuKien",
    "HauQua",
    "ThoaThuan",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("quy_dinh_quyen_tai_san_rieng_cua_con", "Quy định về quyền có tài sản riêng và nghĩa vụ đóng góp của con", "QuyDinh", ["Luat_HNGD_2014_Dieu_75"]),
    ("quy_dinh_quan_ly_tai_san_rieng_cua_con", "Quy định về quản lý tài sản riêng của con", "QuyDinh", ["Luat_HNGD_2014_Dieu_76"]),
    ("quy_dinh_dinh_doat_tai_san_rieng_cua_con", "Quy định về định đoạt tài sản riêng của con chưa thành niên hoặc đã thành niên mất năng lực hành vi dân sự", "QuyDinh", ["Luat_HNGD_2014_Dieu_77"]),
    ("cac_thanh_phan_tai_san_rieng_cua_con", "Nhóm các loại tài sản được xác định là tài sản riêng của con", "QuyDinh", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("con", "Người con có tài sản riêng", "ChuThe", ["Luat_HNGD_2014_Dieu_75", "Luat_HNGD_2014_Dieu_76", "Luat_HNGD_2014_Dieu_77"]),
    ("cha_me", "Cha mẹ của người con", "ChuThe", ["Luat_HNGD_2014_Dieu_76", "Luat_HNGD_2014_Dieu_77"]),
    ("nguoi_giam_ho", "Người giám hộ của con theo quy định pháp luật", "ChuThe", ["Luat_HNGD_2014_Dieu_76_Khoan_3", "Luat_HNGD_2014_Dieu_76_Khoan_4", "Luat_HNGD_2014_Dieu_77_Khoan_1", "Luat_HNGD_2014_Dieu_77_Khoan_2", "Luat_HNGD_2014_Dieu_77_Khoan_3"]),
    ("nguoi_duoc_uy_quyen_quan_ly", "Người được cha mẹ ủy quyền quản lý tài sản riêng của con", "ChuThe", ["Luat_HNGD_2014_Dieu_76_Khoan_2"]),
    ("nguoi_duoc_chi_dinh_quan_ly", "Người được người tặng cho hoặc người để lại di chúc chỉ định quản lý tài sản", "ChuThe", ["Luat_HNGD_2014_Dieu_76_Khoan_3"]),
    ("gia_dinh", "Gia đình nơi người con có nghĩa vụ chăm lo hoặc đóng góp", "ChuThe", ["Luat_HNGD_2014_Dieu_75_Khoan_2", "Luat_HNGD_2014_Dieu_75_Khoan_3"]),
    ("tai_san_rieng_cua_con", "Toàn bộ tài sản riêng thuộc quyền của con", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("tai_san_thua_ke_rieng", "Tài sản con được thừa kế riêng", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("tai_san_tang_cho_rieng", "Tài sản con được tặng cho riêng", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("thu_nhap_lao_dong", "Thu nhập do lao động của con", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("hoa_loi_loi_tuc", "Hoa lợi, lợi tức phát sinh từ tài sản riêng của con", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("thu_nhap_hop_phap_khac", "Thu nhập hợp pháp khác của con", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("tai_san_hinh_thanh_tu_tai_san_rieng", "Tài sản được hình thành từ tài sản riêng của con", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("bat_dong_san", "Bất động sản thuộc tài sản riêng của con", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_77_Khoan_2"]),
    ("dong_san_phai_dang_ky", "Động sản có đăng ký quyền sở hữu hoặc quyền sử dụng", "LoaiTaiSan", ["Luat_HNGD_2014_Dieu_77_Khoan_2"]),
    ("thua_ke_rieng", "Nguồn tài sản từ thừa kế riêng", "NguonGocTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("tang_cho_rieng", "Nguồn tài sản từ tặng cho riêng", "NguonGocTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("lao_dong_cua_con", "Nguồn thu nhập do lao động của con", "NguonGocTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("phat_sinh_tu_tai_san_rieng", "Nguồn hoa lợi, lợi tức phát sinh từ tài sản riêng", "NguonGocTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("nguon_thu_nhap_hop_phap_khac", "Nguồn thu nhập hợp pháp khác", "NguonGocTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("hinh_thanh_tu_tai_san_rieng", "Nguồn tài sản được hình thành từ tài sản riêng", "NguonGocTaiSan", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("quyen_co_tai_san_rieng", "Con có quyền có tài sản riêng", "Quyen", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("quyen_tu_quan_ly_tai_san_tu_du_15_tuoi", "Con từ đủ 15 tuổi có thể tự quản lý tài sản riêng", "Quyen", ["Luat_HNGD_2014_Dieu_76_Khoan_1"]),
    ("quyen_nho_cha_me_quan_ly_tai_san", "Con từ đủ 15 tuổi có thể nhờ cha mẹ quản lý tài sản riêng", "Quyen", ["Luat_HNGD_2014_Dieu_76_Khoan_1"]),
    ("quyen_dinh_doat_tai_san_con_duoi_15_cua_nguoi_quan_ly", "Cha mẹ hoặc người giám hộ đang quản lý có quyền định đoạt tài sản của con dưới 15 tuổi vì lợi ích của con", "Quyen", ["Luat_HNGD_2014_Dieu_77_Khoan_1"]),
    ("quyen_dinh_doat_tai_san_con_tu_du_15_den_duoi_18", "Con từ đủ 15 tuổi đến dưới 18 tuổi có quyền định đoạt tài sản riêng", "Quyen", ["Luat_HNGD_2014_Dieu_77_Khoan_2"]),
    ("quyen_dinh_doat_tai_san_con_thanh_nien_mat_nang_luc_cua_nguoi_giam_ho", "Người giám hộ thực hiện việc định đoạt tài sản của con đã thành niên mất năng lực hành vi dân sự", "Quyen", ["Luat_HNGD_2014_Dieu_77_Khoan_3"]),
    ("quyen_duoc_xem_xet_nguyen_vong_khi_dinh_doat_tai_san", "Con từ đủ 09 tuổi được xem xét nguyện vọng khi tài sản riêng bị định đoạt", "Quyen", ["Luat_HNGD_2014_Dieu_77_Khoan_1"]),
    ("nghia_vu_cham_lo_doi_song_chung_cua_gia_dinh", "Con từ đủ 15 tuổi sống chung với cha mẹ phải chăm lo đời sống chung của gia đình", "NghiaVu", ["Luat_HNGD_2014_Dieu_75_Khoan_2"]),
    ("nghia_vu_dong_gop_nhu_cau_thiet_yeu_khi_co_thu_nhap", "Con từ đủ 15 tuổi sống chung với cha mẹ phải đóng góp đáp ứng nhu cầu thiết yếu nếu có thu nhập", "NghiaVu", ["Luat_HNGD_2014_Dieu_75_Khoan_2"]),
    ("nghia_vu_dong_gop_thu_nhap_cua_con_thanh_nien", "Con đã thành niên có nghĩa vụ đóng góp thu nhập vào nhu cầu của gia đình", "NghiaVu", ["Luat_HNGD_2014_Dieu_75_Khoan_3"]),
    ("nghia_vu_xem_xet_nguyen_vong_con_tu_du_09_tuoi", "Người định đoạt phải xem xét nguyện vọng của con từ đủ 09 tuổi", "NghiaVu", ["Luat_HNGD_2014_Dieu_77_Khoan_1"]),
    ("nghia_vu_lay_dong_y_bang_van_ban", "Việc định đoạt tài sản thuộc nhóm ngoại lệ phải có sự đồng ý bằng văn bản của cha mẹ hoặc người giám hộ", "NghiaVu", ["Luat_HNGD_2014_Dieu_77_Khoan_2"]),
    ("quan_ly_tai_san_rieng_cua_con", "Hoạt động quản lý tài sản riêng của con", "HanhVi", ["Luat_HNGD_2014_Dieu_76"]),
    ("cha_me_quan_ly_tai_san_con_duoi_15", "Cha mẹ quản lý tài sản riêng của con dưới 15 tuổi", "HanhVi", ["Luat_HNGD_2014_Dieu_76_Khoan_2"]),
    ("cha_me_quan_ly_tai_san_con_mat_nang_luc", "Cha mẹ quản lý tài sản riêng của con mất năng lực hành vi dân sự", "HanhVi", ["Luat_HNGD_2014_Dieu_76_Khoan_2"]),
    ("uy_quyen_nguoi_khac_quan_ly_tai_san", "Cha mẹ ủy quyền cho người khác quản lý tài sản riêng của con", "HanhVi", ["Luat_HNGD_2014_Dieu_76_Khoan_2"]),
    ("giao_lai_tai_san_cho_con", "Giao lại tài sản cho con khi đủ tuổi hoặc khôi phục năng lực hành vi dân sự đầy đủ", "HanhVi", ["Luat_HNGD_2014_Dieu_76_Khoan_2"]),
    ("cha_me_khong_quan_ly_tai_san_cua_con", "Cha mẹ không quản lý tài sản trong các trường hợp khoản 3 Điều 76", "HanhVi", ["Luat_HNGD_2014_Dieu_76_Khoan_3"]),
    ("chi_dinh_nguoi_khac_quan_ly_tai_san", "Người tặng cho hoặc người để lại di chúc chỉ định người khác quản lý tài sản", "HanhVi", ["Luat_HNGD_2014_Dieu_76_Khoan_3"]),
    ("giao_tai_san_cho_nguoi_giam_ho_quan_ly", "Giao tài sản đang do cha mẹ quản lý cho người giám hộ quản lý", "HanhVi", ["Luat_HNGD_2014_Dieu_76_Khoan_4"]),
    ("dinh_doat_tai_san_rieng_cua_con", "Hoạt động định đoạt tài sản riêng của con", "HanhVi", ["Luat_HNGD_2014_Dieu_77"]),
    ("dinh_doat_tai_san_con_duoi_15", "Định đoạt tài sản riêng của con dưới 15 tuổi", "HanhVi", ["Luat_HNGD_2014_Dieu_77_Khoan_1"]),
    ("xem_xet_nguyen_vong_cua_con", "Xem xét nguyện vọng của con từ đủ 09 tuổi khi định đoạt tài sản", "HanhVi", ["Luat_HNGD_2014_Dieu_77_Khoan_1"]),
    ("dinh_doat_tai_san_con_tu_du_15_den_duoi_18", "Con từ đủ 15 tuổi đến dưới 18 tuổi định đoạt tài sản riêng", "HanhVi", ["Luat_HNGD_2014_Dieu_77_Khoan_2"]),
    ("dung_tai_san_de_kinh_doanh", "Dùng tài sản riêng của con từ đủ 15 tuổi đến dưới 18 tuổi để kinh doanh", "HanhVi", ["Luat_HNGD_2014_Dieu_77_Khoan_2"]),
    ("dinh_doat_tai_san_con_thanh_nien_mat_nang_luc", "Định đoạt tài sản của con đã thành niên mất năng lực hành vi dân sự", "HanhVi", ["Luat_HNGD_2014_Dieu_77_Khoan_3"]),
    ("con_tu_du_15_tuoi", "Con từ đủ 15 tuổi trở lên", "DieuKien", ["Luat_HNGD_2014_Dieu_75_Khoan_2", "Luat_HNGD_2014_Dieu_76_Khoan_1", "Luat_HNGD_2014_Dieu_76_Khoan_2"]),
    ("con_duoi_15_tuoi", "Con chưa đủ 15 tuổi", "DieuKien", ["Luat_HNGD_2014_Dieu_76_Khoan_2", "Luat_HNGD_2014_Dieu_77_Khoan_1"]),
    ("con_tu_du_09_tuoi", "Con từ đủ 09 tuổi trở lên", "DieuKien", ["Luat_HNGD_2014_Dieu_77_Khoan_1"]),
    ("con_tu_du_15_den_duoi_18_tuoi", "Con từ đủ 15 tuổi đến dưới 18 tuổi", "DieuKien", ["Luat_HNGD_2014_Dieu_77_Khoan_2"]),
    ("con_da_thanh_nien", "Con đã thành niên", "DieuKien", ["Luat_HNGD_2014_Dieu_75_Khoan_3"]),
    ("con_song_chung_voi_cha_me", "Con sống chung với cha mẹ", "DieuKien", ["Luat_HNGD_2014_Dieu_75_Khoan_2"]),
    ("con_co_thu_nhap", "Con có thu nhập để đóng góp cho nhu cầu gia đình", "DieuKien", ["Luat_HNGD_2014_Dieu_75_Khoan_2"]),
    ("con_mat_nang_luc_hanh_vi_dan_su", "Con mất năng lực hành vi dân sự", "DieuKien", ["Luat_HNGD_2014_Dieu_76_Khoan_2", "Luat_HNGD_2014_Dieu_76_Khoan_4", "Luat_HNGD_2014_Dieu_77_Khoan_3"]),
    ("con_khoi_phuc_nang_luc_hanh_vi_dan_su_day_du", "Con khôi phục năng lực hành vi dân sự đầy đủ", "DieuKien", ["Luat_HNGD_2014_Dieu_76_Khoan_2"]),
    ("con_dang_duoc_nguoi_khac_giam_ho", "Con đang được người khác giám hộ theo Bộ luật dân sự", "DieuKien", ["Luat_HNGD_2014_Dieu_76_Khoan_3"]),
    ("nguoi_tang_cho_hoac_de_lai_di_chuc_chi_dinh_nguoi_quan_ly", "Người tặng cho hoặc người để lại di chúc đã chỉ định người khác quản lý tài sản", "DieuKien", ["Luat_HNGD_2014_Dieu_76_Khoan_3"]),
    ("cha_me_dang_quan_ly_khi_con_chuyen_sang_nguoi_giam_ho", "Cha mẹ đang quản lý tài sản và con được giao cho người khác giám hộ", "DieuKien", ["Luat_HNGD_2014_Dieu_76_Khoan_4"]),
    ("quan_ly_vi_loi_ich_cua_con", "Việc định đoạt được thực hiện vì lợi ích của con", "DieuKien", ["Luat_HNGD_2014_Dieu_77_Khoan_1"]),
    ("tai_san_la_bat_dong_san", "Tài sản định đoạt là bất động sản", "DieuKien", ["Luat_HNGD_2014_Dieu_77_Khoan_2"]),
    ("tai_san_la_dong_san_phai_dang_ky", "Tài sản định đoạt là động sản có đăng ký quyền sở hữu hoặc quyền sử dụng", "DieuKien", ["Luat_HNGD_2014_Dieu_77_Khoan_2"]),
    ("giao_dich_dung_tai_san_de_kinh_doanh", "Tài sản được dùng để kinh doanh", "DieuKien", ["Luat_HNGD_2014_Dieu_77_Khoan_2"]),
    ("thoa_thuan_khac_ve_thoi_diem_giao_lai_tai_san", "Thỏa thuận khác giữa cha mẹ và con về việc giao lại tài sản", "ThoaThuan", ["Luat_HNGD_2014_Dieu_76_Khoan_2"]),
    ("dong_y_bang_van_ban_cua_cha_me_hoac_nguoi_giam_ho", "Sự đồng ý bằng văn bản của cha mẹ hoặc người giám hộ", "ThoaThuan", ["Luat_HNGD_2014_Dieu_77_Khoan_2"]),
    ("tai_san_duoc_xac_dinh_la_tai_san_rieng_cua_con", "Tài sản thuộc tài sản riêng của con", "HauQua", ["Luat_HNGD_2014_Dieu_75_Khoan_1"]),
    ("cha_me_hoac_nguoi_duoc_uy_quyen_quan_ly", "Tài sản do cha mẹ hoặc người được ủy quyền quản lý", "HauQua", ["Luat_HNGD_2014_Dieu_76_Khoan_2"]),
    ("giao_lai_tai_san_khi_con_du_tuoi_hoac_khoi_phuc_nang_luc", "Tài sản được giao lại khi con từ đủ 15 tuổi hoặc khôi phục năng lực hành vi dân sự đầy đủ, trừ thỏa thuận khác", "HauQua", ["Luat_HNGD_2014_Dieu_76_Khoan_2"]),
    ("nguoi_khac_thay_cha_me_quan_ly", "Người giám hộ hoặc người được chỉ định quản lý thay cha mẹ", "HauQua", ["Luat_HNGD_2014_Dieu_76_Khoan_3"]),
    ("nguoi_giam_ho_tiep_nhan_quan_ly_tai_san", "Người giám hộ tiếp nhận quản lý tài sản từ cha mẹ", "HauQua", ["Luat_HNGD_2014_Dieu_76_Khoan_4"]),
    ("phai_xem_xet_nguyen_vong_cua_con", "Phải xem xét nguyện vọng của con từ đủ 09 tuổi", "HauQua", ["Luat_HNGD_2014_Dieu_77_Khoan_1"]),
    ("phai_co_dong_y_bang_van_ban", "Phải có sự đồng ý bằng văn bản của cha mẹ hoặc người giám hộ", "HauQua", ["Luat_HNGD_2014_Dieu_77_Khoan_2"]),
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
    ("`QuyDinh`", "quy_dinh_quyen_tai_san_rieng_cua_con", "`BAO_GOM`", "`Quyen`", "quyen_co_tai_san_rieng"),
    ("`QuyDinh`", "quy_dinh_quyen_tai_san_rieng_cua_con", "`BAO_GOM`", "`QuyDinh`", "cac_thanh_phan_tai_san_rieng_cua_con"),
    ("`QuyDinh`", "quy_dinh_quyen_tai_san_rieng_cua_con", "`BAO_GOM`", "`NghiaVu`", "nghia_vu_cham_lo_doi_song_chung_cua_gia_dinh"),
    ("`QuyDinh`", "quy_dinh_quyen_tai_san_rieng_cua_con", "`BAO_GOM`", "`NghiaVu`", "nghia_vu_dong_gop_nhu_cau_thiet_yeu_khi_co_thu_nhap"),
    ("`QuyDinh`", "quy_dinh_quyen_tai_san_rieng_cua_con", "`BAO_GOM`", "`NghiaVu`", "nghia_vu_dong_gop_thu_nhap_cua_con_thanh_nien"),
    ("`QuyDinh`", "cac_thanh_phan_tai_san_rieng_cua_con", "`BAO_GOM`", "`LoaiTaiSan`", "tai_san_thua_ke_rieng"),
    ("`QuyDinh`", "cac_thanh_phan_tai_san_rieng_cua_con", "`BAO_GOM`", "`LoaiTaiSan`", "tai_san_tang_cho_rieng"),
    ("`QuyDinh`", "cac_thanh_phan_tai_san_rieng_cua_con", "`BAO_GOM`", "`LoaiTaiSan`", "thu_nhap_lao_dong"),
    ("`QuyDinh`", "cac_thanh_phan_tai_san_rieng_cua_con", "`BAO_GOM`", "`LoaiTaiSan`", "hoa_loi_loi_tuc"),
    ("`QuyDinh`", "cac_thanh_phan_tai_san_rieng_cua_con", "`BAO_GOM`", "`LoaiTaiSan`", "thu_nhap_hop_phap_khac"),
    ("`QuyDinh`", "cac_thanh_phan_tai_san_rieng_cua_con", "`BAO_GOM`", "`LoaiTaiSan`", "tai_san_hinh_thanh_tu_tai_san_rieng"),
    ("`LoaiTaiSan`", "tai_san_thua_ke_rieng", "`LA_LOAI_CON_CUA`", "`LoaiTaiSan`", "tai_san_rieng_cua_con"),
    ("`LoaiTaiSan`", "tai_san_tang_cho_rieng", "`LA_LOAI_CON_CUA`", "`LoaiTaiSan`", "tai_san_rieng_cua_con"),
    ("`LoaiTaiSan`", "thu_nhap_lao_dong", "`LA_LOAI_CON_CUA`", "`LoaiTaiSan`", "tai_san_rieng_cua_con"),
    ("`LoaiTaiSan`", "hoa_loi_loi_tuc", "`LA_LOAI_CON_CUA`", "`LoaiTaiSan`", "tai_san_rieng_cua_con"),
    ("`LoaiTaiSan`", "thu_nhap_hop_phap_khac", "`LA_LOAI_CON_CUA`", "`LoaiTaiSan`", "tai_san_rieng_cua_con"),
    ("`LoaiTaiSan`", "tai_san_hinh_thanh_tu_tai_san_rieng", "`LA_LOAI_CON_CUA`", "`LoaiTaiSan`", "tai_san_rieng_cua_con"),
    ("`LoaiTaiSan`", "bat_dong_san", "`LA_LOAI_CON_CUA`", "`LoaiTaiSan`", "tai_san_rieng_cua_con"),
    ("`LoaiTaiSan`", "dong_san_phai_dang_ky", "`LA_LOAI_CON_CUA`", "`LoaiTaiSan`", "tai_san_rieng_cua_con"),
    ("`LoaiTaiSan`", "tai_san_thua_ke_rieng", "`CO_NGUON_GOC`", "`NguonGocTaiSan`", "thua_ke_rieng"),
    ("`LoaiTaiSan`", "tai_san_tang_cho_rieng", "`CO_NGUON_GOC`", "`NguonGocTaiSan`", "tang_cho_rieng"),
    ("`LoaiTaiSan`", "thu_nhap_lao_dong", "`CO_NGUON_GOC`", "`NguonGocTaiSan`", "lao_dong_cua_con"),
    ("`LoaiTaiSan`", "hoa_loi_loi_tuc", "`CO_NGUON_GOC`", "`NguonGocTaiSan`", "phat_sinh_tu_tai_san_rieng"),
    ("`LoaiTaiSan`", "thu_nhap_hop_phap_khac", "`CO_NGUON_GOC`", "`NguonGocTaiSan`", "nguon_thu_nhap_hop_phap_khac"),
    ("`LoaiTaiSan`", "tai_san_hinh_thanh_tu_tai_san_rieng", "`CO_NGUON_GOC`", "`NguonGocTaiSan`", "hinh_thanh_tu_tai_san_rieng"),
    ("`Quyen`", "quyen_co_tai_san_rieng", "`THUC_HIEN_BOI`", "`ChuThe`", "con"),
    ("`Quyen`", "quyen_co_tai_san_rieng", "`TAC_DONG_LEN`", "`LoaiTaiSan`", "tai_san_rieng_cua_con"),
    ("`LoaiTaiSan`", "tai_san_rieng_cua_con", "`DAN_TOI`", "`HauQua`", "tai_san_duoc_xac_dinh_la_tai_san_rieng_cua_con"),
    ("`NghiaVu`", "nghia_vu_cham_lo_doi_song_chung_cua_gia_dinh", "`THUC_HIEN_BOI`", "`ChuThe`", "con"),
    ("`NghiaVu`", "nghia_vu_cham_lo_doi_song_chung_cua_gia_dinh", "`AP_DUNG_KHI`", "`DieuKien`", "con_tu_du_15_tuoi"),
    ("`NghiaVu`", "nghia_vu_cham_lo_doi_song_chung_cua_gia_dinh", "`AP_DUNG_KHI`", "`DieuKien`", "con_song_chung_voi_cha_me"),
    ("`NghiaVu`", "nghia_vu_dong_gop_nhu_cau_thiet_yeu_khi_co_thu_nhap", "`THUC_HIEN_BOI`", "`ChuThe`", "con"),
    ("`NghiaVu`", "nghia_vu_dong_gop_nhu_cau_thiet_yeu_khi_co_thu_nhap", "`AP_DUNG_KHI`", "`DieuKien`", "con_tu_du_15_tuoi"),
    ("`NghiaVu`", "nghia_vu_dong_gop_nhu_cau_thiet_yeu_khi_co_thu_nhap", "`AP_DUNG_KHI`", "`DieuKien`", "con_song_chung_voi_cha_me"),
    ("`NghiaVu`", "nghia_vu_dong_gop_nhu_cau_thiet_yeu_khi_co_thu_nhap", "`AP_DUNG_KHI`", "`DieuKien`", "con_co_thu_nhap"),
    ("`NghiaVu`", "nghia_vu_dong_gop_thu_nhap_cua_con_thanh_nien", "`THUC_HIEN_BOI`", "`ChuThe`", "con"),
    ("`NghiaVu`", "nghia_vu_dong_gop_thu_nhap_cua_con_thanh_nien", "`AP_DUNG_KHI`", "`DieuKien`", "con_da_thanh_nien"),
    ("`QuyDinh`", "quy_dinh_quan_ly_tai_san_rieng_cua_con", "`BAO_GOM`", "`Quyen`", "quyen_tu_quan_ly_tai_san_tu_du_15_tuoi"),
    ("`QuyDinh`", "quy_dinh_quan_ly_tai_san_rieng_cua_con", "`BAO_GOM`", "`Quyen`", "quyen_nho_cha_me_quan_ly_tai_san"),
    ("`QuyDinh`", "quy_dinh_quan_ly_tai_san_rieng_cua_con", "`BAO_GOM`", "`HanhVi`", "cha_me_quan_ly_tai_san_con_duoi_15"),
    ("`QuyDinh`", "quy_dinh_quan_ly_tai_san_rieng_cua_con", "`BAO_GOM`", "`HanhVi`", "cha_me_quan_ly_tai_san_con_mat_nang_luc"),
    ("`QuyDinh`", "quy_dinh_quan_ly_tai_san_rieng_cua_con", "`BAO_GOM`", "`HanhVi`", "uy_quyen_nguoi_khac_quan_ly_tai_san"),
    ("`QuyDinh`", "quy_dinh_quan_ly_tai_san_rieng_cua_con", "`BAO_GOM`", "`HanhVi`", "giao_lai_tai_san_cho_con"),
    ("`QuyDinh`", "quy_dinh_quan_ly_tai_san_rieng_cua_con", "`BAO_GOM`", "`HanhVi`", "cha_me_khong_quan_ly_tai_san_cua_con"),
    ("`QuyDinh`", "quy_dinh_quan_ly_tai_san_rieng_cua_con", "`BAO_GOM`", "`HanhVi`", "giao_tai_san_cho_nguoi_giam_ho_quan_ly"),
    ("`Quyen`", "quyen_tu_quan_ly_tai_san_tu_du_15_tuoi", "`THUC_HIEN_BOI`", "`ChuThe`", "con"),
    ("`Quyen`", "quyen_tu_quan_ly_tai_san_tu_du_15_tuoi", "`AP_DUNG_KHI`", "`DieuKien`", "con_tu_du_15_tuoi"),
    ("`Quyen`", "quyen_nho_cha_me_quan_ly_tai_san", "`THUC_HIEN_BOI`", "`ChuThe`", "con"),
    ("`Quyen`", "quyen_nho_cha_me_quan_ly_tai_san", "`AP_DUNG_KHI`", "`DieuKien`", "con_tu_du_15_tuoi"),
    ("`HanhVi`", "cha_me_quan_ly_tai_san_con_duoi_15", "`THUC_HIEN_BOI`", "`ChuThe`", "cha_me"),
    ("`HanhVi`", "cha_me_quan_ly_tai_san_con_duoi_15", "`AP_DUNG_KHI`", "`DieuKien`", "con_duoi_15_tuoi"),
    ("`HanhVi`", "cha_me_quan_ly_tai_san_con_duoi_15", "`DAN_TOI`", "`HauQua`", "cha_me_hoac_nguoi_duoc_uy_quyen_quan_ly"),
    ("`HanhVi`", "cha_me_quan_ly_tai_san_con_mat_nang_luc", "`THUC_HIEN_BOI`", "`ChuThe`", "cha_me"),
    ("`HanhVi`", "cha_me_quan_ly_tai_san_con_mat_nang_luc", "`AP_DUNG_KHI`", "`DieuKien`", "con_mat_nang_luc_hanh_vi_dan_su"),
    ("`HanhVi`", "uy_quyen_nguoi_khac_quan_ly_tai_san", "`THUC_HIEN_BOI`", "`ChuThe`", "cha_me"),
    ("`HanhVi`", "uy_quyen_nguoi_khac_quan_ly_tai_san", "`DAN_TOI`", "`ChuThe`", "nguoi_duoc_uy_quyen_quan_ly"),
    ("`HanhVi`", "giao_lai_tai_san_cho_con", "`AP_DUNG_KHI`", "`DieuKien`", "con_tu_du_15_tuoi"),
    ("`HanhVi`", "giao_lai_tai_san_cho_con", "`AP_DUNG_KHI`", "`DieuKien`", "con_khoi_phuc_nang_luc_hanh_vi_dan_su_day_du"),
    ("`HanhVi`", "giao_lai_tai_san_cho_con", "`YEU_CAU_THOA_THUAN`", "`ThoaThuan`", "thoa_thuan_khac_ve_thoi_diem_giao_lai_tai_san"),
    ("`HanhVi`", "giao_lai_tai_san_cho_con", "`DAN_TOI`", "`HauQua`", "giao_lai_tai_san_khi_con_du_tuoi_hoac_khoi_phuc_nang_luc"),
    ("`HanhVi`", "cha_me_khong_quan_ly_tai_san_cua_con", "`AP_DUNG_KHI`", "`DieuKien`", "con_dang_duoc_nguoi_khac_giam_ho"),
    ("`HanhVi`", "chi_dinh_nguoi_khac_quan_ly_tai_san", "`AP_DUNG_KHI`", "`DieuKien`", "nguoi_tang_cho_hoac_de_lai_di_chuc_chi_dinh_nguoi_quan_ly"),
    ("`HanhVi`", "chi_dinh_nguoi_khac_quan_ly_tai_san", "`DAN_TOI`", "`HauQua`", "nguoi_khac_thay_cha_me_quan_ly"),
    ("`HanhVi`", "giao_tai_san_cho_nguoi_giam_ho_quan_ly", "`AP_DUNG_KHI`", "`DieuKien`", "cha_me_dang_quan_ly_khi_con_chuyen_sang_nguoi_giam_ho"),
    ("`HanhVi`", "giao_tai_san_cho_nguoi_giam_ho_quan_ly", "`DAN_TOI`", "`HauQua`", "nguoi_giam_ho_tiep_nhan_quan_ly_tai_san"),
    ("`QuyDinh`", "quy_dinh_dinh_doat_tai_san_rieng_cua_con", "`BAO_GOM`", "`HanhVi`", "dinh_doat_tai_san_con_duoi_15"),
    ("`QuyDinh`", "quy_dinh_dinh_doat_tai_san_rieng_cua_con", "`BAO_GOM`", "`HanhVi`", "dinh_doat_tai_san_con_tu_du_15_den_duoi_18"),
    ("`QuyDinh`", "quy_dinh_dinh_doat_tai_san_rieng_cua_con", "`BAO_GOM`", "`HanhVi`", "dinh_doat_tai_san_con_thanh_nien_mat_nang_luc"),
    ("`Quyen`", "quyen_dinh_doat_tai_san_con_duoi_15_cua_nguoi_quan_ly", "`THUC_HIEN_BOI`", "`ChuThe`", "cha_me"),
    ("`Quyen`", "quyen_dinh_doat_tai_san_con_duoi_15_cua_nguoi_quan_ly", "`THUC_HIEN_BOI`", "`ChuThe`", "nguoi_giam_ho"),
    ("`Quyen`", "quyen_dinh_doat_tai_san_con_duoi_15_cua_nguoi_quan_ly", "`AP_DUNG_KHI`", "`DieuKien`", "con_duoi_15_tuoi"),
    ("`Quyen`", "quyen_dinh_doat_tai_san_con_duoi_15_cua_nguoi_quan_ly", "`AP_DUNG_KHI`", "`DieuKien`", "quan_ly_vi_loi_ich_cua_con"),
    ("`HanhVi`", "xem_xet_nguyen_vong_cua_con", "`AP_DUNG_KHI`", "`DieuKien`", "con_tu_du_09_tuoi"),
    ("`HanhVi`", "xem_xet_nguyen_vong_cua_con", "`DAN_TOI`", "`HauQua`", "phai_xem_xet_nguyen_vong_cua_con"),
    ("`Quyen`", "quyen_dinh_doat_tai_san_con_tu_du_15_den_duoi_18", "`THUC_HIEN_BOI`", "`ChuThe`", "con"),
    ("`Quyen`", "quyen_dinh_doat_tai_san_con_tu_du_15_den_duoi_18", "`AP_DUNG_KHI`", "`DieuKien`", "con_tu_du_15_den_duoi_18_tuoi"),
    ("`HanhVi`", "dinh_doat_tai_san_con_tu_du_15_den_duoi_18", "`AP_DUNG_KHI`", "`DieuKien`", "tai_san_la_bat_dong_san"),
    ("`HanhVi`", "dinh_doat_tai_san_con_tu_du_15_den_duoi_18", "`AP_DUNG_KHI`", "`DieuKien`", "tai_san_la_dong_san_phai_dang_ky"),
    ("`HanhVi`", "dung_tai_san_de_kinh_doanh", "`AP_DUNG_KHI`", "`DieuKien`", "giao_dich_dung_tai_san_de_kinh_doanh"),
    ("`HanhVi`", "dinh_doat_tai_san_con_tu_du_15_den_duoi_18", "`YEU_CAU_THOA_THUAN`", "`ThoaThuan`", "dong_y_bang_van_ban_cua_cha_me_hoac_nguoi_giam_ho"),
    ("`HanhVi`", "dinh_doat_tai_san_con_tu_du_15_den_duoi_18", "`DAN_TOI`", "`HauQua`", "phai_co_dong_y_bang_van_ban"),
    ("`Quyen`", "quyen_dinh_doat_tai_san_con_thanh_nien_mat_nang_luc_cua_nguoi_giam_ho", "`THUC_HIEN_BOI`", "`ChuThe`", "nguoi_giam_ho"),
    ("`Quyen`", "quyen_dinh_doat_tai_san_con_thanh_nien_mat_nang_luc_cua_nguoi_giam_ho", "`AP_DUNG_KHI`", "`DieuKien`", "con_mat_nang_luc_hanh_vi_dan_su"),
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
