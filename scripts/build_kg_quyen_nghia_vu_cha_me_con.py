"""Build KG ngữ nghĩa cho topic 'Quyền, nghĩa vụ cha mẹ và con' (quyen_nghia_vu_cha_me_con).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_quyen_nghia_vu_cha_me_con.py           # MERGE idempotent
    python scripts/build_kg_quyen_nghia_vu_cha_me_con.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_quyen_nghia_vu_cha_me_con.py --dry-run # chỉ in summary

Schema: docs/kg_quyen_nghia_vu_cha_me_con_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "quyen_nghia_vu_cha_me_con"
TOPIC_LABEL = "QuyenNghiaVuChaMeCon"

SEMANTIC_LABELS = [
    "ChuThe",
    "QuyDinh",
    "Quyen",
    "NghiaVu",
    "HanhVi",
    "QuanHe",
    "DieuKien",
    "HauQua",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    (
        "quyen_nghia_vu_cha_me_con",
        "Hệ thống quyền, nghĩa vụ của cha mẹ và con trong phạm vi Điều 68-74, 78-80",
        "QuyDinh",
        [
            "Luat_HNGD_2014_Dieu_68",
            "Luat_HNGD_2014_Dieu_69",
            "Luat_HNGD_2014_Dieu_70",
            "Luat_HNGD_2014_Dieu_71",
            "Luat_HNGD_2014_Dieu_72",
            "Luat_HNGD_2014_Dieu_73",
            "Luat_HNGD_2014_Dieu_74",
            "Luat_HNGD_2014_Dieu_78",
            "Luat_HNGD_2014_Dieu_79",
            "Luat_HNGD_2014_Dieu_80",
        ],
    ),
    (
        "quan_he_cha_me_con",
        "Quan hệ giữa cha mẹ và con",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_68"],
    ),
    (
        "cha_me",
        "Cha và mẹ",
        "ChuThe",
        [
            "Luat_HNGD_2014_Dieu_69",
            "Luat_HNGD_2014_Dieu_71",
            "Luat_HNGD_2014_Dieu_72",
            "Luat_HNGD_2014_Dieu_73",
            "Luat_HNGD_2014_Dieu_74",
        ],
    ),
    (
        "con",
        "Con trong quan hệ với cha mẹ, không phụ thuộc tình trạng hôn nhân của cha mẹ",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_68_Khoan_2", "Luat_HNGD_2014_Dieu_70"],
    ),
    (
        "con_chua_thanh_nien",
        "Con chưa thành niên",
        "ChuThe",
        [
            "Luat_HNGD_2014_Dieu_69_Khoan_2",
            "Luat_HNGD_2014_Dieu_70_Khoan_3",
            "Luat_HNGD_2014_Dieu_71_Khoan_1",
            "Luat_HNGD_2014_Dieu_73_Khoan_1",
            "Luat_HNGD_2014_Dieu_74",
        ],
    ),
    (
        "con_can_duoc_cham_soc_dac_biet",
        "Con đã thành niên mất năng lực hành vi dân sự hoặc không có khả năng lao động và không có tài sản để tự nuôi mình",
        "ChuThe",
        [
            "Luat_HNGD_2014_Dieu_69_Khoan_2",
            "Luat_HNGD_2014_Dieu_70_Khoan_3",
            "Luat_HNGD_2014_Dieu_71_Khoan_1",
            "Luat_HNGD_2014_Dieu_73_Khoan_1",
        ],
    ),
    (
        "cha_nuoi_me_nuoi",
        "Cha nuôi, mẹ nuôi",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_68_Khoan_3", "Luat_HNGD_2014_Dieu_78"],
    ),
    (
        "con_nuoi",
        "Con nuôi",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_68_Khoan_3", "Luat_HNGD_2014_Dieu_78"],
    ),
    (
        "cha_de_me_de",
        "Cha đẻ, mẹ đẻ của người con đã làm con nuôi",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_78_Khoan_2", "Luat_HNGD_2014_Dieu_78_Khoan_3"],
    ),
    (
        "cha_duong_me_ke",
        "Cha dượng, mẹ kế",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_79"],
    ),
    (
        "con_rieng_cua_vo_hoac_chong",
        "Con riêng của vợ hoặc của chồng",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_79"],
    ),
    (
        "con_dau_con_re",
        "Con dâu, con rể",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_80"],
    ),
    (
        "cha_me_vo_cha_me_chong",
        "Cha mẹ vợ, cha mẹ chồng",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_80"],
    ),
    (
        "bao_ve_quyen_nghia_vu_cha_me_con",
        "Quyền và nghĩa vụ của cha mẹ và con được tôn trọng và bảo vệ",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_68_Khoan_1"],
    ),
    (
        "con_binh_dang_khong_phu_thuoc_hon_nhan_cha_me",
        "Con có quyền và nghĩa vụ như nhau đối với cha mẹ, không phụ thuộc tình trạng hôn nhân của cha mẹ",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_68_Khoan_2"],
    ),
    (
        "quan_he_cha_me_nuoi_con_nuoi_co_quyen_nghia_vu_cha_me_con",
        "Giữa cha mẹ nuôi và con nuôi có quyền, nghĩa vụ của cha mẹ và con",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_68_Khoan_3"],
    ),
    (
        "thoa_thuan_khong_duoc_anh_huong_quyen_loi_nguoi_duoc_bao_ve",
        "Thỏa thuận về nhân thân, tài sản không được ảnh hưởng quyền, lợi ích hợp pháp của người được luật bảo vệ",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_68_Khoan_4"],
    ),
    (
        "nghia_vu_quyen_cua_cha_me",
        "Toàn bộ nghĩa vụ và quyền của cha mẹ đối với con",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_69"],
    ),
    (
        "thuong_yeu_ton_trong_y_kien_cham_lo_hoc_tap_giao_duc_con",
        "Thương yêu, tôn trọng ý kiến, chăm lo học tập và giáo dục con phát triển lành mạnh",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_69_Khoan_1"],
    ),
    (
        "trong_nom_nuoi_duong_cham_soc_bao_ve_quyen_loi_con",
        "Trông nom, nuôi dưỡng, chăm sóc và bảo vệ quyền, lợi ích hợp pháp của con thuộc diện luật định",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_69_Khoan_2"],
    ),
    (
        "giam_ho_hoac_dai_dien_cho_con",
        "Giám hộ hoặc đại diện cho con theo quy định của pháp luật",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_69_Khoan_3"],
    ),
    (
        "khong_phan_biet_doi_xu_voi_con",
        "Không phân biệt đối xử với con theo giới hoặc tình trạng hôn nhân của cha mẹ",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_69_Khoan_4"],
    ),
    (
        "khong_lam_dung_suc_lao_dong_cua_con",
        "Không lạm dụng sức lao động của con thuộc diện được bảo vệ",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_69_Khoan_4"],
    ),
    (
        "khong_xui_giuc_ep_buoc_con_lam_viec_trai_phap_luat_dao_duc",
        "Không xúi giục, ép buộc con làm việc trái pháp luật hoặc trái đạo đức xã hội",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_69_Khoan_4"],
    ),
    (
        "quyen_nghia_vu_cua_con",
        "Toàn bộ quyền và nghĩa vụ của con đối với cha mẹ và gia đình",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_70"],
    ),
    (
        "con_duoc_thuong_yeu_ton_trong_hoc_tap_giao_duc_phat_trien",
        "Con được cha mẹ thương yêu, tôn trọng, bảo vệ quyền lợi, học tập, giáo dục và phát triển lành mạnh",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_70_Khoan_1"],
    ),
    (
        "con_yeu_quy_kinh_trong_biet_on_hieu_thao_phung_duong_cha_me",
        "Con có bổn phận yêu quý, kính trọng, biết ơn, hiếu thảo và phụng dưỡng cha mẹ",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_70_Khoan_2"],
    ),
    (
        "con_duoc_song_chung_trong_nom_nuoi_duong_cham_soc",
        "Con thuộc diện luật định có quyền sống chung và được cha mẹ trông nom, nuôi dưỡng, chăm sóc",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_70_Khoan_3"],
    ),
    (
        "con_chua_thanh_nien_tham_gia_cong_viec_gia_dinh_phu_hop_lua_tuoi",
        "Con chưa thành niên tham gia công việc gia đình phù hợp lứa tuổi và pháp luật bảo vệ trẻ em",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_70_Khoan_3"],
    ),
    (
        "con_thanh_nien_tu_do_chon_nghe_noi_cu_tru_hoc_tap_hoat_dong",
        "Con đã thành niên tự do lựa chọn nghề nghiệp, nơi cư trú, học tập và hoạt động theo nguyện vọng, khả năng",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_70_Khoan_4"],
    ),
    (
        "con_song_cung_cha_me_tham_gia_cong_viec_dong_gop_thu_nhap",
        "Con đã thành niên sống cùng cha mẹ tham gia công việc gia đình và đóng góp thu nhập phù hợp khả năng",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_70_Khoan_4"],
    ),
    (
        "con_huong_quyen_tai_san_tuong_xung_cong_suc",
        "Con được hưởng quyền về tài sản tương xứng với công sức đóng góp vào tài sản gia đình",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_70_Khoan_5"],
    ),
    (
        "cha_me_ngang_nhau_cung_cham_soc_nuoi_duong_con",
        "Cha và mẹ có nghĩa vụ, quyền ngang nhau và cùng chăm sóc, nuôi dưỡng con thuộc diện luật định",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_71_Khoan_1"],
    ),
    (
        "con_cham_soc_nuoi_duong_cha_me",
        "Con có nghĩa vụ và quyền chăm sóc, nuôi dưỡng cha mẹ, đặc biệt khi cha mẹ cần được hỗ trợ",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_71_Khoan_2"],
    ),
    (
        "cac_con_cung_nhau_cham_soc_nuoi_duong_cha_me",
        "Gia đình có nhiều con thì các con cùng nhau chăm sóc, nuôi dưỡng cha mẹ",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_71_Khoan_2"],
    ),
    (
        "cha_me_giao_duc_tao_dieu_kien_hoc_tap_cho_con",
        "Cha mẹ giáo dục, chăm lo và tạo điều kiện cho con học tập",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_72_Khoan_1"],
    ),
    (
        "tao_moi_truong_gia_dinh_lam_guong_phoi_hop_giao_duc",
        "Cha mẹ tạo môi trường gia đình đầm ấm, làm gương và phối hợp với nhà trường, cơ quan, tổ chức",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_72_Khoan_1"],
    ),
    (
        "huong_dan_va_ton_trong_quyen_chon_nghe_cua_con",
        "Cha mẹ hướng dẫn nhưng phải tôn trọng quyền chọn nghề và quyền tham gia hoạt động của con",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_72_Khoan_2"],
    ),
    (
        "de_nghi_co_quan_to_chuc_ho_tro_giao_duc_con",
        "Cha mẹ có thể đề nghị cơ quan, tổ chức hữu quan hỗ trợ khi không thể tự giải quyết khó khăn giáo dục con",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_72_Khoan_3"],
    ),
    (
        "cha_me_dai_dien_theo_phap_luat_cho_con",
        "Cha mẹ là người đại diện theo pháp luật cho con thuộc diện luật định",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_73_Khoan_1"],
    ),
    (
        "ngoai_le_co_nguoi_giam_ho_hoac_dai_dien_khac",
        "Không áp dụng đại diện của cha mẹ khi con có người khác làm giám hộ hoặc đại diện theo pháp luật",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_73_Khoan_1"],
    ),
    (
        "giao_dich_nhu_cau_thiet_yeu_cua_con",
        "Giao dịch nhằm đáp ứng nhu cầu thiết yếu của con thuộc diện luật định",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_73_Khoan_2"],
    ),
    (
        "cha_hoac_me_tu_minh_thuc_hien_giao_dich_thiet_yeu",
        "Cha hoặc mẹ có quyền tự mình thực hiện giao dịch nhằm đáp ứng nhu cầu thiết yếu của con",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_73_Khoan_2"],
    ),
    (
        "giao_dich_tai_san_quan_trong_cua_con",
        "Giao dịch về bất động sản, động sản phải đăng ký hoặc tài sản đưa vào kinh doanh của con",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_73_Khoan_3"],
    ),
    (
        "giao_dich_tai_san_quan_trong_can_thoa_thuan_cha_me",
        "Giao dịch tài sản quan trọng của con phải có sự thỏa thuận của cha mẹ",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_73_Khoan_3"],
    ),
    (
        "cha_me_chiu_trach_nhiem_lien_doi_giao_dich_tai_san_cua_con",
        "Cha mẹ chịu trách nhiệm liên đới về giao dịch tài sản của con theo khoản 2, khoản 3 và Bộ luật dân sự",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_73_Khoan_4"],
    ),
    (
        "con_thuoc_dien_luat_dinh_gay_thiet_hai",
        "Con chưa thành niên hoặc con đã thành niên mất năng lực hành vi dân sự gây thiệt hại",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_74"],
    ),
    (
        "cha_me_boi_thuong_thiet_hai_do_con_gay_ra",
        "Cha mẹ bồi thường thiệt hại do con thuộc diện luật định gây ra theo Bộ luật dân sự",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_74"],
    ),
    (
        "quan_he_nuoi_con_nuoi_duoc_xac_lap",
        "Quan hệ nuôi con nuôi được xác lập theo Luật nuôi con nuôi",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_78_Khoan_1"],
    ),
    (
        "quyen_nghia_vu_cha_me_nuoi_con_nuoi_phat_sinh",
        "Quyền, nghĩa vụ giữa cha mẹ nuôi và con nuôi phát sinh từ thời điểm quan hệ nuôi con nuôi được xác lập",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_78_Khoan_1"],
    ),
    (
        "quyet_dinh_cham_dut_nuoi_con_nuoi_co_hieu_luc",
        "Quyết định của Tòa án chấm dứt việc nuôi con nuôi có hiệu lực pháp luật",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_78_Khoan_1"],
    ),
    (
        "quyen_nghia_vu_cha_me_nuoi_con_nuoi_cham_dut",
        "Quyền, nghĩa vụ giữa cha mẹ nuôi và con nuôi chấm dứt từ ngày quyết định của Tòa án có hiệu lực",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_78_Khoan_1"],
    ),
    (
        "quyen_nghia_vu_cha_me_de_con_da_cho_lam_con_nuoi",
        "Quyền, nghĩa vụ giữa cha mẹ đẻ và con đã làm con nuôi được thực hiện theo Luật nuôi con nuôi",
        "QuyDinh",
        ["Luat_HNGD_2014_Dieu_78_Khoan_2"],
    ),
    (
        "quan_he_nuoi_con_nuoi_cham_dut",
        "Quan hệ nuôi con nuôi chấm dứt",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_78_Khoan_3"],
    ),
    (
        "quyen_nghia_vu_cha_me_de_con_de_duoc_khoi_phuc",
        "Quyền, nghĩa vụ giữa cha mẹ đẻ và con đẻ được khôi phục khi quan hệ nuôi con nuôi chấm dứt",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_78_Khoan_3"],
    ),
    (
        "toa_an_chi_dinh_nguoi_giam_ho_khi_can",
        "Tòa án chỉ định người giám hộ khi cha mẹ đẻ không còn hoặc không đủ điều kiện nuôi người con thuộc diện luật định",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_78_Khoan_3"],
    ),
    (
        "quan_he_cha_duong_me_ke_con_rieng_cung_song_chung",
        "Quan hệ cha dượng, mẹ kế và con riêng của bên kia cùng sống chung",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_79"],
    ),
    (
        "cha_duong_me_ke_cham_soc_giao_duc_con_rieng",
        "Cha dượng, mẹ kế trông nom, nuôi dưỡng, chăm sóc, giáo dục con riêng cùng sống chung",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_79_Khoan_1"],
    ),
    (
        "con_rieng_cham_soc_phung_duong_cha_duong_me_ke",
        "Con riêng chăm sóc, phụng dưỡng cha dượng, mẹ kế cùng sống chung",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_79_Khoan_2"],
    ),
    (
        "quan_he_con_dau_re_cha_me_vo_chong_cung_song_chung",
        "Quan hệ con dâu, con rể với cha mẹ chồng, cha mẹ vợ khi cùng sống chung",
        "QuanHe",
        ["Luat_HNGD_2014_Dieu_80"],
    ),
    (
        "cac_ben_ton_trong_quan_tam_cham_soc_giup_do_nhau",
        "Các bên cùng sống chung tôn trọng, quan tâm, chăm sóc và giúp đỡ nhau",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_80"],
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
    ("QuyDinh", "quyen_nghia_vu_cha_me_con", "BAO_GOM", "QuyDinh", "bao_ve_quyen_nghia_vu_cha_me_con"),
    ("QuyDinh", "quyen_nghia_vu_cha_me_con", "BAO_GOM", "QuyDinh", "nghia_vu_quyen_cua_cha_me"),
    ("QuyDinh", "quyen_nghia_vu_cha_me_con", "BAO_GOM", "QuyDinh", "quyen_nghia_vu_cua_con"),
    ("QuyDinh", "quyen_nghia_vu_cha_me_con", "LIEN_QUAN", "QuanHe", "quan_he_cha_me_con"),
    ("QuanHe", "quan_he_cha_me_con", "CO_CHU_THE", "ChuThe", "cha_me"),
    ("QuanHe", "quan_he_cha_me_con", "CO_CHU_THE", "ChuThe", "con"),
    ("QuyDinh", "bao_ve_quyen_nghia_vu_cha_me_con", "LIEN_QUAN", "Quyen", "con_binh_dang_khong_phu_thuoc_hon_nhan_cha_me"),
    ("QuyDinh", "bao_ve_quyen_nghia_vu_cha_me_con", "LIEN_QUAN", "QuyDinh", "quan_he_cha_me_nuoi_con_nuoi_co_quyen_nghia_vu_cha_me_con"),
    ("QuyDinh", "bao_ve_quyen_nghia_vu_cha_me_con", "LIEN_QUAN", "DieuKien", "thoa_thuan_khong_duoc_anh_huong_quyen_loi_nguoi_duoc_bao_ve"),
    ("ChuThe", "cha_me", "CO_NGHIA_VU", "NghiaVu", "thuong_yeu_ton_trong_y_kien_cham_lo_hoc_tap_giao_duc_con"),
    ("ChuThe", "cha_me", "CO_NGHIA_VU", "NghiaVu", "trong_nom_nuoi_duong_cham_soc_bao_ve_quyen_loi_con"),
    ("ChuThe", "cha_me", "CO_NGHIA_VU", "NghiaVu", "giam_ho_hoac_dai_dien_cho_con"),
    ("ChuThe", "cha_me", "CO_NGHIA_VU", "NghiaVu", "khong_phan_biet_doi_xu_voi_con"),
    ("ChuThe", "cha_me", "CO_NGHIA_VU", "NghiaVu", "khong_lam_dung_suc_lao_dong_cua_con"),
    ("ChuThe", "cha_me", "CO_NGHIA_VU", "NghiaVu", "khong_xui_giuc_ep_buoc_con_lam_viec_trai_phap_luat_dao_duc"),
    ("ChuThe", "con", "CO_QUYEN", "Quyen", "con_duoc_thuong_yeu_ton_trong_hoc_tap_giao_duc_phat_trien"),
    ("ChuThe", "con", "CO_NGHIA_VU", "NghiaVu", "con_yeu_quy_kinh_trong_biet_on_hieu_thao_phung_duong_cha_me"),
    ("ChuThe", "con_chua_thanh_nien", "CO_QUYEN", "Quyen", "con_duoc_song_chung_trong_nom_nuoi_duong_cham_soc"),
    ("ChuThe", "con_chua_thanh_nien", "CO_NGHIA_VU", "NghiaVu", "con_chua_thanh_nien_tham_gia_cong_viec_gia_dinh_phu_hop_lua_tuoi"),
    ("ChuThe", "con", "CO_QUYEN", "Quyen", "con_thanh_nien_tu_do_chon_nghe_noi_cu_tru_hoc_tap_hoat_dong"),
    ("ChuThe", "con", "CO_NGHIA_VU", "NghiaVu", "con_song_cung_cha_me_tham_gia_cong_viec_dong_gop_thu_nhap"),
    ("ChuThe", "con", "CO_QUYEN", "Quyen", "con_huong_quyen_tai_san_tuong_xung_cong_suc"),
    ("ChuThe", "cha_me", "CO_NGHIA_VU", "NghiaVu", "cha_me_ngang_nhau_cung_cham_soc_nuoi_duong_con"),
    ("ChuThe", "con", "CO_NGHIA_VU", "NghiaVu", "con_cham_soc_nuoi_duong_cha_me"),
    ("NghiaVu", "con_cham_soc_nuoi_duong_cha_me", "BAO_GOM", "NghiaVu", "cac_con_cung_nhau_cham_soc_nuoi_duong_cha_me"),
    ("ChuThe", "cha_me", "CO_NGHIA_VU", "NghiaVu", "cha_me_giao_duc_tao_dieu_kien_hoc_tap_cho_con"),
    ("NghiaVu", "cha_me_giao_duc_tao_dieu_kien_hoc_tap_cho_con", "BAO_GOM", "NghiaVu", "tao_moi_truong_gia_dinh_lam_guong_phoi_hop_giao_duc"),
    ("ChuThe", "cha_me", "CO_NGHIA_VU", "NghiaVu", "huong_dan_va_ton_trong_quyen_chon_nghe_cua_con"),
    ("ChuThe", "cha_me", "CO_QUYEN", "Quyen", "de_nghi_co_quan_to_chuc_ho_tro_giao_duc_con"),
    ("ChuThe", "cha_me", "CO_QUYEN", "Quyen", "cha_me_dai_dien_theo_phap_luat_cho_con"),
    ("Quyen", "cha_me_dai_dien_theo_phap_luat_cho_con", "AP_DUNG_KHI", "DieuKien", "ngoai_le_co_nguoi_giam_ho_hoac_dai_dien_khac"),
    ("ChuThe", "cha_me", "THUC_HIEN", "HanhVi", "giao_dich_nhu_cau_thiet_yeu_cua_con"),
    ("HanhVi", "giao_dich_nhu_cau_thiet_yeu_cua_con", "LIEN_QUAN", "Quyen", "cha_hoac_me_tu_minh_thuc_hien_giao_dich_thiet_yeu"),
    ("ChuThe", "cha_me", "THUC_HIEN", "HanhVi", "giao_dich_tai_san_quan_trong_cua_con"),
    ("HanhVi", "giao_dich_tai_san_quan_trong_cua_con", "AP_DUNG_KHI", "DieuKien", "giao_dich_tai_san_quan_trong_can_thoa_thuan_cha_me"),
    ("HanhVi", "giao_dich_tai_san_quan_trong_cua_con", "LIEN_QUAN", "NghiaVu", "cha_me_chiu_trach_nhiem_lien_doi_giao_dich_tai_san_cua_con"),
    ("DieuKien", "con_thuoc_dien_luat_dinh_gay_thiet_hai", "DAN_TOI", "NghiaVu", "cha_me_boi_thuong_thiet_hai_do_con_gay_ra"),
    ("DieuKien", "quan_he_nuoi_con_nuoi_duoc_xac_lap", "DAN_TOI", "HauQua", "quyen_nghia_vu_cha_me_nuoi_con_nuoi_phat_sinh"),
    ("DieuKien", "quyet_dinh_cham_dut_nuoi_con_nuoi_co_hieu_luc", "DAN_TOI", "HauQua", "quyen_nghia_vu_cha_me_nuoi_con_nuoi_cham_dut"),
    ("DieuKien", "quan_he_nuoi_con_nuoi_cham_dut", "DAN_TOI", "HauQua", "quyen_nghia_vu_cha_me_de_con_de_duoc_khoi_phuc"),
    ("HauQua", "quyen_nghia_vu_cha_me_de_con_de_duoc_khoi_phuc", "LIEN_QUAN", "HauQua", "toa_an_chi_dinh_nguoi_giam_ho_khi_can"),
    ("QuanHe", "quan_he_cha_duong_me_ke_con_rieng_cung_song_chung", "CO_CHU_THE", "ChuThe", "cha_duong_me_ke"),
    ("QuanHe", "quan_he_cha_duong_me_ke_con_rieng_cung_song_chung", "CO_CHU_THE", "ChuThe", "con_rieng_cua_vo_hoac_chong"),
    ("QuanHe", "quan_he_cha_duong_me_ke_con_rieng_cung_song_chung", "CO_NGHIA_VU", "NghiaVu", "cha_duong_me_ke_cham_soc_giao_duc_con_rieng"),
    ("QuanHe", "quan_he_cha_duong_me_ke_con_rieng_cung_song_chung", "CO_NGHIA_VU", "NghiaVu", "con_rieng_cham_soc_phung_duong_cha_duong_me_ke"),
    ("QuanHe", "quan_he_con_dau_re_cha_me_vo_chong_cung_song_chung", "CO_CHU_THE", "ChuThe", "con_dau_con_re"),
    ("QuanHe", "quan_he_con_dau_re_cha_me_vo_chong_cung_song_chung", "CO_CHU_THE", "ChuThe", "cha_me_vo_cha_me_chong"),
    ("QuanHe", "quan_he_con_dau_re_cha_me_vo_chong_cung_song_chung", "CO_NGHIA_VU", "NghiaVu", "cac_ben_ton_trong_quan_tam_cham_soc_giup_do_nhau"),
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
