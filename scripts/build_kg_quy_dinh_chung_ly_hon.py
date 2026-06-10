"""Build KG ngữ nghĩa cho topic 'Quy định chung ly hôn' (Điều 51-57 Luật HN&GĐ 2014).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_quy_dinh_chung_ly_hon.py           # MERGE idempotent
    python scripts/build_kg_quy_dinh_chung_ly_hon.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_quy_dinh_chung_ly_hon.py --dry-run # chỉ in summary

Schema: docs/kg_quy_dinh_chung_ly_hon_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "quy_dinh_chung_ly_hon"
TOPIC_LABEL = "QuyDinhChungLyHon"

SEMANTIC_LABELS = [
    "NghiaVu",
    "Quyen",
    "ChuThe",
    "DieuKien",
    "HauQua",
    "HanhVi",
    "ThoaThuan",
    "HinhThucLyHon",
    "GiaiDoanLyHon",
    "TinhTrangHonNhan",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("vo", "Người vợ trong quan hệ hôn nhân", "ChuThe", ["Luat_HNGD_2014_Dieu_51_Khoan_1"]),
    ("chong", "Người chồng trong quan hệ hôn nhân", "ChuThe", ["Luat_HNGD_2014_Dieu_51_Khoan_1", "Luat_HNGD_2014_Dieu_51_Khoan_3"]),
    ("ca_hai_vo_chong", "Cả hai vợ chồng cùng yêu cầu ly hôn", "ChuThe", ["Luat_HNGD_2014_Dieu_51_Khoan_1", "Luat_HNGD_2014_Dieu_55"]),
    ("cha_me_nguoi_than_thich", "Cha, mẹ hoặc người thân thích khác của vợ hoặc chồng", "ChuThe", ["Luat_HNGD_2014_Dieu_51_Khoan_2"]),
    ("toa_an_giai_quyet_ly_hon", "Tòa án thụ lý và giải quyết yêu cầu ly hôn", "ChuThe", ["Luat_HNGD_2014_Dieu_51", "Luat_HNGD_2014_Dieu_53", "Luat_HNGD_2014_Dieu_54", "Luat_HNGD_2014_Dieu_55", "Luat_HNGD_2014_Dieu_56", "Luat_HNGD_2014_Dieu_57"]),
    ("quyen_vo_yeu_cau_ly_hon", "Quyền của người vợ yêu cầu Tòa án giải quyết ly hôn", "Quyen", ["Luat_HNGD_2014_Dieu_51_Khoan_1"]),
    ("quyen_chong_yeu_cau_ly_hon", "Quyền của người chồng yêu cầu Tòa án giải quyết ly hôn, trừ trường hợp bị hạn chế", "Quyen", ["Luat_HNGD_2014_Dieu_51_Khoan_1", "Luat_HNGD_2014_Dieu_51_Khoan_3"]),
    ("quyen_ca_hai_vo_chong_yeu_cau_ly_hon", "Quyền của cả hai vợ chồng cùng yêu cầu Tòa án giải quyết ly hôn", "Quyen", ["Luat_HNGD_2014_Dieu_51_Khoan_1"]),
    ("quyen_cha_me_nguoi_than_yeu_cau_ly_hon", "Quyền của cha, mẹ, người thân thích yêu cầu ly hôn trong trường hợp đặc biệt", "Quyen", ["Luat_HNGD_2014_Dieu_51_Khoan_2", "Luat_HNGD_2014_Dieu_56_Khoan_3"]),
    ("han_che_quyen_chong_yeu_cau_ly_hon", "Chồng không có quyền yêu cầu ly hôn trong thời gian bảo vệ thai sản và trẻ dưới 12 tháng", "Quyen", ["Luat_HNGD_2014_Dieu_51_Khoan_3"]),
    ("hoa_giai_o_co_so", "Hòa giải ở cơ sở trước hoặc khi vợ chồng có yêu cầu ly hôn", "GiaiDoanLyHon", ["Luat_HNGD_2014_Dieu_52"]),
    ("thu_ly_don_yeu_cau_ly_hon", "Tòa án thụ lý đơn yêu cầu ly hôn theo pháp luật tố tụng dân sự", "GiaiDoanLyHon", ["Luat_HNGD_2014_Dieu_53_Khoan_1"]),
    ("thu_ly_yeu_cau_khi_khong_dang_ky_ket_hon", "Thụ lý yêu cầu và tuyên không công nhận quan hệ vợ chồng khi không đăng ký kết hôn", "GiaiDoanLyHon", ["Luat_HNGD_2014_Dieu_53_Khoan_2", "Luat_HNGD_2014_Dieu_14_Khoan_1", "Luat_HNGD_2014_Dieu_15", "Luat_HNGD_2014_Dieu_16"]),
    ("hoa_giai_tai_toa_sau_thu_ly", "Tòa án tiến hành hòa giải sau khi đã thụ lý đơn yêu cầu ly hôn", "GiaiDoanLyHon", ["Luat_HNGD_2014_Dieu_54"]),
    ("thuan_tinh_ly_hon", "Ly hôn khi vợ chồng cùng yêu cầu và đáp ứng điều kiện công nhận", "HinhThucLyHon", ["Luat_HNGD_2014_Dieu_55"]),
    ("ly_hon_theo_yeu_cau_mot_ben", "Ly hôn theo yêu cầu của một bên vợ hoặc chồng", "HinhThucLyHon", ["Luat_HNGD_2014_Dieu_56"]),
    ("ly_hon_do_nguoi_than_yeu_cau", "Ly hôn do cha, mẹ hoặc người thân thích yêu cầu trong trường hợp đặc biệt", "HinhThucLyHon", ["Luat_HNGD_2014_Dieu_51_Khoan_2", "Luat_HNGD_2014_Dieu_56_Khoan_3"]),
    ("ly_hon_voi_nguoi_bi_tuyen_bo_mat_tich", "Ly hôn với vợ hoặc chồng đã bị Tòa án tuyên bố mất tích", "HinhThucLyHon", ["Luat_HNGD_2014_Dieu_56_Khoan_2", "BoLuat_DanSu_2015_Dieu_68"]),
    ("ly_hon_co_yeu_to_nuoc_ngoai", "Ly hôn có ít nhất một bên hoặc tài sản liên quan ở nước ngoài", "HinhThucLyHon", ["Luat_HNGD_2014_Dieu_51_Khoan_1", "Luat_HNGD_2014_Dieu_127"]),
    ("thoa_thuan_chia_tai_san_khi_thuan_tinh", "Thỏa thuận của vợ chồng về việc chia tài sản khi thuận tình ly hôn", "ThoaThuan", ["Luat_HNGD_2014_Dieu_55"]),
    ("thoa_thuan_viec_trong_nom_nuoi_duong_cham_soc_giao_duc_con", "Thỏa thuận về việc trông nom, nuôi dưỡng, chăm sóc, giáo dục con", "ThoaThuan", ["Luat_HNGD_2014_Dieu_55"]),
    ("thoa_thuan_bao_dam_quyen_loi_chinh_dang_cua_vo_va_con", "Thỏa thuận bảo đảm quyền lợi chính đáng của vợ và con", "ThoaThuan", ["Luat_HNGD_2014_Dieu_55"]),
    ("hai_ben_that_su_tu_nguyen_ly_hon", "Hai bên thật sự tự nguyện ly hôn", "DieuKien", ["Luat_HNGD_2014_Dieu_55"]),
    ("da_thoa_thuan_ve_chia_tai_san", "Vợ chồng đã thỏa thuận về việc chia tài sản", "DieuKien", ["Luat_HNGD_2014_Dieu_55"]),
    ("da_thoa_thuan_ve_viec_con", "Vợ chồng đã thỏa thuận về việc trông nom, nuôi dưỡng, chăm sóc, giáo dục con", "DieuKien", ["Luat_HNGD_2014_Dieu_55"]),
    ("thoa_thuan_bao_dam_quyen_loi_vo_va_con", "Nội dung thỏa thuận bảo đảm quyền lợi chính đáng của vợ và con", "DieuKien", ["Luat_HNGD_2014_Dieu_55"]),
    ("khong_thoa_thuan_duoc_ve_tai_san_hoac_con", "Vợ chồng không thỏa thuận được về tài sản hoặc việc con", "DieuKien", ["Luat_HNGD_2014_Dieu_55"]),
    ("thoa_thuan_khong_bao_dam_quyen_loi_vo_va_con", "Có thỏa thuận nhưng không bảo đảm quyền lợi chính đáng của vợ và con", "DieuKien", ["Luat_HNGD_2014_Dieu_55"]),
    ("hoa_giai_tai_toa_khong_thanh", "Hòa giải tại Tòa án không thành trước khi giải quyết ly hôn theo yêu cầu một bên", "DieuKien", ["Luat_HNGD_2014_Dieu_56_Khoan_1"]),
    ("co_hanh_vi_bao_luc_gia_dinh", "Vợ hoặc chồng có hành vi bạo lực gia đình", "DieuKien", ["Luat_HNGD_2014_Dieu_56_Khoan_1"]),
    ("vi_pham_nghiem_trong_quyen_nghia_vu_vo_chong", "Vợ hoặc chồng vi phạm nghiêm trọng quyền, nghĩa vụ của vợ chồng", "DieuKien", ["Luat_HNGD_2014_Dieu_56_Khoan_1"]),
    ("hon_nhan_lam_vao_tinh_trang_tram_trong", "Hôn nhân lâm vào tình trạng trầm trọng", "DieuKien", ["Luat_HNGD_2014_Dieu_56_Khoan_1"]),
    ("doi_song_chung_khong_the_keo_dai", "Đời sống chung của vợ chồng không thể kéo dài", "DieuKien", ["Luat_HNGD_2014_Dieu_56_Khoan_1"]),
    ("muc_dich_hon_nhan_khong_dat_duoc", "Mục đích của hôn nhân không đạt được", "DieuKien", ["Luat_HNGD_2014_Dieu_56_Khoan_1"]),
    ("mot_ben_mat_nang_luc_nhan_thuc_lam_chu_hanh_vi", "Một bên do bệnh tâm thần hoặc bệnh khác không thể nhận thức, làm chủ hành vi", "DieuKien", ["Luat_HNGD_2014_Dieu_51_Khoan_2"]),
    ("nan_nhan_bao_luc_bi_anh_huong_nghiem_trong", "Người mất năng lực nhận thức đồng thời là nạn nhân bạo lực bị ảnh hưởng nghiêm trọng", "DieuKien", ["Luat_HNGD_2014_Dieu_51_Khoan_2", "Luat_HNGD_2014_Dieu_56_Khoan_3"]),
    ("vo_dang_co_thai", "Người vợ đang có thai", "DieuKien", ["Luat_HNGD_2014_Dieu_51_Khoan_3"]),
    ("vo_dang_sinh_con", "Người vợ đang trong trường hợp sinh con", "DieuKien", ["Luat_HNGD_2014_Dieu_51_Khoan_3"]),
    ("vo_dang_nuoi_con_duoi_12_thang", "Người vợ đang nuôi con dưới 12 tháng tuổi", "DieuKien", ["Luat_HNGD_2014_Dieu_51_Khoan_3"]),
    ("da_bi_toa_an_tuyen_bo_mat_tich", "Vợ hoặc chồng đã bị Tòa án tuyên bố mất tích", "DieuKien", ["Luat_HNGD_2014_Dieu_56_Khoan_2", "BoLuat_DanSu_2015_Dieu_68"]),
    ("biet_tich_hai_nam_da_ap_dung_bien_phap_tim_kiem", "Biệt tích từ hai năm liền trở lên và đã áp dụng đầy đủ biện pháp thông báo, tìm kiếm nhưng không có tin tức xác thực", "DieuKien", ["BoLuat_DanSu_2015_Dieu_68"]),
    ("ngoai_tinh_vi_pham_nghia_vu_chung_thuy", "Ngoại tình là dữ kiện có thể thể hiện vi phạm nghĩa vụ chung thủy, cần đánh giá thêm hậu quả hôn nhân", "DieuKien", ["Luat_HNGD_2014_Dieu_19_Khoan_1", "Luat_HNGD_2014_Dieu_56_Khoan_1"]),
    ("co_bac_ruou_che_bo_mac_co_the_la_vi_pham_nghiem_trong", "Cờ bạc, rượu chè, bỏ mặc gia đình có thể là dữ kiện của vi phạm nghiêm trọng, không tự động đủ căn cứ", "DieuKien", ["Luat_HNGD_2014_Dieu_19", "Luat_HNGD_2014_Dieu_56_Khoan_1"]),
    ("yeu_cau_toa_an_giai_quyet_ly_hon", "Thực hiện yêu cầu Tòa án giải quyết ly hôn", "HanhVi", ["Luat_HNGD_2014_Dieu_51"]),
    ("cung_yeu_cau_ly_hon", "Vợ chồng cùng yêu cầu ly hôn", "HanhVi", ["Luat_HNGD_2014_Dieu_55"]),
    ("mot_ben_yeu_cau_ly_hon", "Vợ hoặc chồng yêu cầu ly hôn", "HanhVi", ["Luat_HNGD_2014_Dieu_56"]),
    ("toa_an_thu_ly_don_ly_hon", "Tòa án thụ lý đơn yêu cầu ly hôn", "HanhVi", ["Luat_HNGD_2014_Dieu_53"]),
    ("toa_an_tien_hanh_hoa_giai", "Tòa án tiến hành hòa giải sau khi thụ lý", "HanhVi", ["Luat_HNGD_2014_Dieu_54"]),
    ("chung_song_voi_nguoi_khac_khi_hon_nhan_chua_cham_dut", "Chung sống với người khác khi bản án hoặc quyết định ly hôn chưa có hiệu lực", "HanhVi", ["Luat_HNGD_2014_Dieu_19_Khoan_1", "Luat_HNGD_2014_Dieu_57_Khoan_1"]),
    ("ly_than_khi_chua_co_ban_an_ly_hon", "Vợ chồng ly thân nhưng chưa có bản án, quyết định ly hôn có hiệu lực", "HanhVi", ["Luat_HNGD_2014_Dieu_57_Khoan_1"]),
    ("xe_giay_dang_ky_ket_hon", "Tự xé hoặc hủy bản giấy đăng ký kết hôn", "HanhVi", ["Luat_HNGD_2014_Dieu_3_Khoan_14", "Luat_HNGD_2014_Dieu_57_Khoan_1"]),
    ("toa_an_gui_ban_an_quyet_dinh_ly_hon", "Tòa án gửi bản án, quyết định ly hôn đã có hiệu lực cho các chủ thể luật định", "HanhVi", ["Luat_HNGD_2014_Dieu_57_Khoan_2"]),
    ("toa_an_cong_nhan_thuan_tinh_ly_hon", "Tòa án công nhận thuận tình ly hôn khi đủ điều kiện", "HauQua", ["Luat_HNGD_2014_Dieu_55"]),
    ("toa_an_giai_quyet_ly_hon_khi_thoa_thuan_khong_dat", "Tòa án giải quyết việc ly hôn nếu không thỏa thuận được hoặc thỏa thuận không bảo đảm quyền lợi", "HauQua", ["Luat_HNGD_2014_Dieu_55"]),
    ("toa_an_giai_quyet_cho_ly_hon_mot_ben", "Tòa án giải quyết cho ly hôn theo yêu cầu một bên khi đủ căn cứ", "HauQua", ["Luat_HNGD_2014_Dieu_56_Khoan_1"]),
    ("toa_an_giai_quyet_ly_hon_nguoi_bi_tuyen_bo_mat_tich", "Tòa án giải quyết cho ly hôn với người đã bị tuyên bố mất tích", "HauQua", ["Luat_HNGD_2014_Dieu_56_Khoan_2"]),
    ("toa_an_giai_quyet_ly_hon_do_bao_luc_truong_hop_dac_biet", "Tòa án giải quyết ly hôn theo yêu cầu của người thân trong trường hợp bạo lực đặc biệt", "HauQua", ["Luat_HNGD_2014_Dieu_56_Khoan_3"]),
    ("quan_he_hon_nhan_cham_dut_khi_ban_an_co_hieu_luc", "Quan hệ hôn nhân chấm dứt từ ngày bản án, quyết định ly hôn có hiệu lực pháp luật", "HauQua", ["Luat_HNGD_2014_Dieu_3_Khoan_14", "Luat_HNGD_2014_Dieu_57_Khoan_1"]),
    ("dang_lam_thu_tuc_hon_nhan_van_ton_tai", "Trong thời gian làm thủ tục nhưng chưa có quyết định có hiệu lực, quan hệ hôn nhân vẫn tồn tại", "HauQua", ["Luat_HNGD_2014_Dieu_3_Khoan_13", "Luat_HNGD_2014_Dieu_57_Khoan_1"]),
    ("ly_than_khong_tu_cham_dut_hon_nhan", "Ly thân không tự làm chấm dứt quan hệ hôn nhân", "HauQua", ["Luat_HNGD_2014_Dieu_3_Khoan_14", "Luat_HNGD_2014_Dieu_57_Khoan_1"]),
    ("xe_giay_khong_tu_cham_dut_hon_nhan", "Xé giấy đăng ký kết hôn không tự làm chấm dứt quan hệ hôn nhân", "HauQua", ["Luat_HNGD_2014_Dieu_3_Khoan_14", "Luat_HNGD_2014_Dieu_57_Khoan_1"]),
    ("ban_an_duoc_gui_cho_co_quan_va_cac_ben", "Bản án, quyết định có hiệu lực được gửi cho cơ quan đăng ký kết hôn, hai bên và chủ thể liên quan", "HauQua", ["Luat_HNGD_2014_Dieu_57_Khoan_2"]),
    ("bat_dong_san_o_nuoc_ngoai_ap_dung_phap_luat_noi_co_tai_san", "Bất động sản ở nước ngoài khi ly hôn tuân theo pháp luật nơi có bất động sản", "HauQua", ["Luat_HNGD_2014_Dieu_127_Khoan_3"]),
    ("hon_nhan_dang_ton_tai", "Thời kỳ hôn nhân chưa kết thúc bằng căn cứ luật định", "TinhTrangHonNhan", ["Luat_HNGD_2014_Dieu_3_Khoan_13", "Luat_HNGD_2014_Dieu_57_Khoan_1"]),
    ("hon_nhan_da_cham_dut_do_ly_hon", "Quan hệ vợ chồng đã chấm dứt theo bản án, quyết định ly hôn có hiệu lực", "TinhTrangHonNhan", ["Luat_HNGD_2014_Dieu_3_Khoan_14", "Luat_HNGD_2014_Dieu_57_Khoan_1"]),
    ("hon_nhan_cham_dut_do_vo_chong_chet", "Hôn nhân chấm dứt do vợ hoặc chồng chết hoặc bị tuyên bố đã chết", "TinhTrangHonNhan", ["Luat_HNGD_2014_Dieu_65"]),
    ("nghia_vu_chung_thuy", "Nghĩa vụ chung thủy giữa vợ và chồng", "NghiaVu", ["Luat_HNGD_2014_Dieu_19_Khoan_1"]),
    ("nghia_vu_song_chung", "Nghĩa vụ sống chung, trừ thỏa thuận hoặc lý do chính đáng", "NghiaVu", ["Luat_HNGD_2014_Dieu_19_Khoan_2"]),
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
    ("ChuThe", "vo", "CO_QUYEN", "Quyen", "quyen_vo_yeu_cau_ly_hon", {}),
    ("ChuThe", "chong", "CO_QUYEN", "Quyen", "quyen_chong_yeu_cau_ly_hon", {}),
    ("ChuThe", "ca_hai_vo_chong", "CO_QUYEN", "Quyen", "quyen_ca_hai_vo_chong_yeu_cau_ly_hon", {}),
    ("ChuThe", "cha_me_nguoi_than_thich", "CO_QUYEN", "Quyen", "quyen_cha_me_nguoi_than_yeu_cau_ly_hon", {}),
    ("Quyen", "quyen_vo_yeu_cau_ly_hon", "THUC_HIEN", "HanhVi", "mot_ben_yeu_cau_ly_hon", {}),
    ("Quyen", "quyen_chong_yeu_cau_ly_hon", "THUC_HIEN", "HanhVi", "mot_ben_yeu_cau_ly_hon", {}),
    ("Quyen", "quyen_ca_hai_vo_chong_yeu_cau_ly_hon", "THUC_HIEN", "HanhVi", "cung_yeu_cau_ly_hon", {}),
    ("Quyen", "quyen_cha_me_nguoi_than_yeu_cau_ly_hon", "THUC_HIEN", "HinhThucLyHon", "ly_hon_do_nguoi_than_yeu_cau", {}),
    ("Quyen", "quyen_chong_yeu_cau_ly_hon", "LIEN_QUAN", "Quyen", "han_che_quyen_chong_yeu_cau_ly_hon", {}),
    ("Quyen", "han_che_quyen_chong_yeu_cau_ly_hon", "BI_HAN_CHE_KHI", "DieuKien", "vo_dang_co_thai", {}),
    ("Quyen", "han_che_quyen_chong_yeu_cau_ly_hon", "BI_HAN_CHE_KHI", "DieuKien", "vo_dang_sinh_con", {}),
    ("Quyen", "han_che_quyen_chong_yeu_cau_ly_hon", "BI_HAN_CHE_KHI", "DieuKien", "vo_dang_nuoi_con_duoi_12_thang", {}),
    ("Quyen", "quyen_cha_me_nguoi_than_yeu_cau_ly_hon", "AP_DUNG_KHI", "DieuKien", "mot_ben_mat_nang_luc_nhan_thuc_lam_chu_hanh_vi", {}),
    ("Quyen", "quyen_cha_me_nguoi_than_yeu_cau_ly_hon", "AP_DUNG_KHI", "DieuKien", "nan_nhan_bao_luc_bi_anh_huong_nghiem_trong", {}),
    ("HanhVi", "cung_yeu_cau_ly_hon", "THUOC_HINH_THUC", "HinhThucLyHon", "thuan_tinh_ly_hon", {}),
    ("HanhVi", "mot_ben_yeu_cau_ly_hon", "THUOC_HINH_THUC", "HinhThucLyHon", "ly_hon_theo_yeu_cau_mot_ben", {}),
    ("GiaiDoanLyHon", "hoa_giai_o_co_so", "TIEP_THEO", "GiaiDoanLyHon", "thu_ly_don_yeu_cau_ly_hon", {}),
    ("GiaiDoanLyHon", "thu_ly_don_yeu_cau_ly_hon", "TIEP_THEO", "GiaiDoanLyHon", "hoa_giai_tai_toa_sau_thu_ly", {}),
    ("ChuThe", "toa_an_giai_quyet_ly_hon", "THUC_HIEN", "HanhVi", "toa_an_thu_ly_don_ly_hon", {}),
    ("ChuThe", "toa_an_giai_quyet_ly_hon", "THUC_HIEN", "HanhVi", "toa_an_tien_hanh_hoa_giai", {}),
    ("ThoaThuan", "thoa_thuan_chia_tai_san_khi_thuan_tinh", "DIEU_KIEN_CUA", "HinhThucLyHon", "thuan_tinh_ly_hon", {}),
    ("ThoaThuan", "thoa_thuan_viec_trong_nom_nuoi_duong_cham_soc_giao_duc_con", "DIEU_KIEN_CUA", "HinhThucLyHon", "thuan_tinh_ly_hon", {}),
    ("ThoaThuan", "thoa_thuan_bao_dam_quyen_loi_chinh_dang_cua_vo_va_con", "DIEU_KIEN_CUA", "HinhThucLyHon", "thuan_tinh_ly_hon", {}),
    ("HinhThucLyHon", "thuan_tinh_ly_hon", "AP_DUNG_KHI", "DieuKien", "hai_ben_that_su_tu_nguyen_ly_hon", {}),
    ("HinhThucLyHon", "thuan_tinh_ly_hon", "AP_DUNG_KHI", "DieuKien", "da_thoa_thuan_ve_chia_tai_san", {}),
    ("HinhThucLyHon", "thuan_tinh_ly_hon", "AP_DUNG_KHI", "DieuKien", "da_thoa_thuan_ve_viec_con", {}),
    ("HinhThucLyHon", "thuan_tinh_ly_hon", "AP_DUNG_KHI", "DieuKien", "thoa_thuan_bao_dam_quyen_loi_vo_va_con", {}),
    ("HinhThucLyHon", "thuan_tinh_ly_hon", "DAN_TOI", "HauQua", "toa_an_cong_nhan_thuan_tinh_ly_hon", {}),
    ("DieuKien", "khong_thoa_thuan_duoc_ve_tai_san_hoac_con", "DAN_TOI", "HauQua", "toa_an_giai_quyet_ly_hon_khi_thoa_thuan_khong_dat", {}),
    ("DieuKien", "thoa_thuan_khong_bao_dam_quyen_loi_vo_va_con", "DAN_TOI", "HauQua", "toa_an_giai_quyet_ly_hon_khi_thoa_thuan_khong_dat", {}),
    ("HinhThucLyHon", "ly_hon_theo_yeu_cau_mot_ben", "AP_DUNG_KHI", "DieuKien", "hoa_giai_tai_toa_khong_thanh", {}),
    ("HinhThucLyHon", "ly_hon_theo_yeu_cau_mot_ben", "AP_DUNG_KHI", "DieuKien", "co_hanh_vi_bao_luc_gia_dinh", {}),
    ("HinhThucLyHon", "ly_hon_theo_yeu_cau_mot_ben", "AP_DUNG_KHI", "DieuKien", "vi_pham_nghiem_trong_quyen_nghia_vu_vo_chong", {}),
    ("HinhThucLyHon", "ly_hon_theo_yeu_cau_mot_ben", "AP_DUNG_KHI", "DieuKien", "hon_nhan_lam_vao_tinh_trang_tram_trong", {}),
    ("HinhThucLyHon", "ly_hon_theo_yeu_cau_mot_ben", "AP_DUNG_KHI", "DieuKien", "doi_song_chung_khong_the_keo_dai", {}),
    ("HinhThucLyHon", "ly_hon_theo_yeu_cau_mot_ben", "AP_DUNG_KHI", "DieuKien", "muc_dich_hon_nhan_khong_dat_duoc", {}),
    ("HinhThucLyHon", "ly_hon_theo_yeu_cau_mot_ben", "DAN_TOI", "HauQua", "toa_an_giai_quyet_cho_ly_hon_mot_ben", {}),
    ("DieuKien", "ngoai_tinh_vi_pham_nghia_vu_chung_thuy", "LIEN_QUAN", "DieuKien", "vi_pham_nghiem_trong_quyen_nghia_vu_vo_chong", {}),
    ("DieuKien", "co_bac_ruou_che_bo_mac_co_the_la_vi_pham_nghiem_trong", "LIEN_QUAN", "DieuKien", "vi_pham_nghiem_trong_quyen_nghia_vu_vo_chong", {}),
    ("DieuKien", "ngoai_tinh_vi_pham_nghia_vu_chung_thuy", "VI_PHAM", "NghiaVu", "nghia_vu_chung_thuy", {}),
    ("HinhThucLyHon", "ly_hon_do_nguoi_than_yeu_cau", "AP_DUNG_KHI", "DieuKien", "mot_ben_mat_nang_luc_nhan_thuc_lam_chu_hanh_vi", {}),
    ("HinhThucLyHon", "ly_hon_do_nguoi_than_yeu_cau", "AP_DUNG_KHI", "DieuKien", "nan_nhan_bao_luc_bi_anh_huong_nghiem_trong", {}),
    ("HinhThucLyHon", "ly_hon_do_nguoi_than_yeu_cau", "DAN_TOI", "HauQua", "toa_an_giai_quyet_ly_hon_do_bao_luc_truong_hop_dac_biet", {}),
    ("HinhThucLyHon", "ly_hon_voi_nguoi_bi_tuyen_bo_mat_tich", "AP_DUNG_KHI", "DieuKien", "da_bi_toa_an_tuyen_bo_mat_tich", {}),
    ("DieuKien", "biet_tich_hai_nam_da_ap_dung_bien_phap_tim_kiem", "DAN_TOI", "DieuKien", "da_bi_toa_an_tuyen_bo_mat_tich", {}),
    ("HinhThucLyHon", "ly_hon_voi_nguoi_bi_tuyen_bo_mat_tich", "DAN_TOI", "HauQua", "toa_an_giai_quyet_ly_hon_nguoi_bi_tuyen_bo_mat_tich", {}),
    ("HinhThucLyHon", "ly_hon_co_yeu_to_nuoc_ngoai", "LIEN_QUAN", "HauQua", "bat_dong_san_o_nuoc_ngoai_ap_dung_phap_luat_noi_co_tai_san", {}),
    ("HauQua", "quan_he_hon_nhan_cham_dut_khi_ban_an_co_hieu_luc", "XAC_LAP", "TinhTrangHonNhan", "hon_nhan_da_cham_dut_do_ly_hon", {}),
    ("HauQua", "dang_lam_thu_tuc_hon_nhan_van_ton_tai", "XAC_LAP", "TinhTrangHonNhan", "hon_nhan_dang_ton_tai", {}),
    ("HauQua", "ly_than_khong_tu_cham_dut_hon_nhan", "XAC_LAP", "TinhTrangHonNhan", "hon_nhan_dang_ton_tai", {}),
    ("HauQua", "xe_giay_khong_tu_cham_dut_hon_nhan", "XAC_LAP", "TinhTrangHonNhan", "hon_nhan_dang_ton_tai", {}),
    ("HanhVi", "chung_song_voi_nguoi_khac_khi_hon_nhan_chua_cham_dut", "VI_PHAM", "NghiaVu", "nghia_vu_chung_thuy", {}),
    ("HanhVi", "chung_song_voi_nguoi_khac_khi_hon_nhan_chua_cham_dut", "LIEN_QUAN", "HauQua", "dang_lam_thu_tuc_hon_nhan_van_ton_tai", {}),
    ("HanhVi", "ly_than_khi_chua_co_ban_an_ly_hon", "LIEN_QUAN", "HauQua", "ly_than_khong_tu_cham_dut_hon_nhan", {}),
    ("HanhVi", "xe_giay_dang_ky_ket_hon", "LIEN_QUAN", "HauQua", "xe_giay_khong_tu_cham_dut_hon_nhan", {}),
    ("HanhVi", "toa_an_gui_ban_an_quyet_dinh_ly_hon", "DAN_TOI", "HauQua", "ban_an_duoc_gui_cho_co_quan_va_cac_ben", {}),
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
