"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic xu_phat_vi_pham."""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "loai_che_tai": {
        "phạt hành chính": "vphc",
        "phạt tiền": "vphc",
        "mức phạt tiền": "vphc",
        "truy cứu hình sự": "hinh_su",
        "trách nhiệm hình sự": "hinh_su",
        "phạt tù": "hinh_su",
        "đi tù": "hinh_su",
        "tội gì": "hinh_su",
        "cả hành chính và hình sự": "ca_hai",
        "toàn bộ chế tài": "ca_hai",
    },
    "khia_canh_che_tai": {
        "phạt bao nhiêu": "muc_phat",
        "mức phạt": "muc_phat",
        "cao nhất bao nhiêu": "muc_phat",
        "khi nào bị": "dieu_kien_ap_dung",
        "điều kiện truy cứu": "dieu_kien_ap_dung",
        "có cấu thành không": "dieu_kien_ap_dung",
        "tịch thu": "hinh_thuc_bo_sung",
        "đình chỉ": "hinh_thuc_bo_sung",
        "tước giấy phép": "hinh_thuc_bo_sung",
        "cấm hành nghề": "hinh_thuc_bo_sung",
        "buộc xin lỗi": "bien_phap_khac_phuc",
        "trả lại tài sản": "bien_phap_khac_phuc",
        "nộp lại tiền": "bien_phap_khac_phuc",
        "khắc phục": "bien_phap_khac_phuc",
    },
    "dang_hanh_vi": {
        "ngoại tình": "ngoai_tinh_khong_ro",
        "có bồ": "ngoai_tinh_khong_ro",
        "sống với nhau như vợ chồng": "chung_song_khi_dang_co_vo_chong",
        "ăn ở như vợ chồng": "chung_song_khi_dang_co_vo_chong",
        "lấy thêm vợ": "ket_hon_voi_nguoi_khac",
        "lấy thêm chồng": "ket_hon_voi_nguoi_khac",
        "tảo hôn": "ket_hon_chua_du_tuoi",
        "cưới khi chưa đủ tuổi": "ket_hon_chua_du_tuoi",
        "tổ chức hôn lễ cho trẻ": "to_chuc_tao_hon",
        "bố mẹ cho con chưa đủ tuổi lấy chồng": "to_chuc_tao_hon",
        "vẫn duy trì sau bản án": "duy_tri_sau_ban_an",
        "ép cưới": "cuong_ep_ket_hon",
        "bắt lấy chồng": "cuong_ep_ket_hon",
        "bắt lấy vợ": "cuong_ep_ket_hon",
        "ép ly hôn": "cuong_ep_ly_hon",
        "bắt bỏ vợ chồng": "cuong_ep_ly_hon",
        "không cho cưới": "can_tro_ket_hon",
        "phá đám cưới": "can_tro_ket_hon",
        "không cho ly hôn": "can_tro_ly_hon",
        "thách cưới": "yeu_sach_cua_cai",
        "đòi của hồi môn quá đáng": "yeu_sach_cua_cai",
        "đẻ thuê": "mang_thai_ho_thuong_mai",
        "mang thai hộ lấy tiền": "mang_thai_ho_thuong_mai",
        "môi giới mang thai hộ": "to_chuc_mang_thai_ho_thuong_mai",
        "đường dây mang thai hộ": "to_chuc_mang_thai_ho_thuong_mai",
        "bỏ nghĩa vụ giám hộ": "tron_tranh_nghia_vu",
        "khai gian hồ sơ con nuôi": "khai_sai",
        "sửa giấy tờ con nuôi": "tay_xoa_giay_to",
        "tẩy xóa giấy tờ con nuôi": "tay_xoa_giay_to",
        "ép cho con nuôi": "ep_buoc_dong_y",
        "nhận con nuôi để bóc lột": "boc_lot_suc_lao_dong",
        "cho mượn giấy phép văn phòng con nuôi": "cho_muon_giay_phep",
        "đánh đập": "danh_dap",
        "hành hung thành viên gia đình": "danh_dap",
        "bỏ đói": "hanh_ha_nguoc_dai",
        "ngược đãi": "hanh_ha_nguoc_dai",
        "không cho vệ sinh": "hanh_ha_nguoc_dai",
        "không đưa đi cấp cứu": "khong_cap_cuu_cham_soc",
        "bỏ mặc cha mẹ già": "bo_mac_khong_cham_soc",
        "bỏ mặc người khuyết tật": "bo_mac_khong_cham_soc",
        "chửi bới": "lang_ma_chiet_chi",
        "lăng mạ": "lang_ma_chiet_chi",
        "chì chiết": "lang_ma_chiet_chi",
        "đăng ảnh riêng tư": "phat_tan_bi_mat_de_xuc_pham",
        "nhốt trong nhà": "co_lap_giam_cam",
        "cô lập": "co_lap_giam_cam",
        "không cho gặp người thân": "ngan_gap_go",
        "bắt xem cảnh bạo lực": "ep_chung_kien_bao_luc",
        "ép xem phim khiêu dâm": "ep_tiep_nhan_noi_dung_khieu_dam",
        "ép quan hệ vợ chồng": "ep_quan_he_tinh_duc_trai_y_muon",
        "chiếm đoạt tài sản": "chiem_doat_tai_san",
        "lấy tài sản riêng của vợ": "chiem_doat_tai_san",
        "lấy tài sản riêng của chồng": "chiem_doat_tai_san",
        "giữ lương": "kiem_soat_tai_san_thu_nhap",
        "kiểm soát tiền": "kiem_soat_tai_san_thu_nhap",
        "đuổi ra khỏi nhà": "cuong_ep_thong_thuong",
        "trả thù người báo tin": "tra_thu_hanh_hung",
        "xúi người khác đánh vợ": "kich_dong_xui_giuc",
        "xúi người khác đánh chồng": "kich_dong_xui_giuc",
        "biết mà không báo": "khong_bao_tin",
        "bao che bạo lực gia đình": "dung_tung_bao_che",
        "lộ địa chỉ tạm lánh": "tiet_lo_noi_tam_lanh",
        "lộ danh tính người báo tin": "tiet_lo_nguoi_bao_tin",
        "không niêm yết giá": "khong_cong_khai_bang_gia",
        "cơ sở trợ giúp kiếm lời": "lap_co_so_co_loi_nhuan",
        "hoạt động chưa có giấy đăng ký": "chua_duoc_cap",
        "vi phạm lệnh cấm tiếp xúc": "den_gan_trong_100m",
        "đến gần dưới 100 mét": "den_gan_trong_100m",
        "nhắn tin đe dọa khi bị cấm tiếp xúc": "dung_dien_thoai_email_cong_cu_de_bao_luc",
    },
    "hau_qua_hinh_su": {
        "gia đình tan vỡ": "dan_den_ly_hon",
        "dẫn đến ly hôn": "dan_den_ly_hon",
        "tự sát": "lam_tu_sat",
        "tòa bắt chấm dứt": "khong_chap_hanh_quyet_dinh_toa",
    },
    "moi_quan_he": {
        "ba đời": "trong_pham_vi_ba_doi",
        "họ hàng gần": "trong_pham_vi_ba_doi",
        "cận huyết": "trong_pham_vi_ba_doi",
        "cha nuôi": "cha_me_nuoi_con_nuoi",
        "mẹ nuôi": "cha_me_nuoi_con_nuoi",
        "cha chồng": "quan_he_thong_gia_nuoi_duong_cu",
        "con dâu": "quan_he_thong_gia_nuoi_duong_cu",
        "cùng huyết thống": "cung_dong_mau_truc_he",
        "loạn luân": "co",
        "giao cấu": "co",
    },
    "co_hanh_vi_giao_cau": {
        "loạn luân": "co",
        "giao cấu": "co",
    },
    "dang_gia_tao": {
        "kết hôn giả": "ket_hon_gia_tao",
        "ly hôn giả": "ly_hon_gia_tao",
    },
    "muc_dich": {
        "nhập quốc tịch": "nhap_quoc_tich",
        "né nợ": "tron_nghia_vu_tai_san",
        "tẩu tán tài sản": "tron_nghia_vu_tai_san",
    },
    "dang_nghia_vu": {
        "không gửi tiền nuôi con": "cap_duong",
        "không nuôi cha mẹ": "nuoi_duong",
    },
    "quan_he_cap_duong": {
        "không cấp dưỡng cho con": "cha_me_con",
        "vợ chồng sau ly hôn": "vo_chong_sau_ly_hon",
    },
    "muc_do": {
        "đuổi ra khỏi nhà": "cuong_ep_thong_thuong",
        "dọa giết để đuổi": "de_doa_suc_khoe_tinh_mang",
    },
    "dang_quyen": {
        "thăm con": "tham_nom",
        "thăm nuôi": "tham_nom",
    },
    "quan_he": {
        "ông bà thăm cháu": "ong_ba_chau",
        "thăm con": "cha_me_con",
    },
    "pham_vi": {
        "kết hôn trái pháp luật": "ket_hon_trai_phap_luat",
        "hợp đồng hôn nhân": "vi_pham_ket_hon_ly_hon",
    },
}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def resolve_term(field_name: str, query: str) -> Optional[str]:
    mapping = COMMON_TO_LEGAL_TERMS.get(field_name)
    if not mapping:
        return None
    q = _normalize(query)
    best_key = ""
    best_val = None
    for phrase, value in mapping.items():
        p = _normalize(phrase)
        if p in q and len(p) > len(best_key):
            best_key = p
            best_val = value
    return best_val
