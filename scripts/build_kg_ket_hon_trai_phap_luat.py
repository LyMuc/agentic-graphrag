"""Build KG ngữ nghĩa cho topic 'Kết hôn trái pháp luật' (Đ3 K6, Đ10-12 + TTLT 01/2016 Đ2-4).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_ket_hon_trai_phap_luat.py           # MERGE idempotent
    python scripts/build_kg_ket_hon_trai_phap_luat.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_ket_hon_trai_phap_luat.py --dry-run # chỉ in summary

Schema: docs/kg_ket_hon_trai_phap_luat_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "ket_hon_trai_phap_luat"
TOPIC_LABEL = "KetHonTraiPhapLuat"

SEMANTIC_LABELS = [
    "QuyDinh",
    "ChuThe",
    "Quyen",
    "HanhVi",
    "DieuKien",
    "HauQua",
    "TinhTrangHonNhan",
    "TaiLieu",
]

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    (
        "dinh_nghia_ket_hon_trai_phap_luat",
        "Kết hôn trái pháp luật là việc nam, nữ đã đăng ký kết hôn tại cơ quan có thẩm quyền nhưng một bên hoặc cả hai vi phạm điều kiện kết hôn",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_3_Khoan_6"],
    ),
    (
        "can_cu_huy_ket_hon_trai_phap_luat",
        "Căn cứ hủy được xác định bằng việc đối chiếu các điều kiện kết hôn và các lưu ý hướng dẫn",
        "QuyDinh",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_2"],
    ),
    (
        "nguyen_tac_xu_ly_yeu_cau_huy_ket_hon_trai_phap_luat",
        "Tòa án xử lý yêu cầu theo tình trạng điều kiện kết hôn và yêu cầu của các bên",
        "QuyDinh",
        [
            "Luat_HNGD_2014_Dieu_11",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_1",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_4",
        ],
    ),
    (
        "nhom_hau_qua_huy_ket_hon_trai_phap_luat",
        "Nhóm hậu quả về quan hệ vợ chồng, cha mẹ con, tài sản, nghĩa vụ và hợp đồng",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_12"],
    ),
    (
        "hai_ben_ket_hon_trai_phap_luat",
        "Hai bên nam, nữ trong quan hệ kết hôn trái pháp luật",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_3_Khoan_6", "Luat_HNGD_2014_Dieu_11"],
    ),
    (
        "nguoi_bi_cuong_ep_hoac_lua_doi_ket_hon",
        "Người bị cưỡng ép hoặc bị lừa dối dẫn đến việc đồng ý kết hôn",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_10_Khoan_1"],
    ),
    (
        "vo_chong_hop_phap_cua_nguoi_dang_co_vo_chong",
        "Vợ hoặc chồng hợp pháp của người đang có vợ, có chồng mà kết hôn với người khác",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_10_Khoan_2_Diem_a"],
    ),
    (
        "cha_me_con_nguoi_giam_ho_hoac_dai_dien_hop_phap",
        "Cha, mẹ, con, người giám hộ hoặc người đại diện theo pháp luật khác của người kết hôn trái pháp luật",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_10_Khoan_2_Diem_a"],
    ),
    (
        "co_quan_quan_ly_nha_nuoc_ve_gia_dinh",
        "Cơ quan quản lý nhà nước về gia đình",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_10_Khoan_2_Diem_b"],
    ),
    (
        "co_quan_quan_ly_nha_nuoc_ve_tre_em",
        "Cơ quan quản lý nhà nước về trẻ em",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_10_Khoan_2_Diem_c"],
    ),
    (
        "hoi_lien_hiep_phu_nu",
        "Hội liên hiệp phụ nữ",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_10_Khoan_2_Diem_d"],
    ),
    (
        "ca_nhan_co_quan_to_chuc_khac_phat_hien_vi_pham",
        "Cá nhân, cơ quan, tổ chức khác phát hiện việc kết hôn trái pháp luật",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_10_Khoan_3"],
    ),
    (
        "toa_an_giai_quyet_yeu_cau_huy_ket_hon_trai_phap_luat",
        "Tòa án thụ lý và giải quyết yêu cầu hủy kết hôn trái pháp luật",
        "ChuThe",
        [
            "Luat_HNGD_2014_Dieu_11_Khoan_1",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_2",
        ],
    ),
    (
        "co_quan_da_thuc_hien_dang_ky_ket_hon",
        "Cơ quan đã thực hiện việc đăng ký kết hôn và ghi nhận kết quả xử lý",
        "ChuThe",
        [
            "Luat_HNGD_2014_Dieu_11_Khoan_3",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_1",
        ],
    ),
    (
        "hai_ben_chung_song_khong_dang_ky_ket_hon",
        "Nam, nữ chung sống như vợ chồng nhưng không có đăng ký kết hôn",
        "ChuThe",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_4"],
    ),
    (
        "quyen_tu_minh_yeu_cau_huy_cua_nguoi_bi_cuong_ep_lua_doi",
        "Quyền tự mình yêu cầu Tòa án hủy của người bị cưỡng ép hoặc lừa dối kết hôn",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_10_Khoan_1"],
    ),
    (
        "quyen_de_nghi_chu_the_luat_dinh_yeu_cau_huy",
        "Quyền đề nghị cá nhân, tổ chức luật định yêu cầu Tòa án hủy",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_10_Khoan_1"],
    ),
    (
        "quyen_yeu_cau_huy_cua_vo_chong_cha_me_con_nguoi_giam_ho_dai_dien",
        "Quyền yêu cầu hủy của vợ/chồng hợp pháp, cha, mẹ, con, người giám hộ hoặc đại diện hợp pháp trong trường hợp luật định",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_10_Khoan_2_Diem_a"],
    ),
    (
        "quyen_yeu_cau_huy_cua_co_quan_quan_ly_gia_dinh",
        "Quyền yêu cầu hủy của cơ quan quản lý nhà nước về gia đình",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_10_Khoan_2_Diem_b"],
    ),
    (
        "quyen_yeu_cau_huy_cua_co_quan_quan_ly_tre_em",
        "Quyền yêu cầu hủy của cơ quan quản lý nhà nước về trẻ em",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_10_Khoan_2_Diem_c"],
    ),
    (
        "quyen_yeu_cau_huy_cua_hoi_lien_hiep_phu_nu",
        "Quyền yêu cầu hủy của Hội liên hiệp phụ nữ",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_10_Khoan_2_Diem_d"],
    ),
    (
        "quyen_cua_chu_the_khac_de_nghi_co_quan_to_chuc_yeu_cau_huy",
        "Quyền của chủ thể khác đề nghị cơ quan, tổ chức luật định yêu cầu Tòa án hủy",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_10_Khoan_3"],
    ),
    (
        "yeu_cau_toa_an_huy_ket_hon_trai_phap_luat",
        "Thực hiện yêu cầu Tòa án hủy việc kết hôn trái pháp luật",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_10", "Luat_HNGD_2014_Dieu_11_Khoan_1"],
    ),
    (
        "de_nghi_co_quan_to_chuc_yeu_cau_huy",
        "Đề nghị cơ quan, tổ chức có quyền trực tiếp yêu cầu Tòa án hủy",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_10_Khoan_1", "Luat_HNGD_2014_Dieu_10_Khoan_3"],
    ),
    (
        "nop_ho_so_yeu_cau_huy_ket_hon_trai_phap_luat",
        "Nộp đơn và tài liệu kèm theo để yêu cầu hủy kết hôn trái pháp luật",
        "HanhVi",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_1"],
    ),
    (
        "toa_an_thu_ly_giai_quyet_yeu_cau_huy",
        "Tòa án thụ lý, giải quyết yêu cầu khi việc kết hôn thuộc trường hợp hủy",
        "HanhVi",
        [
            "Luat_HNGD_2014_Dieu_11_Khoan_1",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_2",
        ],
    ),
    (
        "toa_an_cong_nhan_quan_he_hon_nhan",
        "Tòa án công nhận quan hệ hôn nhân khi đủ điều kiện và đúng cấu hình yêu cầu",
        "HanhVi",
        [
            "Luat_HNGD_2014_Dieu_11_Khoan_2",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2",
        ],
    ),
    (
        "toa_an_quyet_dinh_huy_ket_hon_trai_phap_luat",
        "Tòa án quyết định hủy việc kết hôn trái pháp luật",
        "HanhVi",
        [
            "Luat_HNGD_2014_Dieu_11",
            "Luat_HNGD_2014_Dieu_12",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_3",
        ],
    ),
    (
        "toa_an_giai_quyet_cho_ly_hon",
        "Tòa án giải quyết cho ly hôn trong cấu hình yêu cầu được hướng dẫn",
        "HanhVi",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2"],
    ),
    (
        "toa_an_tuyen_khong_cong_nhan_quan_he_hon_nhan",
        "Tòa án tuyên không công nhận quan hệ hôn nhân do sai thẩm quyền đăng ký hoặc không đăng ký",
        "HanhVi",
        [
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_3",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_4",
        ],
    ),
    (
        "toa_an_huy_giay_chung_nhan_ket_hon_sai_tham_quyen",
        "Tòa án hủy Giấy chứng nhận kết hôn được cấp không đúng thẩm quyền",
        "HanhVi",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_3"],
    ),
    (
        "gui_quyet_dinh_huy_hoac_cong_nhan_quan_he_hon_nhan",
        "Gửi quyết định hủy hoặc công nhận cho cơ quan đăng ký, các bên và chủ thể liên quan",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_11_Khoan_3"],
    ),
    (
        "toa_an_xac_dinh_thoi_diem_hai_ben_du_dieu_kien_ket_hon",
        "Tòa án yêu cầu tài liệu và xác định thời điểm hai bên đã đủ điều kiện kết hôn",
        "HanhVi",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_2_Khoan_5"],
    ),
    (
        "da_dang_ky_ket_hon_dung_co_quan_co_tham_quyen",
        "Việc kết hôn đã được đăng ký tại đúng cơ quan có thẩm quyền",
        "DieuKien",
        [
            "Luat_HNGD_2014_Dieu_3_Khoan_6",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_2",
        ],
    ),
    (
        "vi_pham_dieu_kien_tuoi_ket_hon",
        "Một hoặc cả hai bên chưa đủ tuổi kết hôn tại thời điểm đăng ký",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_2_Khoan_1"],
    ),
    (
        "vi_pham_dieu_kien_tu_nguyen_ket_hon",
        "Việc kết hôn không hoàn toàn tự do theo ý chí của nam và nữ",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_2_Khoan_2"],
    ),
    (
        "bi_lua_doi_dan_den_dong_y_ket_hon",
        "Có hành vi cố ý làm bên kia hiểu sai lệch và vì vậy đồng ý kết hôn",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_2_Khoan_3"],
    ),
    (
        "vi_pham_do_mot_ben_dang_co_vo_hoac_chong",
        "Một bên thuộc trường hợp đang có vợ hoặc chồng theo hướng dẫn",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_2_Khoan_4"],
    ),
    (
        "vi_pham_dieu_kien_ket_hon_khac_can_doi_chieu_dieu_8",
        "Có dấu hiệu vi phạm điều kiện kết hôn khác cần đối chiếu Điều 8",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_2"],
    ),
    (
        "tai_thoi_diem_giai_quyet_ca_hai_da_du_dieu_kien",
        "Tại thời điểm Tòa án giải quyết, cả hai bên đã có đủ điều kiện kết hôn",
        "DieuKien",
        [
            "Luat_HNGD_2014_Dieu_11_Khoan_2",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_2_Khoan_5",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2",
        ],
    ),
    (
        "tai_thoi_diem_giai_quyet_van_chua_du_dieu_kien",
        "Tại thời điểm Tòa án giải quyết, hai bên vẫn không có đủ điều kiện kết hôn",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_3"],
    ),
    (
        "hai_ben_cung_yeu_cau_cong_nhan_quan_he_hon_nhan",
        "Cả hai bên cùng yêu cầu Tòa án công nhận quan hệ hôn nhân",
        "DieuKien",
        [
            "Luat_HNGD_2014_Dieu_11_Khoan_2",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2",
        ],
    ),
    (
        "mot_hoac_hai_ben_yeu_cau_huy",
        "Một hoặc cả hai bên yêu cầu hủy việc kết hôn trái pháp luật",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2"],
    ),
    (
        "mot_ben_yeu_cau_cong_nhan_ben_kia_khong_yeu_cau",
        "Một bên yêu cầu công nhận còn bên kia không có yêu cầu tương ứng",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2"],
    ),
    (
        "hai_ben_cung_yeu_cau_ly_hon",
        "Hai bên cùng yêu cầu Tòa án cho ly hôn",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2"],
    ),
    (
        "mot_ben_yeu_cau_ly_hon_ben_kia_yeu_cau_cong_nhan",
        "Một bên yêu cầu ly hôn còn bên kia yêu cầu công nhận quan hệ hôn nhân",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2"],
    ),
    (
        "dang_ky_ket_hon_sai_co_quan_co_tham_quyen",
        "Việc đăng ký kết hôn được thực hiện tại cơ quan không đúng thẩm quyền",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_3"],
    ),
    (
        "chung_song_nhu_vo_chong_khong_dang_ky_ket_hon",
        "Nam, nữ chung sống như vợ chồng nhưng không đăng ký kết hôn",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_4"],
    ),
    (
        "that_lac_giay_chung_nhan_ket_hon",
        "Giấy chứng nhận kết hôn đã cấp bị thất lạc",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_1"],
    ),
    (
        "can_cu_phap_luat_tai_thoi_diem_xac_lap_quan_he",
        "Phải dùng pháp luật hôn nhân gia đình có hiệu lực tại thời điểm xác lập quan hệ để xác định tính trái pháp luật",
        "DieuKien",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_4"],
    ),
    (
        "don_yeu_cau_huy_ket_hon_trai_phap_luat",
        "Đơn yêu cầu Tòa án hủy việc kết hôn trái pháp luật",
        "TaiLieu",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_1"],
    ),
    (
        "giay_chung_nhan_ket_hon_hoac_tai_lieu_chung_minh_da_dang_ky",
        "Giấy chứng nhận kết hôn hoặc giấy tờ, tài liệu khác chứng minh đã đăng ký kết hôn",
        "TaiLieu",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_1"],
    ),
    (
        "tai_lieu_chung_cu_vi_pham_dieu_kien_ket_hon",
        "Tài liệu, chứng cứ chứng minh việc kết hôn vi phạm điều kiện kết hôn",
        "TaiLieu",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_1"],
    ),
    (
        "xac_nhan_cua_ubnd_da_cap_giay_khi_giay_chung_nhan_bi_that_lac",
        "Xác nhận của UBND đã cấp Giấy chứng nhận kết hôn khi bản giấy bị thất lạc",
        "TaiLieu",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_1"],
    ),
    (
        "tai_lieu_chung_minh_thoi_diem_hai_ben_du_dieu_kien",
        "Tài liệu, chứng cứ xác định thời điểm cả hai bên đã đủ điều kiện kết hôn",
        "TaiLieu",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_2_Khoan_5"],
    ),
    (
        "hai_ben_phai_cham_dut_quan_he_nhu_vo_chong",
        "Hai bên phải chấm dứt quan hệ như vợ chồng khi việc kết hôn trái pháp luật bị hủy",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_12_Khoan_1"],
    ),
    (
        "quyen_nghia_vu_cha_me_con_giai_quyet_nhu_khi_ly_hon",
        "Quyền, nghĩa vụ của cha, mẹ, con được giải quyết theo quy định áp dụng khi ly hôn",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_12_Khoan_2"],
    ),
    (
        "tai_san_nghia_vu_hop_dong_giai_quyet_theo_dieu_16",
        "Tài sản, nghĩa vụ và hợp đồng giữa các bên được giải quyết theo Điều 16",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_12_Khoan_3"],
    ),
    (
        "cong_nhan_hon_nhan_tu_thoi_diem_hai_ben_du_dieu_kien",
        "Quan hệ hôn nhân được công nhận kể từ thời điểm hai bên có đủ điều kiện kết hôn",
        "HauQua",
        [
            "Luat_HNGD_2014_Dieu_11_Khoan_2",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2",
        ],
    ),
    (
        "huy_ket_hon_khi_khong_cung_yeu_cau_cong_nhan",
        "Tòa án hủy khi cấu hình yêu cầu không đáp ứng điều kiện cùng yêu cầu công nhận",
        "HauQua",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2"],
    ),
    (
        "giai_quyet_ly_hon_khi_co_cau_hinh_yeu_cau_phu_hop",
        "Tòa án giải quyết cho ly hôn khi hai bên cùng yêu cầu ly hôn hoặc một bên ly hôn, bên kia yêu cầu công nhận",
        "HauQua",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2"],
    ),
    (
        "bat_buoc_huy_khi_van_khong_du_dieu_kien",
        "Tòa án quyết định hủy khi tại thời điểm giải quyết hai bên vẫn không đủ điều kiện kết hôn",
        "HauQua",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_3"],
    ),
    (
        "khong_cong_nhan_quan_he_hon_nhan_do_dang_ky_sai_tham_quyen",
        "Không công nhận quan hệ hôn nhân và xử lý giấy chứng nhận do đăng ký sai thẩm quyền",
        "HauQua",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_3"],
    ),
    (
        "khong_cong_nhan_quan_he_hon_nhan_do_khong_dang_ky",
        "Không công nhận quan hệ hôn nhân đối với nam, nữ chung sống không đăng ký",
        "HauQua",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_4"],
    ),
    (
        "quyet_dinh_duoc_gui_cho_co_quan_va_cac_ben_lien_quan",
        "Quyết định hủy hoặc công nhận được gửi cho cơ quan đăng ký, hai bên và chủ thể liên quan",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_11_Khoan_3"],
    ),
    (
        "quan_he_hon_nhan_duoc_cong_nhan",
        "Quan hệ hôn nhân được Tòa án công nhận",
        "TinhTrangHonNhan",
        ["Luat_HNGD_2014_Dieu_11_Khoan_2"],
    ),
    (
        "quan_he_ket_hon_trai_phap_luat_da_bi_huy",
        "Quan hệ kết hôn trái pháp luật đã bị Tòa án hủy",
        "TinhTrangHonNhan",
        ["Luat_HNGD_2014_Dieu_11", "Luat_HNGD_2014_Dieu_12"],
    ),
    (
        "khong_phat_sinh_quan_he_hon_nhan_do_khong_dang_ky_hoac_sai_tham_quyen",
        "Không phát sinh quan hệ hôn nhân được công nhận do không đăng ký hoặc đăng ký sai thẩm quyền",
        "TinhTrangHonNhan",
        [
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_3",
            "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_3_Khoan_4",
        ],
    ),
    (
        "quan_he_hon_nhan_cham_dut_bang_ly_hon_sau_khi_du_dieu_kien",
        "Quan hệ được giải quyết bằng ly hôn sau khi các bên đã đủ điều kiện kết hôn",
        "TinhTrangHonNhan",
        ["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_4_Khoan_2"],
    ),
]

_ID_TO_LABEL: dict[str, str] = {sid: label for sid, _, label, _ in _SEMANTIC_ROWS}


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

_EDGE_TRIPLES: list[tuple[str, str, str]] = [
    ("dinh_nghia_ket_hon_trai_phap_luat", "BAO_GOM", "da_dang_ky_ket_hon_dung_co_quan_co_tham_quyen"),
    ("dinh_nghia_ket_hon_trai_phap_luat", "BAO_GOM", "can_cu_huy_ket_hon_trai_phap_luat"),
    ("can_cu_huy_ket_hon_trai_phap_luat", "BAO_GOM", "vi_pham_dieu_kien_tuoi_ket_hon"),
    ("can_cu_huy_ket_hon_trai_phap_luat", "BAO_GOM", "vi_pham_dieu_kien_tu_nguyen_ket_hon"),
    ("can_cu_huy_ket_hon_trai_phap_luat", "BAO_GOM", "bi_lua_doi_dan_den_dong_y_ket_hon"),
    ("can_cu_huy_ket_hon_trai_phap_luat", "BAO_GOM", "vi_pham_do_mot_ben_dang_co_vo_hoac_chong"),
    ("can_cu_huy_ket_hon_trai_phap_luat", "BAO_GOM", "vi_pham_dieu_kien_ket_hon_khac_can_doi_chieu_dieu_8"),
    ("hai_ben_ket_hon_trai_phap_luat", "LIEN_QUAN", "dinh_nghia_ket_hon_trai_phap_luat"),
    ("nguoi_bi_cuong_ep_hoac_lua_doi_ket_hon", "CO_QUYEN", "quyen_tu_minh_yeu_cau_huy_cua_nguoi_bi_cuong_ep_lua_doi"),
    ("nguoi_bi_cuong_ep_hoac_lua_doi_ket_hon", "CO_QUYEN", "quyen_de_nghi_chu_the_luat_dinh_yeu_cau_huy"),
    ("vo_chong_hop_phap_cua_nguoi_dang_co_vo_chong", "CO_QUYEN", "quyen_yeu_cau_huy_cua_vo_chong_cha_me_con_nguoi_giam_ho_dai_dien"),
    ("cha_me_con_nguoi_giam_ho_hoac_dai_dien_hop_phap", "CO_QUYEN", "quyen_yeu_cau_huy_cua_vo_chong_cha_me_con_nguoi_giam_ho_dai_dien"),
    ("co_quan_quan_ly_nha_nuoc_ve_gia_dinh", "CO_QUYEN", "quyen_yeu_cau_huy_cua_co_quan_quan_ly_gia_dinh"),
    ("co_quan_quan_ly_nha_nuoc_ve_tre_em", "CO_QUYEN", "quyen_yeu_cau_huy_cua_co_quan_quan_ly_tre_em"),
    ("hoi_lien_hiep_phu_nu", "CO_QUYEN", "quyen_yeu_cau_huy_cua_hoi_lien_hiep_phu_nu"),
    ("ca_nhan_co_quan_to_chuc_khac_phat_hien_vi_pham", "CO_QUYEN", "quyen_cua_chu_the_khac_de_nghi_co_quan_to_chuc_yeu_cau_huy"),
    ("quyen_tu_minh_yeu_cau_huy_cua_nguoi_bi_cuong_ep_lua_doi", "THUC_HIEN", "yeu_cau_toa_an_huy_ket_hon_trai_phap_luat"),
    ("quyen_de_nghi_chu_the_luat_dinh_yeu_cau_huy", "THUC_HIEN", "de_nghi_co_quan_to_chuc_yeu_cau_huy"),
    ("quyen_yeu_cau_huy_cua_vo_chong_cha_me_con_nguoi_giam_ho_dai_dien", "THUC_HIEN", "yeu_cau_toa_an_huy_ket_hon_trai_phap_luat"),
    ("quyen_yeu_cau_huy_cua_co_quan_quan_ly_gia_dinh", "THUC_HIEN", "yeu_cau_toa_an_huy_ket_hon_trai_phap_luat"),
    ("quyen_yeu_cau_huy_cua_co_quan_quan_ly_tre_em", "THUC_HIEN", "yeu_cau_toa_an_huy_ket_hon_trai_phap_luat"),
    ("quyen_yeu_cau_huy_cua_hoi_lien_hiep_phu_nu", "THUC_HIEN", "yeu_cau_toa_an_huy_ket_hon_trai_phap_luat"),
    ("quyen_cua_chu_the_khac_de_nghi_co_quan_to_chuc_yeu_cau_huy", "THUC_HIEN", "de_nghi_co_quan_to_chuc_yeu_cau_huy"),
    ("de_nghi_co_quan_to_chuc_yeu_cau_huy", "LIEN_QUAN", "co_quan_quan_ly_nha_nuoc_ve_gia_dinh"),
    ("de_nghi_co_quan_to_chuc_yeu_cau_huy", "LIEN_QUAN", "co_quan_quan_ly_nha_nuoc_ve_tre_em"),
    ("de_nghi_co_quan_to_chuc_yeu_cau_huy", "LIEN_QUAN", "hoi_lien_hiep_phu_nu"),
    ("yeu_cau_toa_an_huy_ket_hon_trai_phap_luat", "THUC_HIEN", "nop_ho_so_yeu_cau_huy_ket_hon_trai_phap_luat"),
    ("toa_an_giai_quyet_yeu_cau_huy_ket_hon_trai_phap_luat", "THUC_HIEN", "toa_an_thu_ly_giai_quyet_yeu_cau_huy"),
    ("toa_an_giai_quyet_yeu_cau_huy_ket_hon_trai_phap_luat", "THUC_HIEN", "toa_an_xac_dinh_thoi_diem_hai_ben_du_dieu_kien_ket_hon"),
    ("toa_an_giai_quyet_yeu_cau_huy_ket_hon_trai_phap_luat", "THUC_HIEN", "toa_an_cong_nhan_quan_he_hon_nhan"),
    ("toa_an_giai_quyet_yeu_cau_huy_ket_hon_trai_phap_luat", "THUC_HIEN", "toa_an_quyet_dinh_huy_ket_hon_trai_phap_luat"),
    ("toa_an_giai_quyet_yeu_cau_huy_ket_hon_trai_phap_luat", "THUC_HIEN", "toa_an_giai_quyet_cho_ly_hon"),
    ("toa_an_giai_quyet_yeu_cau_huy_ket_hon_trai_phap_luat", "THUC_HIEN", "toa_an_tuyen_khong_cong_nhan_quan_he_hon_nhan"),
    ("toa_an_giai_quyet_yeu_cau_huy_ket_hon_trai_phap_luat", "THUC_HIEN", "gui_quyet_dinh_huy_hoac_cong_nhan_quan_he_hon_nhan"),
    ("toa_an_thu_ly_giai_quyet_yeu_cau_huy", "AP_DUNG_KHI", "da_dang_ky_ket_hon_dung_co_quan_co_tham_quyen"),
    ("toa_an_thu_ly_giai_quyet_yeu_cau_huy", "AP_DUNG_KHI", "can_cu_phap_luat_tai_thoi_diem_xac_lap_quan_he"),
    ("nop_ho_so_yeu_cau_huy_ket_hon_trai_phap_luat", "YEU_CAU", "don_yeu_cau_huy_ket_hon_trai_phap_luat"),
    ("nop_ho_so_yeu_cau_huy_ket_hon_trai_phap_luat", "YEU_CAU", "giay_chung_nhan_ket_hon_hoac_tai_lieu_chung_minh_da_dang_ky"),
    ("nop_ho_so_yeu_cau_huy_ket_hon_trai_phap_luat", "YEU_CAU", "tai_lieu_chung_cu_vi_pham_dieu_kien_ket_hon"),
    ("nop_ho_so_yeu_cau_huy_ket_hon_trai_phap_luat", "AP_DUNG_KHI", "that_lac_giay_chung_nhan_ket_hon"),
    ("nop_ho_so_yeu_cau_huy_ket_hon_trai_phap_luat", "YEU_CAU", "xac_nhan_cua_ubnd_da_cap_giay_khi_giay_chung_nhan_bi_that_lac"),
    ("toa_an_xac_dinh_thoi_diem_hai_ben_du_dieu_kien_ket_hon", "YEU_CAU", "tai_lieu_chung_minh_thoi_diem_hai_ben_du_dieu_kien"),
    ("toa_an_cong_nhan_quan_he_hon_nhan", "AP_DUNG_KHI", "tai_thoi_diem_giai_quyet_ca_hai_da_du_dieu_kien"),
    ("toa_an_cong_nhan_quan_he_hon_nhan", "AP_DUNG_KHI", "hai_ben_cung_yeu_cau_cong_nhan_quan_he_hon_nhan"),
    ("toa_an_cong_nhan_quan_he_hon_nhan", "DAN_TOI", "cong_nhan_hon_nhan_tu_thoi_diem_hai_ben_du_dieu_kien"),
    ("cong_nhan_hon_nhan_tu_thoi_diem_hai_ben_du_dieu_kien", "XAC_LAP", "quan_he_hon_nhan_duoc_cong_nhan"),
    ("toa_an_quyet_dinh_huy_ket_hon_trai_phap_luat", "AP_DUNG_KHI", "mot_hoac_hai_ben_yeu_cau_huy"),
    ("toa_an_quyet_dinh_huy_ket_hon_trai_phap_luat", "AP_DUNG_KHI", "mot_ben_yeu_cau_cong_nhan_ben_kia_khong_yeu_cau"),
    ("toa_an_quyet_dinh_huy_ket_hon_trai_phap_luat", "AP_DUNG_KHI", "tai_thoi_diem_giai_quyet_van_chua_du_dieu_kien"),
    ("toa_an_quyet_dinh_huy_ket_hon_trai_phap_luat", "DAN_TOI", "huy_ket_hon_khi_khong_cung_yeu_cau_cong_nhan"),
    ("toa_an_quyet_dinh_huy_ket_hon_trai_phap_luat", "DAN_TOI", "bat_buoc_huy_khi_van_khong_du_dieu_kien"),
    ("huy_ket_hon_khi_khong_cung_yeu_cau_cong_nhan", "XAC_LAP", "quan_he_ket_hon_trai_phap_luat_da_bi_huy"),
    ("bat_buoc_huy_khi_van_khong_du_dieu_kien", "XAC_LAP", "quan_he_ket_hon_trai_phap_luat_da_bi_huy"),
    ("toa_an_giai_quyet_cho_ly_hon", "AP_DUNG_KHI", "hai_ben_cung_yeu_cau_ly_hon"),
    ("toa_an_giai_quyet_cho_ly_hon", "AP_DUNG_KHI", "mot_ben_yeu_cau_ly_hon_ben_kia_yeu_cau_cong_nhan"),
    ("toa_an_giai_quyet_cho_ly_hon", "DAN_TOI", "giai_quyet_ly_hon_khi_co_cau_hinh_yeu_cau_phu_hop"),
    ("giai_quyet_ly_hon_khi_co_cau_hinh_yeu_cau_phu_hop", "XAC_LAP", "quan_he_hon_nhan_cham_dut_bang_ly_hon_sau_khi_du_dieu_kien"),
    ("toa_an_tuyen_khong_cong_nhan_quan_he_hon_nhan", "AP_DUNG_KHI", "dang_ky_ket_hon_sai_co_quan_co_tham_quyen"),
    ("toa_an_tuyen_khong_cong_nhan_quan_he_hon_nhan", "AP_DUNG_KHI", "chung_song_nhu_vo_chong_khong_dang_ky_ket_hon"),
    ("toa_an_tuyen_khong_cong_nhan_quan_he_hon_nhan", "DAN_TOI", "khong_cong_nhan_quan_he_hon_nhan_do_dang_ky_sai_tham_quyen"),
    ("toa_an_tuyen_khong_cong_nhan_quan_he_hon_nhan", "DAN_TOI", "khong_cong_nhan_quan_he_hon_nhan_do_khong_dang_ky"),
    ("toa_an_huy_giay_chung_nhan_ket_hon_sai_tham_quyen", "AP_DUNG_KHI", "dang_ky_ket_hon_sai_co_quan_co_tham_quyen"),
    ("toa_an_huy_giay_chung_nhan_ket_hon_sai_tham_quyen", "LIEN_QUAN", "khong_cong_nhan_quan_he_hon_nhan_do_dang_ky_sai_tham_quyen"),
    ("khong_cong_nhan_quan_he_hon_nhan_do_dang_ky_sai_tham_quyen", "XAC_LAP", "khong_phat_sinh_quan_he_hon_nhan_do_khong_dang_ky_hoac_sai_tham_quyen"),
    ("khong_cong_nhan_quan_he_hon_nhan_do_khong_dang_ky", "XAC_LAP", "khong_phat_sinh_quan_he_hon_nhan_do_khong_dang_ky_hoac_sai_tham_quyen"),
    ("nhom_hau_qua_huy_ket_hon_trai_phap_luat", "BAO_GOM", "hai_ben_phai_cham_dut_quan_he_nhu_vo_chong"),
    ("nhom_hau_qua_huy_ket_hon_trai_phap_luat", "BAO_GOM", "quyen_nghia_vu_cha_me_con_giai_quyet_nhu_khi_ly_hon"),
    ("nhom_hau_qua_huy_ket_hon_trai_phap_luat", "BAO_GOM", "tai_san_nghia_vu_hop_dong_giai_quyet_theo_dieu_16"),
    ("toa_an_quyet_dinh_huy_ket_hon_trai_phap_luat", "DAN_TOI", "hai_ben_phai_cham_dut_quan_he_nhu_vo_chong"),
    ("toa_an_quyet_dinh_huy_ket_hon_trai_phap_luat", "DAN_TOI", "quyen_nghia_vu_cha_me_con_giai_quyet_nhu_khi_ly_hon"),
    ("toa_an_quyet_dinh_huy_ket_hon_trai_phap_luat", "DAN_TOI", "tai_san_nghia_vu_hop_dong_giai_quyet_theo_dieu_16"),
    ("gui_quyet_dinh_huy_hoac_cong_nhan_quan_he_hon_nhan", "DAN_TOI", "quyet_dinh_duoc_gui_cho_co_quan_va_cac_ben_lien_quan"),
    ("co_quan_da_thuc_hien_dang_ky_ket_hon", "LIEN_QUAN", "quyet_dinh_duoc_gui_cho_co_quan_va_cac_ben_lien_quan"),
]

EDGES: list[tuple] = [
    (_ID_TO_LABEL[src], src, rel, _ID_TO_LABEL[dst], dst, {})
    for src, rel, dst in _EDGE_TRIPLES
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
