"""Build KG ngữ nghĩa cho 'Đại diện và trách nhiệm của vợ chồng' (Điều 24-27 Luật HN&GĐ 2014).

Cách chạy:
    python scripts/build_kg_dai_dien_trach_nhiem_vo_chong.py
    python scripts/build_kg_dai_dien_trach_nhiem_vo_chong.py --reset
    python scripts/build_kg_dai_dien_trach_nhiem_vo_chong.py --dry-run

Schema: docs/kg_dai_dien_trach_nhiem_vo_chong_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "dai_dien_trach_nhiem_vo_chong"
TOPIC_LABEL = "DaiDienTrachNhiemVoChong"

SEMANTIC_LABELS = [
    "ChuThe",
    "HanhVi",
    "GiaoDich",
    "NghiaVu",
    "Quyen",
    "LoaiTaiSan",
    "DieuKien",
    "HauQua",
    "ThoaThuan",
    "VanBanPhapLy",
    "TruongHopNgoaiLe",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}


def _rows(label: str, items: list[tuple[str, str]]) -> list[dict[str, Any]]:
    return [{"id": node_id, "ten": ten, "topic": TOPIC} for node_id, ten in items]


NODES: dict[str, list[dict[str, Any]]] = {
    "ChuThe": _rows(
        "ChuThe",
        [
            ("vo_chong", "Vợ chồng"),
            ("mot_ben_vo_chong", "Một bên vợ hoặc chồng"),
            ("ben_vo_chong_con_lai", "Bên vợ hoặc chồng còn lại"),
            ("toa_an", "Tòa án"),
            ("nguoi_thu_ba", "Người thứ ba trong giao dịch"),
            ("nguoi_thu_ba_ngay_tinh", "Người thứ ba ngay tình"),
        ],
    ),
    "HanhVi": _rows(
        "HanhVi",
        [
            ("xac_lap_thuc_hien_cham_dut_giao_dich", "Xác lập, thực hiện và chấm dứt giao dịch"),
            ("uy_quyen_giua_vo_chong", "Vợ chồng ủy quyền cho nhau thực hiện giao dịch"),
            ("dai_dien_khi_mat_nang_luc_hanh_vi_dan_su", "Đại diện khi một bên mất năng lực hành vi dân sự"),
            ("dai_dien_khi_han_che_nang_luc_hanh_vi_dan_su", "Đại diện khi một bên bị hạn chế năng lực hành vi dân sự"),
            ("toa_an_chi_dinh_nguoi_khac_dai_dien_khi_ly_hon", "Tòa án chỉ định người khác đại diện khi giải quyết ly hôn"),
            ("kinh_doanh_chung_cua_vo_chong", "Vợ chồng kinh doanh chung"),
            ("truc_tiep_tham_gia_quan_he_kinh_doanh", "Trực tiếp tham gia quan hệ kinh doanh chung"),
            ("dua_tai_san_chung_vao_kinh_doanh", "Đưa tài sản chung vào kinh doanh"),
            ("giao_dich_tai_san_chung_gcn_mot_ben", "Giao dịch tài sản chung có giấy chứng nhận chỉ ghi tên một bên"),
            ("mot_ben_tu_minh_giao_dich_trai_quy_dinh_dai_dien", "Một bên tự mình giao dịch trái quy định về đại diện"),
            ("thanh_toan_no_bang_tai_san_chung", "Thanh toán nợ bằng tài sản chung"),
            ("giai_quyet_no_khi_ly_hon", "Giải quyết nghĩa vụ nợ với người thứ ba khi ly hôn"),
        ],
    ),
    "Quyen": _rows(
        "Quyen",
        [
            ("quyen_uy_quyen_cho_nhau", "Quyền ủy quyền cho nhau trong giao dịch cần sự đồng ý của cả hai"),
            ("quyen_dai_dien_cho_ben_mat_han_che_nang_luc", "Quyền đại diện cho bên mất hoặc bị hạn chế năng lực hành vi dân sự"),
            ("quyen_loi_nguoi_thu_ba_ngay_tinh_duoc_bao_ve", "Quyền lợi người thứ ba ngay tình được pháp luật bảo vệ"),
        ],
    ),
    "GiaoDich": _rows(
        "GiaoDich",
        [
            ("giao_dich_can_su_dong_y_cua_ca_hai", "Giao dịch theo luật phải có sự đồng ý của cả hai vợ chồng"),
            ("giao_dich_phu_hop_quy_dinh_dai_dien", "Giao dịch phù hợp quy định đại diện tại Điều 24-26"),
            ("giao_dich_mot_ben_dap_ung_nhu_cau_thiet_yeu", "Giao dịch do một bên thực hiện nhằm đáp ứng nhu cầu thiết yếu của gia đình"),
            ("giao_dich_voi_nguoi_thu_ba", "Giao dịch do một bên xác lập với người thứ ba"),
            ("giao_dich_mua_ban_chuyen_nhuong_tai_san_chung", "Mua bán hoặc chuyển nhượng tài sản chung"),
        ],
    ),
    "NghiaVu": _rows(
        "NghiaVu",
        [
            ("nghia_vu_lien_doi_tu_giao_dich_mot_ben", "Trách nhiệm liên đới từ giao dịch do một bên thực hiện"),
            ("nghia_vu_lien_doi_tu_giao_dich_phu_hop_dai_dien", "Trách nhiệm liên đới từ giao dịch phù hợp quy định đại diện"),
            ("nghia_vu_lien_doi_tu_nghia_vu_chung", "Trách nhiệm liên đới đối với nghĩa vụ chung của vợ chồng"),
            ("nghia_vu_chung_cua_vo_chong", "Nghĩa vụ chung về tài sản của vợ chồng"),
            ("nghia_vu_rieng_cua_mot_ben", "Nghĩa vụ riêng về tài sản của một bên"),
            ("trach_nhiem_voi_nguoi_thu_ba_khi_ly_hon", "Trách nhiệm đối với người thứ ba khi ly hôn"),
        ],
    ),
    "LoaiTaiSan": _rows(
        "LoaiTaiSan",
        [
            ("tai_san_chung", "Tài sản chung của vợ chồng"),
            ("tai_san_rieng", "Tài sản riêng của một bên vợ hoặc chồng"),
            ("tai_san_chung_dua_vao_kinh_doanh", "Tài sản chung được đưa vào kinh doanh"),
            ("tai_san_chung_co_gcn_chi_ghi_ten_mot_ben", "Tài sản chung có giấy chứng nhận chỉ ghi tên vợ hoặc chồng"),
        ],
    ),
    "ThoaThuan": _rows(
        "ThoaThuan",
        [
            ("thoa_thuan_uy_quyen_giua_vo_chong", "Thỏa thuận ủy quyền giữa vợ và chồng"),
            ("thoa_thuan_nguoi_dai_dien_truoc_khi_kinh_doanh", "Thỏa thuận người đại diện trước khi tham gia kinh doanh chung"),
            ("thoa_thuan_kinh_doanh", "Thỏa thuận bằng văn bản về việc đưa tài sản chung vào kinh doanh"),
        ],
    ),
    "VanBanPhapLy": _rows(
        "VanBanPhapLy",
        [
            ("gcn_quyen_so_huu_chi_ghi_ten_mot_ben", "Giấy chứng nhận quyền sở hữu chỉ ghi tên một bên"),
            ("gcn_quyen_su_dung_chi_ghi_ten_mot_ben", "Giấy chứng nhận quyền sử dụng chỉ ghi tên một bên"),
        ],
    ),
    "DieuKien": _rows(
        "DieuKien",
        [
            ("can_cu_dai_dien_theo_luat_hngd_blds_luat_lien_quan", "Đại diện được xác định theo Luật HN&GĐ, Bộ luật dân sự và luật liên quan"),
            ("mat_nang_luc_hanh_vi_dan_su", "Một bên mất năng lực hành vi dân sự"),
            ("ben_kia_du_dieu_kien_lam_nguoi_giam_ho", "Bên kia đủ điều kiện làm người giám hộ"),
            ("han_che_nang_luc_hanh_vi_dan_su", "Một bên bị hạn chế năng lực hành vi dân sự"),
            ("ben_kia_duoc_toa_an_chi_dinh_dai_dien", "Bên kia được Tòa án chỉ định làm người đại diện theo pháp luật"),
            ("yeu_cau_ly_hon_khi_ben_kia_mat_nang_luc", "Một bên yêu cầu ly hôn khi bên kia mất năng lực hành vi dân sự"),
            ("vo_chong_kinh_doanh_chung", "Vợ chồng cùng tham gia quan hệ kinh doanh"),
            ("co_thoa_thuan_khac_truoc_khi_kinh_doanh", "Có thỏa thuận khác trước khi tham gia quan hệ kinh doanh"),
            ("gcn_chi_ghi_ten_mot_ben", "Giấy chứng nhận của tài sản chung chỉ ghi tên một bên"),
            ("no_phat_sinh_trong_thoi_ky_hon_nhan", "Khoản nợ phát sinh trong thời kỳ hôn nhân"),
            ("no_phuc_vu_nhu_cau_gia_dinh", "Khoản nợ phục vụ nhu cầu thiết yếu của gia đình"),
            ("no_phuc_vu_kinh_doanh_chung", "Khoản nợ phục vụ hoạt động kinh doanh chung"),
            ("no_phuc_vu_muc_dich_ca_nhan", "Khoản nợ từ giao dịch cá nhân không vì nhu cầu gia đình"),
        ],
    ),
    "HauQua": _rows(
        "HauQua",
        [
            ("dai_dien_hop_phap_trong_giao_dich", "Việc đại diện trong giao dịch được xác lập hợp pháp"),
            ("dai_dien_hop_phap_trong_kinh_doanh_chung", "Người trực tiếp tham gia là đại diện hợp pháp trong quan hệ kinh doanh chung"),
            ("ap_dung_quy_dinh_dai_dien_dieu_24_25", "Áp dụng quy định đại diện tại Điều 24 và Điều 25"),
            ("giao_dich_vo_hieu_do_trai_quy_dinh_dai_dien", "Giao dịch vô hiệu do trái quy định về đại diện giữa vợ và chồng"),
            ("giao_dich_duoc_bao_ve_vi_nguoi_thu_ba_ngay_tinh", "Giao dịch/quyền lợi được bảo vệ do người thứ ba ngay tình"),
        ],
    ),
    "TruongHopNgoaiLe": _rows(
        "TruongHopNgoaiLe",
        [
            ("quyen_nghia_vu_phai_tu_minh_thuc_hien", "Quyền, nghĩa vụ mà người bị mất hoặc hạn chế năng lực phải tự mình thực hiện"),
            ("co_thoa_thuan_hoac_luat_quy_dinh_khac_ve_dai_dien_kinh_doanh", "Có thỏa thuận khác hoặc luật liên quan quy định khác về đại diện kinh doanh"),
            ("ngoai_le_nguoi_thu_ba_ngay_tinh_duoc_bao_ve", "Ngoại lệ người thứ ba ngay tình được bảo vệ quyền lợi"),
        ],
    ),
}


EDGES: list[tuple] = [
    ("HanhVi", "xac_lap_thuc_hien_cham_dut_giao_dich", "THUC_HIEN_BOI", "ChuThe", "vo_chong", {}),
    ("HanhVi", "xac_lap_thuc_hien_cham_dut_giao_dich", "AP_DUNG_KHI", "DieuKien", "can_cu_dai_dien_theo_luat_hngd_blds_luat_lien_quan", {}),
    ("HanhVi", "uy_quyen_giua_vo_chong", "THUC_HIEN_BOI", "ChuThe", "mot_ben_vo_chong", {}),
    ("HanhVi", "uy_quyen_giua_vo_chong", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_uy_quyen_giua_vo_chong", {}),
    ("HanhVi", "uy_quyen_giua_vo_chong", "TAC_DONG_LEN", "GiaoDich", "giao_dich_can_su_dong_y_cua_ca_hai", {}),
    ("ThoaThuan", "thoa_thuan_uy_quyen_giua_vo_chong", "DAN_TOI", "HauQua", "dai_dien_hop_phap_trong_giao_dich", {}),
    ("Quyen", "quyen_uy_quyen_cho_nhau", "LIEN_QUAN", "ThoaThuan", "thoa_thuan_uy_quyen_giua_vo_chong", {}),
    ("HanhVi", "dai_dien_khi_mat_nang_luc_hanh_vi_dan_su", "AP_DUNG_KHI", "DieuKien", "mat_nang_luc_hanh_vi_dan_su", {}),
    ("HanhVi", "dai_dien_khi_mat_nang_luc_hanh_vi_dan_su", "AP_DUNG_KHI", "DieuKien", "ben_kia_du_dieu_kien_lam_nguoi_giam_ho", {}),
    ("HanhVi", "dai_dien_khi_mat_nang_luc_hanh_vi_dan_su", "DAN_TOI", "HauQua", "dai_dien_hop_phap_trong_giao_dich", {}),
    ("HanhVi", "dai_dien_khi_mat_nang_luc_hanh_vi_dan_su", "CO_NGOAI_LE", "TruongHopNgoaiLe", "quyen_nghia_vu_phai_tu_minh_thuc_hien", {}),
    ("HanhVi", "dai_dien_khi_han_che_nang_luc_hanh_vi_dan_su", "AP_DUNG_KHI", "DieuKien", "han_che_nang_luc_hanh_vi_dan_su", {}),
    ("HanhVi", "dai_dien_khi_han_che_nang_luc_hanh_vi_dan_su", "AP_DUNG_KHI", "DieuKien", "ben_kia_duoc_toa_an_chi_dinh_dai_dien", {}),
    ("HanhVi", "dai_dien_khi_han_che_nang_luc_hanh_vi_dan_su", "DAN_TOI", "HauQua", "dai_dien_hop_phap_trong_giao_dich", {}),
    ("HanhVi", "dai_dien_khi_han_che_nang_luc_hanh_vi_dan_su", "CO_NGOAI_LE", "TruongHopNgoaiLe", "quyen_nghia_vu_phai_tu_minh_thuc_hien", {}),
    ("HanhVi", "toa_an_chi_dinh_nguoi_khac_dai_dien_khi_ly_hon", "THUC_HIEN_BOI", "ChuThe", "toa_an", {}),
    ("HanhVi", "toa_an_chi_dinh_nguoi_khac_dai_dien_khi_ly_hon", "AP_DUNG_KHI", "DieuKien", "yeu_cau_ly_hon_khi_ben_kia_mat_nang_luc", {}),
    ("HanhVi", "kinh_doanh_chung_cua_vo_chong", "AP_DUNG_KHI", "DieuKien", "vo_chong_kinh_doanh_chung", {}),
    ("HanhVi", "truc_tiep_tham_gia_quan_he_kinh_doanh", "LIEN_QUAN", "HanhVi", "kinh_doanh_chung_cua_vo_chong", {}),
    ("HanhVi", "truc_tiep_tham_gia_quan_he_kinh_doanh", "DAN_TOI", "HauQua", "dai_dien_hop_phap_trong_kinh_doanh_chung", {}),
    ("HanhVi", "kinh_doanh_chung_cua_vo_chong", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_nguoi_dai_dien_truoc_khi_kinh_doanh", {}),
    ("HanhVi", "kinh_doanh_chung_cua_vo_chong", "AP_DUNG_KHI", "DieuKien", "co_thoa_thuan_khac_truoc_khi_kinh_doanh", {}),
    ("HanhVi", "kinh_doanh_chung_cua_vo_chong", "CO_NGOAI_LE", "TruongHopNgoaiLe", "co_thoa_thuan_hoac_luat_quy_dinh_khac_ve_dai_dien_kinh_doanh", {}),
    ("HanhVi", "dua_tai_san_chung_vao_kinh_doanh", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_chung_dua_vao_kinh_doanh", {}),
    ("HanhVi", "dua_tai_san_chung_vao_kinh_doanh", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_kinh_doanh", {}),
    ("HanhVi", "giao_dich_tai_san_chung_gcn_mot_ben", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_chung_co_gcn_chi_ghi_ten_mot_ben", {}),
    ("LoaiTaiSan", "tai_san_chung_co_gcn_chi_ghi_ten_mot_ben", "GHI_NHAN_TREN", "VanBanPhapLy", "gcn_quyen_so_huu_chi_ghi_ten_mot_ben", {}),
    ("LoaiTaiSan", "tai_san_chung_co_gcn_chi_ghi_ten_mot_ben", "GHI_NHAN_TREN", "VanBanPhapLy", "gcn_quyen_su_dung_chi_ghi_ten_mot_ben", {}),
    ("HanhVi", "giao_dich_tai_san_chung_gcn_mot_ben", "AP_DUNG_KHI", "DieuKien", "gcn_chi_ghi_ten_mot_ben", {}),
    ("HanhVi", "giao_dich_tai_san_chung_gcn_mot_ben", "DAN_TOI", "HauQua", "ap_dung_quy_dinh_dai_dien_dieu_24_25", {}),
    ("GiaoDich", "giao_dich_mua_ban_chuyen_nhuong_tai_san_chung", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_chung_co_gcn_chi_ghi_ten_mot_ben", {}),
    ("HanhVi", "mot_ben_tu_minh_giao_dich_trai_quy_dinh_dai_dien", "TAC_DONG_LEN", "GiaoDich", "giao_dich_voi_nguoi_thu_ba", {}),
    ("HanhVi", "mot_ben_tu_minh_giao_dich_trai_quy_dinh_dai_dien", "TAC_DONG_LEN", "GiaoDich", "giao_dich_mua_ban_chuyen_nhuong_tai_san_chung", {}),
    ("HanhVi", "mot_ben_tu_minh_giao_dich_trai_quy_dinh_dai_dien", "DAN_TOI", "HauQua", "giao_dich_vo_hieu_do_trai_quy_dinh_dai_dien", {}),
    ("HauQua", "giao_dich_vo_hieu_do_trai_quy_dinh_dai_dien", "CO_NGOAI_LE", "TruongHopNgoaiLe", "ngoai_le_nguoi_thu_ba_ngay_tinh_duoc_bao_ve", {}),
    ("TruongHopNgoaiLe", "ngoai_le_nguoi_thu_ba_ngay_tinh_duoc_bao_ve", "AP_DUNG_KHI", "ChuThe", "nguoi_thu_ba_ngay_tinh", {}),
    ("TruongHopNgoaiLe", "ngoai_le_nguoi_thu_ba_ngay_tinh_duoc_bao_ve", "DAN_TOI", "HauQua", "giao_dich_duoc_bao_ve_vi_nguoi_thu_ba_ngay_tinh", {}),
    ("Quyen", "quyen_loi_nguoi_thu_ba_ngay_tinh_duoc_bao_ve", "LIEN_QUAN", "HauQua", "giao_dich_duoc_bao_ve_vi_nguoi_thu_ba_ngay_tinh", {}),
    ("NghiaVu", "nghia_vu_lien_doi_tu_giao_dich_mot_ben", "PHAT_SINH_TU", "GiaoDich", "giao_dich_mot_ben_dap_ung_nhu_cau_thiet_yeu", {}),
    ("NghiaVu", "nghia_vu_lien_doi_tu_giao_dich_phu_hop_dai_dien", "PHAT_SINH_TU", "GiaoDich", "giao_dich_phu_hop_quy_dinh_dai_dien", {}),
    ("NghiaVu", "nghia_vu_lien_doi_tu_nghia_vu_chung", "PHAT_SINH_TU", "NghiaVu", "nghia_vu_chung_cua_vo_chong", {}),
    ("NghiaVu", "nghia_vu_chung_cua_vo_chong", "PHAT_SINH_TU", "DieuKien", "no_phat_sinh_trong_thoi_ky_hon_nhan", {}),
    ("NghiaVu", "nghia_vu_chung_cua_vo_chong", "PHAT_SINH_TU", "DieuKien", "no_phuc_vu_nhu_cau_gia_dinh", {}),
    ("NghiaVu", "nghia_vu_chung_cua_vo_chong", "PHAT_SINH_TU", "DieuKien", "no_phuc_vu_kinh_doanh_chung", {}),
    ("NghiaVu", "nghia_vu_rieng_cua_mot_ben", "PHAT_SINH_TU", "DieuKien", "no_phuc_vu_muc_dich_ca_nhan", {}),
    ("NghiaVu", "nghia_vu_chung_cua_vo_chong", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_chung", {}),
    ("NghiaVu", "nghia_vu_rieng_cua_mot_ben", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_rieng", {}),
    ("HanhVi", "thanh_toan_no_bang_tai_san_chung", "TAC_DONG_LEN", "NghiaVu", "nghia_vu_chung_cua_vo_chong", {}),
    ("HanhVi", "thanh_toan_no_bang_tai_san_chung", "LIEN_QUAN", "NghiaVu", "nghia_vu_rieng_cua_mot_ben", {}),
    ("HanhVi", "giai_quyet_no_khi_ly_hon", "DAN_TOI", "NghiaVu", "trach_nhiem_voi_nguoi_thu_ba_khi_ly_hon", {}),
    ("NghiaVu", "trach_nhiem_voi_nguoi_thu_ba_khi_ly_hon", "PHAT_SINH_TU", "DieuKien", "no_phat_sinh_trong_thoi_ky_hon_nhan", {}),
    ("NghiaVu", "trach_nhiem_voi_nguoi_thu_ba_khi_ly_hon", "LIEN_QUAN", "ChuThe", "nguoi_thu_ba", {}),
]


CAN_CU_TAI: list[tuple[str, str, str]] = [
    ("ChuThe", "toa_an", "Luat_HNGD_2014_Dieu_24_Khoan_3"),
    ("ChuThe", "nguoi_thu_ba_ngay_tinh", "Luat_HNGD_2014_Dieu_26_Khoan_2"),
    ("HanhVi", "xac_lap_thuc_hien_cham_dut_giao_dich", "Luat_HNGD_2014_Dieu_24_Khoan_1"),
    ("HanhVi", "uy_quyen_giua_vo_chong", "Luat_HNGD_2014_Dieu_24_Khoan_2"),
    ("HanhVi", "dai_dien_khi_mat_nang_luc_hanh_vi_dan_su", "Luat_HNGD_2014_Dieu_24_Khoan_3"),
    ("HanhVi", "dai_dien_khi_han_che_nang_luc_hanh_vi_dan_su", "Luat_HNGD_2014_Dieu_24_Khoan_3"),
    ("HanhVi", "toa_an_chi_dinh_nguoi_khac_dai_dien_khi_ly_hon", "Luat_HNGD_2014_Dieu_24_Khoan_3"),
    ("HanhVi", "kinh_doanh_chung_cua_vo_chong", "Luat_HNGD_2014_Dieu_25_Khoan_1"),
    ("HanhVi", "truc_tiep_tham_gia_quan_he_kinh_doanh", "Luat_HNGD_2014_Dieu_25_Khoan_1"),
    ("HanhVi", "dua_tai_san_chung_vao_kinh_doanh", "Luat_HNGD_2014_Dieu_25_Khoan_2"),
    ("HanhVi", "dua_tai_san_chung_vao_kinh_doanh", "Luat_HNGD_2014_Dieu_36"),
    ("HanhVi", "giao_dich_tai_san_chung_gcn_mot_ben", "Luat_HNGD_2014_Dieu_26_Khoan_1"),
    ("HanhVi", "mot_ben_tu_minh_giao_dich_trai_quy_dinh_dai_dien", "Luat_HNGD_2014_Dieu_26_Khoan_2"),
    ("HanhVi", "thanh_toan_no_bang_tai_san_chung", "Luat_HNGD_2014_Dieu_27_Khoan_2"),
    ("HanhVi", "thanh_toan_no_bang_tai_san_chung", "Luat_HNGD_2014_Dieu_37"),
    ("HanhVi", "giai_quyet_no_khi_ly_hon", "Luat_HNGD_2014_Dieu_27_Khoan_2"),
    ("HanhVi", "giai_quyet_no_khi_ly_hon", "Luat_HNGD_2014_Dieu_60_Khoan_1"),
    ("Quyen", "quyen_uy_quyen_cho_nhau", "Luat_HNGD_2014_Dieu_24_Khoan_2"),
    ("Quyen", "quyen_dai_dien_cho_ben_mat_han_che_nang_luc", "Luat_HNGD_2014_Dieu_24_Khoan_3"),
    ("Quyen", "quyen_loi_nguoi_thu_ba_ngay_tinh_duoc_bao_ve", "Luat_HNGD_2014_Dieu_26_Khoan_2"),
    ("GiaoDich", "giao_dich_can_su_dong_y_cua_ca_hai", "Luat_HNGD_2014_Dieu_24_Khoan_2"),
    ("GiaoDich", "giao_dich_phu_hop_quy_dinh_dai_dien", "Luat_HNGD_2014_Dieu_27_Khoan_1"),
    ("GiaoDich", "giao_dich_mot_ben_dap_ung_nhu_cau_thiet_yeu", "Luat_HNGD_2014_Dieu_27_Khoan_1"),
    ("GiaoDich", "giao_dich_mot_ben_dap_ung_nhu_cau_thiet_yeu", "Luat_HNGD_2014_Dieu_30_Khoan_1"),
    ("GiaoDich", "giao_dich_voi_nguoi_thu_ba", "Luat_HNGD_2014_Dieu_26_Khoan_2"),
    ("GiaoDich", "giao_dich_mua_ban_chuyen_nhuong_tai_san_chung", "Luat_HNGD_2014_Dieu_26_Khoan_1"),
    ("GiaoDich", "giao_dich_mua_ban_chuyen_nhuong_tai_san_chung", "Luat_HNGD_2014_Dieu_26_Khoan_2"),
    ("NghiaVu", "nghia_vu_lien_doi_tu_giao_dich_mot_ben", "Luat_HNGD_2014_Dieu_27_Khoan_1"),
    ("NghiaVu", "nghia_vu_lien_doi_tu_giao_dich_phu_hop_dai_dien", "Luat_HNGD_2014_Dieu_27_Khoan_1"),
    ("NghiaVu", "nghia_vu_lien_doi_tu_nghia_vu_chung", "Luat_HNGD_2014_Dieu_27_Khoan_2"),
    ("NghiaVu", "nghia_vu_chung_cua_vo_chong", "Luat_HNGD_2014_Dieu_27_Khoan_2"),
    ("NghiaVu", "nghia_vu_chung_cua_vo_chong", "Luat_HNGD_2014_Dieu_37"),
    ("NghiaVu", "nghia_vu_rieng_cua_mot_ben", "Luat_HNGD_2014_Dieu_45"),
    ("NghiaVu", "trach_nhiem_voi_nguoi_thu_ba_khi_ly_hon", "Luat_HNGD_2014_Dieu_27_Khoan_2"),
    ("NghiaVu", "trach_nhiem_voi_nguoi_thu_ba_khi_ly_hon", "Luat_HNGD_2014_Dieu_37"),
    ("NghiaVu", "trach_nhiem_voi_nguoi_thu_ba_khi_ly_hon", "Luat_HNGD_2014_Dieu_60_Khoan_1"),
    ("LoaiTaiSan", "tai_san_chung", "Luat_HNGD_2014_Dieu_37"),
    ("LoaiTaiSan", "tai_san_rieng", "Luat_HNGD_2014_Dieu_45"),
    ("LoaiTaiSan", "tai_san_chung_dua_vao_kinh_doanh", "Luat_HNGD_2014_Dieu_25_Khoan_2"),
    ("LoaiTaiSan", "tai_san_chung_dua_vao_kinh_doanh", "Luat_HNGD_2014_Dieu_36"),
    ("LoaiTaiSan", "tai_san_chung_co_gcn_chi_ghi_ten_mot_ben", "Luat_HNGD_2014_Dieu_26_Khoan_1"),
    ("ThoaThuan", "thoa_thuan_uy_quyen_giua_vo_chong", "Luat_HNGD_2014_Dieu_24_Khoan_2"),
    ("ThoaThuan", "thoa_thuan_nguoi_dai_dien_truoc_khi_kinh_doanh", "Luat_HNGD_2014_Dieu_25_Khoan_1"),
    ("ThoaThuan", "thoa_thuan_kinh_doanh", "Luat_HNGD_2014_Dieu_25_Khoan_2"),
    ("ThoaThuan", "thoa_thuan_kinh_doanh", "Luat_HNGD_2014_Dieu_36"),
    ("VanBanPhapLy", "gcn_quyen_so_huu_chi_ghi_ten_mot_ben", "Luat_HNGD_2014_Dieu_26_Khoan_1"),
    ("VanBanPhapLy", "gcn_quyen_su_dung_chi_ghi_ten_mot_ben", "Luat_HNGD_2014_Dieu_26_Khoan_1"),
    ("DieuKien", "can_cu_dai_dien_theo_luat_hngd_blds_luat_lien_quan", "Luat_HNGD_2014_Dieu_24_Khoan_1"),
    ("DieuKien", "mat_nang_luc_hanh_vi_dan_su", "Luat_HNGD_2014_Dieu_24_Khoan_3"),
    ("DieuKien", "ben_kia_du_dieu_kien_lam_nguoi_giam_ho", "Luat_HNGD_2014_Dieu_24_Khoan_3"),
    ("DieuKien", "han_che_nang_luc_hanh_vi_dan_su", "Luat_HNGD_2014_Dieu_24_Khoan_3"),
    ("DieuKien", "ben_kia_duoc_toa_an_chi_dinh_dai_dien", "Luat_HNGD_2014_Dieu_24_Khoan_3"),
    ("DieuKien", "yeu_cau_ly_hon_khi_ben_kia_mat_nang_luc", "Luat_HNGD_2014_Dieu_24_Khoan_3"),
    ("DieuKien", "vo_chong_kinh_doanh_chung", "Luat_HNGD_2014_Dieu_25_Khoan_1"),
    ("DieuKien", "co_thoa_thuan_khac_truoc_khi_kinh_doanh", "Luat_HNGD_2014_Dieu_25_Khoan_1"),
    ("DieuKien", "gcn_chi_ghi_ten_mot_ben", "Luat_HNGD_2014_Dieu_26_Khoan_1"),
    ("DieuKien", "no_phat_sinh_trong_thoi_ky_hon_nhan", "Luat_HNGD_2014_Dieu_27_Khoan_2"),
    ("DieuKien", "no_phat_sinh_trong_thoi_ky_hon_nhan", "Luat_HNGD_2014_Dieu_37"),
    ("DieuKien", "no_phuc_vu_nhu_cau_gia_dinh", "Luat_HNGD_2014_Dieu_27_Khoan_1"),
    ("DieuKien", "no_phuc_vu_nhu_cau_gia_dinh", "Luat_HNGD_2014_Dieu_30_Khoan_1"),
    ("DieuKien", "no_phuc_vu_nhu_cau_gia_dinh", "Luat_HNGD_2014_Dieu_37_Khoan_2"),
    ("DieuKien", "no_phuc_vu_kinh_doanh_chung", "Luat_HNGD_2014_Dieu_27_Khoan_2"),
    ("DieuKien", "no_phuc_vu_kinh_doanh_chung", "Luat_HNGD_2014_Dieu_37_Khoan_1"),
    ("DieuKien", "no_phuc_vu_muc_dich_ca_nhan", "Luat_HNGD_2014_Dieu_45_Khoan_3"),
    ("HauQua", "dai_dien_hop_phap_trong_giao_dich", "Luat_HNGD_2014_Dieu_24_Khoan_2"),
    ("HauQua", "dai_dien_hop_phap_trong_giao_dich", "Luat_HNGD_2014_Dieu_24_Khoan_3"),
    ("HauQua", "dai_dien_hop_phap_trong_kinh_doanh_chung", "Luat_HNGD_2014_Dieu_25_Khoan_1"),
    ("HauQua", "ap_dung_quy_dinh_dai_dien_dieu_24_25", "Luat_HNGD_2014_Dieu_26_Khoan_1"),
    ("HauQua", "giao_dich_vo_hieu_do_trai_quy_dinh_dai_dien", "Luat_HNGD_2014_Dieu_26_Khoan_2"),
    ("HauQua", "giao_dich_duoc_bao_ve_vi_nguoi_thu_ba_ngay_tinh", "Luat_HNGD_2014_Dieu_26_Khoan_2"),
    ("TruongHopNgoaiLe", "quyen_nghia_vu_phai_tu_minh_thuc_hien", "Luat_HNGD_2014_Dieu_24_Khoan_3"),
    ("TruongHopNgoaiLe", "co_thoa_thuan_hoac_luat_quy_dinh_khac_ve_dai_dien_kinh_doanh", "Luat_HNGD_2014_Dieu_25_Khoan_1"),
    ("TruongHopNgoaiLe", "ngoai_le_nguoi_thu_ba_ngay_tinh_duoc_bao_ve", "Luat_HNGD_2014_Dieu_26_Khoan_2"),
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
    print(f"[reset] Xoá node có label :{TOPIC_LABEL}...")
    session.run(f"MATCH (n:{TOPIC_LABEL}) DETACH DELETE n")


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
        help=f"Xoá node có label :{TOPIC_LABEL} trước khi build.",
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
