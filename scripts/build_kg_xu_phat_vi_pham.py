"""Build KG ngữ nghĩa cho topic 'Xử phạt vi phạm' (xu_phat_vi_pham).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_xu_phat_vi_pham.py           # MERGE idempotent
    python scripts/build_kg_xu_phat_vi_pham.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_xu_phat_vi_pham.py --dry-run # chỉ in summary

Schema: docs/kg_xu_phat_vi_pham_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "xu_phat_vi_pham"
TOPIC_LABEL = "XuPhatViPham"

SEMANTIC_LABELS = [
    "HanhVi",
    "ChuThe",
    "QuanHe",
    "HauQua",
    "QuyDinh",
    "DieuKien",
    "CheTai",
    "BienPhapKhacPhuc",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("che_tai_vi_pham_hanh_chinh", "Xử phạt vi phạm hành chính trong phạm vi topic", "CheTai", ["NghiDinh_82_2020_ND_CP_Dieu_58", "NghiDinh_82_2020_ND_CP_Dieu_59", "NghiDinh_82_2020_ND_CP_Dieu_60", "NghiDinh_82_2020_ND_CP_Dieu_61", "NghiDinh_82_2020_ND_CP_Dieu_62", "NghiDinh_82_2020_ND_CP_Dieu_63", "NghiDinh_282_2025_ND_CP_Dieu_37", "NghiDinh_282_2025_ND_CP_Dieu_38", "NghiDinh_282_2025_ND_CP_Dieu_39", "NghiDinh_282_2025_ND_CP_Dieu_40", "NghiDinh_282_2025_ND_CP_Dieu_41", "NghiDinh_282_2025_ND_CP_Dieu_42", "NghiDinh_282_2025_ND_CP_Dieu_43", "NghiDinh_282_2025_ND_CP_Dieu_44", "NghiDinh_282_2025_ND_CP_Dieu_45", "NghiDinh_282_2025_ND_CP_Dieu_46", "NghiDinh_282_2025_ND_CP_Dieu_47", "NghiDinh_282_2025_ND_CP_Dieu_48", "NghiDinh_282_2025_ND_CP_Dieu_49", "NghiDinh_282_2025_ND_CP_Dieu_50", "NghiDinh_282_2025_ND_CP_Dieu_51", "NghiDinh_282_2025_ND_CP_Dieu_52", "NghiDinh_282_2025_ND_CP_Dieu_53"]),
    ("che_tai_trach_nhiem_hinh_su", "Truy cứu trách nhiệm hình sự trong phạm vi topic", "CheTai", ["BoLuat_HinhSu_2015_Dieu_181", "BoLuat_HinhSu_2015_Dieu_182", "BoLuat_HinhSu_2015_Dieu_183", "BoLuat_HinhSu_2015_Dieu_184", "BoLuat_HinhSu_2015_Dieu_185", "BoLuat_HinhSu_2015_Dieu_186", "BoLuat_HinhSu_2015_Dieu_187"]),
    ("che_tai_hinh_thuc_bo_sung", "Hình thức xử phạt hoặc hình phạt bổ sung", "CheTai", ["NghiDinh_82_2020_ND_CP_Dieu_62_Khoan_4", "NghiDinh_82_2020_ND_CP_Dieu_63_Khoan_7", "NghiDinh_282_2025_ND_CP_Dieu_37_Khoan_4", "NghiDinh_282_2025_ND_CP_Dieu_51_Khoan_3", "NghiDinh_282_2025_ND_CP_Dieu_53_Khoan_3", "BoLuat_HinhSu_2015_Dieu_187"]),
    ("bien_phap_xin_loi_cong_khai", "Buộc xin lỗi công khai theo yêu cầu của người bị xâm hại", "BienPhapKhacPhuc", ["NghiDinh_282_2025_ND_CP_Dieu_37_Khoan_5_Diem_a", "NghiDinh_282_2025_ND_CP_Dieu_38_Khoan_3", "NghiDinh_282_2025_ND_CP_Dieu_39_Khoan_3_Diem_a", "NghiDinh_282_2025_ND_CP_Dieu_40_Khoan_5", "NghiDinh_282_2025_ND_CP_Dieu_41_Khoan_4", "NghiDinh_282_2025_ND_CP_Dieu_45_Khoan_4", "NghiDinh_282_2025_ND_CP_Dieu_46_Khoan_3_Diem_b", "NghiDinh_282_2025_ND_CP_Dieu_51_Khoan_4_Diem_b"]),
    ("bien_phap_nop_lai_loi_bat_hop_phap", "Buộc nộp lại số lợi bất hợp pháp", "BienPhapKhacPhuc", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_3", "NghiDinh_82_2020_ND_CP_Dieu_60_Khoan_2", "NghiDinh_82_2020_ND_CP_Dieu_61_Khoan_3_Diem_a", "NghiDinh_82_2020_ND_CP_Dieu_62_Khoan_5_Diem_b", "NghiDinh_82_2020_ND_CP_Dieu_63_Khoan_8_Diem_b", "NghiDinh_282_2025_ND_CP_Dieu_51_Khoan_4_Diem_a"]),
    ("bien_phap_chi_tra_chi_phi_kham_chua_benh", "Buộc chịu hoặc chi trả chi phí khám, chữa bệnh và chi phí liên quan", "BienPhapKhacPhuc", ["NghiDinh_82_2020_ND_CP_Dieu_61_Khoan_3_Diem_b", "NghiDinh_82_2020_ND_CP_Dieu_62_Khoan_5_Diem_c", "NghiDinh_282_2025_ND_CP_Dieu_37_Khoan_5_Diem_b"]),
    ("bien_phap_tra_lai_tai_san_khoi_phuc_tinh_trang", "Trả lại tài sản, hoàn trả giá trị hoặc khôi phục tình trạng ban đầu", "BienPhapKhacPhuc", ["NghiDinh_282_2025_ND_CP_Dieu_44_Khoan_2", "NghiDinh_282_2025_ND_CP_Dieu_46_Khoan_3_Diem_a"]),
    ("bien_phap_thuc_hien_nghia_vu_nuoi_duong_cap_duong", "Buộc thực hiện nghĩa vụ đóng góp, nuôi dưỡng, cấp dưỡng", "BienPhapKhacPhuc", ["NghiDinh_282_2025_ND_CP_Dieu_43_Khoan_2"]),
    ("dieu_kien_da_bi_xu_phat_vphc_ma_con_vi_pham", "Đã bị xử phạt VPHC về hành vi tương ứng mà còn vi phạm", "DieuKien", ["BoLuat_HinhSu_2015_Dieu_181", "BoLuat_HinhSu_2015_Dieu_182", "BoLuat_HinhSu_2015_Dieu_183", "BoLuat_HinhSu_2015_Dieu_185", "BoLuat_HinhSu_2015_Dieu_186"]),
    ("dieu_kien_chua_den_muc_truy_cuu_hinh_su", "Hành vi hoặc hậu quả chưa đến mức truy cứu TNHS", "DieuKien", ["NghiDinh_282_2025_ND_CP_Dieu_37_Khoan_2", "NghiDinh_282_2025_ND_CP_Dieu_37_Khoan_3_Diem_b", "NghiDinh_282_2025_ND_CP_Dieu_44_Khoan_1_Diem_b", "NghiDinh_282_2025_ND_CP_Dieu_46_Khoan_2_Diem_b"]),
    ("quy_dinh_ket_hon_ly_hon_tong_quat", "Xử lý vi phạm kết hôn, ly hôn và kết hôn trái pháp luật ở mức tổng quát", "QuyDinh", ["NghiDinh_82_2020_ND_CP_Dieu_59", "Luat_HNGD_2014_Dieu_3_Khoan_6"]),
    ("quy_dinh_tao_hon", "Tảo hôn, tổ chức tảo hôn và duy trì quan hệ trái pháp luật với người chưa đủ tuổi", "QuyDinh", ["NghiDinh_82_2020_ND_CP_Dieu_58", "BoLuat_HinhSu_2015_Dieu_183", "Luat_HNGD_2014_Dieu_3_Khoan_8"]),
    ("quy_dinh_mot_vo_mot_chong", "Vi phạm chế độ một vợ, một chồng", "QuyDinh", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1", "BoLuat_HinhSu_2015_Dieu_182"]),
    ("quy_dinh_can_tro_cuong_ep_ket_hon_ly_hon", "Cản trở, cưỡng ép hoặc lừa dối kết hôn/ly hôn; yêu sách của cải", "QuyDinh", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1_Diem_đ", "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_c", "BoLuat_HinhSu_2015_Dieu_181", "Luat_HNGD_2014_Dieu_3_Khoan_9", "Luat_HNGD_2014_Dieu_3_Khoan_10", "Luat_HNGD_2014_Dieu_3_Khoan_12"]),
    ("quy_dinh_quan_he_hon_nhan_bi_cam_vphc", "Kết hôn/chung sống trong quan hệ huyết thống, nuôi dưỡng hoặc thông gia bị cấm", "QuyDinh", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1_Diem_d", "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_a", "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_b", "Luat_HNGD_2014_Dieu_3_Khoan_17", "Luat_HNGD_2014_Dieu_3_Khoan_18", "Luat_HNGD_2014_Dieu_3_Khoan_19"]),
    ("quy_dinh_toi_loan_luan", "Truy cứu hình sự về tội loạn luân", "QuyDinh", ["BoLuat_HinhSu_2015_Dieu_184", "Luat_HNGD_2014_Dieu_3_Khoan_17"]),
    ("quy_dinh_ket_hon_ly_hon_gia_tao", "Kết hôn giả tạo hoặc ly hôn giả tạo", "QuyDinh", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_d", "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_đ", "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_3", "Luat_HNGD_2014_Dieu_3_Khoan_11", "Luat_HNGD_2014_Dieu_3_Khoan_15"]),
    ("quy_dinh_sinh_con_mang_thai_ho_thuong_mai", "Sinh con hỗ trợ vì thương mại, sinh sản vô tính, mang thai hộ thương mại và tổ chức mang thai hộ thương mại", "QuyDinh", ["NghiDinh_82_2020_ND_CP_Dieu_60", "BoLuat_HinhSu_2015_Dieu_187", "Luat_HNGD_2014_Dieu_3_Khoan_23"]),
    ("quy_dinh_vi_pham_giam_ho", "Vi phạm nghĩa vụ và lạm dụng hoạt động giám hộ", "QuyDinh", ["NghiDinh_82_2020_ND_CP_Dieu_61"]),
    ("quy_dinh_vi_pham_nuoi_con_nuoi", "Vi phạm quy định về nuôi con nuôi", "QuyDinh", ["NghiDinh_82_2020_ND_CP_Dieu_62"]),
    ("quy_dinh_van_phong_con_nuoi_nuoc_ngoai", "Vi phạm của văn phòng con nuôi nước ngoài tại Việt Nam", "QuyDinh", ["NghiDinh_82_2020_ND_CP_Dieu_63"]),
    ("quy_dinh_bao_luc_the_chat_nguoc_dai", "Bạo lực thể chất, hành hạ, ngược đãi thành viên gia đình", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_37", "BoLuat_HinhSu_2015_Dieu_185"]),
    ("quy_dinh_bo_mac_khong_cham_soc_giao_duc", "Bỏ mặc, không nuôi dưỡng/chăm sóc người cần chăm sóc; không giáo dục trẻ em", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_38"]),
    ("quy_dinh_xuc_pham_danh_du_bi_mat", "Xúc phạm danh dự, nhân phẩm hoặc phát tán bí mật đời tư gia đình", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_39"]),
    ("quy_dinh_co_lap_ap_luc_tam_ly", "Cô lập, giam cầm, kỳ thị, cản trở quan hệ hợp pháp hoặc gây áp lực tâm lý", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_40"]),
    ("quy_dinh_bao_luc_tinh_duc", "Bạo lực tình dục trong gia đình", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_41"]),
    ("quy_dinh_ngan_can_tham_nom_cham_soc", "Ngăn cản quyền thăm nom, chăm sóc giữa các thành viên gia đình", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_42"]),
    ("quy_dinh_cap_duong_nuoi_duong", "Từ chối, trốn tránh nghĩa vụ nuôi dưỡng, chăm sóc, cấp dưỡng", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_43", "BoLuat_HinhSu_2015_Dieu_186", "Luat_HNGD_2014_Dieu_3_Khoan_24"]),
    ("quy_dinh_bao_luc_kinh_te", "Chiếm đoạt, hủy hoại, kiểm soát tài sản hoặc cưỡng ép tài chính/lao động", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_44"]),
    ("quy_dinh_cuong_ep_ra_khoi_cho_o", "Cưỡng ép thành viên gia đình ra khỏi chỗ ở hợp pháp", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_45"]),
    ("quy_dinh_bao_luc_nguoi_bao_tin_giup_do", "Bạo lực, trả thù hoặc cản trở người báo tin/ngăn chặn/giúp đỡ", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_46"]),
    ("quy_dinh_xui_giuc_cuong_ep_bao_luc", "Kích động, xúi giục, giúp sức hoặc cưỡng ép người khác bạo lực gia đình", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_47"]),
    ("quy_dinh_ngan_chan_bao_tin_xu_ly", "Vi phạm nghĩa vụ ngăn chặn, báo tin, tiếp nhận và xử lý tin báo", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_48"]),
    ("quy_dinh_truyen_ba_kich_dong_bao_luc", "Truyền bá thông tin, tài liệu, hình ảnh, âm thanh kích động bạo lực", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_49"]),
    ("quy_dinh_tiet_lo_thong_tin_va_bang_gia", "Tiết lộ thông tin nạn nhân/người báo tin hoặc không công khai bảng giá dịch vụ", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_50"]),
    ("quy_dinh_loi_dung_hoat_dong_phong_chong_bao_luc", "Lợi dụng hoạt động phòng, chống bạo lực gia đình", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_51"]),
    ("quy_dinh_dang_ky_co_so_tro_giup", "Vi phạm đăng ký/phạm vi hoạt động của cơ sở trợ giúp", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_52"]),
    ("quy_dinh_vi_pham_cam_tiep_xuc", "Vi phạm quyết định cấm tiếp xúc", "QuyDinh", ["NghiDinh_282_2025_ND_CP_Dieu_53"]),
    ("to_chuc_lay_vo_chong_cho_nguoi_chua_du_tuoi", "Tổ chức lấy vợ, lấy chồng cho người chưa đủ tuổi kết hôn", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_58_Khoan_1", "BoLuat_HinhSu_2015_Dieu_183", "Luat_HNGD_2014_Dieu_3_Khoan_8"]),
    ("duy_tri_quan_he_vo_chong_voi_nguoi_chua_du_tuoi_sau_ban_an", "Duy trì quan hệ vợ chồng trái pháp luật với người chưa đủ tuổi dù đã có bản án/quyết định", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_58_Khoan_2"]),
    ("ket_hon_khi_dang_co_vo_chong", "Đang có vợ/chồng mà kết hôn với người khác hoặc kết hôn với người biết rõ đang có vợ/chồng", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1_Diem_a", "BoLuat_HinhSu_2015_Dieu_182"]),
    ("chung_song_voi_nguoi_khac_khi_dang_co_vo_chong", "Đang có vợ/chồng mà chung sống như vợ chồng với người khác", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1_Diem_b", "BoLuat_HinhSu_2015_Dieu_182"]),
    ("chung_song_voi_nguoi_biet_ro_dang_co_vo_chong", "Chưa có vợ/chồng nhưng chung sống với người biết rõ đang có vợ/chồng", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1_Diem_c", "BoLuat_HinhSu_2015_Dieu_182"]),
    ("mot_vo_mot_chong_lam_quan_he_hon_nhan_dan_den_ly_hon", "Vi phạm một vợ, một chồng làm quan hệ hôn nhân của một hoặc hai bên dẫn đến ly hôn", "DieuKien", ["BoLuat_HinhSu_2015_Dieu_182"]),
    ("mot_vo_mot_chong_lam_vo_chong_con_tu_sat", "Vi phạm một vợ, một chồng làm vợ, chồng hoặc con của một trong hai bên tự sát", "DieuKien", ["BoLuat_HinhSu_2015_Dieu_182"]),
    ("mot_vo_mot_chong_khong_chap_hanh_quyet_dinh_toa", "Tiếp tục quan hệ sau quyết định hủy kết hôn hoặc buộc chấm dứt chung sống", "DieuKien", ["BoLuat_HinhSu_2015_Dieu_182"]),
    ("can_tro_ket_hon_hoac_ly_hon", "Cản trở kết hôn hoặc cản trở ly hôn", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1_Diem_đ", "BoLuat_HinhSu_2015_Dieu_181", "Luat_HNGD_2014_Dieu_3_Khoan_10"]),
    ("yeu_sach_cua_cai_trong_ket_hon", "Yêu sách của cải quá đáng làm điều kiện kết hôn", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1_Diem_đ", "BoLuat_HinhSu_2015_Dieu_181", "Luat_HNGD_2014_Dieu_3_Khoan_12"]),
    ("cuong_ep_ket_hon_hoac_ly_hon", "Cưỡng ép người khác kết hôn hoặc ly hôn trái ý muốn", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_c", "BoLuat_HinhSu_2015_Dieu_181", "Luat_HNGD_2014_Dieu_3_Khoan_9"]),
    ("lua_doi_ket_hon_hoac_ly_hon", "Lừa dối kết hôn hoặc lừa dối ly hôn", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_c"]),
    ("ket_hon_chung_song_quan_he_thong_gia_nuoi_duong_cu", "Kết hôn/chung sống giữa cha mẹ nuôi cũ-con nuôi, cha chồng-con dâu, mẹ vợ-con rể, cha dượng/mẹ kế-con riêng", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1_Diem_d", "Luat_HNGD_2014_Dieu_3_Khoan_19"]),
    ("ket_hon_chung_song_cung_dong_mau_truc_he_hoac_ba_doi", "Kết hôn/chung sống giữa người cùng dòng máu trực hệ hoặc có họ trong phạm vi ba đời", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_a", "Luat_HNGD_2014_Dieu_3_Khoan_17", "Luat_HNGD_2014_Dieu_3_Khoan_18"]),
    ("ket_hon_chung_song_cha_me_nuoi_con_nuoi", "Kết hôn/chung sống giữa cha mẹ nuôi với con nuôi", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_b"]),
    ("giao_cau_voi_nguoi_cung_dong_mau_truc_he_hoac_anh_chi_em", "Giao cấu với người cùng dòng máu trực hệ, anh chị em cùng cha mẹ/cùng cha khác mẹ/cùng mẹ khác cha", "HanhVi", ["BoLuat_HinhSu_2015_Dieu_184", "Luat_HNGD_2014_Dieu_3_Khoan_17"]),
    ("ket_hon_gia_tao_de_dat_muc_dich_khac", "Lợi dụng kết hôn để xuất nhập cảnh, cư trú, nhập quốc tịch, hưởng ưu đãi hoặc mục đích khác", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_d", "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_3", "Luat_HNGD_2014_Dieu_3_Khoan_11"]),
    ("ly_hon_gia_tao_de_tron_nghia_vu", "Lợi dụng ly hôn để trốn nghĩa vụ tài sản, vi phạm chính sách dân số hoặc đạt mục đích khác", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_đ", "NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_3", "Luat_HNGD_2014_Dieu_3_Khoan_15"]),
    ("sinh_con_ho_tro_vi_muc_dich_thuong_mai", "Thực hiện sinh con bằng kỹ thuật hỗ trợ sinh sản vì mục đích thương mại", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_60_Khoan_1"]),
    ("thuc_hien_sinh_san_vo_tinh", "Thực hiện sinh sản vô tính", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_60_Khoan_1"]),
    ("mang_thai_ho_vi_muc_dich_thuong_mai", "Mang thai hộ để hưởng lợi kinh tế hoặc lợi ích khác", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_60_Khoan_1", "Luat_HNGD_2014_Dieu_3_Khoan_23"]),
    ("to_chuc_mang_thai_ho_vi_muc_dich_thuong_mai", "Tổ chức mang thai hộ vì mục đích thương mại", "HanhVi", ["BoLuat_HinhSu_2015_Dieu_187", "Luat_HNGD_2014_Dieu_3_Khoan_23"]),
    ("tron_tranh_khong_thuc_hien_nghia_vu_giam_ho", "Trốn tránh, không thực hiện nghĩa vụ giám hộ sau khi đăng ký", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_61_Khoan_1"]),
    ("loi_dung_giam_ho_de_truc_loi", "Lợi dụng quyền, nghĩa vụ giám hộ để trục lợi", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_61_Khoan_2_Diem_a"]),
    ("loi_dung_giam_ho_xam_pham_tinh_duc_boc_lot", "Lợi dụng giám hộ để xâm phạm tình dục hoặc bóc lột sức lao động", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_61_Khoan_2_Diem_b"]),
    ("khai_sai_de_dang_ky_nuoi_con_nuoi", "Khai không đúng sự thật để đăng ký nuôi con nuôi", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_62_Khoan_1_Diem_a"]),
    ("phan_biet_doi_xu_con_de_con_nuoi", "Phân biệt đối xử giữa con đẻ và con nuôi", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_62_Khoan_1_Diem_b"]),
    ("khong_bao_cao_tinh_hinh_con_nuoi_trong_nuoc", "Không báo cáo tình hình phát triển của con nuôi trong nước", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_62_Khoan_1_Diem_c"]),
    ("tay_xoa_giay_to_nuoi_con_nuoi", "Tẩy xóa, sửa chữa làm sai lệch giấy tờ đăng ký nuôi con nuôi", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_62_Khoan_1_Diem_d"]),
    ("loi_dung_cho_con_nuoi_vi_pham_dan_so", "Lợi dụng việc cho con nuôi để vi phạm pháp luật dân số", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_62_Khoan_2_Diem_a"]),
    ("loi_dung_lam_con_nuoi_de_huong_uu_dai", "Lợi dụng làm con nuôi để hưởng chế độ, chính sách ưu đãi", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_62_Khoan_2_Diem_b"]),
    ("mua_chuoc_ep_buoc_de_co_dong_y_cho_con_nuoi", "Mua chuộc, ép buộc, đe dọa để có sự đồng ý cho trẻ làm con nuôi", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_62_Khoan_3_Diem_a"]),
    ("loi_dung_cho_nhan_gioi_thieu_con_nuoi_de_truc_loi", "Lợi dụng cho, nhận hoặc giới thiệu trẻ em làm con nuôi để trục lợi", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_62_Khoan_3_Diem_b"]),
    ("loi_dung_nhan_con_nuoi_de_boc_lot", "Lợi dụng nhận con nuôi để bóc lột sức lao động", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_62_Khoan_3_Diem_c"]),
    ("tay_xoa_ho_so_giay_phep_van_phong_con_nuoi", "Tẩy xóa, sửa chữa hồ sơ cấp/gia hạn/sửa đổi giấy phép văn phòng con nuôi", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_63_Khoan_1"]),
    ("khong_thong_bao_cham_dut_van_phong_con_nuoi", "Không thông báo bằng văn bản việc chấm dứt hoạt động", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_63_Khoan_2_Diem_a"]),
    ("vi_pham_bao_cao_so_sach_van_phong_con_nuoi", "Không báo cáo, báo cáo sai hoặc vi phạm quản lý sổ sách, biểu mẫu", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_63_Khoan_2_Diem_b"]),
    ("thay_doi_nguoi_dung_dau_van_phong_con_nuoi_chua_duoc_phep", "Thay đổi người đứng đầu khi chưa được phép", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_63_Khoan_3"]),
    ("gioi_thieu_tre_em_lam_con_nuoi_trai_phap_luat", "Giới thiệu trẻ em làm con nuôi trái pháp luật", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_63_Khoan_4_Diem_a"]),
    ("cho_thue_muon_giay_phep_van_phong_con_nuoi", "Cho tổ chức khác thuê, mượn giấy phép hoạt động", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_63_Khoan_4_Diem_b"]),
    ("su_dung_giay_phep_van_phong_con_nuoi_khac", "Sử dụng giấy phép hoạt động của văn phòng con nuôi khác", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_63_Khoan_4_Diem_c"]),
    ("van_phong_con_nuoi_hoat_dong_khong_du_dieu_kien", "Hoạt động khi không đủ điều kiện về nuôi con nuôi có yếu tố nước ngoài", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_63_Khoan_5"]),
    ("van_phong_con_nuoi_vi_pham_phi_loi_nhuan", "Vi phạm nguyên tắc hoạt động phi lợi nhuận", "HanhVi", ["NghiDinh_82_2020_ND_CP_Dieu_63_Khoan_6"]),
    ("de_doa_xam_hai_suc_khoe_tinh_mang_thanh_vien_gia_dinh", "Đe dọa xâm hại sức khỏe, tính mạng thành viên gia đình", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_37_Khoan_1"]),
    ("danh_dap_xam_hai_suc_khoe_thanh_vien_gia_dinh", "Đánh đập hoặc cố ý xâm hại sức khỏe, tính mạng nhưng chưa đến mức TNHS", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_37_Khoan_2"]),
    ("hanh_ha_nguoc_dai_thanh_vien_gia_dinh", "Hành hạ, ngược đãi như bắt nhịn ăn uống, chịu rét, hạn chế vệ sinh", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_37_Khoan_3_Diem_a", "BoLuat_HinhSu_2015_Dieu_185"]),
    ("dung_cong_cu_gay_thuong_tich_thanh_vien_gia_dinh", "Dùng công cụ, phương tiện, vật dụng gây thương tích nhưng chưa đến mức TNHS", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_37_Khoan_3_Diem_b"]),
    ("khong_cap_cuu_cham_soc_nan_nhan_bao_luc", "Không đưa nạn nhân đi cấp cứu/điều trị hoặc không chăm sóc trong thời gian điều trị", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_37_Khoan_3_Diem_c"]),
    ("nguoc_dai_thuong_xuyen_gay_dau_don", "Đối xử tồi tệ hoặc bạo lực thường xuyên làm nạn nhân đau đớn thể xác, tinh thần", "DieuKien", ["BoLuat_HinhSu_2015_Dieu_185"]),
    ("nguoc_dai_nguoi_duoi_16_mang_thai_gia_yeu", "Ngược đãi người dưới 16 tuổi, phụ nữ có thai, người già yếu/khuyết tật/nặng bệnh", "DieuKien", ["BoLuat_HinhSu_2015_Dieu_185"]),
    ("bo_mac_khong_cham_soc_nguoi_can_cham_soc", "Bỏ mặc, không quan tâm, nuôi dưỡng hoặc chăm sóc phụ nữ mang thai/nuôi con nhỏ, người khuyết tật, già yếu, cao tuổi hoặc không tự chăm sóc", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_38_Khoan_1_Diem_a"]),
    ("khong_giao_duc_tre_em_trong_gia_dinh", "Không giáo dục thành viên gia đình là trẻ em", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_38_Khoan_1_Diem_b"]),
    ("lang_ma_chiet_chi_xuc_pham_thanh_vien_gia_dinh", "Lăng mạ, chì chiết hoặc cố ý xúc phạm danh dự, nhân phẩm", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_39_Khoan_1"]),
    ("phat_tan_bi_mat_doi_tu_de_xuc_pham", "Tiết lộ/phát tán đời sống riêng tư, bí mật cá nhân/gia đình nhằm xúc phạm", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_39_Khoan_2"]),
    ("ngan_can_gap_go_quan_he_xa_hoi_hop_phap", "Ngăn cản gặp người thân hoặc quan hệ xã hội hợp pháp, lành mạnh", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_40_Khoan_1_Diem_a"]),
    ("ky_thi_phan_biet_hinh_the_gioi_tinh_nang_luc", "Kỳ thị, phân biệt đối xử về hình thể, giới tính, năng lực", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_40_Khoan_1_Diem_b"]),
    ("ngan_can_quyen_nghia_vu_trong_quan_he_gia_dinh", "Ngăn cản thực hiện quyền, nghĩa vụ giữa ông bà-cháu, cha mẹ-con, vợ-chồng, anh chị em", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_40_Khoan_1_Diem_c"]),
    ("cuong_ep_thanh_vien_hoc_tap_qua_suc", "Cưỡng ép thành viên gia đình học tập quá sức", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_40_Khoan_1_Diem_d"]),
    ("cuong_ep_chung_kien_bao_luc_de_gay_ap_luc", "Cưỡng ép thành viên chứng kiến bạo lực với người hoặc con vật để gây áp lực tâm lý", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_40_Khoan_2_Diem_a"]),
    ("cuong_ep_tiep_nhan_noi_dung_kich_thich_bao_luc", "Cưỡng ép nghe, xem, đọc nội dung kích thích bạo lực", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_40_Khoan_2_Diem_b"]),
    ("co_lap_giam_cam_thanh_vien_gia_dinh", "Cô lập, giam cầm thành viên gia đình", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_40_Khoan_3"]),
    ("cuong_ep_tiep_nhan_noi_dung_khieu_dam", "Cưỡng ép thành viên nghe, xem, đọc nội dung khiêu dâm", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_41_Khoan_1"]),
    ("cuong_ep_trinh_dien_hanh_vi_khieu_dam", "Cưỡng ép thành viên trình diễn hành vi khiêu dâm", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_41_Khoan_2_Diem_a"]),
    ("cuong_ep_quan_he_tinh_duc_trai_y_muon_vo_chong", "Cưỡng ép quan hệ tình dục trái ý muốn của vợ/chồng nhưng chưa bị truy cứu TNHS", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_41_Khoan_2_Diem_b"]),
    ("ngan_can_quyen_tham_nom_cham_soc", "Ngăn cản quyền thăm nom, chăm sóc giữa thành viên gia đình, trừ hạn chế theo quyết định Tòa án", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_42"]),
    ("tron_tranh_cap_duong_vo_chong_hoac_nuoi_duong_ong_ba_chau_anh_chi_em", "Trốn tránh cấp dưỡng giữa vợ chồng sau ly hôn hoặc nuôi dưỡng giữa anh chị em, ông bà và cháu", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_43_Khoan_1_Diem_a", "BoLuat_HinhSu_2015_Dieu_186", "Luat_HNGD_2014_Dieu_3_Khoan_24"]),
    ("tron_tranh_nuoi_duong_cha_me_cap_duong_cham_soc_con", "Trốn tránh nuôi dưỡng cha mẹ hoặc cấp dưỡng, chăm sóc con sau ly hôn", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_43_Khoan_1_Diem_b", "BoLuat_HinhSu_2015_Dieu_186", "Luat_HNGD_2014_Dieu_3_Khoan_24"]),
    ("cap_duong_co_kha_nang_nhung_tu_choi_gay_nguy_hiem", "Có nghĩa vụ và khả năng cấp dưỡng nhưng từ chối/trốn tránh, gây nguy hiểm hoặc tái phạm sau xử phạt VPHC", "DieuKien", ["BoLuat_HinhSu_2015_Dieu_186"]),
    ("chiem_doat_tai_san_gia_dinh", "Chiếm đoạt tài sản chung hoặc tài sản riêng của thành viên gia đình", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_44_Khoan_1_Diem_a"]),
    ("huy_hoai_tai_san_gia_dinh", "Hủy hoại tài sản chung hoặc tài sản riêng nhưng chưa đến mức TNHS", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_44_Khoan_1_Diem_b"]),
    ("cuong_ep_thanh_vien_lao_dong_qua_suc", "Cưỡng ép thành viên gia đình lao động quá sức", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_44_Khoan_1_Diem_c"]),
    ("cuong_ep_dong_gop_tai_chinh_qua_kha_nang", "Cưỡng ép thành viên đóng góp tài chính quá khả năng", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_44_Khoan_1_Diem_d"]),
    ("kiem_soat_tai_san_thu_nhap_tao_le_thuoc", "Kiểm soát tài sản, thu nhập nhằm tạo lệ thuộc vật chất, tinh thần hoặc mặt khác", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_44_Khoan_1_Diem_đ"]),
    ("cuong_ep_ra_khoi_cho_o_hop_phap", "Cưỡng ép thành viên gia đình ra khỏi chỗ ở hợp pháp trái pháp luật", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_45_Khoan_1"]),
    ("de_doa_de_cuong_ep_ra_khoi_cho_o", "Đe dọa sức khỏe, tính mạng để cưỡng ép ra khỏi chỗ ở", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_45_Khoan_2"]),
    ("gay_thuong_tich_de_cuong_ep_ra_khoi_cho_o", "Dùng công cụ, phương tiện gây thương tích để cưỡng ép ra khỏi chỗ ở", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_45_Khoan_3"]),
    ("de_doa_can_tro_nguoi_bao_tin_giup_do", "Đe dọa hoặc cản trở người ngăn chặn, phát hiện, báo tin, tố giác, giúp đỡ", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_46_Khoan_1_Diem_a"]),
    ("xuc_pham_nguoi_bao_tin_giup_do", "Xúc phạm danh dự, nhân phẩm người báo tin, ngăn chặn hoặc giúp đỡ", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_46_Khoan_1_Diem_b"]),
    ("tra_thu_hanh_hung_nguoi_bao_tin_giup_do", "Trả thù, hành hung người báo tin, ngăn chặn hoặc giúp đỡ", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_46_Khoan_2_Diem_a"]),
    ("huy_hoai_tai_san_nguoi_bao_tin_giup_do", "Đập phá, hủy hoại tài sản người báo tin/giúp đỡ nhưng chưa đến mức TNHS", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_46_Khoan_2_Diem_b"]),
    ("xui_giuc_giup_suc_bao_luc_gia_dinh", "Kích động, xúi giục, lôi kéo, dụ dỗ hoặc giúp sức bạo lực gia đình", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_47_Khoan_1"]),
    ("cuong_ep_nguoi_khac_bao_luc_gia_dinh", "Cưỡng ép người khác thực hiện bạo lực gia đình", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_47_Khoan_2"]),
    ("biet_bao_luc_co_dieu_kien_nhung_khong_ngan_chan", "Biết bạo lực, có điều kiện nhưng không ngăn chặn", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_48_Khoan_1_Diem_a"]),
    ("biet_bao_luc_nhung_khong_bao_tin", "Biết bạo lực gia đình nhưng không báo người/cơ quan có thẩm quyền", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_48_Khoan_1_Diem_b"]),
    ("dung_tung_bao_che_bao_luc_gia_dinh", "Dung túng, bao che người có hành vi bạo lực gia đình", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_48_Khoan_1_Diem_c"]),
    ("khong_bo_tri_truc_tong_dai_bao_luc_24_7", "Không bố trí trực Tổng đài quốc gia về phòng, chống bạo lực gia đình 24/7", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_48_Khoan_1_Diem_d"]),
    ("vi_pham_quy_trinh_tiep_nhan_xu_ly_tin_bao_tong_dai", "Không thực hiện đúng, đủ quy trình tiếp nhận/xử lý tin báo qua Tổng đài", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_48_Khoan_1_Diem_đ"]),
    ("can_tro_xu_ly_bao_luc_gia_dinh", "Cản trở việc xử lý hành vi bạo lực gia đình", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_48_Khoan_2_Diem_a"]),
    ("khong_xu_ly_hoac_xu_ly_sai_bao_luc_gia_dinh", "Không xử lý hoặc xử lý không đúng quy định đối với bạo lực gia đình", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_48_Khoan_2_Diem_b"]),
    ("khong_chap_hanh_gop_y_hoac_phuc_vu_cong_dong", "Không chấp hành góp ý phê bình hoặc công việc phục vụ cộng đồng", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_48_Khoan_2_Diem_c"]),
    ("truyen_ba_thong_tin_kich_dong_bao_luc_gia_dinh", "Sử dụng, truyền bá thông tin, tài liệu, hình ảnh, âm thanh kích động bạo lực", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_49"]),
    ("tiet_lo_noi_tam_lanh_cho_nguoi_bao_luc", "Tiết lộ hoặc tạo điều kiện để người bạo lực biết nơi tạm lánh", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_50_Khoan_1_Diem_a"]),
    ("tiet_lo_thong_tin_nguoi_bao_tin_khong_dong_y", "Tiết lộ/phát tán thông tin người báo tin khi chưa được đồng ý", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_50_Khoan_1_Diem_b"]),
    ("khong_cong_khai_bang_gia_dich_vu_tro_giup", "Không công khai bảng giá dịch vụ trợ giúp có thu phí", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_50_Khoan_2"]),
    ("doi_tien_sau_giup_do_hoac_thu_qua_gia_niem_yet", "Đòi tiền sau giúp đỡ hoặc đòi cao hơn giá niêm yết", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_51_Khoan_1_Diem_a"]),
    ("yeu_cau_nan_nhan_tra_chi_phi_noi_tam_lanh", "Yêu cầu nạn nhân trả chi phí sinh hoạt tại địa chỉ tin cậy cộng đồng", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_51_Khoan_1_Diem_b"]),
    ("loi_dung_hoan_canh_nan_nhan_de_yeu_cau_trai_luat", "Lợi dụng hoàn cảnh khó khăn để yêu cầu nạn nhân làm việc trái pháp luật", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_51_Khoan_1_Diem_c"]),
    ("lap_co_so_tro_giup_de_hoat_dong_co_loi_nhuan", "Thành lập cơ sở trợ giúp phòng, chống bạo lực gia đình để hoạt động có lợi nhuận", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_51_Khoan_2_Diem_a"]),
    ("loi_dung_hoat_dong_phong_chong_bao_luc_de_trai_luat", "Lợi dụng hoạt động phòng, chống bạo lực gia đình để thực hiện hành vi trái pháp luật", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_51_Khoan_2_Diem_b"]),
    ("co_so_tro_giup_hoat_dong_ngoai_pham_vi_dang_ky", "Cơ sở trợ giúp hoạt động ngoài phạm vi giấy chứng nhận đăng ký", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_52_Khoan_1"]),
    ("co_so_tro_giup_hoat_dong_chua_dang_ky", "Cơ sở trợ giúp hoạt động khi chưa được cấp giấy chứng nhận hoặc không đăng ký", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_52_Khoan_2"]),
    ("co_tinh_den_gan_nguoi_bi_cam_tiep_xuc", "Cố tình đến gần nạn nhân trong phạm vi 100 m khi đang thi hành quyết định cấm tiếp xúc", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_53_Khoan_1"]),
    ("dung_phuong_tien_de_bao_luc_nguoi_bi_cam_tiep_xuc", "Dùng điện thoại, thư điện tử hoặc công cụ khác để bạo lực với người không được tiếp xúc", "HanhVi", ["NghiDinh_282_2025_ND_CP_Dieu_53_Khoan_2"]),
]
_BAO_GOM: dict[str, list[str]] = {
    "quy_dinh_ket_hon_ly_hon_tong_quat": ["ket_hon_khi_dang_co_vo_chong", "chung_song_voi_nguoi_khac_khi_dang_co_vo_chong", "can_tro_ket_hon_hoac_ly_hon", "cuong_ep_ket_hon_hoac_ly_hon", "ket_hon_gia_tao_de_dat_muc_dich_khac", "ly_hon_gia_tao_de_tron_nghia_vu"],
    "quy_dinh_tao_hon": ["to_chuc_lay_vo_chong_cho_nguoi_chua_du_tuoi", "duy_tri_quan_he_vo_chong_voi_nguoi_chua_du_tuoi_sau_ban_an", "dieu_kien_da_bi_xu_phat_vphc_ma_con_vi_pham"],
    "quy_dinh_mot_vo_mot_chong": ["ket_hon_khi_dang_co_vo_chong", "chung_song_voi_nguoi_khac_khi_dang_co_vo_chong", "chung_song_voi_nguoi_biet_ro_dang_co_vo_chong", "mot_vo_mot_chong_lam_quan_he_hon_nhan_dan_den_ly_hon", "mot_vo_mot_chong_lam_vo_chong_con_tu_sat", "mot_vo_mot_chong_khong_chap_hanh_quyet_dinh_toa"],
    "quy_dinh_can_tro_cuong_ep_ket_hon_ly_hon": ["can_tro_ket_hon_hoac_ly_hon", "yeu_sach_cua_cai_trong_ket_hon", "cuong_ep_ket_hon_hoac_ly_hon", "lua_doi_ket_hon_hoac_ly_hon", "dieu_kien_da_bi_xu_phat_vphc_ma_con_vi_pham"],
    "quy_dinh_quan_he_hon_nhan_bi_cam_vphc": ["ket_hon_chung_song_quan_he_thong_gia_nuoi_duong_cu", "ket_hon_chung_song_cung_dong_mau_truc_he_hoac_ba_doi", "ket_hon_chung_song_cha_me_nuoi_con_nuoi"],
    "quy_dinh_toi_loan_luan": ["giao_cau_voi_nguoi_cung_dong_mau_truc_he_hoac_anh_chi_em"],
    "quy_dinh_ket_hon_ly_hon_gia_tao": ["ket_hon_gia_tao_de_dat_muc_dich_khac", "ly_hon_gia_tao_de_tron_nghia_vu", "bien_phap_nop_lai_loi_bat_hop_phap"],
    "quy_dinh_sinh_con_mang_thai_ho_thuong_mai": ["sinh_con_ho_tro_vi_muc_dich_thuong_mai", "thuc_hien_sinh_san_vo_tinh", "mang_thai_ho_vi_muc_dich_thuong_mai", "to_chuc_mang_thai_ho_vi_muc_dich_thuong_mai"],
    "quy_dinh_vi_pham_giam_ho": ["tron_tranh_khong_thuc_hien_nghia_vu_giam_ho", "loi_dung_giam_ho_de_truc_loi", "loi_dung_giam_ho_xam_pham_tinh_duc_boc_lot"],
    "quy_dinh_vi_pham_nuoi_con_nuoi": ["khai_sai_de_dang_ky_nuoi_con_nuoi", "phan_biet_doi_xu_con_de_con_nuoi", "khong_bao_cao_tinh_hinh_con_nuoi_trong_nuoc", "tay_xoa_giay_to_nuoi_con_nuoi", "loi_dung_cho_con_nuoi_vi_pham_dan_so", "loi_dung_lam_con_nuoi_de_huong_uu_dai", "mua_chuoc_ep_buoc_de_co_dong_y_cho_con_nuoi", "loi_dung_cho_nhan_gioi_thieu_con_nuoi_de_truc_loi", "loi_dung_nhan_con_nuoi_de_boc_lot"],
    "quy_dinh_van_phong_con_nuoi_nuoc_ngoai": ["tay_xoa_ho_so_giay_phep_van_phong_con_nuoi", "khong_thong_bao_cham_dut_van_phong_con_nuoi", "vi_pham_bao_cao_so_sach_van_phong_con_nuoi", "thay_doi_nguoi_dung_dau_van_phong_con_nuoi_chua_duoc_phep", "gioi_thieu_tre_em_lam_con_nuoi_trai_phap_luat", "cho_thue_muon_giay_phep_van_phong_con_nuoi", "su_dung_giay_phep_van_phong_con_nuoi_khac", "van_phong_con_nuoi_hoat_dong_khong_du_dieu_kien", "van_phong_con_nuoi_vi_pham_phi_loi_nhuan"],
    "quy_dinh_bao_luc_the_chat_nguoc_dai": ["de_doa_xam_hai_suc_khoe_tinh_mang_thanh_vien_gia_dinh", "danh_dap_xam_hai_suc_khoe_thanh_vien_gia_dinh", "hanh_ha_nguoc_dai_thanh_vien_gia_dinh", "dung_cong_cu_gay_thuong_tich_thanh_vien_gia_dinh", "khong_cap_cuu_cham_soc_nan_nhan_bao_luc", "nguoc_dai_thuong_xuyen_gay_dau_don", "nguoc_dai_nguoi_duoi_16_mang_thai_gia_yeu"],
    "quy_dinh_bo_mac_khong_cham_soc_giao_duc": ["bo_mac_khong_cham_soc_nguoi_can_cham_soc", "khong_giao_duc_tre_em_trong_gia_dinh"],
    "quy_dinh_xuc_pham_danh_du_bi_mat": ["lang_ma_chiet_chi_xuc_pham_thanh_vien_gia_dinh", "phat_tan_bi_mat_doi_tu_de_xuc_pham"],
    "quy_dinh_co_lap_ap_luc_tam_ly": ["ngan_can_gap_go_quan_he_xa_hoi_hop_phap", "ky_thi_phan_biet_hinh_the_gioi_tinh_nang_luc", "ngan_can_quyen_nghia_vu_trong_quan_he_gia_dinh", "cuong_ep_thanh_vien_hoc_tap_qua_suc", "cuong_ep_chung_kien_bao_luc_de_gay_ap_luc", "cuong_ep_tiep_nhan_noi_dung_kich_thich_bao_luc", "co_lap_giam_cam_thanh_vien_gia_dinh"],
    "quy_dinh_bao_luc_tinh_duc": ["cuong_ep_tiep_nhan_noi_dung_khieu_dam", "cuong_ep_trinh_dien_hanh_vi_khieu_dam", "cuong_ep_quan_he_tinh_duc_trai_y_muon_vo_chong"],
    "quy_dinh_ngan_can_tham_nom_cham_soc": ["ngan_can_quyen_tham_nom_cham_soc"],
    "quy_dinh_cap_duong_nuoi_duong": ["tron_tranh_cap_duong_vo_chong_hoac_nuoi_duong_ong_ba_chau_anh_chi_em", "tron_tranh_nuoi_duong_cha_me_cap_duong_cham_soc_con", "cap_duong_co_kha_nang_nhung_tu_choi_gay_nguy_hiem"],
    "quy_dinh_bao_luc_kinh_te": ["chiem_doat_tai_san_gia_dinh", "huy_hoai_tai_san_gia_dinh", "cuong_ep_thanh_vien_lao_dong_qua_suc", "cuong_ep_dong_gop_tai_chinh_qua_kha_nang", "kiem_soat_tai_san_thu_nhap_tao_le_thuoc"],
    "quy_dinh_cuong_ep_ra_khoi_cho_o": ["cuong_ep_ra_khoi_cho_o_hop_phap", "de_doa_de_cuong_ep_ra_khoi_cho_o", "gay_thuong_tich_de_cuong_ep_ra_khoi_cho_o"],
    "quy_dinh_bao_luc_nguoi_bao_tin_giup_do": ["de_doa_can_tro_nguoi_bao_tin_giup_do", "xuc_pham_nguoi_bao_tin_giup_do", "tra_thu_hanh_hung_nguoi_bao_tin_giup_do", "huy_hoai_tai_san_nguoi_bao_tin_giup_do"],
    "quy_dinh_xui_giuc_cuong_ep_bao_luc": ["xui_giuc_giup_suc_bao_luc_gia_dinh", "cuong_ep_nguoi_khac_bao_luc_gia_dinh"],
    "quy_dinh_ngan_chan_bao_tin_xu_ly": ["biet_bao_luc_co_dieu_kien_nhung_khong_ngan_chan", "biet_bao_luc_nhung_khong_bao_tin", "dung_tung_bao_che_bao_luc_gia_dinh", "khong_bo_tri_truc_tong_dai_bao_luc_24_7", "vi_pham_quy_trinh_tiep_nhan_xu_ly_tin_bao_tong_dai", "can_tro_xu_ly_bao_luc_gia_dinh", "khong_xu_ly_hoac_xu_ly_sai_bao_luc_gia_dinh", "khong_chap_hanh_gop_y_hoac_phuc_vu_cong_dong"],
    "quy_dinh_truyen_ba_kich_dong_bao_luc": ["truyen_ba_thong_tin_kich_dong_bao_luc_gia_dinh"],
    "quy_dinh_tiet_lo_thong_tin_va_bang_gia": ["tiet_lo_noi_tam_lanh_cho_nguoi_bao_luc", "tiet_lo_thong_tin_nguoi_bao_tin_khong_dong_y", "khong_cong_khai_bang_gia_dich_vu_tro_giup"],
    "quy_dinh_loi_dung_hoat_dong_phong_chong_bao_luc": ["doi_tien_sau_giup_do_hoac_thu_qua_gia_niem_yet", "yeu_cau_nan_nhan_tra_chi_phi_noi_tam_lanh", "loi_dung_hoan_canh_nan_nhan_de_yeu_cau_trai_luat", "lap_co_so_tro_giup_de_hoat_dong_co_loi_nhuan", "loi_dung_hoat_dong_phong_chong_bao_luc_de_trai_luat"],
    "quy_dinh_dang_ky_co_so_tro_giup": ["co_so_tro_giup_hoat_dong_ngoai_pham_vi_dang_ky", "co_so_tro_giup_hoat_dong_chua_dang_ky"],
    "quy_dinh_vi_pham_cam_tiep_xuc": ["co_tinh_den_gan_nguoi_bi_cam_tiep_xuc", "dung_phuong_tien_de_bao_luc_nguoi_bi_cam_tiep_xuc"],
}


_DUAL_CHE_TAI_PARENTS = {
    "quy_dinh_tao_hon",
    "quy_dinh_mot_vo_mot_chong",
    "quy_dinh_can_tro_cuong_ep_ket_hon_ly_hon",
    "quy_dinh_bao_luc_the_chat_nguoc_dai",
    "quy_dinh_cap_duong_nuoi_duong",
    "quy_dinh_sinh_con_mang_thai_ho_thuong_mai",
}
_HS_ONLY_PARENTS = {"quy_dinh_toi_loan_luan"}
_VPHC_ONLY_PARENTS = {"quy_dinh_quan_he_hon_nhan_bi_cam_vphc"}


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


def _id_to_label() -> dict[str, str]:
    return {sid: label for sid, _, label, _ in _SEMANTIC_ROWS}


def _refs_by_id() -> dict[str, list[str]]:
    return {sid: refs for sid, _, _, refs in _SEMANTIC_ROWS}


def _has_nghidinh(legal_ids: list[str]) -> bool:
    return any(r.startswith("NghiDinh_") for r in legal_ids)


def _has_blhs(legal_ids: list[str]) -> bool:
    return any(r.startswith("BoLuat_HinhSu_") for r in legal_ids)


def _legal_overlap(parent_refs: list[str], target_refs: list[str]) -> bool:
    for p in parent_refs:
        for t in target_refs:
            if t.startswith(p) or p.startswith(t):
                return True
    return False


def _build_bao_gom_edges(id_label: dict[str, str]) -> list[tuple]:
    edges: list[tuple] = []
    for parent_id, leaf_ids in _BAO_GOM.items():
        for leaf_id in leaf_ids:
            leaf_label = id_label[leaf_id]
            edges.append(("QuyDinh", parent_id, "BAO_GOM", leaf_label, leaf_id))
    return edges


def _build_ap_dung_che_tai_edges(refs_map: dict[str, list[str]]) -> list[tuple]:
    edges: list[tuple] = []
    bo_sung_refs = refs_map["che_tai_hinh_thuc_bo_sung"]
    for sid, _, label, legal_ids in _SEMANTIC_ROWS:
        if label != "QuyDinh":
            continue
        if sid in _DUAL_CHE_TAI_PARENTS:
            edges.append(("QuyDinh", sid, "AP_DUNG_CHE_TAI", "CheTai", "che_tai_vi_pham_hanh_chinh"))
            edges.append(("QuyDinh", sid, "AP_DUNG_CHE_TAI", "CheTai", "che_tai_trach_nhiem_hinh_su"))
        elif sid in _HS_ONLY_PARENTS:
            edges.append(("QuyDinh", sid, "AP_DUNG_CHE_TAI", "CheTai", "che_tai_trach_nhiem_hinh_su"))
        elif sid in _VPHC_ONLY_PARENTS:
            edges.append(("QuyDinh", sid, "AP_DUNG_CHE_TAI", "CheTai", "che_tai_vi_pham_hanh_chinh"))
        else:
            if _has_nghidinh(legal_ids):
                edges.append(("QuyDinh", sid, "AP_DUNG_CHE_TAI", "CheTai", "che_tai_vi_pham_hanh_chinh"))
            if _has_blhs(legal_ids):
                edges.append(("QuyDinh", sid, "AP_DUNG_CHE_TAI", "CheTai", "che_tai_trach_nhiem_hinh_su"))
        if _legal_overlap(legal_ids, bo_sung_refs):
            edges.append(("QuyDinh", sid, "AP_DUNG_CHE_TAI", "CheTai", "che_tai_hinh_thuc_bo_sung"))
    return edges


def _build_co_bien_phap_edges(refs_map: dict[str, list[str]]) -> list[tuple]:
    edges: list[tuple] = []
    for sid, _, label, legal_ids in _SEMANTIC_ROWS:
        if label != "QuyDinh":
            continue
        for bp_sid, _, bp_label, bp_refs in _SEMANTIC_ROWS:
            if bp_label != "BienPhapKhacPhuc":
                continue
            if _legal_overlap(legal_ids, bp_refs):
                edges.append(("QuyDinh", sid, "CO_BIEN_PHAP_KHAC_PHUC", "BienPhapKhacPhuc", bp_sid))
    return edges


def _build_ap_dung_khi_edges(id_label: dict[str, str]) -> list[tuple]:
    edges: list[tuple] = []
    chua_den_refs = _refs_by_id()["dieu_kien_chua_den_muc_truy_cuu_hinh_su"]
    for parent_id, leaf_ids in _BAO_GOM.items():
        for leaf_id in leaf_ids:
            if id_label[leaf_id] == "DieuKien":
                edges.append(("QuyDinh", parent_id, "AP_DUNG_KHI", "DieuKien", leaf_id))
    for sid, _, label, legal_ids in _SEMANTIC_ROWS:
        if label != "HanhVi":
            continue
        if _legal_overlap(legal_ids, chua_den_refs):
            edges.append(("HanhVi", sid, "AP_DUNG_KHI", "DieuKien", "dieu_kien_chua_den_muc_truy_cuu_hinh_su"))
    return edges


def _build_edges() -> list[tuple]:
    id_label = _id_to_label()
    refs_map = _refs_by_id()
    edges: list[tuple] = []
    edges.extend(_build_bao_gom_edges(id_label))
    edges.extend(_build_ap_dung_che_tai_edges(refs_map))
    edges.extend(_build_co_bien_phap_edges(refs_map))
    edges.extend(_build_ap_dung_khi_edges(id_label))
    return edges


NODES = _build_nodes()
CAN_CU_TAI = _build_can_cu_tai()
EDGES = _build_edges()


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
