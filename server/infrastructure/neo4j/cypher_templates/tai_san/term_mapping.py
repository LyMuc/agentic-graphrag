"""Ánh xạ thuật ngữ thông thường → thuật ngữ pháp lý chuẩn cho topic Tài sản.

Cung cấp `COMMON_TO_LEGAL_TERMS` (dict đa cấp theo field) và hàm
`resolve_term(field, raw_text)` để retriever chuẩn hoá raw text trước
khi đẩy params vào Cypher SEED.

Cách hoạt động:
- Mỗi field (vd "loai_tai_san", "loai_giao_dich") có 1 dict {pattern: legal_term}.
- `resolve_term` thực hiện case-insensitive substring match. Nếu raw_text chứa
  pattern → trả legal_term tương ứng. Nếu không match → trả None.
- Một số field trả về tuple (vd `loai_nghia_vu` trả `(loai, sub_keyword)` để
  retriever vừa biết phân loại vừa có tham số phụ trợ).

Lưu ý:
- KHÔNG dùng làm "ground truth" duy nhất — LLM extract vẫn được quyền điền giá
  trị enum thẳng từ mô tả Pydantic. `resolve_term` chỉ là SAFETY NET bổ sung
  khi LLM copy nguyên văn từ ngữ thông tục.
- Khi raw_text rỗng/None → trả None.
"""
from __future__ import annotations

import re
from typing import Any, Optional


# =============================================================================
# 1. Bảng ánh xạ chính
# =============================================================================
COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Loại tài sản — map về `id` của LoaiTaiSan trong KG
    # -------------------------------------------------------------------------
    "loai_tai_san": {
        # Bất động sản & quyền sử dụng đất
        "quyền sử dụng đất": "quyen_su_dung_dat",
        "qsdđ": "quyen_su_dung_dat",
        "sổ đỏ": "quyen_su_dung_dat",
        "đất": "quyen_su_dung_dat",
        "thửa đất": "quyen_su_dung_dat",
        "bất động sản": "bat_dong_san",
        "căn hộ chung cư": "bat_dong_san",
        "chung cư": "bat_dong_san",
        "căn hộ": "bat_dong_san",
        "nhà ở duy nhất": "nha_o_duy_nhat",
        "nhà ở": "bat_dong_san",
        "nhà": "bat_dong_san",
        # Động sản phải đăng ký
        "ô tô": "dong_san_phai_dang_ky",
        "xe ô tô": "dong_san_phai_dang_ky",
        "xe hơi": "dong_san_phai_dang_ky",
        "xe máy": "dong_san_phai_dang_ky",
        "động sản phải đăng ký": "dong_san_phai_dang_ky",
        # Tài khoản / chứng khoán
        "sổ tiết kiệm": "tai_khoan_ngan_hang_chung_khoan",
        "tài khoản ngân hàng": "tai_khoan_ngan_hang_chung_khoan",
        "tài khoản chứng khoán": "tai_khoan_ngan_hang_chung_khoan",
        # Thu nhập
        "lương": "thu_nhap_lao_dong",
        "tiền lương": "thu_nhap_lao_dong",
        "thu nhập đi làm": "thu_nhap_lao_dong",
        "thu nhập do lao động": "thu_nhap_lao_dong",
        "thu nhập từ kinh doanh": "thu_nhap_san_xuat_kinh_doanh",
        "thu nhập kinh doanh": "thu_nhap_san_xuat_kinh_doanh",
        "doanh thu": "thu_nhap_san_xuat_kinh_doanh",
        "lợi nhuận kinh doanh": "thu_nhap_san_xuat_kinh_doanh",
        "tiền trúng số": "thu_nhap_hop_phap_khac",
        "tiền trúng thưởng": "thu_nhap_hop_phap_khac",
        "trúng số": "thu_nhap_hop_phap_khac",
        "trúng thưởng": "thu_nhap_hop_phap_khac",
        "tiền may rủi": "thu_nhap_hop_phap_khac",
        "thu nhập khác": "thu_nhap_hop_phap_khac",
        # Hoa lợi / lợi tức
        "hoa lợi": "hoa_loi_loi_tuc",
        "lợi tức": "hoa_loi_loi_tuc",
        "tiền cho thuê": "hoa_loi_loi_tuc",
        "cổ tức": "hoa_loi_loi_tuc",
        # Nguồn gốc
        "tài sản trước hôn nhân": "tai_san_truoc_ket_hon",
        "tài sản trước khi cưới": "tai_san_truoc_ket_hon",
        "trước hôn nhân": "tai_san_truoc_ket_hon",
        "trước kết hôn": "tai_san_truoc_ket_hon",
        "trước khi kết hôn": "tai_san_truoc_ket_hon",
        "thừa kế chung": "tai_san_thua_ke_chung",
        "thừa kế riêng": "tai_san_thua_ke_rieng",
        "tặng cho chung": "tai_san_tang_cho_chung",
        "biếu chung": "tai_san_tang_cho_chung",
        "tặng cho riêng": "tai_san_tang_cho_rieng",
        "biếu riêng": "tai_san_tang_cho_rieng",
        # Tài sản chung / riêng (chung chung)
        "tài sản chung": "tai_san_chung",
        "tài sản riêng": "tai_san_rieng",
        # Nhu cầu cá nhân
        "đồ dùng cá nhân": "tai_san_phuc_vu_nhu_cau_thiet_yeu_ca_nhan",
        "quần áo cá nhân": "tai_san_phuc_vu_nhu_cau_thiet_yeu_ca_nhan",
        "tài sản cá nhân": "tai_san_phuc_vu_nhu_cau_thiet_yeu_ca_nhan",
        # Tranh chấp
        "tài sản đang tranh chấp": "tai_san_dang_tranh_chap",
        "tài sản chưa rõ chủ": "tai_san_dang_tranh_chap",
        # Nguồn thu nhập chủ yếu
        "nguồn thu nhập chủ yếu": "tai_san_tao_thu_nhap_chu_yeu",
        "nguồn thu nhập chính": "tai_san_tao_thu_nhap_chu_yeu",
    },
    # -------------------------------------------------------------------------
    # Loại giao dịch — map về `loai` (hoặc `id`) của HanhVi
    # -------------------------------------------------------------------------
    "loai_giao_dich": {
        "bán đất": "ban_chuyen_nhuong",
        "bán nhà": "ban_chuyen_nhuong",
        "bán bất động sản": "ban_chuyen_nhuong",
        "bán": "ban_chuyen_nhuong",
        "chuyển nhượng": "ban_chuyen_nhuong",
        "mua bán": "ban_chuyen_nhuong",
        "tặng cho": "tang_cho",
        "tặng": "tang_cho",
        "cho": "tang_cho",
        "biếu": "tang_cho",
        "thế chấp": "the_chap_cam_co",
        "cầm cố": "the_chap_cam_co",
        "vay thế chấp": "the_chap_cam_co",
        "đứng tên": "dang_ky_quyen_so_huu",
        "ghi tên": "dang_ky_quyen_so_huu",
        "đăng ký quyền sở hữu": "dang_ky_quyen_so_huu",
        "ký hợp đồng": "dinh_doat_van_ban",
        "ký tên": "dinh_doat_van_ban",
        "đưa vào kinh doanh": "kinh_doanh",
        "góp vốn": "kinh_doanh",
        "định đoạt": "dinh_doat",
        "sử dụng": "su_dung",
        "chiếm hữu": "su_dung",
        "chia": "chia",
        "phân chia": "chia",
        "nhập vào tài sản chung": "nhap",
        "sáp nhập": "nhap",
    },
    # -------------------------------------------------------------------------
    # Nghĩa vụ — trả (loai_nghia_vu, optional_sub_keyword)
    # -------------------------------------------------------------------------
    "loai_nghia_vu": {
        # === ĐỐI CHIẾU chung-riêng (cần whitelist Đ27+30+37+45 — dùng tat_ca) ===
        # Ưu tiên các pattern này TRƯỚC (longest-match đảm bảo qua sort) để
        # không bị 'nợ chung' / 'nợ riêng' nuốt mất khi câu chứa cả 2.
        "lấy tài sản chung trả nợ riêng": ("tat_ca", None),
        "lấy tài sản chung để trả nợ riêng": ("tat_ca", None),
        "dùng tài sản chung trả nợ riêng": ("tat_ca", None),
        "dùng tài sản chung để trả nợ riêng": ("tat_ca", None),
        "tài sản chung trả nợ riêng": ("tat_ca", None),
        "lấy tài sản riêng trả nợ chung": ("tat_ca", None),
        "dùng tài sản riêng trả nợ chung": ("tat_ca", None),
        "tài sản riêng trả nợ chung": ("tat_ca", None),
        "nợ này là chung hay riêng": ("tat_ca", None),
        "nợ chung hay riêng": ("tat_ca", None),
        "phân biệt nghĩa vụ chung và riêng": ("tat_ca", None),
        "vợ có phải trả nợ thay chồng": ("tat_ca", None),
        "chồng có phải trả nợ thay vợ": ("tat_ca", None),
        "nợ của một bên có thành nợ chung": ("tat_ca", None),
        # === Single-side keywords ===
        "nợ chung": ("chung", None),
        "nợ riêng": ("rieng", None),
        "nợ trước hôn nhân": ("rieng", "truoc_ket_hon"),
        "nợ trước khi cưới": ("rieng", "truoc_ket_hon"),
        "nuôi con": ("chung", "nhu_cau_thiet_yeu"),
        "nuôi dưỡng con": ("chung", "nhu_cau_thiet_yeu"),
        "tiền học cho con": ("chung", "nhu_cau_thiet_yeu"),
        "tiền học": ("chung", "nhu_cau_thiet_yeu"),
        "tiền chợ": ("chung", "nhu_cau_thiet_yeu"),
        "tiền sinh hoạt": ("chung", "nhu_cau_thiet_yeu"),
        "nhu cầu thiết yếu": ("chung", "nhu_cau_thiet_yeu"),
        "vay tiêu dùng cá nhân": ("rieng", "giao_dich_ca_nhan"),
        "vay riêng": ("rieng", "giao_dich_ca_nhan"),
        "đầu tư cá nhân": ("rieng", "giao_dich_ca_nhan"),
        "bồi thường do con gây ra": ("chung", "con_gay_thiet_hai"),
        "bồi thường do con": ("chung", "con_gay_thiet_hai"),
        "bồi thường do vi phạm pháp luật": ("rieng", "vi_pham_phap_luat"),
        "vi phạm pháp luật": ("rieng", "vi_pham_phap_luat"),
        "tai nạn giao thông": ("rieng", "vi_pham_phap_luat"),
        "liên đới": ("lien_doi", None),
        "trách nhiệm liên đới": ("lien_doi", None),
        "ôm nợ": ("rieng", "giao_dich_ca_nhan"),
    },
    # -------------------------------------------------------------------------
    # Khía cạnh thỏa thuận chế độ tài sản (Đ47-50)
    # -------------------------------------------------------------------------
    "khia_canh_thoa_thuan": {
        "ký trước khi cưới": "xac_lap",
        "lập trước kết hôn": "xac_lap",
        "công chứng": "xac_lap",
        "chứng thực": "xac_lap",
        "viết tay": "xac_lap",
        "không công chứng": "xac_lap",
        "không có công chứng": "xac_lap",
        "hình thức thỏa thuận": "xac_lap",
        "xác lập": "xac_lap",
        "nội dung gồm gì": "noi_dung",
        "nội dung của thỏa thuận": "noi_dung",
        "thỏa thuận gồm gì": "noi_dung",
        "ghi gì trong thỏa thuận": "noi_dung",
        "sửa đổi": "sua_doi",
        "thay đổi": "sua_doi",
        "bổ sung thỏa thuận": "sua_doi",
        "vô hiệu": "vo_hieu",
        "bị tuyên hủy": "vo_hieu",
        "bị hủy": "vo_hieu",
        "không có hiệu lực": "vo_hieu",
    },
    # -------------------------------------------------------------------------
    # Khía cạnh chia tài sản chung trong hôn nhân (Đ38-42)
    # -------------------------------------------------------------------------
    "khia_canh_chia": {
        "thỏa thuận chia": "thoa_thuan_chia",
        "ly thân tài sản": "thoa_thuan_chia",
        "tách tài sản": "thoa_thuan_chia",
        "chia tài sản trong hôn nhân": "thoa_thuan_chia",
        "khi nào có hiệu lực": "thoi_diem_hieu_luc",
        "thời điểm có hiệu lực": "thoi_diem_hieu_luc",
        "ngày bắt đầu chia": "thoi_diem_hieu_luc",
        "sau khi chia thì sao": "hau_qua",
        "hậu quả chia": "hau_qua",
        "tài sản sau chia": "hau_qua",
        "hủy việc chia": "cham_dut",
        "chấm dứt chia": "cham_dut",
        "khôi phục tài sản chung": "cham_dut",
        "không hợp lệ": "vo_hieu",
        "vô hiệu": "vo_hieu",
        "trốn nợ": "vo_hieu",
        "trốn nghĩa vụ": "vo_hieu",
    },
    # -------------------------------------------------------------------------
    # Khía cạnh tài sản riêng + nhà ở duy nhất (Đ31, 43, 44, 46)
    # -------------------------------------------------------------------------
    "khia_canh_tai_san_rieng": {
        "chiếm hữu tài sản riêng": "chiem_huu_su_dung",
        "sử dụng tài sản riêng": "chiem_huu_su_dung",
        "để dành tài sản riêng": "chiem_huu_su_dung",
        "định đoạt tài sản riêng": "dinh_doat",
        "bán tài sản riêng": "dinh_doat",
        "tặng tài sản riêng": "dinh_doat",
        "nhập tài sản riêng": "nhap_vao_chung",
        "nhập vào tài sản chung": "nhap_vao_chung",
        "sáp nhập tài sản": "nhap_vao_chung",
        "nhà ở duy nhất": "nha_o_duy_nhat",
        "nơi ở duy nhất": "nha_o_duy_nhat",
        "căn nhà duy nhất": "nha_o_duy_nhat",
        "nguồn sống duy nhất": "nguon_song_duy_nhat",
        "duy nhất nuôi sống": "nguon_song_duy_nhat",
    },
    # -------------------------------------------------------------------------
    # Khía cạnh nguyên tắc chế độ tài sản (Đ29-32)
    # -------------------------------------------------------------------------
    "khia_canh_nguyen_tac": {
        "bình đẳng": "binh_dang",
        "công bằng vợ chồng": "binh_dang",
        "không phân biệt lao động": "binh_dang",
        "nhu cầu thiết yếu gia đình": "nhu_cau_thiet_yeu_gia_dinh",
        "nhu cầu của gia đình": "nhu_cau_thiet_yeu_gia_dinh",
        "đóng góp tài sản riêng": "nhu_cau_thiet_yeu_gia_dinh",
        "nhà ở duy nhất": "giao_dich_nha_o_duy_nhat",
        "giao dịch nhà ở": "giao_dich_nha_o_duy_nhat",
        "người thứ ba ngay tình": "giao_dich_nguoi_thu_ba_ngay_tinh",
        "ngay tình": "giao_dich_nguoi_thu_ba_ngay_tinh",
        "đứng tên tài khoản": "giao_dich_nguoi_thu_ba_ngay_tinh",
    },
    # -------------------------------------------------------------------------
    # Loại tài sản đăng ký quyền sở hữu (Đ34)
    # -------------------------------------------------------------------------
    "loai_tai_san_dang_ky": {
        "đất": "bat_dong_san",
        "nhà": "bat_dong_san",
        "căn hộ": "bat_dong_san",
        "chung cư": "bat_dong_san",
        "bất động sản": "bat_dong_san",
        "ô tô": "dong_san_phai_dang_ky",
        "xe máy": "dong_san_phai_dang_ky",
        "xe": "dong_san_phai_dang_ky",
        "động sản phải đăng ký": "dong_san_phai_dang_ky",
    },
    # -------------------------------------------------------------------------
    # Scenario keywords — gợi ý template (không phải param)
    # -------------------------------------------------------------------------
    "scenario_keywords": {
        "nhân tình": ("chong_dinh_doat_tai_san_chung_trai_phep", "quyen_dinh_doat_tai_san"),
        "ngoại tình": ("chong_dinh_doat_tai_san_chung_trai_phep", "quyen_dinh_doat_tai_san"),
        "trúng số": ("xac_dinh_thu_nhap_hop_phap", "phan_loai_tai_san"),
        "ôm nợ": ("phan_loai_no", "nghia_vu_tai_san"),
        "trốn nợ": ("chia_tai_san_chung_de_tron_no", "chia_tai_san_thoi_ky_hon_nhan"),
        "viết tay": ("hop_dong_khong_cong_chung", "thoa_thuan_che_do_tai_san"),
    },
}


# =============================================================================
# 2. Resolver
# =============================================================================
def _normalize(text: str) -> str:
    """Hạ chữ thường + thay nhiều space liên tiếp bằng 1 space."""
    return re.sub(r"\s+", " ", text.lower().strip())


def resolve_term(field: str, raw_text: Optional[str]) -> Optional[Any]:
    """Trả về thuật ngữ pháp lý (str hoặc tuple) chuẩn theo `field`.

    Args:
        field: tên field trong COMMON_TO_LEGAL_TERMS (vd 'loai_tai_san').
        raw_text: chuỗi text (thường là param LLM extract được). None/rỗng → None.

    Returns:
        - str: legal term chuẩn (vd 'quyen_su_dung_dat').
        - tuple: với field `loai_nghia_vu` trả (loai, sub_keyword).
        - None: nếu không tìm được match nào, hoặc field không tồn tại.

    Quy tắc match:
        1. Nếu raw_text chứa pattern (substring), trả legal term tương ứng.
        2. Patterns được match theo độ dài giảm dần (longest match first) để
           tránh "đất" nuốt "nhà ở duy nhất".
        3. Case-insensitive, ignore extra whitespace.
    """
    if not raw_text or field not in COMMON_TO_LEGAL_TERMS:
        return None

    norm = _normalize(raw_text)
    mapping = COMMON_TO_LEGAL_TERMS[field]

    # Sort patterns by length DESC để longest-match-first
    patterns = sorted(mapping.keys(), key=len, reverse=True)
    for pattern in patterns:
        if pattern.lower() in norm:
            return mapping[pattern]
    return None


def resolve_many(field: str, raw_text: Optional[str]) -> list[Any]:
    """Trả về TẤT CẢ legal term match (không chỉ longest).

    Hữu ích khi raw_text chứa nhiều keyword (vd 'cả đất và xe máy').
    """
    if not raw_text or field not in COMMON_TO_LEGAL_TERMS:
        return []
    norm = _normalize(raw_text)
    mapping = COMMON_TO_LEGAL_TERMS[field]
    matched: list[Any] = []
    seen: set[Any] = set()
    for pattern, legal in sorted(mapping.items(), key=lambda x: -len(x[0])):
        if pattern.lower() in norm:
            key = legal if not isinstance(legal, tuple) else legal
            if key not in seen:
                matched.append(legal)
                seen.add(key)
    return matched


# =============================================================================
# 3. Public API
# =============================================================================
__all__ = ["COMMON_TO_LEGAL_TERMS", "resolve_term", "resolve_many"]
