"""Build KG ngữ nghĩa cho topic quan hệ HNGĐ có yếu tố nước ngoài (Đ121-130).

Cách chạy:
    python scripts/build_kg_quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.py
    python scripts/build_kg_quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.py --reset
    python scripts/build_kg_quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.py --dry-run

Schema: docs/kg_quan_he_hon_nhan_co_yeu_to_nuoc_ngoai_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402

TOPIC = "quan_he_hon_nhan_co_yeu_to_nuoc_ngoai"
TOPIC_LABEL = "QuanHeHonNhanCoYeuToNuocNgoai"

SEMANTIC_LABELS = ['ChuThe', 'CoQuan', 'DieuKien', 'HanhVi', 'HauQua', 'NghiaVu', 'QuanHe', 'QuyDinh', 'Quyen', 'TaiSan']

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    (
        'quan_he_hon_nhan_gia_dinh_co_yeu_to_nuoc_ngoai',
        'Quan hệ hôn nhân và gia đình có yếu tố nước ngoài',
        'QuanHe',
        ['Luat_HNGD_2014_Dieu_121', 'Luat_HNGD_2014_Dieu_122'],
    ),
    (
        'cac_ben_trong_quan_he_co_yeu_to_nuoc_ngoai',
        'Các bên trong quan hệ hôn nhân và gia đình có yếu tố nước ngoài',
        'ChuThe',
        ['Luat_HNGD_2014_Dieu_121'],
    ),
    (
        'bao_ve_quyen_loi_cac_ben',
        'Bảo vệ quyền, lợi ích hợp pháp của các bên',
        'Quyen',
        ['Luat_HNGD_2014_Dieu_121'],
    ),
    (
        'ton_trong_va_bao_ve_tai_viet_nam',
        'Quan hệ có yếu tố nước ngoài được tôn trọng và bảo vệ tại Việt Nam',
        'Quyen',
        ['Luat_HNGD_2014_Dieu_121_Khoan_1'],
    ),
    (
        'phu_hop_phap_luat_viet_nam_va_dieu_uoc_quoc_te',
        'Việc tôn trọng, bảo vệ phù hợp pháp luật Việt Nam và điều ước quốc tế mà Việt Nam là thành viên',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_121_Khoan_1'],
    ),
    (
        'nguoi_nuoc_ngoai_tai_viet_nam_trong_quan_he_voi_cong_dan_viet_nam',
        'Người nước ngoài tại Việt Nam trong quan hệ hôn nhân và gia đình với công dân Việt Nam',
        'ChuThe',
        ['Luat_HNGD_2014_Dieu_121_Khoan_2'],
    ),
    (
        'quyen_nghia_vu_nhu_cong_dan_viet_nam',
        'Người nước ngoài có quyền, nghĩa vụ như công dân Việt Nam',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_121_Khoan_2'],
    ),
    (
        'ngoai_le_do_phap_luat_viet_nam_quy_dinh',
        'Ngoại lệ khi pháp luật Việt Nam có quy định khác',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_121_Khoan_2'],
    ),
    (
        'cong_dan_viet_nam_o_nuoc_ngoai',
        'Công dân Việt Nam ở nước ngoài trong quan hệ hôn nhân và gia đình',
        'ChuThe',
        ['Luat_HNGD_2014_Dieu_121_Khoan_3'],
    ),
    (
        'bao_ho_quyen_loi_cong_dan_viet_nam_o_nuoc_ngoai',
        'Nhà nước Việt Nam bảo hộ quyền, lợi ích hợp pháp của công dân Việt Nam ở nước ngoài',
        'Quyen',
        ['Luat_HNGD_2014_Dieu_121_Khoan_3'],
    ),
    (
        'phu_hop_phap_luat_viet_nam_nuoc_so_tai_va_quoc_te',
        'Việc bảo hộ phù hợp pháp luật Việt Nam, pháp luật nước sở tại, pháp luật và tập quán quốc tế',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_121_Khoan_3'],
    ),
    (
        'chinh_phu',
        'Chính phủ',
        'CoQuan',
        ['Luat_HNGD_2014_Dieu_121_Khoan_4'],
    ),
    (
        'chinh_phu_quy_dinh_chi_tiet_giai_quyet',
        'Quy định chi tiết việc giải quyết quan hệ hôn nhân và gia đình có yếu tố nước ngoài',
        'HanhVi',
        ['Luat_HNGD_2014_Dieu_121_Khoan_4'],
    ),
    (
        'bao_dam_quyen_loi_va_thuc_hien_khoan_2_dieu_5',
        'Bảo đảm quyền, lợi ích hợp pháp của các bên và thực hiện khoản 2 Điều 5',
        'HauQua',
        ['Luat_HNGD_2014_Dieu_121_Khoan_4', 'Luat_HNGD_2014_Dieu_5_Khoan_2'],
    ),
    (
        'nguyen_tac_ap_dung_phap_luat',
        'Nguyên tắc áp dụng pháp luật đối với quan hệ có yếu tố nước ngoài',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_122'],
    ),
    (
        'ap_dung_phap_luat_hon_nhan_gia_dinh_viet_nam',
        'Mặc định áp dụng pháp luật hôn nhân và gia đình Việt Nam',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_122_Khoan_1'],
    ),
    (
        'dieu_uoc_quoc_te_uu_tien_khi_co_quy_dinh_khac',
        'Ưu tiên điều ước quốc tế khi có quy định khác với Luật',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_122_Khoan_1'],
    ),
    (
        'phap_luat_viet_nam_dan_chieu_phap_luat_nuoc_ngoai',
        'Luật hoặc văn bản pháp luật Việt Nam dẫn chiếu áp dụng pháp luật nước ngoài',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_122_Khoan_2'],
    ),
    (
        'ap_dung_phap_luat_nuoc_ngoai_do_dan_chieu_viet_nam',
        'Áp dụng pháp luật nước ngoài theo dẫn chiếu của pháp luật Việt Nam',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_122_Khoan_2'],
    ),
    (
        'khong_trai_nguyen_tac_co_ban_cua_luat',
        'Việc áp dụng pháp luật nước ngoài không trái các nguyên tắc cơ bản tại Điều 2',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_122_Khoan_2', 'Luat_HNGD_2014_Dieu_2'],
    ),
    (
        'dan_chieu_tro_lai_phap_luat_viet_nam',
        'Pháp luật nước ngoài dẫn chiếu trở lại thì áp dụng pháp luật hôn nhân và gia đình Việt Nam',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_122_Khoan_2'],
    ),
    (
        'dieu_uoc_quoc_te_dan_chieu_phap_luat_nuoc_ngoai',
        'Điều ước quốc tế mà Việt Nam là thành viên dẫn chiếu pháp luật nước ngoài',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_122_Khoan_3'],
    ),
    (
        'ap_dung_phap_luat_nuoc_ngoai_do_dan_chieu_dieu_uoc',
        'Áp dụng pháp luật nước ngoài theo dẫn chiếu của điều ước quốc tế',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_122_Khoan_3'],
    ),
    (
        'tham_quyen_giai_quyet_vu_viec_co_yeu_to_nuoc_ngoai',
        'Thẩm quyền giải quyết vụ việc hôn nhân và gia đình có yếu tố nước ngoài',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_123'],
    ),
    (
        'co_quan_dang_ky_ho_tich',
        'Cơ quan đăng ký hộ tịch Việt Nam',
        'CoQuan',
        ['Luat_HNGD_2014_Dieu_123_Khoan_1', 'Luat_HNGD_2014_Dieu_128_Khoan_1'],
    ),
    (
        'dang_ky_ho_tich_theo_phap_luat_ho_tich',
        'Đăng ký hộ tịch theo quy định của pháp luật về hộ tịch',
        'HanhVi',
        ['Luat_HNGD_2014_Dieu_123_Khoan_1'],
    ),
    (
        'toa_an_co_tham_quyen',
        'Tòa án có thẩm quyền giải quyết vụ việc có yếu tố nước ngoài',
        'CoQuan',
        ['Luat_HNGD_2014_Dieu_123_Khoan_2'],
    ),
    (
        'giai_quyet_tai_toa_an_theo_bo_luat_to_tung_dan_su',
        'Thẩm quyền tại Tòa án thực hiện theo Bộ luật tố tụng dân sự',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_123_Khoan_2'],
    ),
    (
        'toa_an_nhan_dan_cap_huyen_noi_cong_dan_viet_nam_cu_tru',
        'Tòa án nhân dân cấp huyện nơi công dân Việt Nam cư trú',
        'CoQuan',
        ['Luat_HNGD_2014_Dieu_123_Khoan_3'],
    ),
    (
        'vu_viec_hon_nhan_gia_dinh_khu_vuc_bien_gioi',
        'Vụ việc hôn nhân và gia đình giữa các bên cùng cư trú ở khu vực biên giới',
        'QuanHe',
        ['Luat_HNGD_2014_Dieu_123_Khoan_3'],
    ),
    (
        'cong_dan_nuoc_lang_gieng_cung_cu_tru_khu_vuc_bien_gioi',
        'Công dân nước láng giềng cùng cư trú ở khu vực biên giới với Việt Nam',
        'ChuThe',
        ['Luat_HNGD_2014_Dieu_123_Khoan_3'],
    ),
    (
        'cap_huyen_giai_quyet_vu_viec_bien_gioi',
        'Cấp huyện giải quyết ly hôn và các tranh chấp được liệt kê tại khu vực biên giới',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_123_Khoan_3'],
    ),
    (
        'giay_to_nuoc_ngoai_dung_giai_quyet_vu_viec_hon_nhan_gia_dinh',
        'Giấy tờ do cơ quan nước ngoài lập, cấp hoặc xác nhận để giải quyết vụ việc hôn nhân và gia đình',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_124'],
    ),
    (
        'hop_phap_hoa_lanh_su',
        'Thực hiện hợp pháp hóa lãnh sự giấy tờ, tài liệu nước ngoài',
        'NghiaVu',
        ['Luat_HNGD_2014_Dieu_124'],
    ),
    (
        'mien_hop_phap_hoa_theo_dieu_uoc_quoc_te',
        'Miễn hợp pháp hóa lãnh sự theo điều ước quốc tế mà Việt Nam là thành viên',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_124'],
    ),
    (
        'mien_hop_phap_hoa_theo_nguyen_tac_co_di_co_lai',
        'Miễn hợp pháp hóa lãnh sự theo nguyên tắc có đi có lại',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_124'],
    ),
    (
        'ban_an_quyet_dinh_toa_an_nuoc_ngoai_co_yeu_cau_thi_hanh',
        'Bản án, quyết định của Tòa án nước ngoài có yêu cầu thi hành tại Việt Nam',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_125_Khoan_1'],
    ),
    (
        'cong_nhan_theo_bo_luat_to_tung_dan_su',
        'Công nhận bản án, quyết định theo Bộ luật tố tụng dân sự',
        'HanhVi',
        ['Luat_HNGD_2014_Dieu_125_Khoan_1'],
    ),
    (
        'ban_an_quyet_dinh_khong_yeu_cau_thi_hanh',
        'Bản án, quyết định nước ngoài không có yêu cầu thi hành tại Việt Nam',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_125_Khoan_2'],
    ),
    (
        'khong_co_don_yeu_cau_khong_cong_nhan_tai_viet_nam',
        'Không có đơn yêu cầu không công nhận tại Việt Nam',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_125_Khoan_2'],
    ),
    (
        'ghi_vao_so_ho_tich',
        'Ghi việc hôn nhân và gia đình theo bản án, quyết định nước ngoài vào sổ hộ tịch',
        'HanhVi',
        ['Luat_HNGD_2014_Dieu_125_Khoan_2'],
    ),
    (
        'quyet_dinh_co_quan_khac_co_tham_quyen_nuoc_ngoai',
        'Quyết định hôn nhân và gia đình của cơ quan khác có thẩm quyền của nước ngoài',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_125_Khoan_2'],
    ),
    (
        'ket_hon_cong_dan_viet_nam_voi_nguoi_nuoc_ngoai',
        'Kết hôn giữa công dân Việt Nam với người nước ngoài',
        'QuanHe',
        ['Luat_HNGD_2014_Dieu_126_Khoan_1'],
    ),
    (
        'moi_ben_tuan_phap_luat_nuoc_minh_ve_dieu_kien_ket_hon',
        'Mỗi bên tuân theo pháp luật của nước mình về điều kiện kết hôn',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_126_Khoan_1'],
    ),
    (
        'ket_hon_tai_co_quan_co_tham_quyen_viet_nam',
        'Việc kết hôn được tiến hành tại cơ quan nhà nước có thẩm quyền của Việt Nam',
        'HanhVi',
        ['Luat_HNGD_2014_Dieu_126_Khoan_1'],
    ),
    (
        'nguoi_nuoc_ngoai_tuan_them_dieu_kien_ket_hon_viet_nam',
        'Người nước ngoài còn phải tuân theo điều kiện kết hôn của Luật Việt Nam khi kết hôn tại cơ quan Việt Nam',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_126_Khoan_1', 'Luat_HNGD_2014_Dieu_8'],
    ),
    (
        'hai_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam',
        'Hai người nước ngoài thường trú tại Việt Nam',
        'ChuThe',
        ['Luat_HNGD_2014_Dieu_126_Khoan_2'],
    ),
    (
        'tuan_dieu_kien_ket_hon_viet_nam',
        'Tuân theo các điều kiện kết hôn của pháp luật Việt Nam',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_126_Khoan_2', 'Luat_HNGD_2014_Dieu_8', 'Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_a', 'Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b', 'Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c', 'Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d'],
    ),
    (
        'ly_hon_co_yeu_to_nuoc_ngoai',
        'Ly hôn có yếu tố nước ngoài',
        'HanhVi',
        ['Luat_HNGD_2014_Dieu_127'],
    ),
    (
        'ly_hon_cong_dan_viet_nam_voi_nguoi_nuoc_ngoai',
        'Ly hôn giữa công dân Việt Nam với người nước ngoài',
        'QuanHe',
        ['Luat_HNGD_2014_Dieu_127_Khoan_1'],
    ),
    (
        'ly_hon_giua_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam',
        'Ly hôn giữa người nước ngoài với nhau thường trú tại Việt Nam',
        'QuanHe',
        ['Luat_HNGD_2014_Dieu_127_Khoan_1'],
    ),
    (
        'co_quan_co_tham_quyen_viet_nam_giai_quyet_ly_hon',
        'Cơ quan có thẩm quyền của Việt Nam giải quyết ly hôn',
        'CoQuan',
        ['Luat_HNGD_2014_Dieu_127_Khoan_1'],
    ),
    (
        'thuan_tinh_ly_hon_co_yeu_to_nuoc_ngoai',
        'Thuận tình ly hôn có yếu tố nước ngoài',
        'HanhVi',
        ['Luat_HNGD_2014_Dieu_127'],
    ),
    (
        'don_phuong_ly_hon_co_yeu_to_nuoc_ngoai',
        'Một bên yêu cầu ly hôn trong quan hệ có yếu tố nước ngoài',
        'HanhVi',
        ['Luat_HNGD_2014_Dieu_127', 'Luat_HNGD_2014_Dieu_51_Khoan_1'],
    ),
    (
        'cong_dan_viet_nam_khong_thuong_tru_tai_viet_nam',
        'Bên là công dân Việt Nam không thường trú tại Việt Nam khi yêu cầu ly hôn',
        'ChuThe',
        ['Luat_HNGD_2014_Dieu_127_Khoan_2'],
    ),
    (
        'phap_luat_noi_thuong_tru_chung_cua_vo_chong',
        'Áp dụng pháp luật của nước nơi thường trú chung của vợ chồng',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_127_Khoan_2'],
    ),
    (
        'khong_co_noi_thuong_tru_chung_ap_dung_phap_luat_viet_nam',
        'Không có nơi thường trú chung thì áp dụng pháp luật Việt Nam',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_127_Khoan_2'],
    ),
    (
        'bat_dong_san_o_nuoc_ngoai',
        'Bất động sản ở nước ngoài khi ly hôn',
        'TaiSan',
        ['Luat_HNGD_2014_Dieu_127_Khoan_3'],
    ),
    (
        'phap_luat_noi_co_bat_dong_san',
        'Áp dụng pháp luật của nước nơi có bất động sản',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_127_Khoan_3'],
    ),
    (
        'xac_dinh_cha_me_con_co_yeu_to_nuoc_ngoai',
        'Xác định cha, mẹ, con có yếu tố nước ngoài',
        'HanhVi',
        ['Luat_HNGD_2014_Dieu_128'],
    ),
    (
        'xac_dinh_cha_me_con_khong_co_tranh_chap',
        'Xác định cha, mẹ, con không có tranh chấp',
        'HanhVi',
        ['Luat_HNGD_2014_Dieu_128_Khoan_1'],
    ),
    (
        'cong_dan_viet_nam_voi_nguoi_nuoc_ngoai',
        'Công dân Việt Nam với người nước ngoài trong việc xác định cha, mẹ, con',
        'ChuThe',
        ['Luat_HNGD_2014_Dieu_128_Khoan_1'],
    ),
    (
        'hai_cong_dan_viet_nam_it_nhat_mot_ben_dinh_cu_o_nuoc_ngoai',
        'Hai công dân Việt Nam mà ít nhất một bên định cư ở nước ngoài',
        'ChuThe',
        ['Luat_HNGD_2014_Dieu_128_Khoan_1'],
    ),
    (
        'hai_nguoi_nuoc_ngoai_it_nhat_mot_ben_thuong_tru_tai_viet_nam',
        'Hai người nước ngoài mà ít nhất một bên thường trú tại Việt Nam',
        'ChuThe',
        ['Luat_HNGD_2014_Dieu_128_Khoan_1'],
    ),
    (
        'xac_dinh_cha_me_con_co_tranh_chap',
        'Xác định cha, mẹ, con có tranh chấp',
        'HanhVi',
        ['Luat_HNGD_2014_Dieu_128_Khoan_2'],
    ),
    (
        'toa_an_viet_nam_giai_quyet_xac_dinh_cha_me_con',
        'Tòa án có thẩm quyền của Việt Nam giải quyết xác định cha, mẹ, con',
        'CoQuan',
        ['Luat_HNGD_2014_Dieu_128_Khoan_2'],
    ),
    (
        'truong_hop_luat_dan_chieu_ve_xac_dinh_cha_me_con',
        'Các trường hợp được Điều 128 khoản 2 dẫn chiếu và các trường hợp khác có tranh chấp',
        'DieuKien',
        ['Luat_HNGD_2014_Dieu_128_Khoan_2'],
    ),
    (
        'nghia_vu_cap_duong_co_yeu_to_nuoc_ngoai',
        'Nghĩa vụ cấp dưỡng có yếu tố nước ngoài',
        'NghiaVu',
        ['Luat_HNGD_2014_Dieu_129'],
    ),
    (
        'nguoi_yeu_cau_cap_duong',
        'Người yêu cầu cấp dưỡng',
        'ChuThe',
        ['Luat_HNGD_2014_Dieu_129_Khoan_1', 'Luat_HNGD_2014_Dieu_129_Khoan_2'],
    ),
    (
        'phap_luat_noi_nguoi_yeu_cau_cap_duong_cu_tru',
        'Nghĩa vụ cấp dưỡng tuân theo pháp luật nước nơi người yêu cầu cư trú',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_129_Khoan_1'],
    ),
    (
        'khong_co_noi_cu_tru_tai_viet_nam_ap_dung_phap_luat_quoc_tich',
        'Người yêu cầu không có nơi cư trú tại Việt Nam thì áp dụng pháp luật nước nơi họ là công dân',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_129_Khoan_1'],
    ),
    (
        'co_quan_noi_nguoi_yeu_cau_cap_duong_cu_tru',
        'Cơ quan của nước nơi người yêu cầu cấp dưỡng cư trú',
        'CoQuan',
        ['Luat_HNGD_2014_Dieu_129_Khoan_2'],
    ),
    (
        'yeu_cau_ap_dung_che_do_tai_san_vo_chong_theo_thoa_thuan',
        'Yêu cầu áp dụng chế độ tài sản của vợ chồng theo thỏa thuận có yếu tố nước ngoài',
        'HanhVi',
        ['Luat_HNGD_2014_Dieu_130'],
    ),
    (
        'chung_song_nhu_vo_chong_khong_dang_ky_co_yeu_to_nuoc_ngoai',
        'Nam, nữ chung sống như vợ chồng không đăng ký kết hôn có yếu tố nước ngoài',
        'QuanHe',
        ['Luat_HNGD_2014_Dieu_130'],
    ),
    (
        'co_quan_co_tham_quyen_viet_nam_giai_quyet',
        'Cơ quan có thẩm quyền của Việt Nam giải quyết yêu cầu tại Điều 130',
        'CoQuan',
        ['Luat_HNGD_2014_Dieu_130'],
    ),
    (
        'ap_dung_luat_hon_nhan_gia_dinh_va_luat_viet_nam_lien_quan',
        'Áp dụng Luật Hôn nhân và gia đình và các luật Việt Nam có liên quan',
        'QuyDinh',
        ['Luat_HNGD_2014_Dieu_130'],
    ),
    (
        'hau_qua_tai_san_khi_cham_dut_chung_song',
        'Giải quyết hậu quả tài sản khi chấm dứt chung sống không đăng ký kết hôn có yếu tố nước ngoài',
        'HauQua',
        ['Luat_HNGD_2014_Dieu_130'],
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
    ('QuanHe', 'quan_he_hon_nhan_gia_dinh_co_yeu_to_nuoc_ngoai', 'BAO_GOM', 'Quyen', 'bao_ve_quyen_loi_cac_ben'),
    ('QuanHe', 'quan_he_hon_nhan_gia_dinh_co_yeu_to_nuoc_ngoai', 'BAO_GOM', 'QuyDinh', 'nguyen_tac_ap_dung_phap_luat'),
    ('QuanHe', 'quan_he_hon_nhan_gia_dinh_co_yeu_to_nuoc_ngoai', 'BAO_GOM', 'QuyDinh', 'tham_quyen_giai_quyet_vu_viec_co_yeu_to_nuoc_ngoai'),
    ('ChuThe', 'cac_ben_trong_quan_he_co_yeu_to_nuoc_ngoai', 'CO_QUYEN', 'Quyen', 'bao_ve_quyen_loi_cac_ben'),
    ('Quyen', 'bao_ve_quyen_loi_cac_ben', 'BAO_GOM', 'Quyen', 'ton_trong_va_bao_ve_tai_viet_nam'),
    ('Quyen', 'ton_trong_va_bao_ve_tai_viet_nam', 'AP_DUNG_KHI', 'DieuKien', 'phu_hop_phap_luat_viet_nam_va_dieu_uoc_quoc_te'),
    ('ChuThe', 'nguoi_nuoc_ngoai_tai_viet_nam_trong_quan_he_voi_cong_dan_viet_nam', 'CO_QUYEN', 'QuyDinh', 'quyen_nghia_vu_nhu_cong_dan_viet_nam'),
    ('QuyDinh', 'quyen_nghia_vu_nhu_cong_dan_viet_nam', 'AP_DUNG_KHI', 'DieuKien', 'ngoai_le_do_phap_luat_viet_nam_quy_dinh'),
    ('ChuThe', 'cong_dan_viet_nam_o_nuoc_ngoai', 'CO_QUYEN', 'Quyen', 'bao_ho_quyen_loi_cong_dan_viet_nam_o_nuoc_ngoai'),
    ('Quyen', 'bao_ho_quyen_loi_cong_dan_viet_nam_o_nuoc_ngoai', 'AP_DUNG_KHI', 'DieuKien', 'phu_hop_phap_luat_viet_nam_nuoc_so_tai_va_quoc_te'),
    ('CoQuan', 'chinh_phu', 'THUC_HIEN', 'HanhVi', 'chinh_phu_quy_dinh_chi_tiet_giai_quyet'),
    ('HanhVi', 'chinh_phu_quy_dinh_chi_tiet_giai_quyet', 'DAN_TOI', 'HauQua', 'bao_dam_quyen_loi_va_thuc_hien_khoan_2_dieu_5'),
    ('QuyDinh', 'nguyen_tac_ap_dung_phap_luat', 'BAO_GOM', 'QuyDinh', 'ap_dung_phap_luat_hon_nhan_gia_dinh_viet_nam'),
    ('QuyDinh', 'nguyen_tac_ap_dung_phap_luat', 'BAO_GOM', 'QuyDinh', 'dieu_uoc_quoc_te_uu_tien_khi_co_quy_dinh_khac'),
    ('QuyDinh', 'nguyen_tac_ap_dung_phap_luat', 'BAO_GOM', 'QuyDinh', 'ap_dung_phap_luat_nuoc_ngoai_do_dan_chieu_viet_nam'),
    ('QuyDinh', 'nguyen_tac_ap_dung_phap_luat', 'BAO_GOM', 'QuyDinh', 'ap_dung_phap_luat_nuoc_ngoai_do_dan_chieu_dieu_uoc'),
    ('QuyDinh', 'ap_dung_phap_luat_nuoc_ngoai_do_dan_chieu_viet_nam', 'AP_DUNG_KHI', 'DieuKien', 'phap_luat_viet_nam_dan_chieu_phap_luat_nuoc_ngoai'),
    ('QuyDinh', 'ap_dung_phap_luat_nuoc_ngoai_do_dan_chieu_viet_nam', 'AP_DUNG_KHI', 'DieuKien', 'khong_trai_nguyen_tac_co_ban_cua_luat'),
    ('QuyDinh', 'ap_dung_phap_luat_nuoc_ngoai_do_dan_chieu_viet_nam', 'DOI_CHIEU_VOI', 'QuyDinh', 'dan_chieu_tro_lai_phap_luat_viet_nam'),
    ('QuyDinh', 'ap_dung_phap_luat_nuoc_ngoai_do_dan_chieu_dieu_uoc', 'AP_DUNG_KHI', 'DieuKien', 'dieu_uoc_quoc_te_dan_chieu_phap_luat_nuoc_ngoai'),
    ('QuyDinh', 'tham_quyen_giai_quyet_vu_viec_co_yeu_to_nuoc_ngoai', 'BAO_GOM', 'HanhVi', 'dang_ky_ho_tich_theo_phap_luat_ho_tich'),
    ('QuyDinh', 'tham_quyen_giai_quyet_vu_viec_co_yeu_to_nuoc_ngoai', 'BAO_GOM', 'QuyDinh', 'giai_quyet_tai_toa_an_theo_bo_luat_to_tung_dan_su'),
    ('CoQuan', 'co_quan_dang_ky_ho_tich', 'THUC_HIEN', 'HanhVi', 'dang_ky_ho_tich_theo_phap_luat_ho_tich'),
    ('CoQuan', 'toa_an_co_tham_quyen', 'LIEN_QUAN', 'QuyDinh', 'giai_quyet_tai_toa_an_theo_bo_luat_to_tung_dan_su'),
    ('CoQuan', 'toa_an_nhan_dan_cap_huyen_noi_cong_dan_viet_nam_cu_tru', 'LIEN_QUAN', 'QuyDinh', 'cap_huyen_giai_quyet_vu_viec_bien_gioi'),
    ('QuyDinh', 'cap_huyen_giai_quyet_vu_viec_bien_gioi', 'AP_DUNG_KHI', 'QuanHe', 'vu_viec_hon_nhan_gia_dinh_khu_vuc_bien_gioi'),
    ('QuanHe', 'vu_viec_hon_nhan_gia_dinh_khu_vuc_bien_gioi', 'LIEN_QUAN', 'ChuThe', 'cong_dan_nuoc_lang_gieng_cung_cu_tru_khu_vuc_bien_gioi'),
    ('QuyDinh', 'giay_to_nuoc_ngoai_dung_giai_quyet_vu_viec_hon_nhan_gia_dinh', 'AP_DUNG_KHI', 'NghiaVu', 'hop_phap_hoa_lanh_su'),
    ('NghiaVu', 'hop_phap_hoa_lanh_su', 'AP_DUNG_KHI', 'DieuKien', 'mien_hop_phap_hoa_theo_dieu_uoc_quoc_te'),
    ('NghiaVu', 'hop_phap_hoa_lanh_su', 'AP_DUNG_KHI', 'DieuKien', 'mien_hop_phap_hoa_theo_nguyen_tac_co_di_co_lai'),
    ('QuyDinh', 'ban_an_quyet_dinh_toa_an_nuoc_ngoai_co_yeu_cau_thi_hanh', 'DAN_TOI', 'HanhVi', 'cong_nhan_theo_bo_luat_to_tung_dan_su'),
    ('QuyDinh', 'ban_an_quyet_dinh_khong_yeu_cau_thi_hanh', 'DAN_TOI', 'HanhVi', 'ghi_vao_so_ho_tich'),
    ('HanhVi', 'ghi_vao_so_ho_tich', 'AP_DUNG_KHI', 'DieuKien', 'khong_co_don_yeu_cau_khong_cong_nhan_tai_viet_nam'),
    ('QuyDinh', 'quyet_dinh_co_quan_khac_co_tham_quyen_nuoc_ngoai', 'LIEN_QUAN', 'HanhVi', 'ghi_vao_so_ho_tich'),
    ('QuanHe', 'ket_hon_cong_dan_viet_nam_voi_nguoi_nuoc_ngoai', 'AP_DUNG_KHI', 'DieuKien', 'moi_ben_tuan_phap_luat_nuoc_minh_ve_dieu_kien_ket_hon'),
    ('HanhVi', 'ket_hon_tai_co_quan_co_tham_quyen_viet_nam', 'AP_DUNG_KHI', 'DieuKien', 'nguoi_nuoc_ngoai_tuan_them_dieu_kien_ket_hon_viet_nam'),
    ('DieuKien', 'tuan_dieu_kien_ket_hon_viet_nam', 'AP_DUNG_KHI', 'ChuThe', 'hai_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam'),
    ('HanhVi', 'ly_hon_co_yeu_to_nuoc_ngoai', 'BAO_GOM', 'HanhVi', 'thuan_tinh_ly_hon_co_yeu_to_nuoc_ngoai'),
    ('HanhVi', 'ly_hon_co_yeu_to_nuoc_ngoai', 'BAO_GOM', 'HanhVi', 'don_phuong_ly_hon_co_yeu_to_nuoc_ngoai'),
    ('HanhVi', 'ly_hon_co_yeu_to_nuoc_ngoai', 'AP_DUNG_KHI', 'QuanHe', 'ly_hon_cong_dan_viet_nam_voi_nguoi_nuoc_ngoai'),
    ('HanhVi', 'ly_hon_co_yeu_to_nuoc_ngoai', 'AP_DUNG_KHI', 'QuanHe', 'ly_hon_giua_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam'),
    ('CoQuan', 'co_quan_co_tham_quyen_viet_nam_giai_quyet_ly_hon', 'THUC_HIEN', 'HanhVi', 'ly_hon_co_yeu_to_nuoc_ngoai'),
    ('QuyDinh', 'phap_luat_noi_thuong_tru_chung_cua_vo_chong', 'AP_DUNG_KHI', 'ChuThe', 'cong_dan_viet_nam_khong_thuong_tru_tai_viet_nam'),
    ('QuyDinh', 'phap_luat_noi_thuong_tru_chung_cua_vo_chong', 'DOI_CHIEU_VOI', 'QuyDinh', 'khong_co_noi_thuong_tru_chung_ap_dung_phap_luat_viet_nam'),
    ('TaiSan', 'bat_dong_san_o_nuoc_ngoai', 'LIEN_QUAN', 'QuyDinh', 'phap_luat_noi_co_bat_dong_san'),
    ('HanhVi', 'xac_dinh_cha_me_con_co_yeu_to_nuoc_ngoai', 'BAO_GOM', 'HanhVi', 'xac_dinh_cha_me_con_khong_co_tranh_chap'),
    ('HanhVi', 'xac_dinh_cha_me_con_co_yeu_to_nuoc_ngoai', 'BAO_GOM', 'HanhVi', 'xac_dinh_cha_me_con_co_tranh_chap'),
    ('CoQuan', 'co_quan_dang_ky_ho_tich', 'THUC_HIEN', 'HanhVi', 'xac_dinh_cha_me_con_khong_co_tranh_chap'),
    ('CoQuan', 'toa_an_viet_nam_giai_quyet_xac_dinh_cha_me_con', 'THUC_HIEN', 'HanhVi', 'xac_dinh_cha_me_con_co_tranh_chap'),
    ('HanhVi', 'xac_dinh_cha_me_con_co_tranh_chap', 'AP_DUNG_KHI', 'DieuKien', 'truong_hop_luat_dan_chieu_ve_xac_dinh_cha_me_con'),
    ('ChuThe', 'nguoi_yeu_cau_cap_duong', 'LIEN_QUAN', 'NghiaVu', 'nghia_vu_cap_duong_co_yeu_to_nuoc_ngoai'),
    ('NghiaVu', 'nghia_vu_cap_duong_co_yeu_to_nuoc_ngoai', 'LIEN_QUAN', 'QuyDinh', 'phap_luat_noi_nguoi_yeu_cau_cap_duong_cu_tru'),
    ('QuyDinh', 'phap_luat_noi_nguoi_yeu_cau_cap_duong_cu_tru', 'DOI_CHIEU_VOI', 'QuyDinh', 'khong_co_noi_cu_tru_tai_viet_nam_ap_dung_phap_luat_quoc_tich'),
    ('CoQuan', 'co_quan_noi_nguoi_yeu_cau_cap_duong_cu_tru', 'LIEN_QUAN', 'ChuThe', 'nguoi_yeu_cau_cap_duong'),
    ('CoQuan', 'co_quan_co_tham_quyen_viet_nam_giai_quyet', 'THUC_HIEN', 'HanhVi', 'yeu_cau_ap_dung_che_do_tai_san_vo_chong_theo_thoa_thuan'),
    ('CoQuan', 'co_quan_co_tham_quyen_viet_nam_giai_quyet', 'LIEN_QUAN', 'QuanHe', 'chung_song_nhu_vo_chong_khong_dang_ky_co_yeu_to_nuoc_ngoai'),
    ('HanhVi', 'yeu_cau_ap_dung_che_do_tai_san_vo_chong_theo_thoa_thuan', 'LIEN_QUAN', 'QuyDinh', 'ap_dung_luat_hon_nhan_gia_dinh_va_luat_viet_nam_lien_quan'),
    ('QuanHe', 'chung_song_nhu_vo_chong_khong_dang_ky_co_yeu_to_nuoc_ngoai', 'DAN_TOI', 'HauQua', 'hau_qua_tai_san_khi_cham_dut_chung_song'),
    ('HauQua', 'hau_qua_tai_san_khi_cham_dut_chung_song', 'LIEN_QUAN', 'QuyDinh', 'ap_dung_luat_hon_nhan_gia_dinh_va_luat_viet_nam_lien_quan'),
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

