"""Build KG ngữ nghĩa cho topic hạn chế quyền cha mẹ con chưa thành niên.

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_han_che_quyen_cha_me_con_chua_thanh_nien.py
    python scripts/build_kg_han_che_quyen_cha_me_con_chua_thanh_nien.py --reset
    python scripts/build_kg_han_che_quyen_cha_me_con_chua_thanh_nien.py --dry-run

Schema: docs/kg_han_che_quyen_cha_me_con_chua_thanh_nien_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "han_che_quyen_cha_me_con_chua_thanh_nien"
TOPIC_LABEL = "HanCheQuyenChaMeConChuaThanhNien"

SEMANTIC_LABELS = [
    "ChuThe",
    "DieuKien",
    "HanhVi",
    "Quyen",
    "NghiaVu",
    "HauQua",
    "ThoaThuan",
    "ThoiHan",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("cha_me_bi_xem_xet_han_che_quyen", "Cha hoặc mẹ bị xem xét hạn chế quyền đối với con chưa thành niên", "ChuThe", ["Luat_HNGD_2014_Dieu_85"]),
    ("con_chua_thanh_nien_trong_vu_viec_han_che_quyen", "Con chưa thành niên trong vụ việc hạn chế quyền của cha, mẹ", "ChuThe", ["Luat_HNGD_2014_Dieu_85"]),
    ("toa_an_quyet_dinh_han_che_quyen", "Tòa án có thẩm quyền tự mình hoặc theo yêu cầu ra quyết định hạn chế quyền", "ChuThe", ["Luat_HNGD_2014_Dieu_85_Khoan_2"]),
    ("cha_hoac_me_co_quyen_yeu_cau_han_che", "Cha hoặc mẹ có quyền yêu cầu Tòa án hạn chế quyền của cha, mẹ", "ChuThe", ["Luat_HNGD_2014_Dieu_86_Khoan_1"]),
    ("nguoi_giam_ho_con_chua_thanh_nien_yeu_cau_han_che", "Người giám hộ của con chưa thành niên có quyền yêu cầu Tòa án", "ChuThe", ["Luat_HNGD_2014_Dieu_86_Khoan_1"]),
    ("nguoi_than_thich_yeu_cau_han_che", "Người thân thích có quyền yêu cầu Tòa án hạn chế quyền", "ChuThe", ["Luat_HNGD_2014_Dieu_86_Khoan_2_Diem_a"]),
    ("co_quan_quan_ly_gia_dinh_yeu_cau_han_che", "Cơ quan quản lý nhà nước về gia đình có quyền yêu cầu Tòa án", "ChuThe", ["Luat_HNGD_2014_Dieu_86_Khoan_2_Diem_b"]),
    ("co_quan_quan_ly_tre_em_yeu_cau_han_che", "Cơ quan quản lý nhà nước về trẻ em có quyền yêu cầu Tòa án", "ChuThe", ["Luat_HNGD_2014_Dieu_86_Khoan_2_Diem_c"]),
    ("hoi_lien_hiep_phu_nu_yeu_cau_han_che", "Hội liên hiệp phụ nữ có quyền yêu cầu Tòa án", "ChuThe", ["Luat_HNGD_2014_Dieu_86_Khoan_2_Diem_d"]),
    ("ca_nhan_co_quan_to_chuc_khac_phat_hien_vi_pham", "Cá nhân, cơ quan, tổ chức khác phát hiện hành vi vi phạm khoản 1 Điều 85", "ChuThe", ["Luat_HNGD_2014_Dieu_86_Khoan_3"]),
    ("ben_cha_me_con_lai_khong_bi_han_che", "Bên cha hoặc mẹ còn lại không bị hạn chế quyền", "ChuThe", ["Luat_HNGD_2014_Dieu_87_Khoan_1", "Luat_HNGD_2014_Dieu_87_Khoan_2"]),
    ("nguoi_giam_ho_tiep_nhan_viec_cham_soc_con", "Người giám hộ được giao trông nom, chăm sóc, giáo dục và quản lý tài sản riêng của con", "ChuThe", ["Luat_HNGD_2014_Dieu_87_Khoan_2"]),
    ("thuoc_truong_hop_han_che_quyen_dieu_85_khoan_1", "Thuộc một trong các trường hợp hạn chế quyền tại khoản 1 Điều 85", "DieuKien", ["Luat_HNGD_2014_Dieu_85_Khoan_1"]),
    ("bi_ket_an_toi_xam_pham_con_voi_loi_co_y", "Bị kết án về tội xâm phạm tính mạng, sức khỏe, nhân phẩm hoặc danh dự của con với lỗi cố ý", "DieuKien", ["Luat_HNGD_2014_Dieu_85_Khoan_1_Diem_a"]),
    ("vi_pham_nghiem_trong_nghia_vu_voi_con", "Vi phạm nghiêm trọng nghĩa vụ trông nom, chăm sóc, nuôi dưỡng hoặc giáo dục con", "DieuKien", ["Luat_HNGD_2014_Dieu_85_Khoan_1_Diem_a"]),
    ("pha_tan_tai_san_cua_con", "Phá tán tài sản của con", "DieuKien", ["Luat_HNGD_2014_Dieu_85_Khoan_1_Diem_b"]),
    ("co_loi_song_doi_truy", "Có lối sống đồi trụy", "DieuKien", ["Luat_HNGD_2014_Dieu_85_Khoan_1_Diem_c"]),
    ("xui_giuc_ep_buoc_con_lam_viec_trai_phap_luat_dao_duc", "Xúi giục hoặc ép buộc con làm việc trái pháp luật, trái đạo đức xã hội", "DieuKien", ["Luat_HNGD_2014_Dieu_85_Khoan_1_Diem_d"]),
    ("mot_ben_cha_me_bi_han_che_quyen", "Chỉ cha hoặc mẹ bị Tòa án hạn chế quyền", "DieuKien", ["Luat_HNGD_2014_Dieu_87_Khoan_1"]),
    ("cha_va_me_deu_bi_han_che_quyen", "Cha và mẹ đều bị Tòa án hạn chế quyền", "DieuKien", ["Luat_HNGD_2014_Dieu_87_Khoan_2_Diem_a"]),
    ("ben_khong_bi_han_che_nhung_khong_du_dieu_kien", "Bên cha, mẹ không bị hạn chế nhưng không đủ điều kiện thực hiện quyền, nghĩa vụ đối với con", "DieuKien", ["Luat_HNGD_2014_Dieu_87_Khoan_2_Diem_b"]),
    ("chua_xac_dinh_duoc_ben_cha_me_con_lai", "Một bên bị hạn chế quyền và chưa xác định được bên cha, mẹ còn lại", "DieuKien", ["Luat_HNGD_2014_Dieu_87_Khoan_2_Diem_c"]),
    ("giao_thoa_cha_me_khong_thoa_thuan_duoc_nguoi_truc_tiep_nuoi", "Cha mẹ sau ly hôn không thỏa thuận được người trực tiếp nuôi con", "DieuKien", ["Luat_HNGD_2014_Dieu_81_Khoan_2"]),
    ("giao_thoa_bao_dam_quyen_loi_moi_mat_cua_con", "Việc giao con phải căn cứ vào quyền lợi về mọi mặt của con", "DieuKien", ["Luat_HNGD_2014_Dieu_81_Khoan_2"]),
    ("giao_thoa_con_tu_du_bay_tuoi_trong_viec_giao_nuoi", "Con từ đủ 07 tuổi trở lên trong việc xác định người trực tiếp nuôi", "DieuKien", ["Luat_HNGD_2014_Dieu_81_Khoan_2"]),
    ("giao_thoa_con_duoi_ba_muoi_sau_thang_tuoi_trong_viec_giao_nuoi", "Con dưới 36 tháng tuổi trong việc xác định người trực tiếp nuôi", "DieuKien", ["Luat_HNGD_2014_Dieu_81_Khoan_3"]),
    ("giao_thoa_me_khong_du_dieu_kien_truc_tiep_nuoi_con", "Người mẹ không đủ điều kiện trực tiếp trông nom, chăm sóc, nuôi dưỡng, giáo dục con", "DieuKien", ["Luat_HNGD_2014_Dieu_81_Khoan_3"]),
    ("giao_thoa_cha_me_co_thoa_thuan_khac_phu_hop_loi_ich_con", "Cha mẹ có thỏa thuận khác phù hợp với lợi ích của con dưới 36 tháng tuổi", "DieuKien", ["Luat_HNGD_2014_Dieu_81_Khoan_3"]),
    ("toa_an_ra_quyet_dinh_han_che_quyen_cha_me", "Tòa án ra quyết định không cho cha, mẹ thực hiện một hoặc nhiều quyền trong phạm vi luật định", "HanhVi", ["Luat_HNGD_2014_Dieu_85_Khoan_2"]),
    ("yeu_cau_toa_an_han_che_quyen_cha_me", "Nộp yêu cầu Tòa án hạn chế quyền của cha, mẹ đối với con chưa thành niên", "HanhVi", ["Luat_HNGD_2014_Dieu_86_Khoan_1", "Luat_HNGD_2014_Dieu_86_Khoan_2"]),
    ("de_nghi_co_quan_to_chuc_yeu_cau_toa_an", "Đề nghị cơ quan có thẩm quyền yêu cầu Tòa án hạn chế quyền", "HanhVi", ["Luat_HNGD_2014_Dieu_86_Khoan_3"]),
    ("giao_thoa_toa_an_quyet_dinh_giao_con_cho_mot_ben_truc_tiep_nuoi", "Tòa án quyết định giao con cho một bên trực tiếp nuôi khi cha mẹ không thỏa thuận được", "HanhVi", ["Luat_HNGD_2014_Dieu_81_Khoan_2"]),
    ("giao_thoa_xem_xet_nguyen_vong_cua_con_tu_du_bay_tuoi", "Xem xét nguyện vọng của con từ đủ 07 tuổi", "HanhVi", ["Luat_HNGD_2014_Dieu_81_Khoan_2"]),
    ("quyen_trong_nom_con", "Quyền trông nom con có thể bị hạn chế theo quyết định của Tòa án", "Quyen", ["Luat_HNGD_2014_Dieu_85_Khoan_2", "Luat_HNGD_2014_Dieu_87_Khoan_1"]),
    ("quyen_cham_soc_con", "Quyền chăm sóc con có thể bị hạn chế theo quyết định của Tòa án", "Quyen", ["Luat_HNGD_2014_Dieu_85_Khoan_2", "Luat_HNGD_2014_Dieu_87_Khoan_1"]),
    ("quyen_giao_duc_con", "Quyền giáo dục con có thể bị hạn chế theo quyết định của Tòa án", "Quyen", ["Luat_HNGD_2014_Dieu_85_Khoan_2", "Luat_HNGD_2014_Dieu_87_Khoan_1"]),
    ("quyen_quan_ly_tai_san_rieng_cua_con", "Quyền quản lý tài sản riêng của con có thể bị hạn chế", "Quyen", ["Luat_HNGD_2014_Dieu_85_Khoan_2", "Luat_HNGD_2014_Dieu_87_Khoan_1"]),
    ("quyen_dai_dien_theo_phap_luat_cho_con", "Quyền đại diện theo pháp luật cho con có thể bị hạn chế", "Quyen", ["Luat_HNGD_2014_Dieu_85_Khoan_2", "Luat_HNGD_2014_Dieu_87_Khoan_1"]),
    ("quyen_yeu_cau_toa_an_han_che_quyen", "Quyền yêu cầu Tòa án hạn chế quyền của cha, mẹ", "Quyen", ["Luat_HNGD_2014_Dieu_86_Khoan_1", "Luat_HNGD_2014_Dieu_86_Khoan_2"]),
    ("nghia_vu_nuoi_duong_con_cua_ben_con_lai", "Nghĩa vụ nuôi dưỡng con do bên cha hoặc mẹ còn lại thực hiện", "NghiaVu", ["Luat_HNGD_2014_Dieu_87_Khoan_1"]),
    ("nghia_vu_cap_duong_van_tiep_tuc", "Cha, mẹ bị hạn chế quyền vẫn phải thực hiện nghĩa vụ cấp dưỡng cho con", "NghiaVu", ["Luat_HNGD_2014_Dieu_87_Khoan_3"]),
    ("khong_duoc_thuc_hien_quyen_trong_pham_vi_quyet_dinh", "Cha, mẹ không được thực hiện quyền nằm trong phạm vi quyết định hạn chế của Tòa án", "HauQua", ["Luat_HNGD_2014_Dieu_85_Khoan_2"]),
    ("ben_con_lai_thuc_hien_quyen_nghia_vu_doi_voi_con", "Bên cha hoặc mẹ còn lại thực hiện các quyền, nghĩa vụ đối với con", "HauQua", ["Luat_HNGD_2014_Dieu_87_Khoan_1"]),
    ("giao_viec_cham_soc_quan_ly_tai_san_cho_nguoi_giam_ho", "Giao việc trông nom, chăm sóc, giáo dục và quản lý tài sản riêng của con cho người giám hộ", "HauQua", ["Luat_HNGD_2014_Dieu_87_Khoan_2"]),
    ("giao_thoa_con_duoc_giao_theo_thoa_thuan_phu_hop_cua_cha_me", "Con được giao cho người trực tiếp nuôi theo thỏa thuận của cha mẹ", "HauQua", ["Luat_HNGD_2014_Dieu_81_Khoan_2"]),
    ("giao_thoa_con_duoc_giao_cho_mot_ben_theo_quyen_loi_moi_mat", "Con được giao cho một bên trực tiếp nuôi căn cứ vào quyền lợi về mọi mặt", "HauQua", ["Luat_HNGD_2014_Dieu_81_Khoan_2"]),
    ("giao_thoa_con_duoi_ba_muoi_sau_thang_khong_mac_dinh_giao_cho_me_khi_co_ngoai_le", "Con dưới 36 tháng không mặc định giao cho mẹ khi mẹ không đủ điều kiện hoặc có thỏa thuận khác phù hợp", "HauQua", ["Luat_HNGD_2014_Dieu_81_Khoan_3"]),
    ("giao_thoa_thoa_thuan_nguoi_truc_tiep_nuoi_con_sau_ly_hon", "Thỏa thuận về người trực tiếp nuôi con, quyền và nghĩa vụ của mỗi bên sau ly hôn", "ThoaThuan", ["Luat_HNGD_2014_Dieu_81_Khoan_2"]),
    ("giao_thoa_thoa_thuan_khac_phu_hop_loi_ich_con_duoi_ba_muoi_sau_thang", "Thỏa thuận khác phù hợp với lợi ích của con dưới 36 tháng tuổi", "ThoaThuan", ["Luat_HNGD_2014_Dieu_81_Khoan_3"]),
    ("thoi_han_han_che_tu_mot_den_nam_nam", "Thời hạn hạn chế quyền từ 01 năm đến 05 năm", "ThoiHan", ["Luat_HNGD_2014_Dieu_85_Khoan_2"]),
    ("toa_an_co_the_rut_ngan_thoi_han_han_che", "Tòa án có thể xem xét rút ngắn thời hạn hạn chế", "ThoiHan", ["Luat_HNGD_2014_Dieu_85_Khoan_2"]),
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
    ('ChuThe', 'cha_me_bi_xem_xet_han_che_quyen', 'CO_QUYEN', 'Quyen', 'quyen_trong_nom_con'),
    ('ChuThe', 'cha_me_bi_xem_xet_han_che_quyen', 'CO_QUYEN', 'Quyen', 'quyen_cham_soc_con'),
    ('ChuThe', 'cha_me_bi_xem_xet_han_che_quyen', 'CO_QUYEN', 'Quyen', 'quyen_giao_duc_con'),
    ('ChuThe', 'cha_me_bi_xem_xet_han_che_quyen', 'CO_QUYEN', 'Quyen', 'quyen_quan_ly_tai_san_rieng_cua_con'),
    ('ChuThe', 'cha_me_bi_xem_xet_han_che_quyen', 'CO_QUYEN', 'Quyen', 'quyen_dai_dien_theo_phap_luat_cho_con'),
    ('DieuKien', 'thuoc_truong_hop_han_che_quyen_dieu_85_khoan_1', 'BAO_GOM', 'DieuKien', 'bi_ket_an_toi_xam_pham_con_voi_loi_co_y'),
    ('DieuKien', 'thuoc_truong_hop_han_che_quyen_dieu_85_khoan_1', 'BAO_GOM', 'DieuKien', 'vi_pham_nghiem_trong_nghia_vu_voi_con'),
    ('DieuKien', 'thuoc_truong_hop_han_che_quyen_dieu_85_khoan_1', 'BAO_GOM', 'DieuKien', 'pha_tan_tai_san_cua_con'),
    ('DieuKien', 'thuoc_truong_hop_han_che_quyen_dieu_85_khoan_1', 'BAO_GOM', 'DieuKien', 'co_loi_song_doi_truy'),
    ('DieuKien', 'thuoc_truong_hop_han_che_quyen_dieu_85_khoan_1', 'BAO_GOM', 'DieuKien', 'xui_giuc_ep_buoc_con_lam_viec_trai_phap_luat_dao_duc'),
    ('DieuKien', 'thuoc_truong_hop_han_che_quyen_dieu_85_khoan_1', 'LAM_CAN_CU_CHO', 'HanhVi', 'toa_an_ra_quyet_dinh_han_che_quyen_cha_me'),
    ('ChuThe', 'toa_an_quyet_dinh_han_che_quyen', 'THUC_HIEN', 'HanhVi', 'toa_an_ra_quyet_dinh_han_che_quyen_cha_me'),
    ('HanhVi', 'toa_an_ra_quyet_dinh_han_che_quyen_cha_me', 'HAN_CHE', 'Quyen', 'quyen_trong_nom_con'),
    ('HanhVi', 'toa_an_ra_quyet_dinh_han_che_quyen_cha_me', 'HAN_CHE', 'Quyen', 'quyen_cham_soc_con'),
    ('HanhVi', 'toa_an_ra_quyet_dinh_han_che_quyen_cha_me', 'HAN_CHE', 'Quyen', 'quyen_giao_duc_con'),
    ('HanhVi', 'toa_an_ra_quyet_dinh_han_che_quyen_cha_me', 'HAN_CHE', 'Quyen', 'quyen_quan_ly_tai_san_rieng_cua_con'),
    ('HanhVi', 'toa_an_ra_quyet_dinh_han_che_quyen_cha_me', 'HAN_CHE', 'Quyen', 'quyen_dai_dien_theo_phap_luat_cho_con'),
    ('HanhVi', 'toa_an_ra_quyet_dinh_han_che_quyen_cha_me', 'CO_THOI_HAN', 'ThoiHan', 'thoi_han_han_che_tu_mot_den_nam_nam'),
    ('HanhVi', 'toa_an_ra_quyet_dinh_han_che_quyen_cha_me', 'CO_THOI_HAN', 'ThoiHan', 'toa_an_co_the_rut_ngan_thoi_han_han_che'),
    ('HanhVi', 'toa_an_ra_quyet_dinh_han_che_quyen_cha_me', 'DAN_TOI', 'HauQua', 'khong_duoc_thuc_hien_quyen_trong_pham_vi_quyet_dinh'),
    ('ChuThe', 'cha_hoac_me_co_quyen_yeu_cau_han_che', 'CO_QUYEN', 'Quyen', 'quyen_yeu_cau_toa_an_han_che_quyen'),
    ('ChuThe', 'nguoi_giam_ho_con_chua_thanh_nien_yeu_cau_han_che', 'CO_QUYEN', 'Quyen', 'quyen_yeu_cau_toa_an_han_che_quyen'),
    ('ChuThe', 'nguoi_than_thich_yeu_cau_han_che', 'CO_QUYEN', 'Quyen', 'quyen_yeu_cau_toa_an_han_che_quyen'),
    ('ChuThe', 'co_quan_quan_ly_gia_dinh_yeu_cau_han_che', 'CO_QUYEN', 'Quyen', 'quyen_yeu_cau_toa_an_han_che_quyen'),
    ('ChuThe', 'co_quan_quan_ly_tre_em_yeu_cau_han_che', 'CO_QUYEN', 'Quyen', 'quyen_yeu_cau_toa_an_han_che_quyen'),
    ('ChuThe', 'hoi_lien_hiep_phu_nu_yeu_cau_han_che', 'CO_QUYEN', 'Quyen', 'quyen_yeu_cau_toa_an_han_che_quyen'),
    ('Quyen', 'quyen_yeu_cau_toa_an_han_che_quyen', 'THUC_HIEN_QUA', 'HanhVi', 'yeu_cau_toa_an_han_che_quyen_cha_me'),
    ('HanhVi', 'yeu_cau_toa_an_han_che_quyen_cha_me', 'YEU_CAU', 'ChuThe', 'toa_an_quyet_dinh_han_che_quyen'),
    ('ChuThe', 'ca_nhan_co_quan_to_chuc_khac_phat_hien_vi_pham', 'CO_QUYEN_DE_NGHI', 'HanhVi', 'de_nghi_co_quan_to_chuc_yeu_cau_toa_an'),
    ('HanhVi', 'de_nghi_co_quan_to_chuc_yeu_cau_toa_an', 'DE_NGHI_DEN', 'ChuThe', 'co_quan_quan_ly_gia_dinh_yeu_cau_han_che'),
    ('HanhVi', 'de_nghi_co_quan_to_chuc_yeu_cau_toa_an', 'DE_NGHI_DEN', 'ChuThe', 'co_quan_quan_ly_tre_em_yeu_cau_han_che'),
    ('HanhVi', 'de_nghi_co_quan_to_chuc_yeu_cau_toa_an', 'DE_NGHI_DEN', 'ChuThe', 'hoi_lien_hiep_phu_nu_yeu_cau_han_che'),
    ('DieuKien', 'mot_ben_cha_me_bi_han_che_quyen', 'DAN_TOI', 'HauQua', 'ben_con_lai_thuc_hien_quyen_nghia_vu_doi_voi_con'),
    ('ChuThe', 'ben_cha_me_con_lai_khong_bi_han_che', 'THUC_HIEN_QUYEN_THAY', 'Quyen', 'quyen_trong_nom_con'),
    ('ChuThe', 'ben_cha_me_con_lai_khong_bi_han_che', 'THUC_HIEN_NGHIA_VU_THAY', 'NghiaVu', 'nghia_vu_nuoi_duong_con_cua_ben_con_lai'),
    ('ChuThe', 'ben_cha_me_con_lai_khong_bi_han_che', 'THUC_HIEN_QUYEN_THAY', 'Quyen', 'quyen_cham_soc_con'),
    ('ChuThe', 'ben_cha_me_con_lai_khong_bi_han_che', 'THUC_HIEN_QUYEN_THAY', 'Quyen', 'quyen_giao_duc_con'),
    ('ChuThe', 'ben_cha_me_con_lai_khong_bi_han_che', 'THUC_HIEN_QUYEN_THAY', 'Quyen', 'quyen_quan_ly_tai_san_rieng_cua_con'),
    ('ChuThe', 'ben_cha_me_con_lai_khong_bi_han_che', 'THUC_HIEN_QUYEN_THAY', 'Quyen', 'quyen_dai_dien_theo_phap_luat_cho_con'),
    ('DieuKien', 'cha_va_me_deu_bi_han_che_quyen', 'DAN_TOI', 'HauQua', 'giao_viec_cham_soc_quan_ly_tai_san_cho_nguoi_giam_ho'),
    ('DieuKien', 'ben_khong_bi_han_che_nhung_khong_du_dieu_kien', 'DAN_TOI', 'HauQua', 'giao_viec_cham_soc_quan_ly_tai_san_cho_nguoi_giam_ho'),
    ('DieuKien', 'chua_xac_dinh_duoc_ben_cha_me_con_lai', 'DAN_TOI', 'HauQua', 'giao_viec_cham_soc_quan_ly_tai_san_cho_nguoi_giam_ho'),
    ('ChuThe', 'nguoi_giam_ho_tiep_nhan_viec_cham_soc_con', 'THUC_HIEN_QUYEN_THAY', 'Quyen', 'quyen_trong_nom_con'),
    ('ChuThe', 'nguoi_giam_ho_tiep_nhan_viec_cham_soc_con', 'THUC_HIEN_QUYEN_THAY', 'Quyen', 'quyen_cham_soc_con'),
    ('ChuThe', 'nguoi_giam_ho_tiep_nhan_viec_cham_soc_con', 'THUC_HIEN_QUYEN_THAY', 'Quyen', 'quyen_giao_duc_con'),
    ('ChuThe', 'nguoi_giam_ho_tiep_nhan_viec_cham_soc_con', 'THUC_HIEN_QUYEN_THAY', 'Quyen', 'quyen_quan_ly_tai_san_rieng_cua_con'),
    ('ChuThe', 'cha_me_bi_xem_xet_han_che_quyen', 'VAN_CO_NGHIA_VU', 'NghiaVu', 'nghia_vu_cap_duong_van_tiep_tuc'),
    ('ThoaThuan', 'giao_thoa_thoa_thuan_nguoi_truc_tiep_nuoi_con_sau_ly_hon', 'DAN_TOI', 'HauQua', 'giao_thoa_con_duoc_giao_theo_thoa_thuan_phu_hop_cua_cha_me'),
    ('DieuKien', 'giao_thoa_cha_me_khong_thoa_thuan_duoc_nguoi_truc_tiep_nuoi', 'AP_DUNG_CHO', 'HanhVi', 'giao_thoa_toa_an_quyet_dinh_giao_con_cho_mot_ben_truc_tiep_nuoi'),
    ('DieuKien', 'giao_thoa_bao_dam_quyen_loi_moi_mat_cua_con', 'LAM_CAN_CU_CHO', 'HanhVi', 'giao_thoa_toa_an_quyet_dinh_giao_con_cho_mot_ben_truc_tiep_nuoi'),
    ('HanhVi', 'giao_thoa_toa_an_quyet_dinh_giao_con_cho_mot_ben_truc_tiep_nuoi', 'DAN_TOI', 'HauQua', 'giao_thoa_con_duoc_giao_cho_mot_ben_theo_quyen_loi_moi_mat'),
    ('DieuKien', 'giao_thoa_con_tu_du_bay_tuoi_trong_viec_giao_nuoi', 'AP_DUNG_CHO', 'HanhVi', 'giao_thoa_xem_xet_nguyen_vong_cua_con_tu_du_bay_tuoi'),
    ('DieuKien', 'giao_thoa_con_duoi_ba_muoi_sau_thang_tuoi_trong_viec_giao_nuoi', 'AP_DUNG_CHO', 'HauQua', 'giao_thoa_con_duoi_ba_muoi_sau_thang_khong_mac_dinh_giao_cho_me_khi_co_ngoai_le'),
    ('DieuKien', 'giao_thoa_me_khong_du_dieu_kien_truc_tiep_nuoi_con', 'AP_DUNG_CHO', 'HauQua', 'giao_thoa_con_duoi_ba_muoi_sau_thang_khong_mac_dinh_giao_cho_me_khi_co_ngoai_le'),
    ('DieuKien', 'giao_thoa_cha_me_co_thoa_thuan_khac_phu_hop_loi_ich_con', 'AP_DUNG_CHO', 'ThoaThuan', 'giao_thoa_thoa_thuan_khac_phu_hop_loi_ich_con_duoi_ba_muoi_sau_thang'),
    ('DieuKien', 'giao_thoa_me_khong_du_dieu_kien_truc_tiep_nuoi_con', 'LIEN_QUAN', 'DieuKien', 'thuoc_truong_hop_han_che_quyen_dieu_85_khoan_1'),
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
