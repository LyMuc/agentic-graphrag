"""Build KG ngữ nghĩa cho topic 'Cha mẹ, con sau ly hôn' (Điều 81-84 Luật HN&GĐ 2014).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_cha_me_con_sau_ly_hon.py           # MERGE idempotent
    python scripts/build_kg_cha_me_con_sau_ly_hon.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_cha_me_con_sau_ly_hon.py --dry-run # chỉ in summary

Schema: docs/kg_cha_me_con_sau_ly_hon_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "cha_me_con_sau_ly_hon"
TOPIC_LABEL = "ChaMeConSauLyHon"

SEMANTIC_LABELS = [
    "NghiaVu",
    "Quyen",
    "ChuThe",
    "DieuKien",
    "HauQua",
    "HanhVi",
    "ThoaThuan",
]

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("cha_me_sau_ly_hon", "Cha, mẹ sau khi ly hôn", "ChuThe", ["Luat_HNGD_2014_Dieu_81"]),
    (
        "con_sau_ly_hon",
        "Con thuộc trường hợp được cha mẹ tiếp tục trông nom, chăm sóc, nuôi dưỡng, giáo dục sau ly hôn",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_81_Khoan_1"],
    ),
    (
        "nguoi_truc_tiep_nuoi_con",
        "Cha hoặc mẹ trực tiếp nuôi con sau ly hôn",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_81_Khoan_2", "Luat_HNGD_2014_Dieu_83"],
    ),
    (
        "nguoi_khong_truc_tiep_nuoi_con",
        "Cha hoặc mẹ không trực tiếp nuôi con sau ly hôn",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_82"],
    ),
    (
        "thanh_vien_gia_dinh_nguoi_truc_tiep_nuoi",
        "Thành viên gia đình của người trực tiếp nuôi con",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_83"],
    ),
    (
        "toa_an_giai_quyet_viec_nuoi_con",
        "Tòa án giải quyết việc giao hoặc thay đổi người trực tiếp nuôi con",
        "ChuThe",
        [
            "Luat_HNGD_2014_Dieu_81_Khoan_2",
            "Luat_HNGD_2014_Dieu_84_Khoan_1",
            "Luat_HNGD_2014_Dieu_84_Khoan_4",
        ],
    ),
    (
        "nguoi_giam_ho_nhan_nuoi_con",
        "Người giám hộ được giao nuôi con khi cả cha và mẹ đều không đủ điều kiện",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_84_Khoan_4"],
    ),
    (
        "nguoi_than_thich_yeu_cau_thay_doi_nguoi_nuoi",
        "Người thân thích có quyền yêu cầu thay đổi người trực tiếp nuôi con",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_84_Khoan_5_Diem_a"],
    ),
    (
        "co_quan_quan_ly_gia_dinh_yeu_cau_thay_doi_nguoi_nuoi",
        "Cơ quan quản lý nhà nước về gia đình có quyền yêu cầu thay đổi người trực tiếp nuôi con",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_84_Khoan_5_Diem_b"],
    ),
    (
        "co_quan_quan_ly_tre_em_yeu_cau_thay_doi_nguoi_nuoi",
        "Cơ quan quản lý nhà nước về trẻ em có quyền yêu cầu thay đổi người trực tiếp nuôi con",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_84_Khoan_5_Diem_c"],
    ),
    (
        "hoi_lien_hiep_phu_nu_yeu_cau_thay_doi_nguoi_nuoi",
        "Hội liên hiệp phụ nữ có quyền yêu cầu thay đổi người trực tiếp nuôi con",
        "ChuThe",
        ["Luat_HNGD_2014_Dieu_84_Khoan_5_Diem_d"],
    ),
    (
        "nghia_vu_trong_nom_cham_soc_nuoi_duong_giao_duc_con",
        "Nghĩa vụ trông nom, chăm sóc, nuôi dưỡng, giáo dục con sau ly hôn",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_81_Khoan_1"],
    ),
    (
        "nghia_vu_nguoi_khong_truc_tiep_nuoi_con",
        "Nhóm nghĩa vụ của cha, mẹ không trực tiếp nuôi con sau ly hôn",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_82"],
    ),
    (
        "nghia_vu_ton_trong_quyen_con_song_chung_voi_nguoi_nuoi",
        "Tôn trọng quyền của con được sống chung với người trực tiếp nuôi",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_82_Khoan_1"],
    ),
    (
        "nghia_vu_tham_nom_con",
        "Nghĩa vụ thăm nom con của người không trực tiếp nuôi",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_82_Khoan_3"],
    ),
    (
        "nghia_vu_ton_trong_quyen_duoc_nuoi_con",
        "Nghĩa vụ tôn trọng quyền được nuôi con của người trực tiếp nuôi",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_83_Khoan_1"],
    ),
    (
        "nghia_vu_khong_can_tro_tham_nom_cham_soc_con",
        "Không cản trở việc thăm nom, chăm sóc, nuôi dưỡng, giáo dục con",
        "NghiaVu",
        ["Luat_HNGD_2014_Dieu_83_Khoan_2"],
    ),
    (
        "quyen_cua_con_duoc_song_chung_voi_nguoi_truc_tiep_nuoi",
        "Quyền của con được sống chung với người trực tiếp nuôi",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_82_Khoan_1"],
    ),
    (
        "quyen_tham_nom_con_khong_bi_can_tro",
        "Quyền thăm nom con mà không ai được cản trở",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_82_Khoan_3"],
    ),
    (
        "quyen_yeu_cau_nguoi_khong_truc_tiep_nuoi_thuc_hien_nghia_vu",
        "Quyền yêu cầu người không trực tiếp nuôi thực hiện nghĩa vụ tại Điều 82",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_83_Khoan_1"],
    ),
    (
        "quyen_yeu_cau_ton_trong_quyen_duoc_nuoi_con",
        "Quyền yêu cầu người không trực tiếp nuôi và thành viên gia đình tôn trọng quyền được nuôi con",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_83_Khoan_1"],
    ),
    (
        "quyen_yeu_cau_toa_an_han_che_tham_nom",
        "Quyền yêu cầu Tòa án hạn chế quyền thăm nom khi việc thăm nom bị lạm dụng",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_82_Khoan_3"],
    ),
    (
        "quyen_yeu_cau_thay_doi_nguoi_truc_tiep_nuoi_con",
        "Quyền yêu cầu Tòa án thay đổi người trực tiếp nuôi con",
        "Quyen",
        ["Luat_HNGD_2014_Dieu_84_Khoan_1", "Luat_HNGD_2014_Dieu_84_Khoan_5"],
    ),
    ("con_chua_thanh_nien", "Con chưa thành niên", "DieuKien", ["Luat_HNGD_2014_Dieu_81_Khoan_1"]),
    (
        "con_thanh_nien_mat_nang_luc_hanh_vi_dan_su",
        "Con đã thành niên mất năng lực hành vi dân sự",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_81_Khoan_1"],
    ),
    (
        "con_thanh_nien_khong_kha_nang_lao_dong_khong_tai_san",
        "Con đã thành niên không có khả năng lao động và không có tài sản để tự nuôi mình",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_81_Khoan_1"],
    ),
    (
        "cha_me_thoa_thuan_nguoi_truc_tiep_nuoi",
        "Cha mẹ thỏa thuận về người trực tiếp nuôi, quyền và nghĩa vụ của mỗi bên",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_81_Khoan_2"],
    ),
    (
        "cha_me_khong_thoa_thuan_duoc_nguoi_nuoi",
        "Cha mẹ không thỏa thuận được về người trực tiếp nuôi con",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_81_Khoan_2"],
    ),
    (
        "bao_dam_quyen_loi_moi_mat_cua_con",
        "Việc giao con phải căn cứ vào quyền lợi về mọi mặt của con",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_81_Khoan_2"],
    ),
    (
        "con_tu_du_bay_tuoi",
        "Con từ đủ 07 tuổi trở lên",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_81_Khoan_2", "Luat_HNGD_2014_Dieu_84_Khoan_3"],
    ),
    (
        "con_duoi_ba_muoi_sau_thang_tuoi",
        "Con dưới 36 tháng tuổi",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_81_Khoan_3"],
    ),
    (
        "me_khong_du_dieu_kien_truc_tiep_nuoi_con",
        "Người mẹ không đủ điều kiện trực tiếp trông nom, chăm sóc, nuôi dưỡng, giáo dục con",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_81_Khoan_3"],
    ),
    (
        "cha_me_co_thoa_thuan_khac_phu_hop_loi_ich_con",
        "Cha mẹ có thỏa thuận khác phù hợp với lợi ích của con dưới 36 tháng tuổi",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_81_Khoan_3"],
    ),
    (
        "lam_dung_tham_nom_can_tro_cham_soc_con",
        "Lạm dụng việc thăm nom để cản trở việc trông nom, chăm sóc, nuôi dưỡng, giáo dục con",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_82_Khoan_3"],
    ),
    (
        "lam_dung_tham_nom_gay_anh_huong_xau_den_con",
        "Lạm dụng việc thăm nom gây ảnh hưởng xấu đến việc chăm sóc và giáo dục con",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_82_Khoan_3"],
    ),
    (
        "co_yeu_cau_thay_doi_nguoi_truc_tiep_nuoi",
        "Có yêu cầu hợp lệ về thay đổi người trực tiếp nuôi con",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_84_Khoan_1"],
    ),
    (
        "cha_me_thoa_thuan_thay_doi_nguoi_nuoi_phu_hop_loi_ich_con",
        "Cha mẹ thỏa thuận thay đổi người trực tiếp nuôi phù hợp với lợi ích của con",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_84_Khoan_2_Diem_a"],
    ),
    (
        "nguoi_truc_tiep_nuoi_khong_con_du_dieu_kien",
        "Người trực tiếp nuôi không còn đủ điều kiện trông nom, chăm sóc, nuôi dưỡng, giáo dục con",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_84_Khoan_2_Diem_b"],
    ),
    (
        "thay_doi_nguoi_nuoi_phai_xem_xet_nguyen_vong_con_tu_du_bay_tuoi",
        "Khi thay đổi người nuôi phải xem xét nguyện vọng của con từ đủ 07 tuổi",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_84_Khoan_3"],
    ),
    (
        "ca_cha_va_me_deu_khong_du_dieu_kien_nuoi_con",
        "Cả cha và mẹ đều không đủ điều kiện trực tiếp nuôi con",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_84_Khoan_4"],
    ),
    (
        "can_cu_diem_b_khoan_2_va_loi_ich_cua_con",
        "Có căn cứ người đang nuôi không còn đủ điều kiện và việc yêu cầu dựa trên lợi ích của con",
        "DieuKien",
        ["Luat_HNGD_2014_Dieu_84_Khoan_5"],
    ),
    (
        "thoa_thuan_nguoi_truc_tiep_nuoi_con",
        "Thỏa thuận người trực tiếp nuôi con, quyền và nghĩa vụ của mỗi bên",
        "ThoaThuan",
        ["Luat_HNGD_2014_Dieu_81_Khoan_2"],
    ),
    (
        "thoa_thuan_thay_doi_nguoi_truc_tiep_nuoi_con",
        "Thỏa thuận thay đổi người trực tiếp nuôi con",
        "ThoaThuan",
        ["Luat_HNGD_2014_Dieu_84_Khoan_2_Diem_a"],
    ),
    (
        "xac_dinh_nguoi_nuoi_theo_thoa_thuan",
        "Xác định người trực tiếp nuôi theo thỏa thuận của cha mẹ",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_81_Khoan_2"],
    ),
    (
        "toa_an_quyet_dinh_giao_con_cho_mot_ben",
        "Tòa án quyết định giao con cho một bên trực tiếp nuôi",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_81_Khoan_2"],
    ),
    (
        "xem_xet_nguyen_vong_cua_con",
        "Xem xét nguyện vọng của con từ đủ 07 tuổi",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_81_Khoan_2", "Luat_HNGD_2014_Dieu_84_Khoan_3"],
    ),
    ("tham_nom_con_sau_ly_hon", "Thăm nom con sau ly hôn", "HanhVi", ["Luat_HNGD_2014_Dieu_82_Khoan_3"]),
    (
        "can_tro_viec_tham_nom_con",
        "Cản trở người không trực tiếp nuôi thăm nom, chăm sóc, nuôi dưỡng, giáo dục con",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_83_Khoan_2"],
    ),
    ("lam_dung_viec_tham_nom_con", "Lạm dụng việc thăm nom con", "HanhVi", ["Luat_HNGD_2014_Dieu_82_Khoan_3"]),
    (
        "yeu_cau_toa_an_han_che_quyen_tham_nom",
        "Yêu cầu Tòa án hạn chế quyền thăm nom",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_82_Khoan_3"],
    ),
    (
        "yeu_cau_toa_an_thay_doi_nguoi_truc_tiep_nuoi_con",
        "Yêu cầu Tòa án thay đổi người trực tiếp nuôi con",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_84_Khoan_1", "Luat_HNGD_2014_Dieu_84_Khoan_5"],
    ),
    (
        "toa_an_xem_xet_thay_doi_nguoi_truc_tiep_nuoi_con",
        "Tòa án xem xét và quyết định thay đổi người trực tiếp nuôi con",
        "HanhVi",
        ["Luat_HNGD_2014_Dieu_84_Khoan_1"],
    ),
    (
        "giao_con_theo_thoa_thuan_cua_cha_me",
        "Con được giao theo thỏa thuận của cha mẹ phù hợp với quyền, lợi ích của con",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_81_Khoan_2"],
    ),
    (
        "toa_an_giao_con_theo_quyen_loi_moi_mat",
        "Con được giao cho một bên căn cứ vào quyền lợi về mọi mặt",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_81_Khoan_2"],
    ),
    (
        "giao_con_duoi_ba_muoi_sau_thang_cho_me",
        "Con dưới 36 tháng tuổi được giao cho mẹ trực tiếp nuôi nếu không có ngoại lệ",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_81_Khoan_3"],
    ),
    (
        "toa_an_han_che_quyen_tham_nom",
        "Tòa án có thể hạn chế quyền thăm nom của người lạm dụng việc thăm nom",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_82_Khoan_3"],
    ),
    (
        "toa_an_thay_doi_nguoi_truc_tiep_nuoi_con",
        "Tòa án thay đổi người trực tiếp nuôi con khi có căn cứ",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_84_Khoan_1", "Luat_HNGD_2014_Dieu_84_Khoan_2"],
    ),
    (
        "toa_an_giao_con_cho_nguoi_giam_ho",
        "Tòa án giao con cho người giám hộ khi cả cha và mẹ đều không đủ điều kiện",
        "HauQua",
        ["Luat_HNGD_2014_Dieu_84_Khoan_4"],
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

# (src_id, rel, dst_id) — cả hai đầu đều thuộc topic này
_EDGE_TRIPLES: list[tuple[str, str, str]] = [
    ("cha_me_sau_ly_hon", "CO_NGHIA_VU", "nghia_vu_trong_nom_cham_soc_nuoi_duong_giao_duc_con"),
    ("nguoi_khong_truc_tiep_nuoi_con", "CO_NGHIA_VU", "nghia_vu_nguoi_khong_truc_tiep_nuoi_con"),
    ("nguoi_khong_truc_tiep_nuoi_con", "CO_NGHIA_VU", "nghia_vu_ton_trong_quyen_con_song_chung_voi_nguoi_nuoi"),
    ("nguoi_khong_truc_tiep_nuoi_con", "CO_NGHIA_VU", "nghia_vu_tham_nom_con"),
    ("nguoi_truc_tiep_nuoi_con", "CO_NGHIA_VU", "nghia_vu_khong_can_tro_tham_nom_cham_soc_con"),
    ("thanh_vien_gia_dinh_nguoi_truc_tiep_nuoi", "CO_NGHIA_VU", "nghia_vu_khong_can_tro_tham_nom_cham_soc_con"),
    ("nguoi_khong_truc_tiep_nuoi_con", "CO_QUYEN", "quyen_tham_nom_con_khong_bi_can_tro"),
    ("nguoi_truc_tiep_nuoi_con", "CO_QUYEN", "quyen_yeu_cau_nguoi_khong_truc_tiep_nuoi_thuc_hien_nghia_vu"),
    ("nguoi_truc_tiep_nuoi_con", "CO_QUYEN", "quyen_yeu_cau_ton_trong_quyen_duoc_nuoi_con"),
    ("nguoi_truc_tiep_nuoi_con", "CO_QUYEN", "quyen_yeu_cau_toa_an_han_che_tham_nom"),
    ("cha_me_sau_ly_hon", "CO_QUYEN", "quyen_yeu_cau_thay_doi_nguoi_truc_tiep_nuoi_con"),
    ("nguoi_than_thich_yeu_cau_thay_doi_nguoi_nuoi", "CO_QUYEN", "quyen_yeu_cau_thay_doi_nguoi_truc_tiep_nuoi_con"),
    ("co_quan_quan_ly_gia_dinh_yeu_cau_thay_doi_nguoi_nuoi", "CO_QUYEN", "quyen_yeu_cau_thay_doi_nguoi_truc_tiep_nuoi_con"),
    ("co_quan_quan_ly_tre_em_yeu_cau_thay_doi_nguoi_nuoi", "CO_QUYEN", "quyen_yeu_cau_thay_doi_nguoi_truc_tiep_nuoi_con"),
    ("hoi_lien_hiep_phu_nu_yeu_cau_thay_doi_nguoi_nuoi", "CO_QUYEN", "quyen_yeu_cau_thay_doi_nguoi_truc_tiep_nuoi_con"),
    ("nghia_vu_ton_trong_quyen_con_song_chung_voi_nguoi_nuoi", "BAO_DAM", "quyen_cua_con_duoc_song_chung_voi_nguoi_truc_tiep_nuoi"),
    ("nghia_vu_khong_can_tro_tham_nom_cham_soc_con", "BAO_DAM", "quyen_tham_nom_con_khong_bi_can_tro"),
    ("nghia_vu_trong_nom_cham_soc_nuoi_duong_giao_duc_con", "AP_DUNG_KHI", "con_chua_thanh_nien"),
    ("nghia_vu_trong_nom_cham_soc_nuoi_duong_giao_duc_con", "AP_DUNG_KHI", "con_thanh_nien_mat_nang_luc_hanh_vi_dan_su"),
    ("nghia_vu_trong_nom_cham_soc_nuoi_duong_giao_duc_con", "AP_DUNG_KHI", "con_thanh_nien_khong_kha_nang_lao_dong_khong_tai_san"),
    ("thoa_thuan_nguoi_truc_tiep_nuoi_con", "DIEU_CHINH", "xac_dinh_nguoi_nuoi_theo_thoa_thuan"),
    ("xac_dinh_nguoi_nuoi_theo_thoa_thuan", "DAN_TOI", "giao_con_theo_thoa_thuan_cua_cha_me"),
    ("toa_an_quyet_dinh_giao_con_cho_mot_ben", "AP_DUNG_KHI", "cha_me_khong_thoa_thuan_duoc_nguoi_nuoi"),
    ("toa_an_quyet_dinh_giao_con_cho_mot_ben", "AP_DUNG_KHI", "bao_dam_quyen_loi_moi_mat_cua_con"),
    ("toa_an_quyet_dinh_giao_con_cho_mot_ben", "AP_DUNG_KHI", "con_tu_du_bay_tuoi"),
    ("toa_an_quyet_dinh_giao_con_cho_mot_ben", "DAN_TOI", "toa_an_giao_con_theo_quyen_loi_moi_mat"),
    ("xem_xet_nguyen_vong_cua_con", "AP_DUNG_KHI", "con_tu_du_bay_tuoi"),
    ("tham_nom_con_sau_ly_hon", "LIEN_QUAN", "quyen_tham_nom_con_khong_bi_can_tro"),
    ("can_tro_viec_tham_nom_con", "LIEN_QUAN", "nghia_vu_khong_can_tro_tham_nom_cham_soc_con"),
    ("lam_dung_viec_tham_nom_con", "AP_DUNG_KHI", "lam_dung_tham_nom_can_tro_cham_soc_con"),
    ("lam_dung_viec_tham_nom_con", "AP_DUNG_KHI", "lam_dung_tham_nom_gay_anh_huong_xau_den_con"),
    ("quyen_yeu_cau_toa_an_han_che_tham_nom", "THUC_HIEN", "yeu_cau_toa_an_han_che_quyen_tham_nom"),
    ("yeu_cau_toa_an_han_che_quyen_tham_nom", "DAN_TOI", "toa_an_han_che_quyen_tham_nom"),
    ("quyen_yeu_cau_thay_doi_nguoi_truc_tiep_nuoi_con", "THUC_HIEN", "yeu_cau_toa_an_thay_doi_nguoi_truc_tiep_nuoi_con"),
    ("yeu_cau_toa_an_thay_doi_nguoi_truc_tiep_nuoi_con", "AP_DUNG_KHI", "co_yeu_cau_thay_doi_nguoi_truc_tiep_nuoi"),
    ("yeu_cau_toa_an_thay_doi_nguoi_truc_tiep_nuoi_con", "AP_DUNG_KHI", "cha_me_thoa_thuan_thay_doi_nguoi_nuoi_phu_hop_loi_ich_con"),
    ("yeu_cau_toa_an_thay_doi_nguoi_truc_tiep_nuoi_con", "AP_DUNG_KHI", "nguoi_truc_tiep_nuoi_khong_con_du_dieu_kien"),
    ("yeu_cau_toa_an_thay_doi_nguoi_truc_tiep_nuoi_con", "AP_DUNG_KHI", "thay_doi_nguoi_nuoi_phai_xem_xet_nguyen_vong_con_tu_du_bay_tuoi"),
    ("yeu_cau_toa_an_thay_doi_nguoi_truc_tiep_nuoi_con", "AP_DUNG_KHI", "can_cu_diem_b_khoan_2_va_loi_ich_cua_con"),
    ("thoa_thuan_thay_doi_nguoi_truc_tiep_nuoi_con", "DIEU_CHINH", "toa_an_xem_xet_thay_doi_nguoi_truc_tiep_nuoi_con"),
    ("toa_an_xem_xet_thay_doi_nguoi_truc_tiep_nuoi_con", "DAN_TOI", "toa_an_thay_doi_nguoi_truc_tiep_nuoi_con"),
    ("toa_an_xem_xet_thay_doi_nguoi_truc_tiep_nuoi_con", "AP_DUNG_KHI", "ca_cha_va_me_deu_khong_du_dieu_kien_nuoi_con"),
    ("ca_cha_va_me_deu_khong_du_dieu_kien_nuoi_con", "DAN_TOI", "toa_an_giao_con_cho_nguoi_giam_ho"),
]

EDGES: list[tuple] = [
    (_ID_TO_LABEL[src], src, rel, _ID_TO_LABEL[dst], dst, {})
    for src, rel, dst in _EDGE_TRIPLES
]

LIEN_KET_CAP_DUONG = (
    "nghia_vu_nguoi_khong_truc_tiep_nuoi_con",
    "nghia_vu_cap_duong_cha_me_khong_truc_tiep_nuoi_con",
)


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


def merge_lien_ket_cap_duong(session) -> int:
    src_id, dst_id = LIEN_KET_CAP_DUONG
    query = (
        f"MATCH (s:NghiaVu:{TOPIC_LABEL} {{id: $src_id, topic: $topic}}) "
        f"OPTIONAL MATCH (d:NghiaVu:CapDuong {{id: $dst_id}}) "
        f"WITH s, d WHERE d IS NOT NULL "
        f"MERGE (s)-[r:LIEN_KET_CAP_DUONG]->(d) "
        f"RETURN count(r) AS created"
    )
    record = session.run(query, src_id=src_id, dst_id=dst_id, topic=TOPIC).single()
    created = record["created"] if record else 0
    if created == 0:
        print(
            "[WARN] LIEN_KET_CAP_DUONG: node đích "
            f"NghiaVu:CapDuong {{id: {dst_id!r}}} chưa tồn tại — bỏ qua edge chéo."
        )
    return created


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

        print("[step 1/5] Tạo indexes...")
        create_indexes(session)

        print("[step 2/5] MERGE nodes...")
        nodes_created = merge_nodes(session)
        print(f"  -> Đã tạo {nodes_created} node mới (số còn lại đã tồn tại).")

        print("[step 3/5] MERGE semantic edges...")
        edges_created = merge_edges(session)
        print(f"  -> Đã tạo {edges_created} edge ngữ nghĩa mới.")

        print("[step 4/5] MERGE LIEN_KET_CAP_DUONG (chéo cap_duong nếu có)...")
        lk_created = merge_lien_ket_cap_duong(session)
        print(f"  -> Đã tạo {lk_created} edge LIEN_KET_CAP_DUONG.")

        print("[step 5/5] MERGE CAN_CU_TAI tới legal layer...")
        cct_created, cct_missing = merge_can_cu_tai(session)
        print(
            f"  -> Đã tạo {cct_created} CAN_CU_TAI mới; "
            f"{cct_missing} legal node thiếu (xem WARN ở trên)."
        )

    print(f"[done] Build KG semantic layer cho '{TOPIC}' hoàn tất.")


if __name__ == "__main__":
    main()
