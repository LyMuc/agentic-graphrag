"""Build KG ngữ nghĩa cho 'Chế độ tài sản của vợ chồng' (Điều 28-50 Luật HN&GĐ 2014).

Script này build / refresh lớp semantic ĐỘC LẬP với Knowledge-Graph-Builder cũ.
Chỉ MERGE node ngữ nghĩa và relationship nội bộ + CAN_CU_TAI sang layer luật
(DieuLuat / DieuKhoanLuat / DieuKhoanDiemLuat) đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_che_do_tai_san.py           # MERGE idempotent
    python scripts/build_kg_che_do_tai_san.py --reset   # XOÁ trước khi build
                                                          (chỉ semantic layer, KHÔNG
                                                           đụng đến layer luật)
    python scripts/build_kg_che_do_tai_san.py --dry-run # chỉ in summary, không ghi DB

Schema đầy đủ: docs/kg_che_do_tai_san_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


# =============================================================================
# 1. SEMANTIC LABELS (chỉ semantic layer; legal layer không liệt kê)
# =============================================================================
SEMANTIC_LABELS = [
    "ChePhapDoTaiSan",
    "LoaiTaiSan",
    "NguonGocTaiSan",
    "HanhVi",
    "NghiaVu",
    "Quyen",
    "ThoaThuan",
    "DieuKien",
    "HauQua",
    "ChuThe",
    "VanBanPhapLy",
    "TruongHopNgoaiLe",
]

# Quan hệ tới legal layer (chỉ dùng cho SEED)
LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}


# =============================================================================
# 2. NODES (semantic layer)
#    Cấu trúc: {label: [{"id", "ten", optional props ...}]}
# =============================================================================
NODES: dict[str, list[dict[str, Any]]] = {
    # -------------------------------------------------------------------------
    # Chế độ tài sản (Đ28)
    # -------------------------------------------------------------------------
    "ChePhapDoTaiSan": [
        {"id": "che_do_luat_dinh", "ten": "Chế độ tài sản theo luật định"},
        {"id": "che_do_thoa_thuan", "ten": "Chế độ tài sản theo thỏa thuận"},
    ],
    # -------------------------------------------------------------------------
    # Loại tài sản — đánh dấu tinh_chat (chung/rieng/trung_lap)
    # -------------------------------------------------------------------------
    "LoaiTaiSan": [
        # === TÀI SẢN CHUNG (Đ33) ===
        {"id": "tai_san_chung", "ten": "Tài sản chung của vợ chồng", "tinh_chat": "chung"},
        {"id": "thu_nhap_lao_dong", "ten": "Thu nhập do lao động", "tinh_chat": "chung"},
        {"id": "thu_nhap_san_xuat_kinh_doanh", "ten": "Thu nhập do hoạt động sản xuất, kinh doanh", "tinh_chat": "chung"},
        {"id": "hoa_loi_loi_tuc", "ten": "Hoa lợi, lợi tức phát sinh từ tài sản riêng", "tinh_chat": "chung"},
        {"id": "thu_nhap_hop_phap_khac", "ten": "Thu nhập hợp pháp khác (gồm tiền trúng số, trúng thưởng, may rủi...)", "tinh_chat": "chung"},
        {"id": "tai_san_thua_ke_chung", "ten": "Tài sản được thừa kế chung", "tinh_chat": "chung"},
        {"id": "tai_san_tang_cho_chung", "ten": "Tài sản được tặng cho chung", "tinh_chat": "chung"},
        {"id": "tai_san_thoa_thuan_la_chung", "ten": "Tài sản khác mà vợ chồng thỏa thuận là tài sản chung", "tinh_chat": "chung"},
        {"id": "quyen_su_dung_dat", "ten": "Quyền sử dụng đất có được sau khi kết hôn", "tinh_chat": "chung"},
        # === TÀI SẢN RIÊNG (Đ43) ===
        {"id": "tai_san_rieng", "ten": "Tài sản riêng của vợ, chồng", "tinh_chat": "rieng"},
        {"id": "tai_san_truoc_ket_hon", "ten": "Tài sản có trước khi kết hôn", "tinh_chat": "rieng"},
        {"id": "tai_san_thua_ke_rieng", "ten": "Tài sản được thừa kế riêng trong thời kỳ hôn nhân", "tinh_chat": "rieng"},
        {"id": "tai_san_tang_cho_rieng", "ten": "Tài sản được tặng cho riêng trong thời kỳ hôn nhân", "tinh_chat": "rieng"},
        {"id": "tai_san_phuc_vu_nhu_cau_thiet_yeu_ca_nhan", "ten": "Tài sản phục vụ nhu cầu thiết yếu cá nhân", "tinh_chat": "rieng"},
        {"id": "tai_san_hinh_thanh_tu_tai_san_rieng", "ten": "Tài sản hình thành từ tài sản riêng", "tinh_chat": "rieng"},
        {"id": "tai_san_chia_rieng_trong_hon_nhan", "ten": "Phần tài sản được chia riêng trong thời kỳ hôn nhân", "tinh_chat": "rieng"},
        # === LOẠI TÀI SẢN VẬT LÝ (trung_lap — chung hay riêng tuỳ ngữ cảnh) ===
        {"id": "bat_dong_san", "ten": "Bất động sản (nhà, đất, căn hộ chung cư...)", "tinh_chat": "trung_lap"},
        {"id": "dong_san_phai_dang_ky", "ten": "Động sản phải đăng ký quyền sở hữu (ô tô, xe máy...)", "tinh_chat": "trung_lap"},
        {"id": "dong_san_khong_phai_dang_ky", "ten": "Động sản không phải đăng ký quyền sở hữu", "tinh_chat": "trung_lap"},
        {"id": "tai_khoan_ngan_hang_chung_khoan", "ten": "Tài khoản ngân hàng, tài khoản chứng khoán", "tinh_chat": "trung_lap"},
        {"id": "nha_o_duy_nhat", "ten": "Nhà là nơi ở duy nhất của vợ chồng", "tinh_chat": "trung_lap"},
        {"id": "tai_san_tao_thu_nhap_chu_yeu", "ten": "Tài sản là nguồn tạo ra thu nhập chủ yếu của gia đình", "tinh_chat": "trung_lap"},
        {"id": "tai_san_chung_phai_dang_ky", "ten": "Tài sản chung phải đăng ký quyền sở hữu/sử dụng", "tinh_chat": "chung"},
        {"id": "tai_san_dang_tranh_chap", "ten": "Tài sản đang có tranh chấp giữa vợ và chồng", "tinh_chat": "trung_lap"},
    ],
    # -------------------------------------------------------------------------
    # Nguồn gốc tài sản
    # -------------------------------------------------------------------------
    "NguonGocTaiSan": [
        {"id": "truoc_ket_hon", "ten": "Có trước khi kết hôn"},
        {"id": "sau_ket_hon", "ten": "Có sau khi kết hôn (trong thời kỳ hôn nhân)"},
        {"id": "tao_lap_trong_hon_nhan", "ten": "Do vợ, chồng tạo ra trong thời kỳ hôn nhân"},
        {"id": "thua_ke_chung", "ten": "Được thừa kế chung"},
        {"id": "thua_ke_rieng", "ten": "Được thừa kế riêng"},
        {"id": "tang_cho_chung", "ten": "Được tặng cho chung"},
        {"id": "tang_cho_rieng", "ten": "Được tặng cho riêng"},
        {"id": "chia_tai_san_chung", "ten": "Phát sinh do chia tài sản chung trong hôn nhân"},
        {"id": "nhap_tu_tai_san_rieng", "ten": "Được nhập từ tài sản riêng vào tài sản chung"},
        {"id": "thoa_thuan_xac_lap", "ten": "Do thỏa thuận xác lập"},
        {"id": "phai_sinh_tu_tai_san_rieng", "ten": "Phát sinh từ tài sản riêng (hoa lợi, lợi tức)"},
    ],
    # -------------------------------------------------------------------------
    # Hành vi pháp lý / giao dịch
    # -------------------------------------------------------------------------
    "HanhVi": [
        # Đ29
        {"id": "tao_lap_chiem_huu_su_dung_dinh_doat_tai_san_chung", "ten": "Tạo lập, chiếm hữu, sử dụng, định đoạt tài sản chung", "loai": "tong_quat"},
        # Đ30
        {"id": "dap_ung_nhu_cau_thiet_yeu_gia_dinh", "ten": "Giao dịch nhằm đáp ứng nhu cầu thiết yếu của gia đình", "loai": "dap_ung_nhu_cau_thiet_yeu"},
        # Đ31
        {"id": "giao_dich_nha_o_duy_nhat", "ten": "Xác lập, thực hiện, chấm dứt giao dịch liên quan đến nhà ở duy nhất", "loai": "giao_dich_nha_o_duy_nhat"},
        # Đ32
        {"id": "giao_dich_nguoi_thu_ba_ngay_tinh", "ten": "Giao dịch với người thứ ba ngay tình", "loai": "giao_dich_nguoi_thu_ba_ngay_tinh"},
        # Đ34
        {"id": "dang_ky_quyen_so_huu", "ten": "Đăng ký quyền sở hữu, quyền sử dụng tài sản chung", "loai": "dang_ky"},
        # Đ35 — Định đoạt tài sản chung
        {"id": "dinh_doat_tai_san_chung", "ten": "Định đoạt tài sản chung", "loai": "dinh_doat"},
        {"id": "chiem_huu_su_dung_tai_san_chung", "ten": "Chiếm hữu, sử dụng tài sản chung", "loai": "su_dung"},
        {"id": "ban_chuyen_nhuong_bds", "ten": "Bán, chuyển nhượng bất động sản", "loai": "ban"},
        {"id": "the_chap_cam_co_bds", "ten": "Thế chấp, cầm cố bất động sản", "loai": "the_chap"},
        {"id": "tang_cho_bds", "ten": "Tặng cho bất động sản", "loai": "tang_cho"},
        # Đ36
        {"id": "dua_tai_san_chung_vao_kinh_doanh", "ten": "Đưa tài sản chung vào kinh doanh", "loai": "kinh_doanh"},
        # Đ38, 41
        {"id": "chia_tai_san_chung_trong_hon_nhan", "ten": "Chia tài sản chung trong thời kỳ hôn nhân", "loai": "chia"},
        {"id": "cham_dut_hieu_luc_chia", "ten": "Chấm dứt hiệu lực của việc chia tài sản chung", "loai": "cham_dut"},
        # Đ44 — Định đoạt tài sản riêng
        {"id": "dinh_doat_tai_san_rieng", "ten": "Định đoạt tài sản riêng", "loai": "dinh_doat"},
        {"id": "chiem_huu_su_dung_tai_san_rieng", "ten": "Chiếm hữu, sử dụng tài sản riêng", "loai": "su_dung"},
        {"id": "ban_chuyen_nhuong_tai_san_rieng", "ten": "Bán, chuyển nhượng tài sản riêng", "loai": "ban"},
        # Đ46
        {"id": "nhap_tai_san_rieng_vao_chung", "ten": "Nhập tài sản riêng vào tài sản chung", "loai": "nhap"},
        # Đ47
        {"id": "xac_lap_thoa_thuan_che_do", "ten": "Xác lập thỏa thuận chế độ tài sản trước kết hôn", "loai": "xac_lap_thoa_thuan"},
        # Đ49
        {"id": "sua_doi_bo_sung_thoa_thuan", "ten": "Sửa đổi, bổ sung thỏa thuận chế độ tài sản", "loai": "sua_doi"},
        # Đ38 (toà án)
        {"id": "khoi_kien_tai_toa_an", "ten": "Khởi kiện yêu cầu Tòa án giải quyết chia tài sản chung", "loai": "khoi_kien"},
    ],
    # -------------------------------------------------------------------------
    # Nghĩa vụ tài sản
    # -------------------------------------------------------------------------
    "NghiaVu": [
        # === Đ29 K2 + Đ30 — nhu cầu thiết yếu ===
        {"id": "nghia_vu_dap_ung_nhu_cau_thiet_yeu_gia_dinh", "ten": "Nghĩa vụ đáp ứng nhu cầu thiết yếu của gia đình", "loai_nghia_vu": "chung"},
        {"id": "nghia_vu_dong_gop_tai_san_rieng_khi_thieu_chung", "ten": "Nghĩa vụ đóng góp tài sản riêng khi không có/không đủ tài sản chung", "loai_nghia_vu": "rieng"},
        # === Đ31 — bảo đảm chỗ ở ===
        {"id": "nghia_vu_bao_dam_cho_o_cho_vo_chong", "ten": "Nghĩa vụ bảo đảm chỗ ở cho vợ chồng (khi nhà thuộc sở hữu riêng)", "loai_nghia_vu": "rieng"},
        # === Đ37 — Nghĩa vụ chung (6 loại) ===
        {"id": "nghia_vu_chung_tu_giao_dich_thoa_thuan", "ten": "Nghĩa vụ chung phát sinh từ giao dịch do vợ chồng cùng thỏa thuận xác lập, hoặc bồi thường thiệt hại chung", "loai_nghia_vu": "chung"},
        {"id": "nghia_vu_chung_dap_ung_nhu_cau_thiet_yeu_gia_dinh", "ten": "Nghĩa vụ chung do vợ hoặc chồng thực hiện nhằm đáp ứng nhu cầu thiết yếu của gia đình", "loai_nghia_vu": "chung"},
        {"id": "nghia_vu_chung_tu_chiem_huu_dinh_doat_tai_san_chung", "ten": "Nghĩa vụ chung phát sinh từ việc chiếm hữu, sử dụng, định đoạt tài sản chung", "loai_nghia_vu": "chung"},
        {"id": "nghia_vu_chung_tu_dung_tai_san_rieng_phuc_vu_tai_san_chung", "ten": "Nghĩa vụ chung phát sinh từ việc dùng tài sản riêng để duy trì, phát triển tài sản chung", "loai_nghia_vu": "chung"},
        {"id": "nghia_vu_chung_boi_thuong_do_con", "ten": "Nghĩa vụ chung bồi thường thiệt hại do con gây ra mà cha mẹ phải bồi thường", "loai_nghia_vu": "chung"},
        {"id": "nghia_vu_chung_khac_theo_luat", "ten": "Nghĩa vụ chung khác theo quy định của các luật có liên quan", "loai_nghia_vu": "chung"},
        # === Đ45 — Nghĩa vụ riêng (4 loại) ===
        {"id": "nghia_vu_rieng_truoc_ket_hon", "ten": "Nghĩa vụ riêng của mỗi bên vợ, chồng có trước khi kết hôn", "loai_nghia_vu": "rieng"},
        {"id": "nghia_vu_rieng_chiem_huu_dinh_doat_tai_san_rieng", "ten": "Nghĩa vụ riêng phát sinh từ việc chiếm hữu, sử dụng, định đoạt tài sản riêng", "loai_nghia_vu": "rieng"},
        {"id": "nghia_vu_rieng_giao_dich_ca_nhan_khong_vi_gia_dinh", "ten": "Nghĩa vụ riêng phát sinh từ giao dịch do một bên xác lập, thực hiện không vì nhu cầu gia đình", "loai_nghia_vu": "rieng"},
        {"id": "nghia_vu_rieng_vi_pham_phap_luat", "ten": "Nghĩa vụ riêng phát sinh từ hành vi vi phạm pháp luật của vợ, chồng", "loai_nghia_vu": "rieng"},
        # === Đ27 (liên đới) — bổ trợ ===
        {"id": "nghia_vu_lien_doi_dap_ung_nhu_cau_gia_dinh", "ten": "Nghĩa vụ liên đới của vợ chồng do giao dịch hợp pháp đáp ứng nhu cầu gia đình", "loai_nghia_vu": "lien_doi"},
    ],
    # -------------------------------------------------------------------------
    # Quyền tài sản
    # -------------------------------------------------------------------------
    "Quyen": [
        {"id": "quyen_lua_chon_che_do", "ten": "Quyền lựa chọn chế độ tài sản (luật định hoặc thỏa thuận)"},
        {"id": "quyen_binh_dang_tai_san_chung", "ten": "Quyền bình đẳng giữa vợ và chồng trong quyền/nghĩa vụ về tài sản chung"},
        {"id": "quyen_chiem_huu_su_dung_tai_san_rieng", "ten": "Quyền chiếm hữu, sử dụng tài sản riêng"},
        {"id": "quyen_dinh_doat_tai_san_rieng", "ten": "Quyền định đoạt tài sản riêng"},
        {"id": "quyen_nhap_hoac_khong_nhap_tai_san_rieng", "ten": "Quyền nhập hoặc không nhập tài sản riêng vào tài sản chung"},
        {"id": "quyen_quan_ly_thay", "ten": "Quyền quản lý tài sản riêng của bên kia khi bên kia không thể tự quản lý và không ủy quyền"},
        {"id": "quyen_yeu_cau_toa_an_chia", "ten": "Quyền yêu cầu Tòa án giải quyết việc chia tài sản chung trong thời kỳ hôn nhân"},
        {"id": "quyen_cham_dut_hieu_luc_chia", "ten": "Quyền thỏa thuận chấm dứt hiệu lực của việc chia tài sản chung"},
        {"id": "quyen_sua_doi_thoa_thuan", "ten": "Quyền sửa đổi, bổ sung thỏa thuận chế độ tài sản"},
    ],
    # -------------------------------------------------------------------------
    # Thỏa thuận
    # -------------------------------------------------------------------------
    "ThoaThuan": [
        # Đ47 — Thỏa thuận chế độ tài sản
        {
            "id": "thoa_thuan_che_do_tai_san",
            "ten": "Thỏa thuận về chế độ tài sản của vợ chồng",
            "yeu_cau_van_ban": True,
            "yeu_cau_cong_chung": True,
            "yeu_cau_chung_thuc": True,
            "thoi_diem_lap": "truoc_ket_hon",
            "co_the_sua_doi": True,
        },
        # Đ35 — Thỏa thuận định đoạt văn bản
        {
            "id": "thoa_thuan_dinh_doat_van_ban",
            "ten": "Thỏa thuận bằng văn bản khi định đoạt tài sản chung là BĐS, động sản đăng ký, hoặc nguồn thu nhập chủ yếu",
            "yeu_cau_van_ban": True,
            "yeu_cau_cong_chung": False,
            "yeu_cau_chung_thuc": False,
            "thoi_diem_lap": "trong_hon_nhan",
            "co_the_sua_doi": True,
        },
        # Đ38 — Thỏa thuận chia tài sản chung
        {
            "id": "thoa_thuan_chia_tai_san_chung",
            "ten": "Thỏa thuận chia tài sản chung trong thời kỳ hôn nhân",
            "yeu_cau_van_ban": True,
            "yeu_cau_cong_chung": False,
            "yeu_cau_chung_thuc": False,
            "thoi_diem_lap": "trong_hon_nhan",
            "co_the_sua_doi": True,
        },
        # Đ36 — Thỏa thuận kinh doanh
        {
            "id": "thoa_thuan_kinh_doanh",
            "ten": "Thỏa thuận đưa tài sản chung vào kinh doanh",
            "yeu_cau_van_ban": True,
            "yeu_cau_cong_chung": False,
            "yeu_cau_chung_thuc": False,
            "thoi_diem_lap": "trong_hon_nhan",
            "co_the_sua_doi": True,
        },
        # Đ46 — Thỏa thuận nhập tài sản riêng vào chung
        {
            "id": "thoa_thuan_nhap_tai_san_rieng",
            "ten": "Thỏa thuận nhập tài sản riêng vào tài sản chung",
            "yeu_cau_van_ban": False,
            "yeu_cau_cong_chung": False,
            "yeu_cau_chung_thuc": False,
            "thoi_diem_lap": "trong_hon_nhan",
            "co_the_sua_doi": True,
        },
        # Đ41 — Thỏa thuận chấm dứt hiệu lực chia
        {
            "id": "thoa_thuan_cham_dut_chia",
            "ten": "Thỏa thuận chấm dứt hiệu lực của việc chia tài sản chung",
            "yeu_cau_van_ban": True,
            "yeu_cau_cong_chung": False,
            "yeu_cau_chung_thuc": False,
            "thoi_diem_lap": "trong_hon_nhan",
            "co_the_sua_doi": True,
        },
        # Đ34 — Thỏa thuận ghi tên một bên trên GCN
        {
            "id": "thoa_thuan_ghi_ten_mot_ben_gcn",
            "ten": "Thỏa thuận ghi tên một bên trên Giấy chứng nhận tài sản chung",
            "yeu_cau_van_ban": False,
            "yeu_cau_cong_chung": False,
            "yeu_cau_chung_thuc": False,
            "thoi_diem_lap": "tuy_y",
            "co_the_sua_doi": True,
        },
        # Đ31 — Thỏa thuận định đoạt nhà ở duy nhất
        {
            "id": "thoa_thuan_dinh_doat_nha_o_duy_nhat",
            "ten": "Thỏa thuận xác lập, thực hiện, chấm dứt giao dịch nhà ở duy nhất",
            "yeu_cau_van_ban": False,
            "yeu_cau_cong_chung": False,
            "yeu_cau_chung_thuc": False,
            "thoi_diem_lap": "trong_hon_nhan",
            "co_the_sua_doi": True,
        },
    ],
    # -------------------------------------------------------------------------
    # Điều kiện / hoàn cảnh
    # -------------------------------------------------------------------------
    "DieuKien": [
        # Đ30
        {"id": "khong_du_tai_san_chung", "ten": "Không có/không đủ tài sản chung để đáp ứng nhu cầu thiết yếu"},
        # Đ31
        {"id": "tai_san_la_nha_o_duy_nhat", "ten": "Tài sản là nhà ở duy nhất của vợ chồng"},
        {"id": "nha_thuoc_so_huu_rieng", "ten": "Nhà thuộc sở hữu riêng của vợ hoặc chồng"},
        # Đ32
        {"id": "giao_dich_ngay_tinh", "ten": "Giao dịch với người thứ ba ngay tình"},
        # Đ33
        {"id": "khong_chung_minh_duoc_tai_san_rieng", "ten": "Không có căn cứ chứng minh tài sản đang tranh chấp là tài sản riêng"},
        # Đ34
        {"id": "tai_san_phai_dang_ky", "ten": "Tài sản thuộc loại phải đăng ký quyền sở hữu/sử dụng"},
        # Đ35
        {"id": "tai_san_la_bat_dong_san", "ten": "Tài sản định đoạt là bất động sản"},
        {"id": "tai_san_la_dong_san_dang_ky", "ten": "Tài sản định đoạt là động sản phải đăng ký"},
        {"id": "tai_san_la_nguon_thu_nhap_chu_yeu", "ten": "Tài sản đang là nguồn thu nhập chủ yếu của gia đình"},
        # Đ38
        {"id": "khong_thoa_thuan_duoc_chia", "ten": "Vợ chồng không thỏa thuận được về chia tài sản chung"},
        # Đ39
        {"id": "khong_xac_dinh_thoi_diem_van_ban", "ten": "Văn bản thỏa thuận không xác định thời điểm có hiệu lực"},
        {"id": "tai_san_yeu_cau_hinh_thuc_giao_dich", "ten": "Tài sản được chia yêu cầu hình thức giao dịch nhất định theo luật"},
        {"id": "chia_boi_toa_an", "ten": "Việc chia tài sản chung do Tòa án quyết định"},
        # Đ42 — vô hiệu chia
        {"id": "anh_huong_loi_ich_gia_dinh", "ten": "Việc chia ảnh hưởng nghiêm trọng đến lợi ích gia đình hoặc quyền/lợi ích con", "nhom_can_cu_vo_hieu": "anh_huong_loi_ich_gia_dinh"},
        {"id": "tron_nghia_vu_nuoi_duong_cap_duong", "ten": "Nhằm trốn nghĩa vụ nuôi dưỡng, cấp dưỡng", "nhom_can_cu_vo_hieu": "tron_nghia_vu"},
        {"id": "tron_nghia_vu_boi_thuong", "ten": "Nhằm trốn nghĩa vụ bồi thường thiệt hại", "nhom_can_cu_vo_hieu": "tron_nghia_vu"},
        {"id": "tron_nghia_vu_pha_san", "ten": "Nhằm trốn nghĩa vụ thanh toán khi bị Tòa án tuyên bố phá sản", "nhom_can_cu_vo_hieu": "tron_nghia_vu"},
        {"id": "tron_nghia_vu_tra_no", "ten": "Nhằm trốn nghĩa vụ trả nợ cho cá nhân, tổ chức", "nhom_can_cu_vo_hieu": "tron_nghia_vu"},
        {"id": "tron_nghia_vu_thue_tai_chinh_nha_nuoc", "ten": "Nhằm trốn nghĩa vụ nộp thuế hoặc nghĩa vụ tài chính khác với Nhà nước", "nhom_can_cu_vo_hieu": "tron_nghia_vu"},
        {"id": "tron_nghia_vu_khac", "ten": "Nhằm trốn nghĩa vụ khác về tài sản theo luật", "nhom_can_cu_vo_hieu": "tron_nghia_vu"},
        # Đ44
        {"id": "khong_tu_quan_ly_va_khong_uy_quyen", "ten": "Vợ/chồng không thể tự quản lý tài sản riêng và không ủy quyền"},
        {"id": "hoa_loi_la_nguon_song_duy_nhat", "ten": "Hoa lợi, lợi tức từ tài sản riêng là nguồn sống duy nhất của gia đình"},
        # Đ47
        {"id": "lap_truoc_ket_hon", "ten": "Thỏa thuận được lập trước khi kết hôn"},
        {"id": "co_cong_chung_hoac_chung_thuc", "ten": "Văn bản thỏa thuận có công chứng hoặc chứng thực"},
        # Đ48
        {"id": "dieu_kien_phan_chia_khi_cham_dut_che_do", "ten": "Điều kiện, thủ tục, nguyên tắc phân chia tài sản khi chấm dứt chế độ tài sản"},
        {"id": "lacuna_thoa_thuan", "ten": "Vấn đề chưa được thỏa thuận hoặc thỏa thuận không rõ ràng"},
        # Đ50 — vô hiệu thỏa thuận chế độ
        {"id": "vi_pham_dieu_kien_giao_dich_blds", "ten": "Vi phạm điều kiện có hiệu lực của giao dịch theo BLDS", "nhom_can_cu_vo_hieu_thoa_thuan": "dieu_kien_giao_dich"},
        {"id": "vi_pham_dieu_29_30_31_32", "ten": "Vi phạm một trong các quy định tại Điều 29, 30, 31, 32", "nhom_can_cu_vo_hieu_thoa_thuan": "vi_pham_d29_d32"},
        {"id": "vi_pham_quyen_thanh_vien_gia_dinh", "ten": "Vi phạm nghiêm trọng quyền cấp dưỡng, thừa kế, quyền lợi cha/mẹ/con/thành viên gia đình", "nhom_can_cu_vo_hieu_thoa_thuan": "quyen_thanh_vien_gia_dinh"},
    ],
    # -------------------------------------------------------------------------
    # Hậu quả pháp lý
    # -------------------------------------------------------------------------
    "HauQua": [
        # Đ29
        {"id": "boi_thuong_thiet_hai_xam_pham", "ten": "Phải bồi thường khi xâm phạm quyền/lợi ích hợp pháp"},
        # Đ31
        {"id": "bao_dam_cho_o", "ten": "Phải bảo đảm chỗ ở cho vợ chồng (khi nhà là tài sản riêng)"},
        # Đ32
        {"id": "bao_ve_nguoi_thu_ba", "ten": "Bảo vệ người thứ ba ngay tình trong giao dịch"},
        # Đ33 K3
        {"id": "coi_la_tai_san_chung_giadinh", "ten": "Tài sản tranh chấp được coi là tài sản chung (presumption)"},
        # Đ39 — hiệu lực chia
        {"id": "hieu_luc_chia_tai_san_thoi_diem_thoa_thuan", "ten": "Có hiệu lực từ thời điểm thỏa thuận trong văn bản"},
        {"id": "hieu_luc_chia_tai_san_ngay_lap_van_ban", "ten": "Có hiệu lực từ ngày lập văn bản (khi không xác định thời điểm)"},
        {"id": "hieu_luc_chia_tai_san_thoi_diem_tuan_thu_hinh_thuc", "ten": "Có hiệu lực từ thời điểm thỏa thuận tuân thủ hình thức giao dịch"},
        {"id": "hieu_luc_chia_tai_san_ngay_ban_an_co_hieu_luc", "ten": "Có hiệu lực kể từ ngày bản án/quyết định Tòa án có hiệu lực pháp luật"},
        {"id": "quyen_nghia_vu_voi_nguoi_thu_ba_truoc_chia_van_co_hieu_luc", "ten": "Quyền/nghĩa vụ với người thứ ba trước thời điểm chia có hiệu lực vẫn có giá trị"},
        # Đ40 — hậu quả chia
        {"id": "chuyen_thanh_tai_san_rieng_phan_chia", "ten": "Phần được chia trở thành tài sản riêng của mỗi bên"},
        {"id": "hoa_loi_loi_tuc_sau_chia_thanh_tai_san_rieng", "ten": "Hoa lợi, lợi tức phát sinh từ tài sản riêng sau chia là tài sản riêng"},
        {"id": "phan_con_lai_van_la_tai_san_chung", "ten": "Phần tài sản còn lại không chia vẫn là tài sản chung"},
        # Đ41 — chấm dứt
        {"id": "khoi_phuc_xac_dinh_theo_d33_d43", "ten": "Khôi phục xác định tài sản theo Điều 33 và Điều 43"},
        {"id": "phan_da_chia_van_la_tai_san_rieng", "ten": "Phần tài sản đã được chia vẫn thuộc sở hữu riêng"},
        # Đ42
        {"id": "vo_hieu_chia_tai_san_chung", "ten": "Việc chia tài sản chung trong hôn nhân bị vô hiệu"},
        # Đ46
        {"id": "chuyen_thanh_tai_san_chung", "ten": "Tài sản riêng được chuyển thành tài sản chung sau khi nhập"},
        {"id": "chuyen_nghia_vu_sang_tai_san_chung", "ten": "Nghĩa vụ liên quan tài sản đã nhập được thực hiện bằng tài sản chung"},
        # Đ48 — lacuna
        {"id": "lacuna_ap_dung_d29_d32_va_luat_dinh", "ten": "Khi thỏa thuận có lacuna, áp dụng Đ29-32 + quy định luật định"},
        # Đ50
        {"id": "vo_hieu_thoa_thuan", "ten": "Thỏa thuận chế độ tài sản bị Tòa án tuyên vô hiệu"},
    ],
    # -------------------------------------------------------------------------
    # Chủ thể pháp lý
    # -------------------------------------------------------------------------
    "ChuThe": [
        {"id": "vo", "ten": "Vợ", "loai": "ca_nhan"},
        {"id": "chong", "ten": "Chồng", "loai": "ca_nhan"},
        {"id": "vo_chong", "ten": "Vợ chồng", "loai": "ca_nhan"},
        {"id": "gia_dinh", "ten": "Gia đình", "loai": "gia_dinh"},
        {"id": "con_chua_thanh_nien", "ten": "Con chưa thành niên", "loai": "ca_nhan"},
        {"id": "con_thanh_nien_yeu_the", "ten": "Con đã thành niên mất năng lực/không có khả năng lao động/không có tài sản", "loai": "ca_nhan"},
        {"id": "nguoi_thu_ba_ngay_tinh", "ten": "Người thứ ba ngay tình", "loai": "ca_nhan"},
        {"id": "toa_an", "ten": "Tòa án", "loai": "co_quan"},
        {"id": "nha_nuoc", "ten": "Nhà nước", "loai": "co_quan"},
        {"id": "chu_no", "ten": "Chủ nợ (cá nhân, tổ chức)", "loai": "ca_nhan"},
    ],
    # -------------------------------------------------------------------------
    # Văn bản pháp lý / giấy tờ
    # -------------------------------------------------------------------------
    "VanBanPhapLy": [
        {"id": "gcn_quyen_so_huu", "ten": "Giấy chứng nhận quyền sở hữu tài sản"},
        {"id": "gcn_quyen_su_dung_dat", "ten": "Giấy chứng nhận quyền sử dụng đất (sổ đỏ)"},
        {"id": "van_ban_thoa_thuan", "ten": "Văn bản thỏa thuận của vợ chồng"},
        {"id": "ban_an_quyet_dinh_toa_an", "ten": "Bản án, quyết định của Tòa án"},
    ],
    # -------------------------------------------------------------------------
    # Trường hợp ngoại lệ
    # -------------------------------------------------------------------------
    "TruongHopNgoaiLe": [
        {"id": "ngoai_le_nha_so_huu_rieng_duoc_tu_giao_dich", "ten": "Ngoại lệ Đ31: Nhà thuộc sở hữu riêng — chủ sở hữu được tự giao dịch nhưng phải bảo đảm chỗ ở"},
        {"id": "ngoai_le_thoa_thuan_ghi_ten_mot_ben", "ten": "Ngoại lệ Đ34: Có thể thỏa thuận chỉ ghi tên một bên trên GCN"},
        {"id": "ngoai_le_hoa_loi_sau_chia_thanh_tai_san_chung_neu_thoa_thuan", "ten": "Ngoại lệ Đ40: Hoa lợi/lợi tức sau chia có thể vẫn là tài sản chung nếu thỏa thuận khác"},
        {"id": "ngoai_le_qsdđ_thua_ke_tang_cho_rieng", "ten": "Ngoại lệ Đ33: QSDĐ sau kết hôn không là tài sản chung nếu thừa kế/tặng cho riêng hoặc giao dịch bằng tài sản riêng"},
        {"id": "ngoai_le_dinh_doat_tai_san_rieng_la_nguon_song_duy_nhat", "ten": "Ngoại lệ Đ44 K4: Định đoạt tài sản riêng có hoa lợi/lợi tức là nguồn sống duy nhất phải có đồng ý của bên kia"},
        {"id": "ngoai_le_nghia_vu_bao_quan_tai_san_rieng_thanh_chung", "ten": "Ngoại lệ Đ45 K2: Nghĩa vụ bảo quản/duy trì/tu sửa tài sản riêng phục vụ tài sản chung → nghĩa vụ chung (Đ37 K4)"},
        {"id": "ngoai_le_qsdđ_thoa_thuan_khac_d33", "ten": "Ngoại lệ Đ33: QSDĐ có được sau kết hôn nhưng thông qua giao dịch bằng tài sản riêng"},
    ],
}


# =============================================================================
# 3. EDGES (semantic ↔ semantic).
#    Cấu trúc: (src_label, src_id, rel_type, dst_label, dst_id, props_dict?)
# =============================================================================
EDGES: list[tuple] = [
    # -------------------------------------------------------------------------
    # PHAN_LOAI_LA + LA_LOAI_CON_CUA — taxonomy LoaiTaiSan
    # -------------------------------------------------------------------------
    ("LoaiTaiSan", "thu_nhap_lao_dong", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_chung", {}),
    ("LoaiTaiSan", "thu_nhap_san_xuat_kinh_doanh", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_chung", {}),
    ("LoaiTaiSan", "hoa_loi_loi_tuc", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_chung", {}),
    ("LoaiTaiSan", "thu_nhap_hop_phap_khac", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_chung", {}),
    ("LoaiTaiSan", "tai_san_thua_ke_chung", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_chung", {}),
    ("LoaiTaiSan", "tai_san_tang_cho_chung", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_chung", {}),
    ("LoaiTaiSan", "tai_san_thoa_thuan_la_chung", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_chung", {}),
    ("LoaiTaiSan", "quyen_su_dung_dat", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_chung", {}),
    ("LoaiTaiSan", "quyen_su_dung_dat", "LA_LOAI_CON_CUA", "LoaiTaiSan", "bat_dong_san", {}),
    ("LoaiTaiSan", "tai_san_chung_phai_dang_ky", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_chung", {}),
    ("LoaiTaiSan", "tai_san_truoc_ket_hon", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_rieng", {}),
    ("LoaiTaiSan", "tai_san_thua_ke_rieng", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_rieng", {}),
    ("LoaiTaiSan", "tai_san_tang_cho_rieng", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_rieng", {}),
    ("LoaiTaiSan", "tai_san_phuc_vu_nhu_cau_thiet_yeu_ca_nhan", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_rieng", {}),
    ("LoaiTaiSan", "tai_san_hinh_thanh_tu_tai_san_rieng", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_rieng", {}),
    ("LoaiTaiSan", "tai_san_chia_rieng_trong_hon_nhan", "LA_LOAI_CON_CUA", "LoaiTaiSan", "tai_san_rieng", {}),
    ("LoaiTaiSan", "nha_o_duy_nhat", "LA_LOAI_CON_CUA", "LoaiTaiSan", "bat_dong_san", {}),
    # -------------------------------------------------------------------------
    # CO_NGUON_GOC — LoaiTaiSan → NguonGocTaiSan
    # -------------------------------------------------------------------------
    ("LoaiTaiSan", "thu_nhap_lao_dong", "CO_NGUON_GOC", "NguonGocTaiSan", "tao_lap_trong_hon_nhan", {}),
    ("LoaiTaiSan", "thu_nhap_san_xuat_kinh_doanh", "CO_NGUON_GOC", "NguonGocTaiSan", "tao_lap_trong_hon_nhan", {}),
    ("LoaiTaiSan", "hoa_loi_loi_tuc", "CO_NGUON_GOC", "NguonGocTaiSan", "phai_sinh_tu_tai_san_rieng", {}),
    ("LoaiTaiSan", "thu_nhap_hop_phap_khac", "CO_NGUON_GOC", "NguonGocTaiSan", "tao_lap_trong_hon_nhan", {}),
    ("LoaiTaiSan", "tai_san_thua_ke_chung", "CO_NGUON_GOC", "NguonGocTaiSan", "thua_ke_chung", {}),
    ("LoaiTaiSan", "tai_san_tang_cho_chung", "CO_NGUON_GOC", "NguonGocTaiSan", "tang_cho_chung", {}),
    ("LoaiTaiSan", "tai_san_thoa_thuan_la_chung", "CO_NGUON_GOC", "NguonGocTaiSan", "thoa_thuan_xac_lap", {}),
    ("LoaiTaiSan", "quyen_su_dung_dat", "CO_NGUON_GOC", "NguonGocTaiSan", "sau_ket_hon", {}),
    ("LoaiTaiSan", "tai_san_truoc_ket_hon", "CO_NGUON_GOC", "NguonGocTaiSan", "truoc_ket_hon", {}),
    ("LoaiTaiSan", "tai_san_thua_ke_rieng", "CO_NGUON_GOC", "NguonGocTaiSan", "thua_ke_rieng", {}),
    ("LoaiTaiSan", "tai_san_tang_cho_rieng", "CO_NGUON_GOC", "NguonGocTaiSan", "tang_cho_rieng", {}),
    ("LoaiTaiSan", "tai_san_chia_rieng_trong_hon_nhan", "CO_NGUON_GOC", "NguonGocTaiSan", "chia_tai_san_chung", {}),
    ("LoaiTaiSan", "tai_san_hinh_thanh_tu_tai_san_rieng", "CO_NGUON_GOC", "NguonGocTaiSan", "phai_sinh_tu_tai_san_rieng", {}),
    # -------------------------------------------------------------------------
    # THUOC_CHE_DO — LoaiTaiSan/ThoaThuan → ChePhapDoTaiSan
    # -------------------------------------------------------------------------
    ("LoaiTaiSan", "tai_san_chung", "THUOC_CHE_DO", "ChePhapDoTaiSan", "che_do_luat_dinh", {}),
    ("LoaiTaiSan", "tai_san_rieng", "THUOC_CHE_DO", "ChePhapDoTaiSan", "che_do_luat_dinh", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "THUOC_CHE_DO", "ChePhapDoTaiSan", "che_do_thoa_thuan", {}),
    # -------------------------------------------------------------------------
    # TAC_DONG_LEN — HanhVi → LoaiTaiSan
    # -------------------------------------------------------------------------
    ("HanhVi", "dinh_doat_tai_san_chung", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_chung", {}),
    ("HanhVi", "dinh_doat_tai_san_chung", "TAC_DONG_LEN", "LoaiTaiSan", "bat_dong_san", {}),
    ("HanhVi", "dinh_doat_tai_san_chung", "TAC_DONG_LEN", "LoaiTaiSan", "dong_san_phai_dang_ky", {}),
    ("HanhVi", "dinh_doat_tai_san_chung", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_tao_thu_nhap_chu_yeu", {}),
    ("HanhVi", "chiem_huu_su_dung_tai_san_chung", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_chung", {}),
    ("HanhVi", "ban_chuyen_nhuong_bds", "TAC_DONG_LEN", "LoaiTaiSan", "bat_dong_san", {}),
    ("HanhVi", "the_chap_cam_co_bds", "TAC_DONG_LEN", "LoaiTaiSan", "bat_dong_san", {}),
    ("HanhVi", "tang_cho_bds", "TAC_DONG_LEN", "LoaiTaiSan", "bat_dong_san", {}),
    ("HanhVi", "dua_tai_san_chung_vao_kinh_doanh", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_chung", {}),
    ("HanhVi", "chia_tai_san_chung_trong_hon_nhan", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_chung", {}),
    ("HanhVi", "dinh_doat_tai_san_rieng", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_rieng", {}),
    ("HanhVi", "ban_chuyen_nhuong_tai_san_rieng", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_rieng", {}),
    ("HanhVi", "chiem_huu_su_dung_tai_san_rieng", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_rieng", {}),
    ("HanhVi", "nhap_tai_san_rieng_vao_chung", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_rieng", {}),
    ("HanhVi", "dang_ky_quyen_so_huu", "TAC_DONG_LEN", "LoaiTaiSan", "tai_san_chung_phai_dang_ky", {}),
    ("HanhVi", "dang_ky_quyen_so_huu", "TAC_DONG_LEN", "LoaiTaiSan", "bat_dong_san", {}),
    ("HanhVi", "dang_ky_quyen_so_huu", "TAC_DONG_LEN", "LoaiTaiSan", "dong_san_phai_dang_ky", {}),
    ("HanhVi", "giao_dich_nha_o_duy_nhat", "TAC_DONG_LEN", "LoaiTaiSan", "nha_o_duy_nhat", {}),
    ("HanhVi", "giao_dich_nguoi_thu_ba_ngay_tinh", "TAC_DONG_LEN", "LoaiTaiSan", "tai_khoan_ngan_hang_chung_khoan", {}),
    ("HanhVi", "giao_dich_nguoi_thu_ba_ngay_tinh", "TAC_DONG_LEN", "LoaiTaiSan", "dong_san_khong_phai_dang_ky", {}),
    # -------------------------------------------------------------------------
    # YEU_CAU_THOA_THUAN — HanhVi → ThoaThuan
    # -------------------------------------------------------------------------
    ("HanhVi", "dinh_doat_tai_san_chung", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_dinh_doat_van_ban", {}),
    ("HanhVi", "ban_chuyen_nhuong_bds", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_dinh_doat_van_ban", {}),
    ("HanhVi", "the_chap_cam_co_bds", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_dinh_doat_van_ban", {}),
    ("HanhVi", "tang_cho_bds", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_dinh_doat_van_ban", {}),
    ("HanhVi", "dua_tai_san_chung_vao_kinh_doanh", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_kinh_doanh", {}),
    ("HanhVi", "chia_tai_san_chung_trong_hon_nhan", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_chia_tai_san_chung", {}),
    ("HanhVi", "cham_dut_hieu_luc_chia", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_cham_dut_chia", {}),
    ("HanhVi", "nhap_tai_san_rieng_vao_chung", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_nhap_tai_san_rieng", {}),
    ("HanhVi", "xac_lap_thoa_thuan_che_do", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_che_do_tai_san", {}),
    ("HanhVi", "sua_doi_bo_sung_thoa_thuan", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_che_do_tai_san", {}),
    ("HanhVi", "giao_dich_nha_o_duy_nhat", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_dinh_doat_nha_o_duy_nhat", {}),
    ("HanhVi", "dang_ky_quyen_so_huu", "YEU_CAU_THOA_THUAN", "ThoaThuan", "thoa_thuan_ghi_ten_mot_ben_gcn", {}),
    # -------------------------------------------------------------------------
    # PHAT_SINH_TU — NghiaVu → HanhVi / NguonGoc / ChuThe
    # -------------------------------------------------------------------------
    # Đ37 K1
    ("NghiaVu", "nghia_vu_chung_tu_giao_dich_thoa_thuan", "PHAT_SINH_TU", "HanhVi", "tao_lap_chiem_huu_su_dung_dinh_doat_tai_san_chung", {}),
    # Đ37 K2 + Đ30
    ("NghiaVu", "nghia_vu_chung_dap_ung_nhu_cau_thiet_yeu_gia_dinh", "PHAT_SINH_TU", "HanhVi", "dap_ung_nhu_cau_thiet_yeu_gia_dinh", {}),
    ("NghiaVu", "nghia_vu_dap_ung_nhu_cau_thiet_yeu_gia_dinh", "PHAT_SINH_TU", "HanhVi", "dap_ung_nhu_cau_thiet_yeu_gia_dinh", {}),
    # Đ37 K3
    ("NghiaVu", "nghia_vu_chung_tu_chiem_huu_dinh_doat_tai_san_chung", "PHAT_SINH_TU", "HanhVi", "chiem_huu_su_dung_tai_san_chung", {}),
    ("NghiaVu", "nghia_vu_chung_tu_chiem_huu_dinh_doat_tai_san_chung", "PHAT_SINH_TU", "HanhVi", "dinh_doat_tai_san_chung", {}),
    # Đ37 K4 (link với Đ44, Đ45)
    ("NghiaVu", "nghia_vu_chung_tu_dung_tai_san_rieng_phuc_vu_tai_san_chung", "PHAT_SINH_TU", "HanhVi", "chiem_huu_su_dung_tai_san_rieng", {}),
    # Đ37 K5
    ("NghiaVu", "nghia_vu_chung_boi_thuong_do_con", "PHAT_SINH_TU", "ChuThe", "con_chua_thanh_nien", {}),
    ("NghiaVu", "nghia_vu_chung_boi_thuong_do_con", "PHAT_SINH_TU", "ChuThe", "con_thanh_nien_yeu_the", {}),
    # Đ45 K1
    ("NghiaVu", "nghia_vu_rieng_truoc_ket_hon", "PHAT_SINH_TU", "NguonGocTaiSan", "truoc_ket_hon", {}),
    # Đ45 K2
    ("NghiaVu", "nghia_vu_rieng_chiem_huu_dinh_doat_tai_san_rieng", "PHAT_SINH_TU", "HanhVi", "dinh_doat_tai_san_rieng", {}),
    ("NghiaVu", "nghia_vu_rieng_chiem_huu_dinh_doat_tai_san_rieng", "PHAT_SINH_TU", "HanhVi", "chiem_huu_su_dung_tai_san_rieng", {}),
    # Đ45 K3
    ("NghiaVu", "nghia_vu_rieng_giao_dich_ca_nhan_khong_vi_gia_dinh", "PHAT_SINH_TU", "ChuThe", "vo", {}),
    ("NghiaVu", "nghia_vu_rieng_giao_dich_ca_nhan_khong_vi_gia_dinh", "PHAT_SINH_TU", "ChuThe", "chong", {}),
    # Đ27 (liên đới)
    ("NghiaVu", "nghia_vu_lien_doi_dap_ung_nhu_cau_gia_dinh", "PHAT_SINH_TU", "HanhVi", "dap_ung_nhu_cau_thiet_yeu_gia_dinh", {}),
    # Đ30 K2
    ("NghiaVu", "nghia_vu_dong_gop_tai_san_rieng_khi_thieu_chung", "PHAT_SINH_TU", "HanhVi", "dap_ung_nhu_cau_thiet_yeu_gia_dinh", {}),
    # Đ31
    ("NghiaVu", "nghia_vu_bao_dam_cho_o_cho_vo_chong", "PHAT_SINH_TU", "HanhVi", "giao_dich_nha_o_duy_nhat", {}),
    # -------------------------------------------------------------------------
    # THANH_TOAN_BANG — NghiaVu → LoaiTaiSan
    # -------------------------------------------------------------------------
    ("NghiaVu", "nghia_vu_chung_tu_giao_dich_thoa_thuan", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_chung", {}),
    ("NghiaVu", "nghia_vu_chung_dap_ung_nhu_cau_thiet_yeu_gia_dinh", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_chung", {}),
    ("NghiaVu", "nghia_vu_chung_tu_chiem_huu_dinh_doat_tai_san_chung", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_chung", {}),
    ("NghiaVu", "nghia_vu_chung_tu_dung_tai_san_rieng_phuc_vu_tai_san_chung", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_chung", {}),
    ("NghiaVu", "nghia_vu_chung_boi_thuong_do_con", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_chung", {}),
    ("NghiaVu", "nghia_vu_chung_khac_theo_luat", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_chung", {}),
    ("NghiaVu", "nghia_vu_lien_doi_dap_ung_nhu_cau_gia_dinh", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_chung", {}),
    ("NghiaVu", "nghia_vu_rieng_truoc_ket_hon", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_rieng", {}),
    ("NghiaVu", "nghia_vu_rieng_chiem_huu_dinh_doat_tai_san_rieng", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_rieng", {}),
    ("NghiaVu", "nghia_vu_rieng_giao_dich_ca_nhan_khong_vi_gia_dinh", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_rieng", {}),
    ("NghiaVu", "nghia_vu_rieng_vi_pham_phap_luat", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_rieng", {}),
    ("NghiaVu", "nghia_vu_dong_gop_tai_san_rieng_khi_thieu_chung", "THANH_TOAN_BANG", "LoaiTaiSan", "tai_san_rieng", {}),
    # -------------------------------------------------------------------------
    # AP_DUNG_KHI — HanhVi/HauQua/ThoaThuan → DieuKien
    # -------------------------------------------------------------------------
    ("HanhVi", "giao_dich_nha_o_duy_nhat", "AP_DUNG_KHI", "DieuKien", "tai_san_la_nha_o_duy_nhat", {}),
    ("HanhVi", "giao_dich_nguoi_thu_ba_ngay_tinh", "AP_DUNG_KHI", "DieuKien", "giao_dich_ngay_tinh", {}),
    ("HanhVi", "dang_ky_quyen_so_huu", "AP_DUNG_KHI", "DieuKien", "tai_san_phai_dang_ky", {}),
    ("HanhVi", "dinh_doat_tai_san_chung", "AP_DUNG_KHI", "DieuKien", "tai_san_la_bat_dong_san", {}),
    ("HanhVi", "dinh_doat_tai_san_chung", "AP_DUNG_KHI", "DieuKien", "tai_san_la_dong_san_dang_ky", {}),
    ("HanhVi", "dinh_doat_tai_san_chung", "AP_DUNG_KHI", "DieuKien", "tai_san_la_nguon_thu_nhap_chu_yeu", {}),
    ("HanhVi", "dinh_doat_tai_san_rieng", "AP_DUNG_KHI", "DieuKien", "hoa_loi_la_nguon_song_duy_nhat", {}),
    ("HanhVi", "khoi_kien_tai_toa_an", "AP_DUNG_KHI", "DieuKien", "khong_thoa_thuan_duoc_chia", {}),
    ("HanhVi", "dap_ung_nhu_cau_thiet_yeu_gia_dinh", "AP_DUNG_KHI", "DieuKien", "khong_du_tai_san_chung", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "AP_DUNG_KHI", "DieuKien", "lap_truoc_ket_hon", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "AP_DUNG_KHI", "DieuKien", "co_cong_chung_hoac_chung_thuc", {}),
    # -------------------------------------------------------------------------
    # DAN_TOI — HanhVi/DieuKien/ThoaThuan → HauQua
    # -------------------------------------------------------------------------
    ("HanhVi", "tao_lap_chiem_huu_su_dung_dinh_doat_tai_san_chung", "DAN_TOI", "HauQua", "boi_thuong_thiet_hai_xam_pham", {}),
    ("HanhVi", "giao_dich_nha_o_duy_nhat", "DAN_TOI", "HauQua", "bao_dam_cho_o", {}),
    ("HanhVi", "giao_dich_nguoi_thu_ba_ngay_tinh", "DAN_TOI", "HauQua", "bao_ve_nguoi_thu_ba", {}),
    ("DieuKien", "khong_chung_minh_duoc_tai_san_rieng", "DAN_TOI", "HauQua", "coi_la_tai_san_chung_giadinh", {}),
    # Đ39 — hiệu lực chia
    ("HanhVi", "chia_tai_san_chung_trong_hon_nhan", "DAN_TOI", "HauQua", "hieu_luc_chia_tai_san_thoi_diem_thoa_thuan", {}),
    ("DieuKien", "khong_xac_dinh_thoi_diem_van_ban", "DAN_TOI", "HauQua", "hieu_luc_chia_tai_san_ngay_lap_van_ban", {}),
    ("DieuKien", "tai_san_yeu_cau_hinh_thuc_giao_dich", "DAN_TOI", "HauQua", "hieu_luc_chia_tai_san_thoi_diem_tuan_thu_hinh_thuc", {}),
    ("DieuKien", "chia_boi_toa_an", "DAN_TOI", "HauQua", "hieu_luc_chia_tai_san_ngay_ban_an_co_hieu_luc", {}),
    # Đ40 — hậu quả chia
    ("HanhVi", "chia_tai_san_chung_trong_hon_nhan", "DAN_TOI", "HauQua", "chuyen_thanh_tai_san_rieng_phan_chia", {}),
    ("HanhVi", "chia_tai_san_chung_trong_hon_nhan", "DAN_TOI", "HauQua", "hoa_loi_loi_tuc_sau_chia_thanh_tai_san_rieng", {}),
    ("HanhVi", "chia_tai_san_chung_trong_hon_nhan", "DAN_TOI", "HauQua", "phan_con_lai_van_la_tai_san_chung", {}),
    # Đ41 — chấm dứt
    ("HanhVi", "cham_dut_hieu_luc_chia", "DAN_TOI", "HauQua", "khoi_phuc_xac_dinh_theo_d33_d43", {}),
    ("HanhVi", "cham_dut_hieu_luc_chia", "DAN_TOI", "HauQua", "phan_da_chia_van_la_tai_san_rieng", {}),
    # Đ42 — vô hiệu chia
    ("DieuKien", "anh_huong_loi_ich_gia_dinh", "DAN_TOI", "HauQua", "vo_hieu_chia_tai_san_chung", {}),
    ("DieuKien", "tron_nghia_vu_nuoi_duong_cap_duong", "DAN_TOI", "HauQua", "vo_hieu_chia_tai_san_chung", {}),
    ("DieuKien", "tron_nghia_vu_boi_thuong", "DAN_TOI", "HauQua", "vo_hieu_chia_tai_san_chung", {}),
    ("DieuKien", "tron_nghia_vu_pha_san", "DAN_TOI", "HauQua", "vo_hieu_chia_tai_san_chung", {}),
    ("DieuKien", "tron_nghia_vu_tra_no", "DAN_TOI", "HauQua", "vo_hieu_chia_tai_san_chung", {}),
    ("DieuKien", "tron_nghia_vu_thue_tai_chinh_nha_nuoc", "DAN_TOI", "HauQua", "vo_hieu_chia_tai_san_chung", {}),
    ("DieuKien", "tron_nghia_vu_khac", "DAN_TOI", "HauQua", "vo_hieu_chia_tai_san_chung", {}),
    # Đ46 — nhập tài sản riêng
    ("HanhVi", "nhap_tai_san_rieng_vao_chung", "DAN_TOI", "HauQua", "chuyen_thanh_tai_san_chung", {}),
    ("HanhVi", "nhap_tai_san_rieng_vao_chung", "DAN_TOI", "HauQua", "chuyen_nghia_vu_sang_tai_san_chung", {}),
    # Đ48 — lacuna
    ("DieuKien", "lacuna_thoa_thuan", "DAN_TOI", "HauQua", "lacuna_ap_dung_d29_d32_va_luat_dinh", {}),
    # Đ50 — vô hiệu thỏa thuận
    ("DieuKien", "vi_pham_dieu_kien_giao_dich_blds", "DAN_TOI", "HauQua", "vo_hieu_thoa_thuan", {}),
    ("DieuKien", "vi_pham_dieu_29_30_31_32", "DAN_TOI", "HauQua", "vo_hieu_thoa_thuan", {}),
    ("DieuKien", "vi_pham_quyen_thanh_vien_gia_dinh", "DAN_TOI", "HauQua", "vo_hieu_thoa_thuan", {}),
    # -------------------------------------------------------------------------
    # CO_NGOAI_LE — HanhVi/ThoaThuan/LoaiTaiSan → TruongHopNgoaiLe
    # -------------------------------------------------------------------------
    ("HanhVi", "giao_dich_nha_o_duy_nhat", "CO_NGOAI_LE", "TruongHopNgoaiLe", "ngoai_le_nha_so_huu_rieng_duoc_tu_giao_dich", {}),
    ("HanhVi", "dang_ky_quyen_so_huu", "CO_NGOAI_LE", "TruongHopNgoaiLe", "ngoai_le_thoa_thuan_ghi_ten_mot_ben", {}),
    ("HanhVi", "chia_tai_san_chung_trong_hon_nhan", "CO_NGOAI_LE", "TruongHopNgoaiLe", "ngoai_le_hoa_loi_sau_chia_thanh_tai_san_chung_neu_thoa_thuan", {}),
    ("LoaiTaiSan", "quyen_su_dung_dat", "CO_NGOAI_LE", "TruongHopNgoaiLe", "ngoai_le_qsdđ_thua_ke_tang_cho_rieng", {}),
    ("LoaiTaiSan", "quyen_su_dung_dat", "CO_NGOAI_LE", "TruongHopNgoaiLe", "ngoai_le_qsdđ_thoa_thuan_khac_d33", {}),
    ("HanhVi", "dinh_doat_tai_san_rieng", "CO_NGOAI_LE", "TruongHopNgoaiLe", "ngoai_le_dinh_doat_tai_san_rieng_la_nguon_song_duy_nhat", {}),
    ("NghiaVu", "nghia_vu_rieng_chiem_huu_dinh_doat_tai_san_rieng", "CO_NGOAI_LE", "TruongHopNgoaiLe", "ngoai_le_nghia_vu_bao_quan_tai_san_rieng_thanh_chung", {}),
    # -------------------------------------------------------------------------
    # THUC_HIEN_BOI — HanhVi/Quyen/NghiaVu → ChuThe
    # -------------------------------------------------------------------------
    ("Quyen", "quyen_lua_chon_che_do", "THUC_HIEN_BOI", "ChuThe", "vo_chong", {}),
    ("Quyen", "quyen_binh_dang_tai_san_chung", "THUC_HIEN_BOI", "ChuThe", "vo_chong", {}),
    ("Quyen", "quyen_chiem_huu_su_dung_tai_san_rieng", "THUC_HIEN_BOI", "ChuThe", "vo", {}),
    ("Quyen", "quyen_chiem_huu_su_dung_tai_san_rieng", "THUC_HIEN_BOI", "ChuThe", "chong", {}),
    ("Quyen", "quyen_dinh_doat_tai_san_rieng", "THUC_HIEN_BOI", "ChuThe", "vo", {}),
    ("Quyen", "quyen_dinh_doat_tai_san_rieng", "THUC_HIEN_BOI", "ChuThe", "chong", {}),
    ("Quyen", "quyen_yeu_cau_toa_an_chia", "THUC_HIEN_BOI", "ChuThe", "vo_chong", {}),
    ("Quyen", "quyen_sua_doi_thoa_thuan", "THUC_HIEN_BOI", "ChuThe", "vo_chong", {}),
    # -------------------------------------------------------------------------
    # LIEN_QUAN — quan hệ ngữ nghĩa lỏng (gom cụm)
    # -------------------------------------------------------------------------
    # Cụm chia tài sản chung trong hôn nhân (Đ38-42)
    ("HanhVi", "chia_tai_san_chung_trong_hon_nhan", "LIEN_QUAN", "HanhVi", "cham_dut_hieu_luc_chia", {}),
    ("HanhVi", "chia_tai_san_chung_trong_hon_nhan", "LIEN_QUAN", "HauQua", "vo_hieu_chia_tai_san_chung", {}),
    ("HanhVi", "chia_tai_san_chung_trong_hon_nhan", "LIEN_QUAN", "Quyen", "quyen_yeu_cau_toa_an_chia", {}),
    ("HanhVi", "chia_tai_san_chung_trong_hon_nhan", "LIEN_QUAN", "HanhVi", "khoi_kien_tai_toa_an", {}),
    # Cụm thỏa thuận chế độ tài sản (Đ47-50)
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "LIEN_QUAN", "HanhVi", "xac_lap_thoa_thuan_che_do", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "LIEN_QUAN", "Quyen", "quyen_sua_doi_thoa_thuan", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "LIEN_QUAN", "DieuKien", "lap_truoc_ket_hon", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "LIEN_QUAN", "DieuKien", "co_cong_chung_hoac_chung_thuc", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "LIEN_QUAN", "HanhVi", "sua_doi_bo_sung_thoa_thuan", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "LIEN_QUAN", "HauQua", "vo_hieu_thoa_thuan", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "LIEN_QUAN", "LoaiTaiSan", "tai_san_chung", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "LIEN_QUAN", "LoaiTaiSan", "tai_san_rieng", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "LIEN_QUAN", "NghiaVu", "nghia_vu_dap_ung_nhu_cau_thiet_yeu_gia_dinh", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "LIEN_QUAN", "DieuKien", "dieu_kien_phan_chia_khi_cham_dut_che_do", {}),
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "LIEN_QUAN", "DieuKien", "lacuna_thoa_thuan", {}),
    # Cụm nhà ở duy nhất + tài sản riêng (Đ31, 43, 44, 46)
    ("LoaiTaiSan", "nha_o_duy_nhat", "LIEN_QUAN", "HanhVi", "giao_dich_nha_o_duy_nhat", {}),
    ("LoaiTaiSan", "tai_san_rieng", "LIEN_QUAN", "HanhVi", "dinh_doat_tai_san_rieng", {}),
    ("LoaiTaiSan", "tai_san_rieng", "LIEN_QUAN", "HanhVi", "nhap_tai_san_rieng_vao_chung", {}),
    ("LoaiTaiSan", "tai_san_rieng", "LIEN_QUAN", "HanhVi", "chiem_huu_su_dung_tai_san_rieng", {}),
    ("LoaiTaiSan", "tai_san_rieng", "LIEN_QUAN", "HanhVi", "ban_chuyen_nhuong_tai_san_rieng", {}),
    ("Quyen", "quyen_quan_ly_thay", "LIEN_QUAN", "DieuKien", "khong_tu_quan_ly_va_khong_uy_quyen", {}),
]


# =============================================================================
# 4. CAN_CU_TAI — bridge tới legal layer.
#    Cấu trúc: (src_label, src_id, dst_legal_id)
#    dst_label sẽ được infer từ pattern id:
#        Luat_HNGD_2014_Dieu_X                 -> DieuLuat
#        Luat_HNGD_2014_Dieu_X_Khoan_Y         -> DieuKhoanLuat
#        Luat_HNGD_2014_Dieu_X_Khoan_Y_Diem_Z  -> DieuKhoanDiemLuat
# =============================================================================
CAN_CU_TAI: list[tuple[str, str, str]] = [
    # === Đ28 — Áp dụng chế độ tài sản ===
    ("ChePhapDoTaiSan", "che_do_luat_dinh", "Luat_HNGD_2014_Dieu_28_Khoan_1"),
    ("ChePhapDoTaiSan", "che_do_thoa_thuan", "Luat_HNGD_2014_Dieu_28_Khoan_1"),
    ("Quyen", "quyen_lua_chon_che_do", "Luat_HNGD_2014_Dieu_28_Khoan_1"),
    # === Đ29 — Nguyên tắc chung ===
    ("Quyen", "quyen_binh_dang_tai_san_chung", "Luat_HNGD_2014_Dieu_29_Khoan_1"),
    ("HanhVi", "tao_lap_chiem_huu_su_dung_dinh_doat_tai_san_chung", "Luat_HNGD_2014_Dieu_29_Khoan_1"),
    ("NghiaVu", "nghia_vu_dap_ung_nhu_cau_thiet_yeu_gia_dinh", "Luat_HNGD_2014_Dieu_29_Khoan_2"),
    ("HauQua", "boi_thuong_thiet_hai_xam_pham", "Luat_HNGD_2014_Dieu_29_Khoan_3"),
    # === Đ30 — Nhu cầu thiết yếu gia đình ===
    ("HanhVi", "dap_ung_nhu_cau_thiet_yeu_gia_dinh", "Luat_HNGD_2014_Dieu_30_Khoan_1"),
    ("DieuKien", "khong_du_tai_san_chung", "Luat_HNGD_2014_Dieu_30_Khoan_2"),
    ("NghiaVu", "nghia_vu_dong_gop_tai_san_rieng_khi_thieu_chung", "Luat_HNGD_2014_Dieu_30_Khoan_2"),
    # === Đ31 — Nhà ở duy nhất ===
    ("HanhVi", "giao_dich_nha_o_duy_nhat", "Luat_HNGD_2014_Dieu_31"),
    ("LoaiTaiSan", "nha_o_duy_nhat", "Luat_HNGD_2014_Dieu_31"),
    ("ThoaThuan", "thoa_thuan_dinh_doat_nha_o_duy_nhat", "Luat_HNGD_2014_Dieu_31"),
    ("TruongHopNgoaiLe", "ngoai_le_nha_so_huu_rieng_duoc_tu_giao_dich", "Luat_HNGD_2014_Dieu_31"),
    ("NghiaVu", "nghia_vu_bao_dam_cho_o_cho_vo_chong", "Luat_HNGD_2014_Dieu_31"),
    ("DieuKien", "tai_san_la_nha_o_duy_nhat", "Luat_HNGD_2014_Dieu_31"),
    ("DieuKien", "nha_thuoc_so_huu_rieng", "Luat_HNGD_2014_Dieu_31"),
    ("HauQua", "bao_dam_cho_o", "Luat_HNGD_2014_Dieu_31"),
    # === Đ32 — Người thứ ba ngay tình ===
    ("HanhVi", "giao_dich_nguoi_thu_ba_ngay_tinh", "Luat_HNGD_2014_Dieu_32_Khoan_1"),
    ("HanhVi", "giao_dich_nguoi_thu_ba_ngay_tinh", "Luat_HNGD_2014_Dieu_32_Khoan_2"),
    ("LoaiTaiSan", "tai_khoan_ngan_hang_chung_khoan", "Luat_HNGD_2014_Dieu_32_Khoan_1"),
    ("LoaiTaiSan", "dong_san_khong_phai_dang_ky", "Luat_HNGD_2014_Dieu_32_Khoan_2"),
    ("DieuKien", "giao_dich_ngay_tinh", "Luat_HNGD_2014_Dieu_32_Khoan_1"),
    ("DieuKien", "giao_dich_ngay_tinh", "Luat_HNGD_2014_Dieu_32_Khoan_2"),
    ("ChuThe", "nguoi_thu_ba_ngay_tinh", "Luat_HNGD_2014_Dieu_32"),
    ("HauQua", "bao_ve_nguoi_thu_ba", "Luat_HNGD_2014_Dieu_32"),
    # === Đ33 — Tài sản chung ===
    ("LoaiTaiSan", "tai_san_chung", "Luat_HNGD_2014_Dieu_33"),
    ("LoaiTaiSan", "tai_san_chung", "Luat_HNGD_2014_Dieu_33_Khoan_1"),
    ("LoaiTaiSan", "thu_nhap_lao_dong", "Luat_HNGD_2014_Dieu_33_Khoan_1"),
    ("LoaiTaiSan", "thu_nhap_san_xuat_kinh_doanh", "Luat_HNGD_2014_Dieu_33_Khoan_1"),
    ("LoaiTaiSan", "hoa_loi_loi_tuc", "Luat_HNGD_2014_Dieu_33_Khoan_1"),
    ("LoaiTaiSan", "thu_nhap_hop_phap_khac", "Luat_HNGD_2014_Dieu_33_Khoan_1"),
    ("LoaiTaiSan", "tai_san_thua_ke_chung", "Luat_HNGD_2014_Dieu_33_Khoan_1"),
    ("LoaiTaiSan", "tai_san_tang_cho_chung", "Luat_HNGD_2014_Dieu_33_Khoan_1"),
    ("LoaiTaiSan", "tai_san_thoa_thuan_la_chung", "Luat_HNGD_2014_Dieu_33_Khoan_1"),
    ("LoaiTaiSan", "quyen_su_dung_dat", "Luat_HNGD_2014_Dieu_33_Khoan_1"),
    ("TruongHopNgoaiLe", "ngoai_le_qsdđ_thua_ke_tang_cho_rieng", "Luat_HNGD_2014_Dieu_33_Khoan_1"),
    ("TruongHopNgoaiLe", "ngoai_le_qsdđ_thoa_thuan_khac_d33", "Luat_HNGD_2014_Dieu_33_Khoan_1"),
    ("HauQua", "coi_la_tai_san_chung_giadinh", "Luat_HNGD_2014_Dieu_33_Khoan_3"),
    ("DieuKien", "khong_chung_minh_duoc_tai_san_rieng", "Luat_HNGD_2014_Dieu_33_Khoan_3"),
    # === Đ34 — Đăng ký ===
    ("HanhVi", "dang_ky_quyen_so_huu", "Luat_HNGD_2014_Dieu_34_Khoan_1"),
    ("HanhVi", "dang_ky_quyen_so_huu", "Luat_HNGD_2014_Dieu_34_Khoan_2"),
    ("LoaiTaiSan", "tai_san_chung_phai_dang_ky", "Luat_HNGD_2014_Dieu_34_Khoan_1"),
    ("VanBanPhapLy", "gcn_quyen_so_huu", "Luat_HNGD_2014_Dieu_34_Khoan_1"),
    ("VanBanPhapLy", "gcn_quyen_su_dung_dat", "Luat_HNGD_2014_Dieu_34_Khoan_1"),
    ("ThoaThuan", "thoa_thuan_ghi_ten_mot_ben_gcn", "Luat_HNGD_2014_Dieu_34_Khoan_1"),
    ("DieuKien", "tai_san_phai_dang_ky", "Luat_HNGD_2014_Dieu_34_Khoan_1"),
    ("TruongHopNgoaiLe", "ngoai_le_thoa_thuan_ghi_ten_mot_ben", "Luat_HNGD_2014_Dieu_34_Khoan_1"),
    # === Đ35 — Định đoạt tài sản chung ===
    ("HanhVi", "chiem_huu_su_dung_tai_san_chung", "Luat_HNGD_2014_Dieu_35_Khoan_1"),
    ("HanhVi", "dinh_doat_tai_san_chung", "Luat_HNGD_2014_Dieu_35_Khoan_1"),
    ("HanhVi", "dinh_doat_tai_san_chung", "Luat_HNGD_2014_Dieu_35_Khoan_2"),
    ("HanhVi", "ban_chuyen_nhuong_bds", "Luat_HNGD_2014_Dieu_35_Khoan_2_Diem_a"),
    ("HanhVi", "the_chap_cam_co_bds", "Luat_HNGD_2014_Dieu_35_Khoan_2_Diem_a"),
    ("HanhVi", "tang_cho_bds", "Luat_HNGD_2014_Dieu_35_Khoan_2_Diem_a"),
    ("LoaiTaiSan", "bat_dong_san", "Luat_HNGD_2014_Dieu_35_Khoan_2_Diem_a"),
    ("LoaiTaiSan", "dong_san_phai_dang_ky", "Luat_HNGD_2014_Dieu_35_Khoan_2_Diem_b"),
    ("LoaiTaiSan", "tai_san_tao_thu_nhap_chu_yeu", "Luat_HNGD_2014_Dieu_35_Khoan_2_Diem_c"),
    ("ThoaThuan", "thoa_thuan_dinh_doat_van_ban", "Luat_HNGD_2014_Dieu_35_Khoan_2"),
    ("DieuKien", "tai_san_la_bat_dong_san", "Luat_HNGD_2014_Dieu_35_Khoan_2_Diem_a"),
    ("DieuKien", "tai_san_la_dong_san_dang_ky", "Luat_HNGD_2014_Dieu_35_Khoan_2_Diem_b"),
    ("DieuKien", "tai_san_la_nguon_thu_nhap_chu_yeu", "Luat_HNGD_2014_Dieu_35_Khoan_2_Diem_c"),
    # === Đ36 — Đưa tài sản chung vào kinh doanh ===
    ("HanhVi", "dua_tai_san_chung_vao_kinh_doanh", "Luat_HNGD_2014_Dieu_36"),
    ("ThoaThuan", "thoa_thuan_kinh_doanh", "Luat_HNGD_2014_Dieu_36"),
    # === Đ37 — Nghĩa vụ chung ===
    ("NghiaVu", "nghia_vu_chung_tu_giao_dich_thoa_thuan", "Luat_HNGD_2014_Dieu_37_Khoan_1"),
    ("NghiaVu", "nghia_vu_chung_dap_ung_nhu_cau_thiet_yeu_gia_dinh", "Luat_HNGD_2014_Dieu_37_Khoan_2"),
    ("NghiaVu", "nghia_vu_chung_tu_chiem_huu_dinh_doat_tai_san_chung", "Luat_HNGD_2014_Dieu_37_Khoan_3"),
    ("NghiaVu", "nghia_vu_chung_tu_dung_tai_san_rieng_phuc_vu_tai_san_chung", "Luat_HNGD_2014_Dieu_37_Khoan_4"),
    ("NghiaVu", "nghia_vu_chung_boi_thuong_do_con", "Luat_HNGD_2014_Dieu_37_Khoan_5"),
    ("NghiaVu", "nghia_vu_chung_khac_theo_luat", "Luat_HNGD_2014_Dieu_37_Khoan_6"),
    # === Đ38 — Chia tài sản chung trong hôn nhân ===
    ("HanhVi", "chia_tai_san_chung_trong_hon_nhan", "Luat_HNGD_2014_Dieu_38_Khoan_1"),
    ("ThoaThuan", "thoa_thuan_chia_tai_san_chung", "Luat_HNGD_2014_Dieu_38_Khoan_2"),
    ("Quyen", "quyen_yeu_cau_toa_an_chia", "Luat_HNGD_2014_Dieu_38_Khoan_1"),
    ("Quyen", "quyen_yeu_cau_toa_an_chia", "Luat_HNGD_2014_Dieu_38_Khoan_3"),
    ("HanhVi", "khoi_kien_tai_toa_an", "Luat_HNGD_2014_Dieu_38_Khoan_3"),
    ("DieuKien", "khong_thoa_thuan_duoc_chia", "Luat_HNGD_2014_Dieu_38_Khoan_1"),
    ("ChuThe", "toa_an", "Luat_HNGD_2014_Dieu_38_Khoan_3"),
    # === Đ39 — Thời điểm có hiệu lực chia ===
    ("HauQua", "hieu_luc_chia_tai_san_thoi_diem_thoa_thuan", "Luat_HNGD_2014_Dieu_39_Khoan_1"),
    ("HauQua", "hieu_luc_chia_tai_san_ngay_lap_van_ban", "Luat_HNGD_2014_Dieu_39_Khoan_1"),
    ("HauQua", "hieu_luc_chia_tai_san_thoi_diem_tuan_thu_hinh_thuc", "Luat_HNGD_2014_Dieu_39_Khoan_2"),
    ("HauQua", "hieu_luc_chia_tai_san_ngay_ban_an_co_hieu_luc", "Luat_HNGD_2014_Dieu_39_Khoan_3"),
    ("HauQua", "quyen_nghia_vu_voi_nguoi_thu_ba_truoc_chia_van_co_hieu_luc", "Luat_HNGD_2014_Dieu_39_Khoan_4"),
    ("DieuKien", "khong_xac_dinh_thoi_diem_van_ban", "Luat_HNGD_2014_Dieu_39_Khoan_1"),
    ("DieuKien", "tai_san_yeu_cau_hinh_thuc_giao_dich", "Luat_HNGD_2014_Dieu_39_Khoan_2"),
    ("DieuKien", "chia_boi_toa_an", "Luat_HNGD_2014_Dieu_39_Khoan_3"),
    # === Đ40 — Hậu quả chia ===
    ("HauQua", "chuyen_thanh_tai_san_rieng_phan_chia", "Luat_HNGD_2014_Dieu_40_Khoan_1"),
    ("HauQua", "hoa_loi_loi_tuc_sau_chia_thanh_tai_san_rieng", "Luat_HNGD_2014_Dieu_40_Khoan_1"),
    ("HauQua", "phan_con_lai_van_la_tai_san_chung", "Luat_HNGD_2014_Dieu_40_Khoan_1"),
    ("LoaiTaiSan", "tai_san_chia_rieng_trong_hon_nhan", "Luat_HNGD_2014_Dieu_40_Khoan_1"),
    ("TruongHopNgoaiLe", "ngoai_le_hoa_loi_sau_chia_thanh_tai_san_chung_neu_thoa_thuan", "Luat_HNGD_2014_Dieu_40_Khoan_1"),
    # === Đ41 — Chấm dứt hiệu lực chia ===
    ("HanhVi", "cham_dut_hieu_luc_chia", "Luat_HNGD_2014_Dieu_41_Khoan_1"),
    ("Quyen", "quyen_cham_dut_hieu_luc_chia", "Luat_HNGD_2014_Dieu_41_Khoan_1"),
    ("ThoaThuan", "thoa_thuan_cham_dut_chia", "Luat_HNGD_2014_Dieu_41_Khoan_1"),
    ("HauQua", "khoi_phuc_xac_dinh_theo_d33_d43", "Luat_HNGD_2014_Dieu_41_Khoan_2"),
    ("HauQua", "phan_da_chia_van_la_tai_san_rieng", "Luat_HNGD_2014_Dieu_41_Khoan_2"),
    # === Đ42 — Chia tài sản chung bị vô hiệu ===
    ("HauQua", "vo_hieu_chia_tai_san_chung", "Luat_HNGD_2014_Dieu_42"),
    ("DieuKien", "anh_huong_loi_ich_gia_dinh", "Luat_HNGD_2014_Dieu_42_Khoan_1"),
    ("DieuKien", "tron_nghia_vu_nuoi_duong_cap_duong", "Luat_HNGD_2014_Dieu_42_Khoan_2_Diem_a"),
    ("DieuKien", "tron_nghia_vu_boi_thuong", "Luat_HNGD_2014_Dieu_42_Khoan_2_Diem_b"),
    ("DieuKien", "tron_nghia_vu_pha_san", "Luat_HNGD_2014_Dieu_42_Khoan_2_Diem_c"),
    ("DieuKien", "tron_nghia_vu_tra_no", "Luat_HNGD_2014_Dieu_42_Khoan_2_Diem_d"),
    ("DieuKien", "tron_nghia_vu_thue_tai_chinh_nha_nuoc", "Luat_HNGD_2014_Dieu_42_Khoan_2_Diem_đ"),
    ("DieuKien", "tron_nghia_vu_khac", "Luat_HNGD_2014_Dieu_42_Khoan_2_Diem_e"),
    ("ChuThe", "con_chua_thanh_nien", "Luat_HNGD_2014_Dieu_42_Khoan_1"),
    ("ChuThe", "con_thanh_nien_yeu_the", "Luat_HNGD_2014_Dieu_42_Khoan_1"),
    # === Đ43 — Tài sản riêng ===
    ("LoaiTaiSan", "tai_san_rieng", "Luat_HNGD_2014_Dieu_43"),
    ("LoaiTaiSan", "tai_san_rieng", "Luat_HNGD_2014_Dieu_43_Khoan_1"),
    ("LoaiTaiSan", "tai_san_truoc_ket_hon", "Luat_HNGD_2014_Dieu_43_Khoan_1"),
    ("LoaiTaiSan", "tai_san_thua_ke_rieng", "Luat_HNGD_2014_Dieu_43_Khoan_1"),
    ("LoaiTaiSan", "tai_san_tang_cho_rieng", "Luat_HNGD_2014_Dieu_43_Khoan_1"),
    ("LoaiTaiSan", "tai_san_phuc_vu_nhu_cau_thiet_yeu_ca_nhan", "Luat_HNGD_2014_Dieu_43_Khoan_1"),
    ("LoaiTaiSan", "tai_san_hinh_thanh_tu_tai_san_rieng", "Luat_HNGD_2014_Dieu_43_Khoan_2"),
    # === Đ44 — Chiếm hữu, sử dụng, định đoạt tài sản riêng ===
    ("Quyen", "quyen_chiem_huu_su_dung_tai_san_rieng", "Luat_HNGD_2014_Dieu_44_Khoan_1"),
    ("Quyen", "quyen_dinh_doat_tai_san_rieng", "Luat_HNGD_2014_Dieu_44_Khoan_1"),
    ("Quyen", "quyen_nhap_hoac_khong_nhap_tai_san_rieng", "Luat_HNGD_2014_Dieu_44_Khoan_1"),
    ("Quyen", "quyen_quan_ly_thay", "Luat_HNGD_2014_Dieu_44_Khoan_2"),
    ("HanhVi", "dinh_doat_tai_san_rieng", "Luat_HNGD_2014_Dieu_44_Khoan_1"),
    ("HanhVi", "dinh_doat_tai_san_rieng", "Luat_HNGD_2014_Dieu_44_Khoan_4"),
    ("HanhVi", "chiem_huu_su_dung_tai_san_rieng", "Luat_HNGD_2014_Dieu_44_Khoan_1"),
    ("HanhVi", "ban_chuyen_nhuong_tai_san_rieng", "Luat_HNGD_2014_Dieu_44_Khoan_1"),
    ("DieuKien", "khong_tu_quan_ly_va_khong_uy_quyen", "Luat_HNGD_2014_Dieu_44_Khoan_2"),
    ("DieuKien", "hoa_loi_la_nguon_song_duy_nhat", "Luat_HNGD_2014_Dieu_44_Khoan_4"),
    ("TruongHopNgoaiLe", "ngoai_le_dinh_doat_tai_san_rieng_la_nguon_song_duy_nhat", "Luat_HNGD_2014_Dieu_44_Khoan_4"),
    # === Đ45 — Nghĩa vụ riêng ===
    ("NghiaVu", "nghia_vu_rieng_truoc_ket_hon", "Luat_HNGD_2014_Dieu_45_Khoan_1"),
    ("NghiaVu", "nghia_vu_rieng_chiem_huu_dinh_doat_tai_san_rieng", "Luat_HNGD_2014_Dieu_45_Khoan_2"),
    ("NghiaVu", "nghia_vu_rieng_giao_dich_ca_nhan_khong_vi_gia_dinh", "Luat_HNGD_2014_Dieu_45_Khoan_3"),
    ("NghiaVu", "nghia_vu_rieng_vi_pham_phap_luat", "Luat_HNGD_2014_Dieu_45_Khoan_4"),
    ("TruongHopNgoaiLe", "ngoai_le_nghia_vu_bao_quan_tai_san_rieng_thanh_chung", "Luat_HNGD_2014_Dieu_45_Khoan_2"),
    # === Đ46 — Nhập tài sản riêng vào tài sản chung ===
    ("HanhVi", "nhap_tai_san_rieng_vao_chung", "Luat_HNGD_2014_Dieu_46_Khoan_1"),
    ("ThoaThuan", "thoa_thuan_nhap_tai_san_rieng", "Luat_HNGD_2014_Dieu_46_Khoan_1"),
    ("ThoaThuan", "thoa_thuan_nhap_tai_san_rieng", "Luat_HNGD_2014_Dieu_46_Khoan_2"),
    ("HauQua", "chuyen_thanh_tai_san_chung", "Luat_HNGD_2014_Dieu_46_Khoan_1"),
    ("HauQua", "chuyen_nghia_vu_sang_tai_san_chung", "Luat_HNGD_2014_Dieu_46_Khoan_3"),
    # === Đ47 — Thỏa thuận xác lập chế độ tài sản ===
    ("ThoaThuan", "thoa_thuan_che_do_tai_san", "Luat_HNGD_2014_Dieu_47"),
    ("HanhVi", "xac_lap_thoa_thuan_che_do", "Luat_HNGD_2014_Dieu_47"),
    ("ChePhapDoTaiSan", "che_do_thoa_thuan", "Luat_HNGD_2014_Dieu_47"),
    ("DieuKien", "lap_truoc_ket_hon", "Luat_HNGD_2014_Dieu_47"),
    ("DieuKien", "co_cong_chung_hoac_chung_thuc", "Luat_HNGD_2014_Dieu_47"),
    # === Đ48 — Nội dung thỏa thuận ===
    ("DieuKien", "dieu_kien_phan_chia_khi_cham_dut_che_do", "Luat_HNGD_2014_Dieu_48_Khoan_1_Diem_c"),
    ("DieuKien", "lacuna_thoa_thuan", "Luat_HNGD_2014_Dieu_48_Khoan_2"),
    ("HauQua", "lacuna_ap_dung_d29_d32_va_luat_dinh", "Luat_HNGD_2014_Dieu_48_Khoan_2"),
    # Liên kết các nội dung của thỏa thuận về Đ48 K1 a/b/c
    ("LoaiTaiSan", "tai_san_chung", "Luat_HNGD_2014_Dieu_48_Khoan_1_Diem_a"),
    ("LoaiTaiSan", "tai_san_rieng", "Luat_HNGD_2014_Dieu_48_Khoan_1_Diem_a"),
    ("Quyen", "quyen_dinh_doat_tai_san_rieng", "Luat_HNGD_2014_Dieu_48_Khoan_1_Diem_b"),
    ("NghiaVu", "nghia_vu_dap_ung_nhu_cau_thiet_yeu_gia_dinh", "Luat_HNGD_2014_Dieu_48_Khoan_1_Diem_b"),
    # === Đ49 — Sửa đổi thỏa thuận ===
    ("HanhVi", "sua_doi_bo_sung_thoa_thuan", "Luat_HNGD_2014_Dieu_49_Khoan_1"),
    ("Quyen", "quyen_sua_doi_thoa_thuan", "Luat_HNGD_2014_Dieu_49_Khoan_1"),
    # === Đ50 — Vô hiệu thỏa thuận chế độ tài sản ===
    ("HauQua", "vo_hieu_thoa_thuan", "Luat_HNGD_2014_Dieu_50_Khoan_1"),
    ("DieuKien", "vi_pham_dieu_kien_giao_dich_blds", "Luat_HNGD_2014_Dieu_50_Khoan_1_Diem_a"),
    ("DieuKien", "vi_pham_dieu_29_30_31_32", "Luat_HNGD_2014_Dieu_50_Khoan_1_Diem_b"),
    ("DieuKien", "vi_pham_quyen_thanh_vien_gia_dinh", "Luat_HNGD_2014_Dieu_50_Khoan_1_Diem_c"),
    ("ChuThe", "toa_an", "Luat_HNGD_2014_Dieu_50_Khoan_1"),
]


# =============================================================================
# 5. AP_DUNG_CHO_CHE_DO — đánh dấu Đ29-32 áp dụng cho mọi chế độ
#    Cấu trúc: (dieu_id, che_do_value)
#    che_do_value: 'tat_ca' / 'luat_dinh' / 'thoa_thuan'
# =============================================================================
AP_DUNG_CHO_CHE_DO_EDGES: list[tuple[str, str]] = [
    # Đ29-32 áp dụng cho mọi chế độ (tat_ca)
    ("Luat_HNGD_2014_Dieu_29", "tat_ca"),
    ("Luat_HNGD_2014_Dieu_29_Khoan_1", "tat_ca"),
    ("Luat_HNGD_2014_Dieu_29_Khoan_2", "tat_ca"),
    ("Luat_HNGD_2014_Dieu_29_Khoan_3", "tat_ca"),
    ("Luat_HNGD_2014_Dieu_30", "tat_ca"),
    ("Luat_HNGD_2014_Dieu_30_Khoan_1", "tat_ca"),
    ("Luat_HNGD_2014_Dieu_30_Khoan_2", "tat_ca"),
    ("Luat_HNGD_2014_Dieu_31", "tat_ca"),
    ("Luat_HNGD_2014_Dieu_32", "tat_ca"),
    ("Luat_HNGD_2014_Dieu_32_Khoan_1", "tat_ca"),
    ("Luat_HNGD_2014_Dieu_32_Khoan_2", "tat_ca"),
]


# =============================================================================
# 6. Helpers
# =============================================================================
def infer_legal_label(legal_id: str) -> str:
    if "_Diem_" in legal_id:
        return "DieuKhoanDiemLuat"
    if "_Khoan_" in legal_id:
        return "DieuKhoanLuat"
    return "DieuLuat"


def chunk_summary() -> dict[str, int]:
    return {
        "nodes_total": sum(len(v) for v in NODES.values()),
        "edges_total": len(EDGES),
        "can_cu_tai_total": len(CAN_CU_TAI),
        "ap_dung_che_do_total": len(AP_DUNG_CHO_CHE_DO_EDGES),
    }


# =============================================================================
# 7. Build functions
# =============================================================================
def create_indexes(session) -> None:
    for label in SEMANTIC_LABELS:
        session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.id)")
    session.run("CREATE INDEX IF NOT EXISTS FOR (n:LoaiTaiSan) ON (n.tinh_chat)")
    session.run("CREATE INDEX IF NOT EXISTS FOR (n:NghiaVu) ON (n.loai_nghia_vu)")
    session.run("CREATE INDEX IF NOT EXISTS FOR (n:HanhVi) ON (n.loai)")
    session.run("CREATE INDEX IF NOT EXISTS FOR (n:DieuKien) ON (n.nhom_can_cu_vo_hieu)")


def reset_semantic_layer(session) -> None:
    print(f"[reset] Xoá toàn bộ node ngữ nghĩa thuộc {SEMANTIC_LABELS}...")
    query = (
        "MATCH (n) WHERE any(l IN labels(n) WHERE l IN $labels) "
        "DETACH DELETE n"
    )
    session.run(query, labels=SEMANTIC_LABELS)


def merge_nodes(session) -> int:
    total = 0
    for label, items in NODES.items():
        if not items:
            continue
        query = (
            f"UNWIND $rows AS row "
            f"MERGE (n:{label} {{id: row.id}}) "
            f"SET n += row "
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
            f"MATCH (s:{src_label} {{id: row.src_id}}) "
            f"MATCH (d:{dst_label} {{id: row.dst_id}}) "
            f"MERGE (s)-[r:{rel}]->(d) "
            f"SET r += row.props"
        )
        result = session.run(query, rows=rows).consume()
        total += result.counters.relationships_created
    return total


def merge_can_cu_tai(session) -> tuple[int, int]:
    """Tạo CAN_CU_TAI edges và báo lỗi nếu legal node không tồn tại."""
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
            f"MATCH (s:{src_label} {{id: row.src_id}}) "
            f"OPTIONAL MATCH (d:{legal_label} {{id: row.dst_id}}) "
            f"WITH s, d, row "
            f"WHERE d IS NOT NULL "
            f"MERGE (s)-[r:CAN_CU_TAI]->(d) "
            f"RETURN count(r) AS created"
        )
        result = session.run(query, rows=rows)
        record = result.single()
        if record:
            total_created += record["created"]
        # Kiểm tra missing
        missing_query = (
            f"UNWIND $rows AS row "
            f"MATCH (s:{src_label} {{id: row.src_id}}) "
            f"OPTIONAL MATCH (d:{legal_label} {{id: row.dst_id}}) "
            f"WITH row, d WHERE d IS NULL "
            f"RETURN collect(row.dst_id) AS missing"
        )
        missing_record = session.run(missing_query, rows=rows).single()
        if missing_record and missing_record["missing"]:
            print(f"[WARN] CAN_CU_TAI: legal node không tồn tại cho {src_label} → {legal_label}: {missing_record['missing']}")
            total_missing += len(missing_record["missing"])
    return total_created, total_missing


def merge_ap_dung_cho_che_do(session) -> int:
    """Tạo AP_DUNG_CHO_CHE_DO từ DieuLuat/DieuKhoanLuat → ChePhapDoTaiSan."""
    grouped: dict[str, list[dict]] = {}
    for legal_id, che_do_value in AP_DUNG_CHO_CHE_DO_EDGES:
        legal_label = infer_legal_label(legal_id)
        grouped.setdefault(legal_label, []).append(
            {"legal_id": legal_id, "che_do_value": che_do_value}
        )
    total = 0
    for legal_label, rows in grouped.items():
        # Đối với 'tat_ca': nối tới cả 2 chế độ.
        query = (
            f"UNWIND $rows AS row "
            f"MATCH (l:{legal_label} {{id: row.legal_id}}) "
            f"MATCH (c:ChePhapDoTaiSan) "
            f"WHERE row.che_do_value = 'tat_ca' "
            f"   OR (row.che_do_value = 'luat_dinh' AND c.id = 'che_do_luat_dinh') "
            f"   OR (row.che_do_value = 'thoa_thuan' AND c.id = 'che_do_thoa_thuan') "
            f"MERGE (l)-[r:AP_DUNG_CHO_CHE_DO]->(c) "
            f"SET r.che_do = row.che_do_value "
            f"RETURN count(r) AS created"
        )
        record = session.run(query, rows=rows).single()
        if record:
            total += record["created"]
    return total


# =============================================================================
# 8. Main
# =============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Xoá semantic layer trước khi build (không đụng layer luật).")
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

        print("[step 1/5] Tạo indexes...")
        create_indexes(session)

        print("[step 2/5] MERGE nodes...")
        nodes_created = merge_nodes(session)
        print(f"  -> Đã tạo {nodes_created} node mới (số còn lại đã tồn tại).")

        print("[step 3/5] MERGE semantic edges...")
        edges_created = merge_edges(session)
        print(f"  -> Đã tạo {edges_created} edge ngữ nghĩa mới.")

        print("[step 4/5] MERGE CAN_CU_TAI tới legal layer...")
        cct_created, cct_missing = merge_can_cu_tai(session)
        print(f"  -> Đã tạo {cct_created} CAN_CU_TAI mới; {cct_missing} legal node thiếu (xem WARN ở trên).")

        print("[step 5/5] MERGE AP_DUNG_CHO_CHE_DO (Đ29-32)...")
        adcd_created = merge_ap_dung_cho_che_do(session)
        print(f"  -> Đã tạo {adcd_created} AP_DUNG_CHO_CHE_DO mới.")

    print("[done] Build KG semantic layer cho 'Chế độ tài sản của vợ chồng' hoàn tất.")


if __name__ == "__main__":
    main()
