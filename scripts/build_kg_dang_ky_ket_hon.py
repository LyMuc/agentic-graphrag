"""Build KG ngữ nghĩa cho topic 'Đăng ký kết hôn' (dang_ky_ket_hon).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_dang_ky_ket_hon.py           # MERGE idempotent
    python scripts/build_kg_dang_ky_ket_hon.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_dang_ky_ket_hon.py --dry-run # chỉ in summary

Schema: docs/kg_dang_ky_ket_hon_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "dang_ky_ket_hon"
TOPIC_LABEL = "DangKyKetHon"

SEMANTIC_LABELS = [
    "ChuThe",
    "DieuKien",
    "HanhVi",
    "NghiaVu",
    "Quyen",
    "HauQua",
    "CoQuanDangKy",
    "NoiCuTru",
    "GiayToHoTich",
    "ThoiHan",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("hai_ben_nam_nu", "Hai bên nam, nữ yêu cầu đăng ký kết hôn", "ChuThe", ["Luat_HNGD_2014_Dieu_8", "Luat_HNGD_2014_Dieu_9", "Luat_HoTich_2014_Dieu_18_Khoan_1", "Luat_HoTich_2014_Dieu_38_Khoan_3"]),
    ("cong_dan_viet_nam_cu_tru_trong_nuoc", "Công dân Việt Nam cư trú ở trong nước đăng ký kết hôn", "ChuThe", ["Luat_HoTich_2014_Dieu_11_Khoan_1", "Luat_HoTich_2014_Dieu_17_Khoan_1"]),
    ("cong_dan_viet_nam_voi_nguoi_nuoc_ngoai", "Công dân Việt Nam kết hôn với người nước ngoài", "ChuThe", ["Luat_HoTich_2014_Dieu_37_Khoan_1", "Luat_HoTich_2014_Dieu_38"]),
    ("cong_dan_viet_nam_dinh_cu_o_nuoc_ngoai", "Công dân Việt Nam định cư ở nước ngoài tham gia đăng ký kết hôn tại Việt Nam", "ChuThe", ["Luat_HoTich_2014_Dieu_37_Khoan_1", "Luat_HoTich_2014_Dieu_38_Khoan_1"]),
    ("nguoi_nuoc_ngoai_cu_tru_tai_viet_nam", "Người nước ngoài cư trú tại Việt Nam yêu cầu đăng ký kết hôn tại Việt Nam", "ChuThe", ["Luat_HoTich_2014_Dieu_37_Khoan_2", "Luat_HoTich_2014_Dieu_38"]),
    ("cong_chuc_tu_phap_ho_tich", "Công chức tư pháp - hộ tịch tiếp nhận, kiểm tra và ghi việc kết hôn", "ChuThe", ["Luat_HoTich_2014_Dieu_18_Khoan_2", "NghiDinh_123_2015_ND_CP_Dieu_18_Khoan_3", "NghiDinh_123_2015_ND_CP_Dieu_27"]),
    ("phong_tu_phap", "Phòng Tư pháp thẩm tra, trình và thông báo kết quả đăng ký kết hôn cấp huyện", "ChuThe", ["Luat_HoTich_2014_Dieu_38_Khoan_2", "NghiDinh_123_2015_ND_CP_Dieu_33_Khoan_2"]),
    ("chu_tich_ubnd_cap_xa", "Chủ tịch UBND cấp xã ký hoặc tổ chức trao Giấy chứng nhận kết hôn", "ChuThe", ["Luat_HoTich_2014_Dieu_18_Khoan_2", "NghiDinh_123_2015_ND_CP_Dieu_18_Khoan_3"]),
    ("chu_tich_ubnd_cap_huyen", "Chủ tịch UBND cấp huyện quyết định việc đăng ký kết hôn thuộc thẩm quyền cấp huyện", "ChuThe", ["Luat_HoTich_2014_Dieu_38_Khoan_2", "Luat_HoTich_2014_Dieu_38_Khoan_3"]),
    ("ubnd_cap_xa_noi_cu_tru_mot_trong_hai_ben", "UBND cấp xã nơi cư trú của một trong hai bên nam, nữ", "CoQuanDangKy", ["Luat_HoTich_2014_Dieu_17_Khoan_1"]),
    ("ubnd_cap_huyen_noi_cu_tru_cong_dan_viet_nam", "UBND cấp huyện nơi cư trú của công dân Việt Nam trong trường hợp có yếu tố nước ngoài", "CoQuanDangKy", ["Luat_HoTich_2014_Dieu_37_Khoan_1"]),
    ("ubnd_cap_huyen_noi_cu_tru_mot_trong_hai_ben", "UBND cấp huyện nơi cư trú của một trong hai người nước ngoài cư trú tại Việt Nam", "CoQuanDangKy", ["Luat_HoTich_2014_Dieu_37_Khoan_2"]),
    ("ubnd_xa_khu_vuc_bien_gioi", "UBND xã khu vực biên giới đăng ký kết hôn với công dân nước láng giềng đủ điều kiện", "CoQuanDangKy", ["NghiDinh_123_2015_ND_CP_Dieu_18"]),
    ("noi_thuong_tru", "Nơi thường trú của công dân", "NoiCuTru", ["Luat_CuTru_2020_Dieu_11_Khoan_1"]),
    ("noi_tam_tru", "Nơi tạm trú của công dân", "NoiCuTru", ["Luat_CuTru_2020_Dieu_11_Khoan_1", "Luat_HoTich_2014_Dieu_17_Khoan_1", "Luat_HoTich_2014_Dieu_37"]),
    ("noi_o_hien_tai_khi_khong_xac_dinh_duoc_cu_tru", "Nơi ở hiện tại khi không xác định được nơi thường trú, nơi tạm trú", "NoiCuTru", ["Luat_CuTru_2020_Dieu_11_Khoan_2"]),
    ("nam_tu_du_20_tuoi", "Nam từ đủ 20 tuổi trở lên", "DieuKien", ["Luat_HNGD_2014_Dieu_8_Khoan_1"]),
    ("nu_tu_du_18_tuoi", "Nữ từ đủ 18 tuổi trở lên", "DieuKien", ["Luat_HNGD_2014_Dieu_8_Khoan_1"]),
    ("hai_ben_tu_nguyen_quyet_dinh", "Việc kết hôn do nam và nữ tự nguyện quyết định", "DieuKien", ["Luat_HNGD_2014_Dieu_8_Khoan_1", "Luat_HoTich_2014_Dieu_38_Khoan_3"]),
    ("khong_bi_mat_nang_luc_hanh_vi_dan_su", "Người kết hôn không bị mất năng lực hành vi dân sự", "DieuKien", ["Luat_HNGD_2014_Dieu_8_Khoan_1"]),
    ("khong_thuoc_truong_hop_cam_ket_hon", "Việc kết hôn không thuộc trường hợp cấm kết hôn", "DieuKien", ["Luat_HNGD_2014_Dieu_8_Khoan_1"]),
    ("du_dieu_kien_ket_hon", "Hai bên đáp ứng đầy đủ điều kiện kết hôn", "DieuKien", ["Luat_HNGD_2014_Dieu_8", "Luat_HoTich_2014_Dieu_18_Khoan_2", "Luat_HoTich_2014_Dieu_38_Khoan_2"]),
    ("can_xac_minh_dieu_kien_ket_hon", "Hồ sơ hoặc tình tiết cần xác minh thêm điều kiện kết hôn", "DieuKien", ["Luat_HoTich_2014_Dieu_18_Khoan_2", "Luat_HoTich_2014_Dieu_38_Khoan_2"]),
    ("co_yeu_to_nuoc_ngoai", "Quan hệ đăng ký kết hôn thuộc nhóm có yếu tố nước ngoài tại Điều 37", "DieuKien", ["Luat_HoTich_2014_Dieu_37"]),
    ("co_giay_xac_nhan_y_te_theo_yeu_cau", "Có giấy xác nhận y tế về khả năng nhận thức, làm chủ hành vi", "DieuKien", ["Luat_HoTich_2014_Dieu_38_Khoan_1"]),
    ("co_giay_tinh_trang_hon_nhan_va_ho_chieu", "Người nước ngoài hoặc công dân Việt Nam định cư ở nước ngoài có giấy tờ tình trạng hôn nhân và hộ chiếu/giấy thay hộ chiếu", "DieuKien", ["Luat_HoTich_2014_Dieu_38_Khoan_1"]),
    ("vi_pham_dieu_cam_hoac_khong_du_dieu_kien", "Một hoặc cả hai bên vi phạm điều cấm hoặc không đủ điều kiện kết hôn", "DieuKien", ["Luat_HNGD_2014_Dieu_8", "NghiDinh_123_2015_ND_CP_Dieu_33_Khoan_1"]),
    ("dang_ky_ket_hon_khong_dung_tham_quyen", "Việc đăng ký kết hôn đã thực hiện tại cơ quan không đúng thẩm quyền", "DieuKien", ["Luat_HNGD_2014_Dieu_13"]),
    ("da_dang_ky_truoc_ngay_01_01_2016", "Việc kết hôn đã được đăng ký tại cơ quan Việt Nam trước ngày 01/01/2016", "DieuKien", ["NghiDinh_123_2015_ND_CP_Dieu_24_Khoan_1"]),
    ("so_ho_tich_va_ban_chinh_deu_bi_mat", "Sổ hộ tịch và bản chính Giấy chứng nhận kết hôn đều bị mất", "DieuKien", ["NghiDinh_123_2015_ND_CP_Dieu_24_Khoan_1"]),
    ("nguoi_yeu_cau_dang_ky_lai_con_song", "Người yêu cầu đăng ký lại kết hôn còn sống khi tiếp nhận hồ sơ", "DieuKien", ["NghiDinh_123_2015_ND_CP_Dieu_24_Khoan_3"]),
    ("ho_so_dang_ky_lai_day_du_chinh_xac", "Hồ sơ đăng ký lại kết hôn đầy đủ, chính xác, đúng quy định", "DieuKien", ["NghiDinh_123_2015_ND_CP_Dieu_27_Khoan_2", "NghiDinh_123_2015_ND_CP_Dieu_27_Khoan_3"]),
    ("thuc_hien_dang_ky_ket_hon", "Thực hiện việc đăng ký kết hôn tại cơ quan có thẩm quyền", "HanhVi", ["Luat_HNGD_2014_Dieu_9_Khoan_1", "Luat_HoTich_2014_Dieu_17", "Luat_HoTich_2014_Dieu_37"]),
    ("nop_to_khai_va_cung_co_mat", "Hai bên nộp tờ khai và cùng có mặt khi đăng ký", "HanhVi", ["Luat_HoTich_2014_Dieu_18_Khoan_1", "Luat_HoTich_2014_Dieu_38_Khoan_3"]),
    ("kiem_tra_xac_minh_ho_so_ket_hon", "Cơ quan hộ tịch kiểm tra, thẩm tra hoặc xác minh hồ sơ", "HanhVi", ["Luat_HoTich_2014_Dieu_18_Khoan_2", "Luat_HoTich_2014_Dieu_38_Khoan_2", "NghiDinh_123_2015_ND_CP_Dieu_18_Khoan_3"]),
    ("ghi_viec_ket_hon_vao_so_ho_tich", "Ghi việc kết hôn vào Sổ hộ tịch", "HanhVi", ["Luat_HoTich_2014_Dieu_18_Khoan_2", "Luat_HoTich_2014_Dieu_38_Khoan_3"]),
    ("hai_ben_ky_so_va_giay_chung_nhan", "Hai bên ký vào Sổ hộ tịch và Giấy chứng nhận kết hôn", "HanhVi", ["Luat_HoTich_2014_Dieu_18_Khoan_2", "Luat_HoTich_2014_Dieu_38_Khoan_3"]),
    ("to_chuc_trao_giay_chung_nhan_ket_hon", "Cơ quan có thẩm quyền tổ chức trao Giấy chứng nhận kết hôn", "HanhVi", ["Luat_HoTich_2014_Dieu_18_Khoan_2", "Luat_HoTich_2014_Dieu_38_Khoan_3"]),
    ("uy_quyen_nguoi_khac_dang_ky_ket_hon", "Nhờ hoặc ủy quyền người khác đăng ký kết hôn thay", "HanhVi", ["Luat_HoTich_2014_Dieu_18_Khoan_1", "Luat_HoTich_2014_Dieu_38_Khoan_3"]),
    ("ket_hon_lai_sau_khi_da_ly_hon", "Vợ chồng đã ly hôn muốn xác lập lại quan hệ vợ chồng", "HanhVi", ["Luat_HNGD_2014_Dieu_9_Khoan_2"]),
    ("tu_choi_dang_ky_ket_hon", "Cơ quan có thẩm quyền từ chối đăng ký kết hôn", "HanhVi", ["NghiDinh_123_2015_ND_CP_Dieu_33"]),
    ("thu_hoi_huy_giay_sai_tham_quyen", "Thu hồi, hủy bỏ Giấy chứng nhận kết hôn do đăng ký sai thẩm quyền", "HanhVi", ["Luat_HNGD_2014_Dieu_13"]),
    ("thuc_hien_lai_dang_ky_dung_tham_quyen", "Hai bên thực hiện lại đăng ký tại cơ quan đúng thẩm quyền", "HanhVi", ["Luat_HNGD_2014_Dieu_13"]),
    ("dang_ky_lai_ket_hon", "Thực hiện đăng ký lại kết hôn đã đăng ký trước đây", "HanhVi", ["NghiDinh_123_2015_ND_CP_Dieu_24", "NghiDinh_123_2015_ND_CP_Dieu_27"]),
    ("xac_minh_viec_luu_giu_so_ho_tich", "Xác minh nơi đăng ký trước đây còn lưu giữ Sổ hộ tịch hay không", "HanhVi", ["NghiDinh_123_2015_ND_CP_Dieu_27_Khoan_2", "NghiDinh_123_2015_ND_CP_Dieu_27_Khoan_3"]),
    ("cap_giay_chung_nhan_ket_hon", "Ký, cấp Giấy chứng nhận kết hôn sau khi đủ điều kiện", "HanhVi", ["Luat_HoTich_2014_Dieu_18_Khoan_2", "Luat_HoTich_2014_Dieu_38_Khoan_3", "NghiDinh_123_2015_ND_CP_Dieu_18_Khoan_3"]),
    ("nghia_vu_dang_ky_ket_hon", "Việc kết hôn phải được đăng ký và do cơ quan có thẩm quyền thực hiện", "NghiaVu", ["Luat_HNGD_2014_Dieu_9_Khoan_1"]),
    ("nghia_vu_hai_ben_cung_co_mat", "Hai bên phải trực tiếp cùng có mặt khi đăng ký kết hôn", "NghiaVu", ["Luat_HoTich_2014_Dieu_18_Khoan_1", "Luat_HoTich_2014_Dieu_38_Khoan_3"]),
    ("nghia_vu_nop_tai_lieu_dang_ky_lai", "Người yêu cầu đăng ký lại nộp đầy đủ bản sao giấy tờ, tài liệu liên quan", "NghiaVu", ["NghiDinh_123_2015_ND_CP_Dieu_24_Khoan_2", "NghiDinh_123_2015_ND_CP_Dieu_27_Khoan_1"]),
    ("nghia_vu_nop_le_phi_truong_hop_khac", "Nộp lệ phí đối với trường hợp không thuộc diện miễn theo Điều 11 khoản 1", "NghiaVu", ["Luat_HoTich_2014_Dieu_11_Khoan_2"]),
    ("nghia_vu_thong_bao_tu_choi_bang_van_ban", "Phòng Tư pháp thông báo bằng văn bản và nêu rõ lý do từ chối", "NghiaVu", ["NghiDinh_123_2015_ND_CP_Dieu_33_Khoan_2"]),
    ("quyen_mien_le_phi_ket_hon_trong_nuoc", "Công dân Việt Nam cư trú trong nước được miễn lệ phí đăng ký kết hôn", "Quyen", ["Luat_HoTich_2014_Dieu_11_Khoan_1"]),
    ("quyen_moi_ben_nhan_mot_ban_chinh", "Mỗi bên vợ, chồng được cấp một bản chính Giấy chứng nhận kết hôn", "Quyen", ["NghiDinh_123_2015_ND_CP_Dieu_18_Khoan_3"]),
    ("to_khai_dang_ky_ket_hon", "Tờ khai đăng ký kết hôn theo mẫu", "GiayToHoTich", ["Luat_HoTich_2014_Dieu_18_Khoan_1", "Luat_HoTich_2014_Dieu_38_Khoan_1", "NghiDinh_123_2015_ND_CP_Dieu_27_Khoan_1"]),
    ("so_ho_tich", "Sổ hộ tịch ghi nhận việc đăng ký kết hôn", "GiayToHoTich", ["Luat_HoTich_2014_Dieu_18_Khoan_2", "Luat_HoTich_2014_Dieu_38_Khoan_3", "NghiDinh_123_2015_ND_CP_Dieu_24_Khoan_1"]),
    ("giay_chung_nhan_ket_hon", "Giấy chứng nhận kết hôn là giấy tờ hộ tịch xác nhận việc kết hôn", "GiayToHoTich", ["Luat_HoTich_2024_Dieu_4_Khoan_7", "Luat_HoTich_2014_Dieu_17_Khoan_2"]),
    ("thong_tin_nhan_than_hai_ben_tren_giay", "Họ tên, ngày sinh, dân tộc, quốc tịch, nơi cư trú và giấy tờ nhân thân của hai bên", "GiayToHoTich", ["Luat_HoTich_2014_Dieu_17_Khoan_2"]),
    ("ngay_thang_nam_dang_ky_tren_giay", "Ngày, tháng, năm đăng ký kết hôn ghi trên Giấy chứng nhận", "GiayToHoTich", ["Luat_HoTich_2014_Dieu_17_Khoan_2"]),
    ("chu_ky_diem_chi_va_xac_nhan_tren_giay", "Chữ ký/điểm chỉ của hai bên và xác nhận của cơ quan đăng ký hộ tịch", "GiayToHoTich", ["Luat_HoTich_2014_Dieu_17_Khoan_2"]),
    ("giay_xac_nhan_y_te", "Giấy xác nhận y tế dùng trong hồ sơ kết hôn có yếu tố nước ngoài", "GiayToHoTich", ["Luat_HoTich_2014_Dieu_38_Khoan_1"]),
    ("giay_chung_minh_tinh_trang_hon_nhan", "Giấy tờ chứng minh tình trạng hôn nhân của người nước ngoài hoặc người Việt Nam định cư ở nước ngoài", "GiayToHoTich", ["Luat_HoTich_2014_Dieu_38_Khoan_1"]),
    ("ho_chieu_hoac_giay_thay_ho_chieu", "Hộ chiếu hoặc giấy tờ có giá trị thay hộ chiếu trong hồ sơ", "GiayToHoTich", ["Luat_HoTich_2014_Dieu_38_Khoan_1"]),
    ("xac_minh_cap_xa_khong_qua_05_ngay_lam_viec", "Thời hạn xác minh điều kiện kết hôn cấp xã không quá 05 ngày làm việc", "ThoiHan", ["Luat_HoTich_2014_Dieu_18_Khoan_2"]),
    ("giai_quyet_xa_bien_gioi_03_ngay_lam_viec", "Thời hạn giải quyết hồ sơ hợp lệ tại xã khu vực biên giới là 03 ngày làm việc", "ThoiHan", ["NghiDinh_123_2015_ND_CP_Dieu_18_Khoan_3"]),
    ("xac_minh_xa_bien_gioi_khong_qua_08_ngay_lam_viec", "Trường hợp cần xác minh tại xã khu vực biên giới, thời hạn không quá 08 ngày làm việc", "ThoiHan", ["NghiDinh_123_2015_ND_CP_Dieu_18_Khoan_3"]),
    ("giai_quyet_cap_huyen_15_ngay", "Thời hạn luật định để nghiên cứu, thẩm tra và xác minh hồ sơ cấp huyện", "ThoiHan", ["Luat_HoTich_2014_Dieu_38_Khoan_2"]),
    ("kiem_tra_ho_so_dang_ky_lai_05_ngay_lam_viec", "Thời hạn kiểm tra, xác minh hồ sơ đăng ký lại là 05 ngày làm việc", "ThoiHan", ["NghiDinh_123_2015_ND_CP_Dieu_27_Khoan_2"]),
    ("noi_dang_ky_truoc_tra_loi_05_ngay_lam_viec", "Nơi đăng ký trước đây trả lời việc lưu giữ Sổ hộ tịch trong 05 ngày làm việc", "ThoiHan", ["NghiDinh_123_2015_ND_CP_Dieu_27_Khoan_2"]),
    ("hoan_tat_dang_ky_lai_03_ngay_sau_xac_minh", "Hoàn tất đăng ký lại trong 03 ngày làm việc sau khi nhận kết quả không còn lưu Sổ hộ tịch", "ThoiHan", ["NghiDinh_123_2015_ND_CP_Dieu_27_Khoan_3"]),
    ("ket_hon_khong_dang_ky_khong_co_gia_tri_phap_ly", "Việc kết hôn không đăng ký đúng quy định không có giá trị pháp lý", "HauQua", ["Luat_HNGD_2014_Dieu_9_Khoan_1"]),
    ("quan_he_vo_chong_duoc_xac_lap_sau_dang_ky", "Quan hệ vợ chồng được pháp luật xác lập khi đăng ký hợp lệ", "HauQua", ["Luat_HNGD_2014_Dieu_9_Khoan_1", "Luat_HoTich_2014_Dieu_18_Khoan_2"]),
    ("phai_dang_ky_khi_xac_lap_lai_quan_he_sau_ly_hon", "Vợ chồng đã ly hôn muốn xác lập lại quan hệ phải đăng ký kết hôn", "HauQua", ["Luat_HNGD_2014_Dieu_9_Khoan_2"]),
    ("quan_he_sai_tham_quyen_tinh_tu_ngay_dang_ky_truoc", "Sau khi thực hiện lại đúng thẩm quyền, quan hệ hôn nhân được xác lập từ ngày đăng ký trước", "HauQua", ["Luat_HNGD_2014_Dieu_13"]),
    ("dang_ky_bi_tu_choi", "Yêu cầu đăng ký kết hôn không được chấp nhận do vi phạm điều cấm hoặc thiếu điều kiện", "HauQua", ["NghiDinh_123_2015_ND_CP_Dieu_33_Khoan_1"]),
    ("quan_he_dang_ky_lai_cong_nhan_tu_ngay_truoc", "Quan hệ hôn nhân đăng ký lại được công nhận từ ngày đăng ký kết hôn trước đây", "HauQua", ["NghiDinh_123_2015_ND_CP_Dieu_27_Khoan_4"]),
    ("khong_xac_dinh_ngay_thang_thi_tinh_tu_01_01", "Không xác định được ngày, tháng đăng ký trước thì công nhận từ ngày 01/01 của năm đăng ký trước", "HauQua", ["NghiDinh_123_2015_ND_CP_Dieu_27_Khoan_4"]),

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
    ('ChuThe', 'hai_ben_nam_nu', 'THUC_HIEN', 'HanhVi', 'thuc_hien_dang_ky_ket_hon'),
    ('ChuThe', 'cong_dan_viet_nam_cu_tru_trong_nuoc', 'DANG_KY_TAI', 'CoQuanDangKy', 'ubnd_cap_xa_noi_cu_tru_mot_trong_hai_ben'),
    ('ChuThe', 'cong_dan_viet_nam_voi_nguoi_nuoc_ngoai', 'DANG_KY_TAI', 'CoQuanDangKy', 'ubnd_cap_huyen_noi_cu_tru_cong_dan_viet_nam'),
    ('ChuThe', 'cong_dan_viet_nam_dinh_cu_o_nuoc_ngoai', 'DANG_KY_TAI', 'CoQuanDangKy', 'ubnd_cap_huyen_noi_cu_tru_cong_dan_viet_nam'),
    ('ChuThe', 'nguoi_nuoc_ngoai_cu_tru_tai_viet_nam', 'DANG_KY_TAI', 'CoQuanDangKy', 'ubnd_cap_huyen_noi_cu_tru_mot_trong_hai_ben'),
    ('CoQuanDangKy', 'ubnd_cap_xa_noi_cu_tru_mot_trong_hai_ben', 'CO_THAM_QUYEN_TAI', 'NoiCuTru', 'noi_thuong_tru'),
    ('CoQuanDangKy', 'ubnd_cap_xa_noi_cu_tru_mot_trong_hai_ben', 'CO_THAM_QUYEN_TAI', 'NoiCuTru', 'noi_tam_tru'),
    ('CoQuanDangKy', 'ubnd_cap_huyen_noi_cu_tru_cong_dan_viet_nam', 'CO_THAM_QUYEN_TAI', 'NoiCuTru', 'noi_thuong_tru'),
    ('CoQuanDangKy', 'ubnd_cap_huyen_noi_cu_tru_cong_dan_viet_nam', 'CO_THAM_QUYEN_TAI', 'NoiCuTru', 'noi_tam_tru'),
    ('CoQuanDangKy', 'ubnd_cap_huyen_noi_cu_tru_mot_trong_hai_ben', 'CO_THAM_QUYEN_TAI', 'NoiCuTru', 'noi_thuong_tru'),
    ('CoQuanDangKy', 'ubnd_cap_huyen_noi_cu_tru_mot_trong_hai_ben', 'CO_THAM_QUYEN_TAI', 'NoiCuTru', 'noi_tam_tru'),
    ('NoiCuTru', 'noi_thuong_tru', 'LIEN_QUAN', 'NoiCuTru', 'noi_o_hien_tai_khi_khong_xac_dinh_duoc_cu_tru'),
    ('NoiCuTru', 'noi_tam_tru', 'LIEN_QUAN', 'NoiCuTru', 'noi_o_hien_tai_khi_khong_xac_dinh_duoc_cu_tru'),
    ('HanhVi', 'thuc_hien_dang_ky_ket_hon', 'AP_DUNG_KHI', 'DieuKien', 'du_dieu_kien_ket_hon'),
    ('DieuKien', 'du_dieu_kien_ket_hon', 'LIEN_QUAN', 'DieuKien', 'nam_tu_du_20_tuoi'),
    ('DieuKien', 'du_dieu_kien_ket_hon', 'LIEN_QUAN', 'DieuKien', 'nu_tu_du_18_tuoi'),
    ('DieuKien', 'du_dieu_kien_ket_hon', 'LIEN_QUAN', 'DieuKien', 'hai_ben_tu_nguyen_quyet_dinh'),
    ('DieuKien', 'du_dieu_kien_ket_hon', 'LIEN_QUAN', 'DieuKien', 'khong_bi_mat_nang_luc_hanh_vi_dan_su'),
    ('DieuKien', 'du_dieu_kien_ket_hon', 'LIEN_QUAN', 'DieuKien', 'khong_thuoc_truong_hop_cam_ket_hon'),
    ('ChuThe', 'hai_ben_nam_nu', 'CO_NGHIA_VU', 'NghiaVu', 'nghia_vu_dang_ky_ket_hon'),
    ('ChuThe', 'hai_ben_nam_nu', 'CO_NGHIA_VU', 'NghiaVu', 'nghia_vu_hai_ben_cung_co_mat'),
    ('NghiaVu', 'nghia_vu_hai_ben_cung_co_mat', 'LIEN_QUAN', 'HanhVi', 'uy_quyen_nguoi_khac_dang_ky_ket_hon'),
    ('HanhVi', 'thuc_hien_dang_ky_ket_hon', 'YEU_CAU', 'GiayToHoTich', 'to_khai_dang_ky_ket_hon'),
    ('HanhVi', 'nop_to_khai_va_cung_co_mat', 'GHI_VAO', 'GiayToHoTich', 'so_ho_tich'),
    ('HanhVi', 'ghi_viec_ket_hon_vao_so_ho_tich', 'GHI_VAO', 'GiayToHoTich', 'so_ho_tich'),
    ('HanhVi', 'hai_ben_ky_so_va_giay_chung_nhan', 'GHI_VAO', 'GiayToHoTich', 'giay_chung_nhan_ket_hon'),
    ('HanhVi', 'to_chuc_trao_giay_chung_nhan_ket_hon', 'YEU_CAU', 'GiayToHoTich', 'giay_chung_nhan_ket_hon'),
    ('GiayToHoTich', 'giay_chung_nhan_ket_hon', 'CO_NOI_DUNG', 'GiayToHoTich', 'thong_tin_nhan_than_hai_ben_tren_giay'),
    ('GiayToHoTich', 'giay_chung_nhan_ket_hon', 'CO_NOI_DUNG', 'GiayToHoTich', 'ngay_thang_nam_dang_ky_tren_giay'),
    ('GiayToHoTich', 'giay_chung_nhan_ket_hon', 'CO_NOI_DUNG', 'GiayToHoTich', 'chu_ky_diem_chi_va_xac_nhan_tren_giay'),
    ('HanhVi', 'kiem_tra_xac_minh_ho_so_ket_hon', 'AP_DUNG_KHI', 'DieuKien', 'can_xac_minh_dieu_kien_ket_hon'),
    ('HanhVi', 'kiem_tra_xac_minh_ho_so_ket_hon', 'CO_THOI_HAN', 'ThoiHan', 'xac_minh_cap_xa_khong_qua_05_ngay_lam_viec'),
    ('CoQuanDangKy', 'ubnd_xa_khu_vuc_bien_gioi', 'LIEN_QUAN', 'ThoiHan', 'giai_quyet_xa_bien_gioi_03_ngay_lam_viec'),
    ('CoQuanDangKy', 'ubnd_xa_khu_vuc_bien_gioi', 'LIEN_QUAN', 'ThoiHan', 'xac_minh_xa_bien_gioi_khong_qua_08_ngay_lam_viec'),
    ('HanhVi', 'kiem_tra_xac_minh_ho_so_ket_hon', 'CO_THOI_HAN', 'ThoiHan', 'giai_quyet_cap_huyen_15_ngay'),
    ('DieuKien', 'co_yeu_to_nuoc_ngoai', 'LIEN_QUAN', 'DieuKien', 'co_giay_xac_nhan_y_te_theo_yeu_cau'),
    ('DieuKien', 'co_yeu_to_nuoc_ngoai', 'LIEN_QUAN', 'DieuKien', 'co_giay_tinh_trang_hon_nhan_va_ho_chieu'),
    ('HanhVi', 'ket_hon_lai_sau_khi_da_ly_hon', 'DAN_TOI', 'HauQua', 'phai_dang_ky_khi_xac_lap_lai_quan_he_sau_ly_hon'),
    ('NghiaVu', 'nghia_vu_dang_ky_ket_hon', 'DAN_TOI', 'HauQua', 'quan_he_vo_chong_duoc_xac_lap_sau_dang_ky'),
    ('HanhVi', 'thuc_hien_dang_ky_ket_hon', 'DAN_TOI', 'HauQua', 'quan_he_vo_chong_duoc_xac_lap_sau_dang_ky'),
    ('HanhVi', 'thuc_hien_dang_ky_ket_hon', 'LIEN_QUAN', 'HauQua', 'ket_hon_khong_dang_ky_khong_co_gia_tri_phap_ly'),
    ('HanhVi', 'tu_choi_dang_ky_ket_hon', 'AP_DUNG_KHI', 'DieuKien', 'vi_pham_dieu_cam_hoac_khong_du_dieu_kien'),
    ('HanhVi', 'tu_choi_dang_ky_ket_hon', 'DAN_TOI', 'HauQua', 'dang_ky_bi_tu_choi'),
    ('ChuThe', 'phong_tu_phap', 'CO_NGHIA_VU', 'NghiaVu', 'nghia_vu_thong_bao_tu_choi_bang_van_ban'),
    ('HanhVi', 'thu_hoi_huy_giay_sai_tham_quyen', 'AP_DUNG_KHI', 'DieuKien', 'dang_ky_ket_hon_khong_dung_tham_quyen'),
    ('HanhVi', 'thu_hoi_huy_giay_sai_tham_quyen', 'THUC_HIEN_LAI', 'HanhVi', 'thuc_hien_lai_dang_ky_dung_tham_quyen'),
    ('HanhVi', 'thuc_hien_lai_dang_ky_dung_tham_quyen', 'DAN_TOI', 'HauQua', 'quan_he_sai_tham_quyen_tinh_tu_ngay_dang_ky_truoc'),
    ('HanhVi', 'dang_ky_lai_ket_hon', 'AP_DUNG_KHI', 'DieuKien', 'da_dang_ky_truoc_ngay_01_01_2016'),
    ('HanhVi', 'dang_ky_lai_ket_hon', 'AP_DUNG_KHI', 'DieuKien', 'so_ho_tich_va_ban_chinh_deu_bi_mat'),
    ('HanhVi', 'dang_ky_lai_ket_hon', 'AP_DUNG_KHI', 'DieuKien', 'nguoi_yeu_cau_dang_ky_lai_con_song'),
    ('HanhVi', 'dang_ky_lai_ket_hon', 'AP_DUNG_KHI', 'DieuKien', 'ho_so_dang_ky_lai_day_du_chinh_xac'),
    ('ChuThe', 'hai_ben_nam_nu', 'CO_NGHIA_VU', 'NghiaVu', 'nghia_vu_nop_tai_lieu_dang_ky_lai'),
    ('HanhVi', 'dang_ky_lai_ket_hon', 'LIEN_QUAN', 'HanhVi', 'xac_minh_viec_luu_giu_so_ho_tich'),
    ('HanhVi', 'dang_ky_lai_ket_hon', 'CO_THOI_HAN', 'ThoiHan', 'kiem_tra_ho_so_dang_ky_lai_05_ngay_lam_viec'),
    ('HanhVi', 'xac_minh_viec_luu_giu_so_ho_tich', 'CO_THOI_HAN', 'ThoiHan', 'noi_dang_ky_truoc_tra_loi_05_ngay_lam_viec'),
    ('HanhVi', 'dang_ky_lai_ket_hon', 'CO_THOI_HAN', 'ThoiHan', 'hoan_tat_dang_ky_lai_03_ngay_sau_xac_minh'),
    ('HanhVi', 'dang_ky_lai_ket_hon', 'DAN_TOI', 'HauQua', 'quan_he_dang_ky_lai_cong_nhan_tu_ngay_truoc'),
    ('HauQua', 'quan_he_dang_ky_lai_cong_nhan_tu_ngay_truoc', 'LIEN_QUAN', 'HauQua', 'khong_xac_dinh_ngay_thang_thi_tinh_tu_01_01'),
    ('ChuThe', 'cong_dan_viet_nam_cu_tru_trong_nuoc', 'CO_QUYEN', 'Quyen', 'quyen_mien_le_phi_ket_hon_trong_nuoc'),
    ('ChuThe', 'hai_ben_nam_nu', 'CO_QUYEN', 'Quyen', 'quyen_moi_ben_nhan_mot_ban_chinh'),

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
