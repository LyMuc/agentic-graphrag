"""Build KG ngữ nghĩa cho topic 'Quyền, nghĩa vụ vợ chồng' (quyen_nghia_vu_vo_chong).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_quyen_nghia_vu_vo_chong.py           # MERGE idempotent
    python scripts/build_kg_quyen_nghia_vu_vo_chong.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_quyen_nghia_vu_vo_chong.py --dry-run # chỉ in summary

Schema: docs/kg_quyen_nghia_vu_vo_chong_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "quyen_nghia_vu_vo_chong"
TOPIC_LABEL = "QuyenNghiaVuVoChong"

SEMANTIC_LABELS = [
    "ChuThe",
    "QuyDinh",
    "Quyen",
    "NghiaVu",
    "HanhVi",
    "DieuKien",
    "HauQua",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

_HNGD_17_23 = [
    f"Luat_HNGD_2014_Dieu_{i}" for i in range(17, 24)
]

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("vo_chong", "Vợ và chồng trong quan hệ hôn nhân", "ChuThe", _HNGD_17_23),
    ("vo", "Người vợ trong quan hệ hôn nhân", "ChuThe", _HNGD_17_23),
    ("chong", "Người chồng trong quan hệ hôn nhân", "ChuThe", _HNGD_17_23),
    (
        "gia_dinh_chong",
        "Thành viên gia đình bên chồng có hành vi can thiệp vào quyền nhân thân của vợ",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_18"],
    ),
    (
        "binh_dang_quyen_nghia_vu_giua_vo_chong",
        "Vợ chồng bình đẳng, có quyền và nghĩa vụ ngang nhau về mọi mặt trong gia đình và khi thực hiện quyền, nghĩa vụ công dân",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_17"],
    ),
    (
        "quyen_nghia_vu_nhan_than_duoc_ton_trong_bao_ve",
        "Quyền và nghĩa vụ về nhân thân của vợ chồng được tôn trọng và bảo vệ",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_18"],
    ),
    (
        "tinh_nghia_vo_chong",
        "Nhóm nghĩa vụ về tình nghĩa và sống chung của vợ chồng",
        "QuyDinh",
        [
            "Luat_HNGD_2014_Dieu_19",
            "Luat_HNGD_2014_Dieu_19_Khoan_1",
            "Luat_HNGD_2014_Dieu_19_Khoan_2",
        ],
    ),
    (
        "lua_chon_noi_cu_tru_do_vo_chong_thoa_thuan",
        "Việc lựa chọn nơi cư trú do vợ chồng thỏa thuận, không do riêng một bên quyết định",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_20"],
    ),
    (
        "noi_cu_tru_vo_chong_la_noi_thuong_xuyen_chung_song",
        "Nơi cư trú của vợ chồng là nơi hai bên thường xuyên chung sống",
        "QuyDinh",
        ["Luat_CuTru_2020_Dieu_14_Khoan_1"],
    ),
    (
        "vo_chong_co_the_co_noi_cu_tru_khac_nhau",
        "Vợ chồng có thể có nơi cư trú khác nhau theo thỏa thuận hoặc pháp luật liên quan",
        "QuyDinh",
        ["Luat_CuTru_2020_Dieu_14_Khoan_2"],
    ),
    (
        "khong_deo_nhan_cuoi_khong_tu_dong_vi_pham_tinh_nghia_vo_chong",
        "Không đeo nhẫn cưới không phải nghĩa vụ được liệt kê tại Điều 19 và không tự động chứng minh vi phạm tình nghĩa vợ chồng",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_19_Khoan_1"],
    ),
    (
        "khong_bat_buoc_vo_chuyen_khau_ve_nha_chong",
        "Sau kết hôn, pháp luật trong phạm vi này không giao riêng cho chồng quyền bắt buộc vợ chuyển hộ khẩu về nhà chồng",
        "QuyDinh",
        [
            "Luat_HNGD_2014_Dieu_19_Khoan_2",
            "Luat_HNGD_2014_Dieu_20",
            "Luat_CuTru_2020_Dieu_14_Khoan_2",
        ],
    ),
    (
        "khong_bat_buoc_vo_o_chung_gia_dinh_chong",
        "Nghĩa vụ sống chung không đồng nghĩa vợ bắt buộc phải ở chung với gia đình chồng; nơi cư trú do vợ chồng thỏa thuận",
        "QuyDinh",
        [
            "Luat_HNGD_2014_Dieu_19_Khoan_2",
            "Luat_HNGD_2014_Dieu_20",
            "Luat_CuTru_2020_Dieu_14_Khoan_2",
        ],
    ),
    (
        "quyen_nghia_vu_ngang_nhau_moi_mat_trong_gia_dinh",
        "Vợ và chồng có quyền, nghĩa vụ ngang nhau về mọi mặt trong gia đình",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_17"],
    ),
    (
        "quyen_nhan_than_cua_vo_chong",
        "Quyền nhân thân của mỗi bên trong quan hệ vợ chồng",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_18"],
    ),
    (
        "quyen_thoa_thuan_noi_cu_tru",
        "Vợ chồng cùng thỏa thuận lựa chọn nơi cư trú",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_20", "Luat_CuTru_2020_Dieu_14_Khoan_2"],
    ),
    (
        "quyen_tu_do_tin_nguong_ton_giao",
        "Mỗi bên có quyền tự do tín ngưỡng, tôn giáo và được bên kia tôn trọng",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_22"],
    ),
    (
        "quyen_chon_nghe_nghiep",
        "Mỗi bên có quyền chọn nghề nghiệp và được bên kia tạo điều kiện, giúp đỡ",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_23"],
    ),
    (
        "quyen_hoc_tap_nang_cao_trinh_do",
        "Mỗi bên có quyền học tập, nâng cao trình độ văn hóa, chuyên môn, nghiệp vụ",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_23"],
    ),
    (
        "quyen_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "Mỗi bên có quyền tham gia hoạt động chính trị, kinh tế, văn hóa, xã hội",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_23"],
    ),
    ("nghia_vu_thuong_yeu", "Vợ chồng có nghĩa vụ thương yêu nhau", "NghiaVu", ["Luat_HNGD_2014_Dieu_19_Khoan_1"]),
    ("nghia_vu_chung_thuy", "Vợ chồng có nghĩa vụ chung thủy với nhau", "NghiaVu", ["Luat_HNGD_2014_Dieu_19_Khoan_1"]),
    ("nghia_vu_ton_trong_lan_nhau", "Vợ chồng có nghĩa vụ tôn trọng nhau", "NghiaVu", ["Luat_HNGD_2014_Dieu_19_Khoan_1"]),
    (
        "nghia_vu_quan_tam_cham_soc_giup_do",
        "Vợ chồng có nghĩa vụ quan tâm, chăm sóc, giúp đỡ nhau",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_19_Khoan_1"],
    ),
    (
        "nghia_vu_chia_se_thuc_hien_cong_viec_gia_dinh",
        "Vợ chồng cùng nhau chia sẻ và thực hiện các công việc trong gia đình",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_19_Khoan_1"],
    ),
    (
        "nghia_vu_song_chung",
        "Vợ chồng có nghĩa vụ sống chung, trừ các trường hợp luật định",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_19_Khoan_2"],
    ),
    (
        "nghia_vu_ton_trong_giu_gin_bao_ve_danh_du_nhan_pham_uy_tin",
        "Vợ chồng có nghĩa vụ tôn trọng, giữ gìn và bảo vệ danh dự, nhân phẩm, uy tín cho nhau",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_21"],
    ),
    (
        "nghia_vu_ton_trong_tu_do_tin_nguong_ton_giao",
        "Vợ chồng có nghĩa vụ tôn trọng quyền tự do tín ngưỡng, tôn giáo của nhau",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_22"],
    ),
    (
        "nghia_vu_tao_dieu_kien_giup_do_chon_nghe_nghiep",
        "Vợ chồng có nghĩa vụ tạo điều kiện, giúp đỡ nhau chọn nghề nghiệp",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_23"],
    ),
    (
        "nghia_vu_tao_dieu_kien_giup_do_hoc_tap_nang_cao_trinh_do",
        "Vợ chồng có nghĩa vụ tạo điều kiện, giúp đỡ nhau học tập và nâng cao trình độ",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_23"],
    ),
    (
        "nghia_vu_tao_dieu_kien_giup_do_tham_gia_hoat_dong_xa_hoi",
        "Vợ chồng có nghĩa vụ tạo điều kiện, giúp đỡ nhau tham gia hoạt động chính trị, kinh tế, văn hóa, xã hội",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_23"],
    ),
    (
        "thoa_thuan_khong_song_chung",
        "Vợ chồng có thỏa thuận khác về việc sống chung",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_19_Khoan_2"],
    ),
    (
        "yeu_cau_nghe_nghiep_cong_tac",
        "Không sống chung do yêu cầu nghề nghiệp hoặc công tác",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_19_Khoan_2"],
    ),
    ("yeu_cau_hoc_tap", "Không sống chung do yêu cầu học tập", "DieuKien", ["Luat_HNGD_2014_Dieu_19_Khoan_2"]),
    (
        "tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "Không sống chung do tham gia hoạt động chính trị, kinh tế, văn hóa, xã hội",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_19_Khoan_2"],
    ),
    (
        "ly_do_chinh_dang_khac",
        "Không sống chung do lý do chính đáng khác",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_19_Khoan_2"],
    ),
    (
        "thoa_thuan_noi_cu_tru_khac_nhau",
        "Vợ chồng thỏa thuận có nơi cư trú khác nhau",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_20", "Luat_CuTru_2020_Dieu_14_Khoan_2"],
    ),
    (
        "mot_ben_tu_quyet_moi_viec_trong_gia_dinh",
        "Một bên tự quyết định mọi việc trong gia đình mà không tôn trọng vị thế bình đẳng của bên kia",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_17"],
    ),
    (
        "gia_dinh_chong_can_thiep_quyen_tu_do_ca_nhan_cua_vo",
        "Gia đình chồng can thiệp vào quyền tự do cá nhân thuộc phạm vi quyền nhân thân của vợ",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_18"],
    ),
    (
        "quan_he_tinh_cam_voi_nguoi_khac_khi_dang_hon_nhan",
        "Một bên có quan hệ tình cảm với người khác trong thời kỳ hôn nhân, cần đối chiếu nghĩa vụ chung thủy",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_19_Khoan_1"],
    ),
    ("khong_deo_nhan_cuoi", "Vợ hoặc chồng không đeo nhẫn cưới", "HanhVi", ["Luat_HNGD_2014_Dieu_19_Khoan_1"]),
    (
        "chong_tu_quyet_noi_cu_tru",
        "Chồng tự quyết định nơi cư trú của vợ chồng",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_20"],
    ),
    (
        "bat_buoc_vo_chuyen_khau_ve_nha_chong",
        "Buộc vợ chuyển hộ khẩu về nhà chồng sau kết hôn",
        "HanhVi",
        [
            "Luat_HNGD_2014_Dieu_19_Khoan_2",
            "Luat_HNGD_2014_Dieu_20",
            "Luat_CuTru_2020_Dieu_14_Khoan_2",
        ],
    ),
    (
        "bat_buoc_vo_o_chung_gia_dinh_chong",
        "Buộc vợ về ở chung với gia đình chồng",
        "HanhVi",
        [
            "Luat_HNGD_2014_Dieu_19_Khoan_2",
            "Luat_HNGD_2014_Dieu_20",
            "Luat_CuTru_2020_Dieu_14_Khoan_2",
        ],
    ),
    (
        "dang_thong_tin_rieng_tu_cua_vo_chong_len_mang",
        "Đăng thông tin riêng tư của bên kia lên mạng làm ảnh hưởng danh dự, nhân phẩm hoặc uy tín",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_21"],
    ),
    (
        "cam_can_thuc_hanh_ton_giao",
        "Cấm cản bên kia đi lễ hoặc thực hành tín ngưỡng, tôn giáo",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_22"],
    ),
    (
        "cam_can_di_lam_kiem_tien",
        "Cấm cản bên kia đi làm hoặc lựa chọn công việc tạo thu nhập",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_23"],
    ),
    (
        "can_tro_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "Cản trở bên kia tham gia hoạt động chính trị, kinh tế, văn hóa hoặc xã hội",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_23"],
    ),
    (
        "dau_hieu_xam_pham_nguyen_tac_binh_dang_vo_chong",
        "Dấu hiệu xâm phạm nguyên tắc bình đẳng về quyền, nghĩa vụ giữa vợ và chồng",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_17"],
    ),
    (
        "dau_hieu_xam_pham_quyen_nhan_than_cua_vo_chong",
        "Dấu hiệu quyền nhân thân của vợ hoặc chồng không được tôn trọng, bảo vệ",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_18"],
    ),
    (
        "dau_hieu_vi_pham_nghia_vu_chung_thuy",
        "Dấu hiệu cần đánh giá theo nghĩa vụ chung thủy giữa vợ và chồng",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_19_Khoan_1"],
    ),
    (
        "dau_hieu_vi_pham_nghia_vu_ton_trong_danh_du",
        "Dấu hiệu vi phạm nghĩa vụ tôn trọng, giữ gìn, bảo vệ danh dự, nhân phẩm, uy tín",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_21"],
    ),
    (
        "dau_hieu_vi_pham_nghia_vu_ton_trong_tu_do_tin_nguong",
        "Dấu hiệu vi phạm nghĩa vụ tôn trọng quyền tự do tín ngưỡng, tôn giáo",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_22"],
    ),
    (
        "dau_hieu_can_tro_quyen_hoc_tap_lam_viec_hoat_dong_xa_hoi",
        "Dấu hiệu cản trở quyền, nghĩa vụ về học tập, làm việc và tham gia hoạt động xã hội",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_23"],
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
    ("ChuThe", "vo_chong", "LIEN_QUAN", "QuyDinh", "binh_dang_quyen_nghia_vu_giua_vo_chong"),
    ("ChuThe", "vo_chong", "LIEN_QUAN", "QuyDinh", "quyen_nghia_vu_nhan_than_duoc_ton_trong_bao_ve"),
    ("ChuThe", "vo_chong", "LIEN_QUAN", "QuyDinh", "tinh_nghia_vo_chong"),
    ("ChuThe", "vo_chong", "LIEN_QUAN", "QuyDinh", "lua_chon_noi_cu_tru_do_vo_chong_thoa_thuan"),
    ("QuyDinh", "binh_dang_quyen_nghia_vu_giua_vo_chong", "BAO_GOM", "Quyen", "quyen_nghia_vu_ngang_nhau_moi_mat_trong_gia_dinh"),
    ("HanhVi", "mot_ben_tu_quyet_moi_viec_trong_gia_dinh", "DOI_CHIEU_VOI", "QuyDinh", "binh_dang_quyen_nghia_vu_giua_vo_chong"),
    ("HanhVi", "mot_ben_tu_quyet_moi_viec_trong_gia_dinh", "DAN_TOI", "HauQua", "dau_hieu_xam_pham_nguyen_tac_binh_dang_vo_chong"),
    ("QuyDinh", "quyen_nghia_vu_nhan_than_duoc_ton_trong_bao_ve", "BAO_GOM", "Quyen", "quyen_nhan_than_cua_vo_chong"),
    ("HanhVi", "gia_dinh_chong_can_thiep_quyen_tu_do_ca_nhan_cua_vo", "VI_PHAM", "Quyen", "quyen_nhan_than_cua_vo_chong"),
    ("HanhVi", "gia_dinh_chong_can_thiep_quyen_tu_do_ca_nhan_cua_vo", "DAN_TOI", "HauQua", "dau_hieu_xam_pham_quyen_nhan_than_cua_vo_chong"),
    ("QuyDinh", "tinh_nghia_vo_chong", "BAO_GOM", "NghiaVu", "nghia_vu_thuong_yeu"),
    ("QuyDinh", "tinh_nghia_vo_chong", "BAO_GOM", "NghiaVu", "nghia_vu_chung_thuy"),
    ("QuyDinh", "tinh_nghia_vo_chong", "BAO_GOM", "NghiaVu", "nghia_vu_ton_trong_lan_nhau"),
    ("QuyDinh", "tinh_nghia_vo_chong", "BAO_GOM", "NghiaVu", "nghia_vu_quan_tam_cham_soc_giup_do"),
    ("QuyDinh", "tinh_nghia_vo_chong", "BAO_GOM", "NghiaVu", "nghia_vu_chia_se_thuc_hien_cong_viec_gia_dinh"),
    ("QuyDinh", "tinh_nghia_vo_chong", "BAO_GOM", "NghiaVu", "nghia_vu_song_chung"),
    ("QuyDinh", "tinh_nghia_vo_chong", "BAO_GOM", "QuyDinh", "khong_deo_nhan_cuoi_khong_tu_dong_vi_pham_tinh_nghia_vo_chong"),
    ("HanhVi", "quan_he_tinh_cam_voi_nguoi_khac_khi_dang_hon_nhan", "DOI_CHIEU_VOI", "NghiaVu", "nghia_vu_chung_thuy"),
    ("HanhVi", "quan_he_tinh_cam_voi_nguoi_khac_khi_dang_hon_nhan", "DAN_TOI", "HauQua", "dau_hieu_vi_pham_nghia_vu_chung_thuy"),
    ("HanhVi", "khong_deo_nhan_cuoi", "DOI_CHIEU_VOI", "QuyDinh", "khong_deo_nhan_cuoi_khong_tu_dong_vi_pham_tinh_nghia_vo_chong"),
    ("NghiaVu", "nghia_vu_song_chung", "AP_DUNG_KHI", "DieuKien", "thoa_thuan_khong_song_chung"),
    ("NghiaVu", "nghia_vu_song_chung", "AP_DUNG_KHI", "DieuKien", "yeu_cau_nghe_nghiep_cong_tac"),
    ("NghiaVu", "nghia_vu_song_chung", "AP_DUNG_KHI", "DieuKien", "yeu_cau_hoc_tap"),
    ("NghiaVu", "nghia_vu_song_chung", "AP_DUNG_KHI", "DieuKien", "tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi"),
    ("NghiaVu", "nghia_vu_song_chung", "AP_DUNG_KHI", "DieuKien", "ly_do_chinh_dang_khac"),
    ("QuyDinh", "lua_chon_noi_cu_tru_do_vo_chong_thoa_thuan", "BAO_GOM", "Quyen", "quyen_thoa_thuan_noi_cu_tru"),
    ("Quyen", "quyen_thoa_thuan_noi_cu_tru", "AP_DUNG_KHI", "DieuKien", "thoa_thuan_noi_cu_tru_khac_nhau"),
    ("QuyDinh", "vo_chong_co_the_co_noi_cu_tru_khac_nhau", "LIEN_QUAN", "DieuKien", "thoa_thuan_noi_cu_tru_khac_nhau"),
    ("HanhVi", "chong_tu_quyet_noi_cu_tru", "VI_PHAM", "Quyen", "quyen_thoa_thuan_noi_cu_tru"),
    ("HanhVi", "bat_buoc_vo_chuyen_khau_ve_nha_chong", "DOI_CHIEU_VOI", "QuyDinh", "khong_bat_buoc_vo_chuyen_khau_ve_nha_chong"),
    ("HanhVi", "bat_buoc_vo_o_chung_gia_dinh_chong", "DOI_CHIEU_VOI", "QuyDinh", "khong_bat_buoc_vo_o_chung_gia_dinh_chong"),
    ("HanhVi", "dang_thong_tin_rieng_tu_cua_vo_chong_len_mang", "VI_PHAM", "NghiaVu", "nghia_vu_ton_trong_giu_gin_bao_ve_danh_du_nhan_pham_uy_tin"),
    ("HanhVi", "dang_thong_tin_rieng_tu_cua_vo_chong_len_mang", "DAN_TOI", "HauQua", "dau_hieu_vi_pham_nghia_vu_ton_trong_danh_du"),
    ("Quyen", "quyen_tu_do_tin_nguong_ton_giao", "LIEN_QUAN", "NghiaVu", "nghia_vu_ton_trong_tu_do_tin_nguong_ton_giao"),
    ("HanhVi", "cam_can_thuc_hanh_ton_giao", "VI_PHAM", "Quyen", "quyen_tu_do_tin_nguong_ton_giao"),
    ("HanhVi", "cam_can_thuc_hanh_ton_giao", "DAN_TOI", "HauQua", "dau_hieu_vi_pham_nghia_vu_ton_trong_tu_do_tin_nguong"),
    ("Quyen", "quyen_chon_nghe_nghiep", "LIEN_QUAN", "NghiaVu", "nghia_vu_tao_dieu_kien_giup_do_chon_nghe_nghiep"),
    ("Quyen", "quyen_hoc_tap_nang_cao_trinh_do", "LIEN_QUAN", "NghiaVu", "nghia_vu_tao_dieu_kien_giup_do_hoc_tap_nang_cao_trinh_do"),
    ("Quyen", "quyen_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi", "LIEN_QUAN", "NghiaVu", "nghia_vu_tao_dieu_kien_giup_do_tham_gia_hoat_dong_xa_hoi"),
    ("HanhVi", "cam_can_di_lam_kiem_tien", "VI_PHAM", "Quyen", "quyen_chon_nghe_nghiep"),
    ("HanhVi", "cam_can_di_lam_kiem_tien", "DAN_TOI", "HauQua", "dau_hieu_can_tro_quyen_hoc_tap_lam_viec_hoat_dong_xa_hoi"),
    ("HanhVi", "can_tro_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi", "VI_PHAM", "Quyen", "quyen_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi"),
    ("HanhVi", "can_tro_tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi", "DAN_TOI", "HauQua", "dau_hieu_can_tro_quyen_hoc_tap_lam_viec_hoat_dong_xa_hoi"),
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
