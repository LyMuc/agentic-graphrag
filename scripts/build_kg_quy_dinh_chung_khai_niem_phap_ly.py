"""Build KG ngữ nghĩa cho topic 'Quy định chung và khái niệm pháp lý' (quy_dinh_chung_khai_niem_phap_ly).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_quy_dinh_chung_khai_niem_phap_ly.py           # MERGE idempotent
    python scripts/build_kg_quy_dinh_chung_khai_niem_phap_ly.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_quy_dinh_chung_khai_niem_phap_ly.py --dry-run # chỉ in summary

Schema: docs/kg_quy_dinh_chung_khai_niem_phap_ly_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "quy_dinh_chung_khai_niem_phap_ly"
TOPIC_LABEL = "QuyDinhChungKhaiNiemPhapLy"

SEMANTIC_LABELS = [
    "ChuThe",
    "QuyDinh",
    "HanhVi",
    "QuanHe",
    "DieuKien",
    "HauQua",
    "NghiaVu",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    # --- 3.1. Điều 1 - Phạm vi điều chỉnh ---
    (
        "quy_dinh_chung_khai_niem_phap_ly",
        "Quy định chung và hệ thống khái niệm pháp lý của Luật Hôn nhân và gia đình",
        "QuyDinh",
        [
            "Luat_HNGD_2014_Dieu_1",
            "Luat_HNGD_2014_Dieu_2",
            "Luat_HNGD_2014_Dieu_3",
            "Luat_HNGD_2014_Dieu_4",
            "Luat_HNGD_2014_Dieu_5",
            "Luat_HNGD_2014_Dieu_6",
            "Luat_HNGD_2014_Dieu_7",
        ],
    ),
    (
        "pham_vi_dieu_chinh_luat_hngd",
        "Phạm vi điều chỉnh của Luật Hôn nhân và gia đình",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_1"],
    ),
    (
        "che_do_hon_nhan_gia_dinh_thuoc_pham_vi_dieu_chinh",
        "Chế độ hôn nhân và gia đình thuộc phạm vi điều chỉnh của Luật",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_1", "Luat_HNGD_2014_Dieu_3_Khoan_3"],
    ),
    (
        "chuan_muc_ung_xu_giua_thanh_vien_gia_dinh",
        "Chuẩn mực pháp lý cho cách ứng xử giữa các thành viên gia đình",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_1"],
    ),
    (
        "trach_nhiem_xay_dung_cung_co_che_do_hngd",
        "Trách nhiệm của cá nhân, tổ chức, Nhà nước và xã hội trong xây dựng, củng cố chế độ hôn nhân và gia đình",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_1"],
    ),
    # --- 3.2. Điều 2 - Nguyên tắc cơ bản ---
    (
        "nguyen_tac_co_ban_che_do_hngd",
        "Toàn bộ nguyên tắc cơ bản của chế độ hôn nhân và gia đình",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_2"],
    ),
    (
        "hon_nhan_tu_nguyen_tien_bo",
        "Hôn nhân tự nguyện, tiến bộ",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_2_Khoan_1"],
    ),
    (
        "hon_nhan_mot_vo_mot_chong",
        "Hôn nhân một vợ một chồng",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_2_Khoan_1"],
    ),
    (
        "vo_chong_binh_dang",
        "Vợ chồng bình đẳng",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_2_Khoan_1"],
    ),
    (
        "ton_trong_hon_nhan_da_dan_toc_ton_giao_quoc_te",
        "Tôn trọng và bảo vệ hôn nhân khác dân tộc, tôn giáo, tín ngưỡng và hôn nhân giữa công dân Việt Nam với người nước ngoài",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_2_Khoan_2"],
    ),
    (
        "xay_dung_gia_dinh_am_no_tien_bo_hanh_phuc",
        "Xây dựng gia đình ấm no, tiến bộ, hạnh phúc",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_2_Khoan_3"],
    ),
    (
        "thanh_vien_gia_dinh_ton_trong_cham_soc_giup_do",
        "Thành viên gia đình tôn trọng, quan tâm, chăm sóc và giúp đỡ nhau",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_2_Khoan_3"],
    ),
    (
        "khong_phan_biet_doi_xu_giua_cac_con",
        "Không phân biệt đối xử giữa các con",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_2_Khoan_3"],
    ),
    (
        "bao_ve_ho_tro_nhom_yeu_the_va_ba_me",
        "Bảo vệ, hỗ trợ trẻ em, người cao tuổi, người khuyết tật và giúp đỡ các bà mẹ",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_2_Khoan_4"],
    ),
    (
        "thuc_hien_ke_hoach_hoa_gia_dinh",
        "Thực hiện kế hoạch hóa gia đình",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_2_Khoan_4"],
    ),
    (
        "ke_thua_phat_huy_truyen_thong_tot_dep",
        "Kế thừa, phát huy truyền thống văn hóa, đạo đức tốt đẹp về hôn nhân và gia đình",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_2_Khoan_5"],
    ),
    # --- 3.3. Điều 3 - Khái niệm pháp lý ---
    (
        "he_thong_khai_niem_phap_ly_hngd",
        "Hệ thống từ ngữ được giải thích trong Luật Hôn nhân và gia đình",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_3"],
    ),
    (
        "khai_niem_hon_nhan",
        "Hôn nhân là quan hệ giữa vợ và chồng sau khi kết hôn",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_3_Khoan_1"],
    ),
    (
        "khai_niem_gia_dinh",
        "Gia đình là tập hợp người gắn bó do hôn nhân, huyết thống hoặc nuôi dưỡng, làm phát sinh quyền và nghĩa vụ",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_3_Khoan_2"],
    ),
    (
        "khai_niem_che_do_hon_nhan_gia_dinh",
        "Chế độ hôn nhân và gia đình là toàn bộ quy định pháp luật về các quan hệ và vấn đề hôn nhân, gia đình",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_3_Khoan_3"],
    ),
    (
        "khai_niem_tap_quan_hon_nhan_gia_dinh",
        "Tập quán về hôn nhân và gia đình là quy tắc xử sự rõ ràng, lặp lại lâu dài và được thừa nhận rộng rãi",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_3_Khoan_4"],
    ),
    (
        "khai_niem_ket_hon",
        "Kết hôn là việc nam và nữ xác lập quan hệ vợ chồng theo điều kiện và đăng ký kết hôn",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_5"],
    ),
    (
        "khai_niem_ket_hon_trai_phap_luat",
        "Kết hôn trái pháp luật là đã đăng ký kết hôn nhưng một hoặc cả hai bên vi phạm điều kiện tại Điều 8",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_6"],
    ),
    (
        "khai_niem_chung_song_nhu_vo_chong",
        "Chung sống như vợ chồng là nam, nữ tổ chức cuộc sống chung và coi nhau là vợ chồng",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_7"],
    ),
    (
        "khai_niem_tao_hon",
        "Tảo hôn là lấy vợ, lấy chồng khi một hoặc cả hai bên chưa đủ tuổi kết hôn",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_8"],
    ),
    (
        "khai_niem_cuong_ep_ket_hon_ly_hon",
        "Cưỡng ép kết hôn, ly hôn là buộc người khác kết hôn hoặc ly hôn trái ý muốn bằng đe dọa, uy hiếp hoặc hành vi khác",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_9"],
    ),
    (
        "khai_niem_can_tro_ket_hon_ly_hon",
        "Cản trở kết hôn, ly hôn là ngăn cản kết hôn đủ điều kiện hoặc buộc duy trì hôn nhân trái ý muốn",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_10"],
    ),
    (
        "khai_niem_ket_hon_gia_tao",
        "Kết hôn giả tạo là lợi dụng kết hôn để đạt mục đích khác mà không nhằm xây dựng gia đình",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_11"],
    ),
    (
        "khai_niem_yeu_sach_cua_cai_trong_ket_hon",
        "Yêu sách của cải trong kết hôn là đòi hỏi vật chất quá đáng và coi đó là điều kiện kết hôn",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_12"],
    ),
    (
        "khai_niem_thoi_ky_hon_nhan",
        "Thời kỳ hôn nhân là khoảng thời gian tồn tại quan hệ vợ chồng từ ngày đăng ký kết hôn đến ngày chấm dứt hôn nhân",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_3_Khoan_13"],
    ),
    (
        "khai_niem_ly_hon",
        "Ly hôn là chấm dứt quan hệ vợ chồng theo bản án hoặc quyết định có hiệu lực pháp luật của Tòa án",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_14"],
    ),
    (
        "khai_niem_ly_hon_gia_tao",
        "Ly hôn giả tạo là lợi dụng ly hôn để trốn tránh nghĩa vụ hoặc đạt mục đích khác mà không nhằm chấm dứt hôn nhân",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_15"],
    ),
    (
        "khai_niem_thanh_vien_gia_dinh",
        "Thành viên gia đình gồm các chủ thể được liệt kê tại khoản 16 Điều 3",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_3_Khoan_16"],
    ),
    (
        "khai_niem_cung_dong_mau_ve_truc_he",
        "Những người cùng dòng máu về trực hệ là người có quan hệ huyết thống, người này sinh ra người kia kế tiếp nhau",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_3_Khoan_17"],
    ),
    (
        "khai_niem_ho_trong_pham_vi_ba_doi",
        "Người có họ trong phạm vi ba đời là những người cùng một gốc sinh ra thuộc đời thứ nhất, thứ hai hoặc thứ ba",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_3_Khoan_18"],
    ),
    (
        "cha_me_la_doi_thu_nhat",
        "Cha mẹ là đời thứ nhất trong cách tính phạm vi ba đời",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_3_Khoan_18"],
    ),
    (
        "anh_chi_em_la_doi_thu_hai",
        "Anh, chị, em cùng cha mẹ, cùng cha khác mẹ hoặc cùng mẹ khác cha là đời thứ hai",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_3_Khoan_18"],
    ),
    (
        "anh_chi_em_ho_la_doi_thu_ba",
        "Anh, chị, em con chú, bác, cô, cậu, dì là đời thứ ba",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_3_Khoan_18"],
    ),
    (
        "khai_niem_nguoi_than_thich",
        "Người thân thích là người có quan hệ hôn nhân, nuôi dưỡng, trực hệ hoặc có họ trong phạm vi ba đời",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_3_Khoan_19"],
    ),
    (
        "khai_niem_nhu_cau_thiet_yeu",
        "Nhu cầu thiết yếu là các nhu cầu sinh hoạt thông thường không thể thiếu",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_3_Khoan_20"],
    ),
    (
        "khai_niem_sinh_con_bang_ky_thuat_ho_tro_sinh_san",
        "Sinh con bằng kỹ thuật hỗ trợ sinh sản là sinh con bằng thụ tinh nhân tạo hoặc thụ tinh trong ống nghiệm",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_21"],
    ),
    (
        "khai_niem_mang_thai_ho_vi_muc_dich_nhan_dao",
        "Mang thai hộ vì mục đích nhân đạo là việc tự nguyện giúp mang thai, không vì mục đích thương mại, theo điều kiện luật định",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_22"],
    ),
    (
        "khai_niem_mang_thai_ho_vi_muc_dich_thuong_mai",
        "Mang thai hộ vì mục đích thương mại là mang thai cho người khác để hưởng lợi kinh tế hoặc lợi ích khác",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_23"],
    ),
    (
        "khai_niem_cap_duong",
        "Cấp dưỡng là nghĩa vụ đóng góp tiền hoặc tài sản để đáp ứng nhu cầu thiết yếu cho người có quan hệ luật định và thuộc trường hợp cần được cấp dưỡng",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_3_Khoan_24"],
    ),
    (
        "khai_niem_quan_he_hngd_co_yeu_to_nuoc_ngoai",
        "Quan hệ hôn nhân và gia đình có yếu tố nước ngoài là quan hệ có chủ thể, căn cứ xác lập hoặc tài sản gắn với nước ngoài theo khoản 25 Điều 3",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_3_Khoan_25"],
    ),
    # --- 3.4. Điều 4 - Trách nhiệm của Nhà nước và xã hội ---
    (
        "trach_nhiem_nha_nuoc_xa_hoi_ve_hngd",
        "Toàn bộ trách nhiệm của Nhà nước và xã hội đối với hôn nhân và gia đình",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_4"],
    ),
    (
        "chu_the_nha_nuoc",
        "Nhà nước trong trách nhiệm bảo hộ hôn nhân và gia đình",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_4_Khoan_1"],
    ),
    (
        "chu_the_chinh_phu",
        "Chính phủ là cơ quan thống nhất quản lý nhà nước về hôn nhân và gia đình",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_4_Khoan_2"],
    ),
    (
        "chu_the_bo_co_quan_ngang_bo",
        "Các bộ và cơ quan ngang bộ quản lý theo phân công của Chính phủ",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_4_Khoan_2"],
    ),
    (
        "chu_the_uy_ban_nhan_dan_va_co_quan_khac",
        "Ủy ban nhân dân các cấp và cơ quan khác quản lý theo quy định pháp luật",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_4_Khoan_2"],
    ),
    (
        "chu_the_co_quan_to_chuc",
        "Cơ quan, tổ chức có trách nhiệm giáo dục, vận động và bảo vệ thành viên gia đình",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_4_Khoan_3"],
    ),
    (
        "chu_the_nha_truong",
        "Nhà trường phối hợp với gia đình giáo dục pháp luật cho thế hệ trẻ",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_4_Khoan_3"],
    ),
    (
        "chu_the_gia_dinh_trong_giao_duc",
        "Gia đình phối hợp với nhà trường trong giáo dục thế hệ trẻ",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_4_Khoan_3"],
    ),
    (
        "bao_ho_va_tao_dieu_kien_xac_lap_hon_nhan",
        "Có chính sách, biện pháp bảo hộ và tạo điều kiện xác lập hôn nhân tự nguyện, tiến bộ, một vợ một chồng, bình đẳng",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_4_Khoan_1"],
    ),
    (
        "tuyen_truyen_pho_bien_giao_duc_phap_luat_hngd",
        "Tăng cường tuyên truyền, phổ biến, giáo dục pháp luật về hôn nhân và gia đình",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_4_Khoan_1"],
    ),
    (
        "xoa_bo_tap_quan_lac_hau_phat_huy_ban_sac",
        "Vận động xóa bỏ phong tục lạc hậu và phát huy phong tục tốt đẹp thể hiện bản sắc dân tộc",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_4_Khoan_1"],
    ),
    (
        "thong_nhat_quan_ly_nha_nuoc_ve_hngd",
        "Thống nhất quản lý nhà nước về hôn nhân và gia đình",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_4_Khoan_2"],
    ),
    (
        "quan_ly_nha_nuoc_theo_phan_cong",
        "Thực hiện quản lý nhà nước theo phân công của Chính phủ hoặc theo quy định pháp luật",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_4_Khoan_2"],
    ),
    (
        "giao_duc_van_dong_xay_dung_gia_dinh_van_hoa",
        "Giáo dục, vận động thành viên và công dân xây dựng gia đình văn hóa",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_4_Khoan_3"],
    ),
    (
        "hoa_giai_mau_thuan_bao_ve_quyen_loi_thanh_vien",
        "Kịp thời hòa giải mâu thuẫn và bảo vệ quyền, lợi ích hợp pháp của thành viên gia đình",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_4_Khoan_3"],
    ),
    (
        "phoi_hop_gia_dinh_giao_duc_the_he_tre",
        "Nhà trường phối hợp với gia đình giáo dục, tuyên truyền, phổ biến pháp luật cho thế hệ trẻ",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_4_Khoan_3"],
    ),
    # --- 3.5. Điều 5 - Bảo vệ chế độ và hành vi bị cấm ---
    (
        "bao_ve_che_do_hon_nhan_gia_dinh",
        "Bảo vệ chế độ hôn nhân và gia đình",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_5"],
    ),
    (
        "quan_he_hngd_hop_phap_duoc_ton_trong_bao_ve",
        "Quan hệ hôn nhân và gia đình xác lập, thực hiện đúng luật được tôn trọng và bảo vệ",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_5_Khoan_1"],
    ),
    (
        "cac_hanh_vi_bi_cam_trong_hngd",
        "Toàn bộ hành vi bị cấm trong lĩnh vực hôn nhân và gia đình",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_5_Khoan_2"],
    ),
    (
        "hanh_vi_cam_ket_hon_ly_hon_gia_tao",
        "Kết hôn giả tạo, ly hôn giả tạo",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_a"],
    ),
    (
        "hanh_vi_cam_tao_hon_cuong_ep_lua_doi_can_tro_ket_hon",
        "Tảo hôn, cưỡng ép kết hôn, lừa dối kết hôn, cản trở kết hôn",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b"],
    ),
    (
        "hanh_vi_cam_vi_pham_mot_vo_mot_chong",
        "Kết hôn hoặc chung sống như vợ chồng với người khác khi một bên đang có vợ hoặc chồng",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c"],
    ),
    (
        "chung_song_voi_nguoi_khac_khi_dang_co_vo_chong",
        "Người đang có vợ, chồng chung sống như vợ chồng với người khác hoặc người độc thân chung sống như vợ chồng với người đang có vợ, chồng",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_3_Khoan_7", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c"],
    ),
    (
        "hanh_vi_cam_quan_he_than_thich",
        "Kết hôn hoặc chung sống như vợ chồng trong các quan hệ huyết thống, nuôi dưỡng và thông gia bị liệt kê",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"],
    ),
    (
        "hanh_vi_cam_yeu_sach_cua_cai",
        "Yêu sách của cải trong kết hôn",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_5_Khoan_2"],
    ),
    (
        "hanh_vi_cam_cuong_ep_lua_doi_can_tro_ly_hon",
        "Cưỡng ép ly hôn, lừa dối ly hôn, cản trở ly hôn",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_5_Khoan_2"],
    ),
    (
        "hanh_vi_cam_sinh_san_thuong_mai_lua_chon_gioi_tinh",
        "Sinh sản hoặc mang thai hộ vì mục đích thương mại, lựa chọn giới tính thai nhi, sinh sản vô tính",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_5_Khoan_2"],
    ),
    (
        "hanh_vi_cam_bao_luc_gia_dinh",
        "Bạo lực gia đình",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_5_Khoan_2"],
    ),
    (
        "hanh_vi_cam_loi_dung_quyen_hngd_de_truc_loi",
        "Lợi dụng quyền về hôn nhân và gia đình để mua bán người, bóc lột, xâm phạm tình dục hoặc trục lợi",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_5_Khoan_2"],
    ),
    (
        "ly_than_khong_tu_cham_dut_thoi_ky_hon_nhan",
        "Ly thân không tự chấm dứt thời kỳ hôn nhân nếu chưa có căn cứ chấm dứt hôn nhân theo luật",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_3_Khoan_13", "Luat_HNGD_2014_Dieu_3_Khoan_14"],
    ),
    (
        "qua_lai_tinh_cam_can_xac_minh_muc_do",
        'Việc "qua lại" cần xác minh có đạt mức kết hôn hoặc tổ chức cuộc sống chung và coi nhau là vợ chồng hay không',
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_3_Khoan_7", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c"],
    ),
    (
        "xu_ly_nghiem_hanh_vi_vi_pham_hngd",
        "Hành vi vi phạm pháp luật hôn nhân và gia đình phải được xử lý nghiêm minh, đúng pháp luật",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_5_Khoan_3"],
    ),
    (
        "quyen_yeu_cau_ngan_chan_xu_ly_vi_pham",
        "Cơ quan, tổ chức, cá nhân có quyền yêu cầu áp dụng biện pháp ngăn chặn và xử lý vi phạm",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_5_Khoan_3"],
    ),
    (
        "ton_trong_bao_ve_danh_du_nhan_pham_rieng_tu",
        "Danh dự, nhân phẩm, uy tín, bí mật đời tư và quyền riêng tư được tôn trọng, bảo vệ khi giải quyết vụ việc",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_5_Khoan_4"],
    ),
    # --- 3.6. Điều 6-7 - Áp dụng luật liên quan và tập quán ---
    (
        "ap_dung_bo_luat_dan_su_va_luat_lien_quan",
        "Áp dụng Bộ luật dân sự và luật khác có liên quan đến quan hệ hôn nhân và gia đình",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_6"],
    ),
    (
        "dieu_kien_luat_hngd_khong_quy_dinh",
        "Chỉ áp dụng luật liên quan đối với vấn đề Luật Hôn nhân và gia đình không quy định",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_6"],
    ),
    (
        "ap_dung_tap_quan_hon_nhan_gia_dinh",
        "Áp dụng tập quán tốt đẹp về hôn nhân và gia đình khi đủ điều kiện luật định",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_7_Khoan_1"],
    ),
    (
        "dieu_kien_phap_luat_khong_quy_dinh",
        "Pháp luật không quy định vấn đề cần giải quyết",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_7_Khoan_1"],
    ),
    (
        "dieu_kien_cac_ben_khong_co_thoa_thuan",
        "Các bên không có thỏa thuận về vấn đề cần giải quyết",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_7_Khoan_1"],
    ),
    (
        "tap_quan_tot_dep_khong_trai_nguyen_tac_va_dieu_cam",
        "Tập quán phải tốt đẹp, thể hiện bản sắc dân tộc, không trái Điều 2 và không vi phạm điều cấm",
        "DieuKien",
        [
            "Luat_HNGD_2014_Dieu_7_Khoan_1",
            "Luat_HNGD_2014_Dieu_2",
            "Luat_HNGD_2014_Dieu_5_Khoan_2",
        ],
    ),
    (
        "chinh_phu_quy_dinh_chi_tiet_ap_dung_tap_quan",
        "Chính phủ quy định chi tiết việc áp dụng tập quán",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_7_Khoan_2"],
    ),
]

_ID_TO_LABEL: dict[str, str] = {sid: label for sid, _, label, _ in _SEMANTIC_ROWS}

_ROOT_BRANCHES = [
    "pham_vi_dieu_chinh_luat_hngd",
    "nguyen_tac_co_ban_che_do_hngd",
    "he_thong_khai_niem_phap_ly_hngd",
    "trach_nhiem_nha_nuoc_xa_hoi_ve_hngd",
    "bao_ve_che_do_hon_nhan_gia_dinh",
    "ap_dung_bo_luat_dan_su_va_luat_lien_quan",
    "ap_dung_tap_quan_hon_nhan_gia_dinh",
]

_3_2_CHILDREN = [
    "hon_nhan_tu_nguyen_tien_bo",
    "hon_nhan_mot_vo_mot_chong",
    "vo_chong_binh_dang",
    "ton_trong_hon_nhan_da_dan_toc_ton_giao_quoc_te",
    "xay_dung_gia_dinh_am_no_tien_bo_hanh_phuc",
    "thanh_vien_gia_dinh_ton_trong_cham_soc_giup_do",
    "khong_phan_biet_doi_xu_giua_cac_con",
    "bao_ve_ho_tro_nhom_yeu_the_va_ba_me",
    "thuc_hien_ke_hoach_hoa_gia_dinh",
    "ke_thua_phat_huy_truyen_thong_tot_dep",
]

_3_3_CHILDREN = [
    "khai_niem_hon_nhan",
    "khai_niem_gia_dinh",
    "khai_niem_che_do_hon_nhan_gia_dinh",
    "khai_niem_tap_quan_hon_nhan_gia_dinh",
    "khai_niem_ket_hon",
    "khai_niem_ket_hon_trai_phap_luat",
    "khai_niem_chung_song_nhu_vo_chong",
    "khai_niem_tao_hon",
    "khai_niem_cuong_ep_ket_hon_ly_hon",
    "khai_niem_can_tro_ket_hon_ly_hon",
    "khai_niem_ket_hon_gia_tao",
    "khai_niem_yeu_sach_cua_cai_trong_ket_hon",
    "khai_niem_thoi_ky_hon_nhan",
    "khai_niem_ly_hon",
    "khai_niem_ly_hon_gia_tao",
    "khai_niem_thanh_vien_gia_dinh",
    "khai_niem_cung_dong_mau_ve_truc_he",
    "khai_niem_ho_trong_pham_vi_ba_doi",
    "cha_me_la_doi_thu_nhat",
    "anh_chi_em_la_doi_thu_hai",
    "anh_chi_em_ho_la_doi_thu_ba",
    "khai_niem_nguoi_than_thich",
    "khai_niem_nhu_cau_thiet_yeu",
    "khai_niem_sinh_con_bang_ky_thuat_ho_tro_sinh_san",
    "khai_niem_mang_thai_ho_vi_muc_dich_nhan_dao",
    "khai_niem_mang_thai_ho_vi_muc_dich_thuong_mai",
    "khai_niem_cap_duong",
    "khai_niem_quan_he_hngd_co_yeu_to_nuoc_ngoai",
]

_3_4_CHU_THE_AND_NGHIA_VU = [
    "chu_the_nha_nuoc",
    "chu_the_chinh_phu",
    "chu_the_bo_co_quan_ngang_bo",
    "chu_the_uy_ban_nhan_dan_va_co_quan_khac",
    "chu_the_co_quan_to_chuc",
    "chu_the_nha_truong",
    "chu_the_gia_dinh_trong_giao_duc",
    "bao_ho_va_tao_dieu_kien_xac_lap_hon_nhan",
    "tuyen_truyen_pho_bien_giao_duc_phap_luat_hngd",
    "xoa_bo_tap_quan_lac_hau_phat_huy_ban_sac",
    "thong_nhat_quan_ly_nha_nuoc_ve_hngd",
    "quan_ly_nha_nuoc_theo_phan_cong",
    "giao_duc_van_dong_xay_dung_gia_dinh_van_hoa",
    "hoa_giai_mau_thuan_bao_ve_quyen_loi_thanh_vien",
    "phoi_hop_gia_dinh_giao_duc_the_he_tre",
]

_HANH_VI_CAM_IDS = [
    sid for sid, _, label, _ in _SEMANTIC_ROWS if sid.startswith("hanh_vi_cam_")
]

_BAO_VE_CHE_DO_CHILDREN = [
    "quan_he_hngd_hop_phap_duoc_ton_trong_bao_ve",
    "cac_hanh_vi_bi_cam_trong_hngd",
    "xu_ly_nghiem_hanh_vi_vi_pham_hngd",
    "quyen_yeu_cau_ngan_chan_xu_ly_vi_pham",
    "ton_trong_bao_ve_danh_du_nhan_pham_rieng_tu",
]

_CO_TRACH_NHIEM_EDGES: list[tuple[str, str]] = [
    ("chu_the_nha_nuoc", "bao_ho_va_tao_dieu_kien_xac_lap_hon_nhan"),
    ("chu_the_nha_nuoc", "tuyen_truyen_pho_bien_giao_duc_phap_luat_hngd"),
    ("chu_the_nha_nuoc", "xoa_bo_tap_quan_lac_hau_phat_huy_ban_sac"),
    ("chu_the_chinh_phu", "thong_nhat_quan_ly_nha_nuoc_ve_hngd"),
    ("chu_the_chinh_phu", "chinh_phu_quy_dinh_chi_tiet_ap_dung_tap_quan"),
    ("chu_the_bo_co_quan_ngang_bo", "quan_ly_nha_nuoc_theo_phan_cong"),
    ("chu_the_uy_ban_nhan_dan_va_co_quan_khac", "quan_ly_nha_nuoc_theo_phan_cong"),
    ("chu_the_co_quan_to_chuc", "giao_duc_van_dong_xay_dung_gia_dinh_van_hoa"),
    ("chu_the_co_quan_to_chuc", "hoa_giai_mau_thuan_bao_ve_quyen_loi_thanh_vien"),
    ("chu_the_nha_truong", "phoi_hop_gia_dinh_giao_duc_the_he_tre"),
    ("chu_the_gia_dinh_trong_giao_duc", "phoi_hop_gia_dinh_giao_duc_the_he_tre"),
]


def _edge(src_id: str, rel: str, dst_id: str) -> tuple:
    return (_ID_TO_LABEL[src_id], src_id, rel, _ID_TO_LABEL[dst_id], dst_id)


def _bao_gom(parent_id: str, child_ids: list[str]) -> list[tuple]:
    return [_edge(parent_id, "BAO_GOM", cid) for cid in child_ids]


def _build_edges() -> list[tuple]:
    edges: list[tuple] = []

    edges.extend(_bao_gom("quy_dinh_chung_khai_niem_phap_ly", _ROOT_BRANCHES))
    edges.extend(_bao_gom("nguyen_tac_co_ban_che_do_hngd", _3_2_CHILDREN))
    edges.extend(_bao_gom("he_thong_khai_niem_phap_ly_hngd", _3_3_CHILDREN))
    edges.extend(_bao_gom("trach_nhiem_nha_nuoc_xa_hoi_ve_hngd", _3_4_CHU_THE_AND_NGHIA_VU))
    edges.extend(_bao_gom("bao_ve_che_do_hon_nhan_gia_dinh", _BAO_VE_CHE_DO_CHILDREN))
    edges.extend(_bao_gom("cac_hanh_vi_bi_cam_trong_hngd", _HANH_VI_CAM_IDS))

    for src_id, dst_id in _CO_TRACH_NHIEM_EDGES:
        edges.append(_edge(src_id, "CO_TRACH_NHIEM", dst_id))

    edges.append(
        _edge(
            "hanh_vi_cam_vi_pham_mot_vo_mot_chong",
            "BAO_GOM",
            "chung_song_voi_nguoi_khac_khi_dang_co_vo_chong",
        )
    )
    edges.append(
        _edge("hanh_vi_cam_vi_pham_mot_vo_mot_chong", "VI_PHAM", "hon_nhan_mot_vo_mot_chong")
    )
    edges.append(
        _edge("hanh_vi_cam_vi_pham_mot_vo_mot_chong", "DAN_TOI", "xu_ly_nghiem_hanh_vi_vi_pham_hngd")
    )

    edges.append(
        _edge("ly_than_khong_tu_cham_dut_thoi_ky_hon_nhan", "DOI_CHIEU_VOI", "khai_niem_thoi_ky_hon_nhan")
    )
    edges.append(
        _edge("ly_than_khong_tu_cham_dut_thoi_ky_hon_nhan", "DOI_CHIEU_VOI", "khai_niem_ly_hon")
    )
    edges.append(
        _edge("qua_lai_tinh_cam_can_xac_minh_muc_do", "DOI_CHIEU_VOI", "khai_niem_chung_song_nhu_vo_chong")
    )
    edges.append(
        _edge(
            "qua_lai_tinh_cam_can_xac_minh_muc_do",
            "DOI_CHIEU_VOI",
            "chung_song_voi_nguoi_khac_khi_dang_co_vo_chong",
        )
    )

    edges.append(
        _edge("ap_dung_bo_luat_dan_su_va_luat_lien_quan", "AP_DUNG_KHI", "dieu_kien_luat_hngd_khong_quy_dinh")
    )
    edges.extend(
        [
            _edge("ap_dung_tap_quan_hon_nhan_gia_dinh", "AP_DUNG_KHI", "dieu_kien_phap_luat_khong_quy_dinh"),
            _edge("ap_dung_tap_quan_hon_nhan_gia_dinh", "AP_DUNG_KHI", "dieu_kien_cac_ben_khong_co_thoa_thuan"),
            _edge(
                "ap_dung_tap_quan_hon_nhan_gia_dinh",
                "AP_DUNG_KHI",
                "tap_quan_tot_dep_khong_trai_nguyen_tac_va_dieu_cam",
            ),
            _edge("ap_dung_tap_quan_hon_nhan_gia_dinh", "KHONG_DUOC_TRAI", "nguyen_tac_co_ban_che_do_hngd"),
            _edge("ap_dung_tap_quan_hon_nhan_gia_dinh", "KHONG_DUOC_TRAI", "cac_hanh_vi_bi_cam_trong_hngd"),
        ]
    )

    return edges


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
