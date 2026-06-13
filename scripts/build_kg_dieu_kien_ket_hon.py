"""Build KG ngữ nghĩa cho topic 'Điều kiện kết hôn' (dieu_kien_ket_hon).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_dieu_kien_ket_hon.py           # MERGE idempotent
    python scripts/build_kg_dieu_kien_ket_hon.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_dieu_kien_ket_hon.py --dry-run # chỉ in summary

Schema: docs/kg_dieu_kien_ket_hon_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "dieu_kien_ket_hon"
TOPIC_LABEL = "DieuKienKetHon"

SEMANTIC_LABELS = [
    "ChuThe",
    "DieuKien",
    "HanhVi",
    "QuanHe",
    "HauQua",
    "QuyDinh",
    "TinhTrangHonNhan",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("hai_ben_nam_nu", "Hai bên nam, nữ dự định xác lập quan hệ vợ chồng", "ChuThe", ["Luat_HNGD_2014_Dieu_3_Khoan_5", "Luat_HNGD_2014_Dieu_8"]),
    ("ket_hon", "Nam và nữ xác lập quan hệ vợ chồng theo điều kiện và đăng ký kết hôn", "HanhVi", ["Luat_HNGD_2014_Dieu_3_Khoan_5", "Luat_HNGD_2014_Dieu_8", "Luat_HNGD_2014_Dieu_9_Khoan_1"]),
    ("thuc_hien_dang_ky_ket_hon", "Thực hiện đăng ký kết hôn tại cơ quan nhà nước có thẩm quyền", "HanhVi", ["Luat_HNGD_2014_Dieu_9_Khoan_1"]),
    ("ket_hon_gia_tao", "Lợi dụng kết hôn không nhằm mục đích xây dựng gia đình", "HanhVi", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_a"]),
    ("tao_hon", "Kết hôn khi một bên hoặc cả hai bên chưa đủ tuổi luật định", "HanhVi", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b", "Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_a"]),
    ("cuong_ep_ket_hon", "Đe dọa, uy hiếp hoặc dùng hành vi khác buộc người khác kết hôn trái ý muốn", "HanhVi", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b", "Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_b"]),
    ("lua_doi_ket_hon", "Lừa dối để người khác kết hôn", "HanhVi", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b", "Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_b"]),
    ("can_tro_ket_hon", "Ngăn cản người có đủ điều kiện thực hiện việc kết hôn tự nguyện", "HanhVi", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b", "Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_b"]),
    ("ket_hon_khi_mot_ben_dang_co_vo_hoac_chong", "Người đang có vợ/chồng kết hôn với người khác hoặc người độc thân kết hôn với người đang có vợ/chồng", "HanhVi", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c", "Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_d"]),
    ("ket_hon_trong_quan_he_than_thich_bi_cam", "Kết hôn giữa các bên có quan hệ huyết thống, nuôi dưỡng hoặc thông gia thuộc danh sách cấm", "HanhVi", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d", "Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_d"]),
    ("du_dieu_kien_ket_hon", "Hai bên đáp ứng đầy đủ điều kiện kết hôn", "DieuKien", ["Luat_HNGD_2014_Dieu_8", "Luat_HNGD_2014_Dieu_8_Khoan_1"]),
    ("nam_tu_du_20_tuoi", "Nam từ đủ 20 tuổi trở lên tại thời điểm kết hôn", "DieuKien", ["Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_a"]),
    ("nu_tu_du_18_tuoi", "Nữ từ đủ 18 tuổi trở lên tại thời điểm kết hôn", "DieuKien", ["Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_a"]),
    ("hai_ben_tu_nguyen_quyet_dinh", "Việc kết hôn do nam và nữ tự nguyện quyết định", "DieuKien", ["Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_b"]),
    ("khong_bi_mat_nang_luc_hanh_vi_dan_su", "Người kết hôn không bị mất năng lực hành vi dân sự", "DieuKien", ["Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_c"]),
    ("khong_thuoc_truong_hop_cam_ket_hon", "Việc kết hôn không thuộc các điểm a-d khoản 2 Điều 5", "DieuKien", ["Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_d", "Luat_HNGD_2014_Dieu_5_Khoan_2"]),
    ("khong_co_vo_chong_hoac_hon_nhan_truoc_da_cham_dut", "Không còn thuộc tình trạng đang có vợ hoặc chồng khi kết hôn với người khác", "DieuKien", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c", "Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_d"]),
    ("hon_nhan_cung_gioi_tinh", "Hôn nhân giữa những người cùng giới tính", "QuanHe", ["Luat_HNGD_2014_Dieu_8_Khoan_2"]),
    ("cung_dong_mau_ve_truc_he", "Người này sinh ra người kia kế tiếp nhau trong quan hệ huyết thống", "QuanHe", ["Luat_HNGD_2014_Dieu_3_Khoan_17", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("co_ho_trong_pham_vi_ba_doi", "Những người cùng một gốc sinh ra thuộc đời thứ nhất, thứ hai hoặc thứ ba theo luật", "QuanHe", ["Luat_HNGD_2014_Dieu_3_Khoan_18", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("anh_chi_em_cung_cha_me", "Anh, chị, em cùng cha mẹ, thuộc đời thứ hai", "QuanHe", ["Luat_HNGD_2014_Dieu_3_Khoan_18", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("anh_chi_em_cung_cha_khac_me", "Anh, chị, em cùng cha khác mẹ, thuộc đời thứ hai", "QuanHe", ["Luat_HNGD_2014_Dieu_3_Khoan_18", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("anh_chi_em_cung_me_khac_cha", "Anh, chị, em cùng mẹ khác cha, thuộc đời thứ hai", "QuanHe", ["Luat_HNGD_2014_Dieu_3_Khoan_18", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("anh_chi_em_con_chu_bac_co_cau_di", "Anh, chị, em con chú, bác, cô, cậu, dì, thuộc đời thứ ba", "QuanHe", ["Luat_HNGD_2014_Dieu_3_Khoan_18", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("con_rieng_cua_bo_cung_cha_khac_me", "Con riêng của bố có cùng cha với người hỏi, tức anh/chị/em cùng cha khác mẹ", "QuanHe", ["Luat_HNGD_2014_Dieu_3_Khoan_18", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("hai_chau_noi_cung_mot_goc_sinh_ra", "Hai người là cháu nội ở hai nhánh nhưng cùng một gốc sinh ra; cần xác định đời cụ thể", "QuanHe", ["Luat_HNGD_2014_Dieu_3_Khoan_18", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("cha_me_nuoi_voi_con_nuoi", "Cha, mẹ nuôi với con nuôi", "QuanHe", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("nguoi_tung_la_cha_me_nuoi_voi_con_nuoi", "Người đã từng là cha, mẹ nuôi với con nuôi", "QuanHe", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("cha_chong_voi_con_dau", "Cha chồng với con dâu", "QuanHe", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("me_vo_voi_con_re", "Mẹ vợ với con rể", "QuanHe", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("cha_duong_voi_con_rieng_cua_vo", "Cha dượng với con riêng của vợ", "QuanHe", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("me_ke_voi_con_rieng_cua_chong", "Mẹ kế với con riêng của chồng", "QuanHe", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("quan_he_thong_gia_khong_tu_phat_sinh_huyet_thong", "Quan hệ thông gia chỉ do hôn nhân của người thân, không tự làm phát sinh quan hệ huyết thống", "QuanHe", ["Luat_HNGD_2014_Dieu_3_Khoan_17", "Luat_HNGD_2014_Dieu_3_Khoan_18", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("em_trai_chong_voi_em_gai_vo", "Em trai của chồng và em gái của vợ", "QuanHe", ["Luat_HNGD_2014_Dieu_3_Khoan_17", "Luat_HNGD_2014_Dieu_3_Khoan_18", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("em_chong_voi_anh_vo", "Em của chồng và anh của vợ", "QuanHe", ["Luat_HNGD_2014_Dieu_3_Khoan_17", "Luat_HNGD_2014_Dieu_3_Khoan_18", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("dang_co_vo_hoac_chong", "Một bên đang tồn tại quan hệ hôn nhân với người khác", "TinhTrangHonNhan", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c", "Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_d"]),
    ("hon_nhan_truoc_da_cham_dut", "Quan hệ hôn nhân trước đã chấm dứt; việc còn hộ khẩu ở nhà chồng cũ không tự thay đổi tình trạng này", "TinhTrangHonNhan", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c", "Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_d"]),
    ("dinh_nghia_ket_hon", "Kết hôn là việc nam và nữ xác lập quan hệ vợ chồng theo quy định về điều kiện và đăng ký", "QuyDinh", ["Luat_HNGD_2014_Dieu_3_Khoan_5"]),
    ("cac_truong_hop_cam_ket_hon_diem_a_den_d", "Nhóm trường hợp làm không đạt điều kiện tại điểm d khoản 1 Điều 8", "QuyDinh", ["Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_d", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_a", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("phan_biet_khong_thua_nhan_va_hanh_vi_cam_hon_nhan_cung_gioi", "Hôn nhân cùng giới không được Nhà nước thừa nhận nhưng không được liệt kê là hành vi cấm tại các điểm a-d khoản 2 Điều 5", "QuyDinh", ["Luat_HNGD_2014_Dieu_5_Khoan_2", "Luat_HNGD_2014_Dieu_8_Khoan_2"]),
    ("dam_cuoi_khong_thay_the_dang_ky_ket_hon", "Lễ cưới hoặc đám cưới không tự xác lập quan hệ vợ chồng hợp pháp", "QuyDinh", ["Luat_HNGD_2014_Dieu_3_Khoan_5", "Luat_HNGD_2014_Dieu_9_Khoan_1"]),
    ("an_treo_khong_tu_dong_la_tro_ngai_ket_hon", "Việc đang chấp hành án treo không tự nằm trong danh sách điều kiện cấm kết hôn", "QuyDinh", ["Luat_HNGD_2014_Dieu_8", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_a", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"]),
    ("an_tich_chua_duoc_xoa_khong_tu_dong_la_tro_ngai_ket_hon", "Việc chưa được xóa án tích không tự nằm trong danh sách điều kiện cấm kết hôn", "QuyDinh", ["Luat_HNGD_2014_Dieu_8"]),
    ("bai_liet_khong_dong_nghia_mat_nang_luc_hanh_vi_dan_su", "Bại liệt hoặc khuyết tật thể chất không tự đồng nghĩa với mất năng lực hành vi dân sự", "QuyDinh", ["Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_c"]),
    ("khac_tin_nguong_khong_tu_dong_la_tro_ngai_ket_hon", "Khác tín ngưỡng không tự nằm trong các điều kiện cấm kết hôn", "QuyDinh", ["Luat_HNGD_2014_Dieu_8", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b"]),
    ("gia_dinh_khong_dong_y_khong_thay_the_y_chi_hai_ben", "Ý kiến phản đối của gia đình không thay thế quyết định tự nguyện của hai bên đủ điều kiện", "QuyDinh", ["Luat_HNGD_2014_Dieu_8_Khoan_1_Diem_b", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b"]),
    ("ho_khau_khong_phai_dieu_kien_noi_dung_ket_hon", "Nơi đăng ký hộ khẩu không phải một điều kiện nội dung tại Điều 8", "QuyDinh", ["Luat_HNGD_2014_Dieu_8"]),
    ("quan_he_giao_vien_hoc_sinh_khong_tu_dong_quyet_dinh", "Quan hệ giáo viên-học sinh không tự quyết định được phép kết hôn; phải kiểm tra tuổi, tự nguyện và các điều cấm", "QuyDinh", ["Luat_HNGD_2014_Dieu_8", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b"]),
    ("xung_khac_tuoi_khong_phai_dieu_kien_luat_dinh", "Quan niệm xung khắc tuổi không phải điều kiện kết hôn luật định", "QuyDinh", ["Luat_HNGD_2014_Dieu_8"]),
    ("hon_nhan_cung_gioi_khong_duoc_nha_nuoc_thua_nhan", "Nhà nước không thừa nhận hôn nhân giữa những người cùng giới tính", "HauQua", ["Luat_HNGD_2014_Dieu_8_Khoan_2"]),
    ("khong_du_dieu_kien_ket_hon", "Một hoặc cả hai bên không đáp ứng ít nhất một điều kiện tại Điều 8", "HauQua", ["Luat_HNGD_2014_Dieu_8"]),
    ("quan_he_vo_chong_duoc_xac_lap_khi_du_dieu_kien_va_dang_ky_hop_le", "Quan hệ vợ chồng hợp pháp được xác lập khi đáp ứng điều kiện kết hôn và đăng ký theo luật", "HauQua", ["Luat_HNGD_2014_Dieu_3_Khoan_1", "Luat_HNGD_2014_Dieu_3_Khoan_5", "Luat_HNGD_2014_Dieu_8", "Luat_HNGD_2014_Dieu_9_Khoan_1"]),
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
    ("ChuThe", "hai_ben_nam_nu", "THUC_HIEN", "HanhVi", "ket_hon"),
    ("ChuThe", "hai_ben_nam_nu", "THUC_HIEN", "HanhVi", "thuc_hien_dang_ky_ket_hon"),
    ("HanhVi", "ket_hon", "AP_DUNG_KHI", "DieuKien", "du_dieu_kien_ket_hon"),
    ("DieuKien", "du_dieu_kien_ket_hon", "BAO_GOM", "DieuKien", "nam_tu_du_20_tuoi"),
    ("DieuKien", "du_dieu_kien_ket_hon", "BAO_GOM", "DieuKien", "nu_tu_du_18_tuoi"),
    ("DieuKien", "du_dieu_kien_ket_hon", "BAO_GOM", "DieuKien", "hai_ben_tu_nguyen_quyet_dinh"),
    ("DieuKien", "du_dieu_kien_ket_hon", "BAO_GOM", "DieuKien", "khong_bi_mat_nang_luc_hanh_vi_dan_su"),
    ("DieuKien", "du_dieu_kien_ket_hon", "BAO_GOM", "DieuKien", "khong_thuoc_truong_hop_cam_ket_hon"),
    ("DieuKien", "khong_thuoc_truong_hop_cam_ket_hon", "LIEN_QUAN", "QuyDinh", "cac_truong_hop_cam_ket_hon_diem_a_den_d"),
    ("QuyDinh", "cac_truong_hop_cam_ket_hon_diem_a_den_d", "BAO_GOM", "HanhVi", "ket_hon_gia_tao"),
    ("QuyDinh", "cac_truong_hop_cam_ket_hon_diem_a_den_d", "BAO_GOM", "HanhVi", "tao_hon"),
    ("QuyDinh", "cac_truong_hop_cam_ket_hon_diem_a_den_d", "BAO_GOM", "HanhVi", "cuong_ep_ket_hon"),
    ("QuyDinh", "cac_truong_hop_cam_ket_hon_diem_a_den_d", "BAO_GOM", "HanhVi", "lua_doi_ket_hon"),
    ("QuyDinh", "cac_truong_hop_cam_ket_hon_diem_a_den_d", "BAO_GOM", "HanhVi", "can_tro_ket_hon"),
    ("QuyDinh", "cac_truong_hop_cam_ket_hon_diem_a_den_d", "BAO_GOM", "HanhVi", "ket_hon_khi_mot_ben_dang_co_vo_hoac_chong"),
    ("QuyDinh", "cac_truong_hop_cam_ket_hon_diem_a_den_d", "BAO_GOM", "HanhVi", "ket_hon_trong_quan_he_than_thich_bi_cam"),
    ("HanhVi", "tao_hon", "VI_PHAM", "DieuKien", "nam_tu_du_20_tuoi"),
    ("HanhVi", "tao_hon", "VI_PHAM", "DieuKien", "nu_tu_du_18_tuoi"),
    ("HanhVi", "cuong_ep_ket_hon", "VI_PHAM", "DieuKien", "hai_ben_tu_nguyen_quyet_dinh"),
    ("HanhVi", "lua_doi_ket_hon", "VI_PHAM", "DieuKien", "hai_ben_tu_nguyen_quyet_dinh"),
    ("HanhVi", "can_tro_ket_hon", "VI_PHAM", "DieuKien", "hai_ben_tu_nguyen_quyet_dinh"),
    ("HanhVi", "ket_hon_khi_mot_ben_dang_co_vo_hoac_chong", "AP_DUNG_KHI", "TinhTrangHonNhan", "dang_co_vo_hoac_chong"),
    ("TinhTrangHonNhan", "dang_co_vo_hoac_chong", "DOI_CHIEU_VOI", "DieuKien", "khong_co_vo_chong_hoac_hon_nhan_truoc_da_cham_dut"),
    ("TinhTrangHonNhan", "hon_nhan_truoc_da_cham_dut", "DOI_CHIEU_VOI", "DieuKien", "khong_co_vo_chong_hoac_hon_nhan_truoc_da_cham_dut"),
    ("HanhVi", "ket_hon_trong_quan_he_than_thich_bi_cam", "AP_DUNG_KHI", "QuanHe", "cung_dong_mau_ve_truc_he"),
    ("HanhVi", "ket_hon_trong_quan_he_than_thich_bi_cam", "AP_DUNG_KHI", "QuanHe", "co_ho_trong_pham_vi_ba_doi"),
    ("HanhVi", "ket_hon_trong_quan_he_than_thich_bi_cam", "AP_DUNG_KHI", "QuanHe", "cha_me_nuoi_voi_con_nuoi"),
    ("HanhVi", "ket_hon_trong_quan_he_than_thich_bi_cam", "AP_DUNG_KHI", "QuanHe", "nguoi_tung_la_cha_me_nuoi_voi_con_nuoi"),
    ("HanhVi", "ket_hon_trong_quan_he_than_thich_bi_cam", "AP_DUNG_KHI", "QuanHe", "cha_chong_voi_con_dau"),
    ("HanhVi", "ket_hon_trong_quan_he_than_thich_bi_cam", "AP_DUNG_KHI", "QuanHe", "me_vo_voi_con_re"),
    ("HanhVi", "ket_hon_trong_quan_he_than_thich_bi_cam", "AP_DUNG_KHI", "QuanHe", "cha_duong_voi_con_rieng_cua_vo"),
    ("HanhVi", "ket_hon_trong_quan_he_than_thich_bi_cam", "AP_DUNG_KHI", "QuanHe", "me_ke_voi_con_rieng_cua_chong"),
    ("QuanHe", "anh_chi_em_cung_cha_me", "THUOC_NHOM", "QuanHe", "co_ho_trong_pham_vi_ba_doi"),
    ("QuanHe", "anh_chi_em_cung_cha_khac_me", "THUOC_NHOM", "QuanHe", "co_ho_trong_pham_vi_ba_doi"),
    ("QuanHe", "anh_chi_em_cung_me_khac_cha", "THUOC_NHOM", "QuanHe", "co_ho_trong_pham_vi_ba_doi"),
    ("QuanHe", "anh_chi_em_con_chu_bac_co_cau_di", "THUOC_NHOM", "QuanHe", "co_ho_trong_pham_vi_ba_doi"),
    ("QuanHe", "con_rieng_cua_bo_cung_cha_khac_me", "THUOC_NHOM", "QuanHe", "anh_chi_em_cung_cha_khac_me"),
    ("QuanHe", "hai_chau_noi_cung_mot_goc_sinh_ra", "THUOC_NHOM", "QuanHe", "co_ho_trong_pham_vi_ba_doi"),
    ("QuanHe", "em_trai_chong_voi_em_gai_vo", "THUOC_NHOM", "QuanHe", "quan_he_thong_gia_khong_tu_phat_sinh_huyet_thong"),
    ("QuanHe", "em_chong_voi_anh_vo", "THUOC_NHOM", "QuanHe", "quan_he_thong_gia_khong_tu_phat_sinh_huyet_thong"),
    ("QuanHe", "hon_nhan_cung_gioi_tinh", "DAN_TOI", "HauQua", "hon_nhan_cung_gioi_khong_duoc_nha_nuoc_thua_nhan"),
    ("QuanHe", "hon_nhan_cung_gioi_tinh", "LIEN_QUAN", "QuyDinh", "phan_biet_khong_thua_nhan_va_hanh_vi_cam_hon_nhan_cung_gioi"),
    ("HanhVi", "ket_hon", "DAN_TOI", "HauQua", "quan_he_vo_chong_duoc_xac_lap_khi_du_dieu_kien_va_dang_ky_hop_le"),
    ("HanhVi", "thuc_hien_dang_ky_ket_hon", "DAN_TOI", "HauQua", "quan_he_vo_chong_duoc_xac_lap_khi_du_dieu_kien_va_dang_ky_hop_le"),
    ("QuyDinh", "dam_cuoi_khong_thay_the_dang_ky_ket_hon", "LIEN_QUAN", "HanhVi", "thuc_hien_dang_ky_ket_hon"),
    ("QuyDinh", "an_treo_khong_tu_dong_la_tro_ngai_ket_hon", "DOI_CHIEU_VOI", "DieuKien", "du_dieu_kien_ket_hon"),
    ("QuyDinh", "an_tich_chua_duoc_xoa_khong_tu_dong_la_tro_ngai_ket_hon", "DOI_CHIEU_VOI", "DieuKien", "du_dieu_kien_ket_hon"),
    ("QuyDinh", "bai_liet_khong_dong_nghia_mat_nang_luc_hanh_vi_dan_su", "DOI_CHIEU_VOI", "DieuKien", "khong_bi_mat_nang_luc_hanh_vi_dan_su"),
    ("QuyDinh", "khac_tin_nguong_khong_tu_dong_la_tro_ngai_ket_hon", "DOI_CHIEU_VOI", "DieuKien", "du_dieu_kien_ket_hon"),
    ("QuyDinh", "gia_dinh_khong_dong_y_khong_thay_the_y_chi_hai_ben", "DOI_CHIEU_VOI", "DieuKien", "hai_ben_tu_nguyen_quyet_dinh"),
    ("QuyDinh", "ho_khau_khong_phai_dieu_kien_noi_dung_ket_hon", "DOI_CHIEU_VOI", "DieuKien", "du_dieu_kien_ket_hon"),
    ("QuyDinh", "quan_he_giao_vien_hoc_sinh_khong_tu_dong_quyet_dinh", "DOI_CHIEU_VOI", "DieuKien", "du_dieu_kien_ket_hon"),
    ("QuyDinh", "xung_khac_tuoi_khong_phai_dieu_kien_luat_dinh", "DOI_CHIEU_VOI", "DieuKien", "du_dieu_kien_ket_hon"),
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
