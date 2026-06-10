"""Build KG ngữ nghĩa cho topic 'Chung sống như vợ chồng không đăng ký kết hôn' (Điều 5, 14-16 Luật HN&GĐ 2014).

Script này build / refresh lớp semantic ĐỘC LẬP. Chỉ MERGE node ngữ nghĩa và
relationship nội bộ + CAN_CU_TAI sang layer luật đã tồn tại trong Neo4j.

Cách chạy:
    python scripts/build_kg_chung_song_nhu_vo_chong.py           # MERGE idempotent
    python scripts/build_kg_chung_song_nhu_vo_chong.py --reset   # XOÁ topic trước khi build
    python scripts/build_kg_chung_song_nhu_vo_chong.py --dry-run # chỉ in summary

Schema: docs/kg_chung_song_nhu_vo_chong_schema.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402


TOPIC = "chung_song_nhu_vo_chong"
TOPIC_LABEL = "ChungSongNhuVoChong"

SEMANTIC_LABELS = [
    "HanhVi",
    "DieuKien",
    "HauQua",
    "Quyen",
    "NghiaVu",
    "ChuThe",
    "ThoaThuan",
    "TinhTrangHonNhan",
]

LEGAL_LABELS = {"DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat"}

# (id, ten, label, [CAN_CU_TAI legal ids])
_SEMANTIC_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("nam_nu_chung_song_khong_dang_ky", "Nam, nữ chung sống với nhau như vợ chồng mà không đăng ký kết hôn", "ChuThe", ["Luat_HNGD_2014_Dieu_14", "Luat_HNGD_2014_Dieu_14_Khoan_1", "Luat_HNGD_2014_Dieu_15", "Luat_HNGD_2014_Dieu_16"]),
    ("cha_me_khong_dang_ky_ket_hon", "Cha mẹ của con chung nhưng không đăng ký kết hôn với nhau", "ChuThe", ["Luat_HNGD_2014_Dieu_15"]),
    ("con_cua_nam_nu_chung_song", "Con của nam, nữ chung sống như vợ chồng không đăng ký kết hôn", "ChuThe", ["Luat_HNGD_2014_Dieu_15"]),
    ("phu_nu_trong_quan_he_chung_song", "Người phụ nữ trong quan hệ chung sống không đăng ký kết hôn", "ChuThe", ["Luat_HNGD_2014_Dieu_16_Khoan_2"]),
    ("chung_song_nhu_vo_chong_khong_dang_ky", "Chung sống với nhau như vợ chồng mà không đăng ký kết hôn", "HanhVi", ["Luat_HNGD_2014_Dieu_14", "Luat_HNGD_2014_Dieu_14_Khoan_1"]),
    ("chung_song_voi_nguoi_dang_co_vo_chong", "Chung sống như vợ chồng khi một bên đang có vợ hoặc chồng", "HanhVi", ["Luat_HNGD_2014_Dieu_5_Khoan_2", "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c"]),
    ("dang_ky_ket_hon_sau_thoi_gian_chung_song", "Đăng ký kết hôn sau một thời gian chung sống như vợ chồng", "HanhVi", ["Luat_HNGD_2014_Dieu_14_Khoan_2"]),
    ("giai_quyet_quan_he_tai_san", "Giải quyết quan hệ tài sản giữa các bên chung sống không đăng ký", "HanhVi", ["Luat_HNGD_2014_Dieu_14_Khoan_1", "Luat_HNGD_2014_Dieu_16", "Luat_HNGD_2014_Dieu_16_Khoan_1", "Luat_HNGD_2014_Dieu_16_Khoan_2"]),
    ("giai_quyet_nghia_vu_giua_cac_ben", "Giải quyết nghĩa vụ giữa các bên chung sống không đăng ký", "HanhVi", ["Luat_HNGD_2014_Dieu_14_Khoan_1", "Luat_HNGD_2014_Dieu_16_Khoan_1"]),
    ("giai_quyet_hop_dong_giua_cac_ben", "Giải quyết hợp đồng giữa các bên chung sống không đăng ký", "HanhVi", ["Luat_HNGD_2014_Dieu_14_Khoan_1", "Luat_HNGD_2014_Dieu_16_Khoan_1"]),
    ("thuc_hien_cong_viec_noi_tro_duy_tri_doi_song_chung", "Thực hiện công việc nội trợ hoặc công việc khác để duy trì đời sống chung", "HanhVi", ["Luat_HNGD_2014_Dieu_16_Khoan_2"]),
    ("du_dieu_kien_ket_hon", "Nam, nữ có đủ điều kiện kết hôn theo Luật Hôn nhân và gia đình", "DieuKien", ["Luat_HNGD_2014_Dieu_14_Khoan_1"]),
    ("khong_dang_ky_ket_hon", "Nam, nữ không thực hiện đăng ký kết hôn", "DieuKien", ["Luat_HNGD_2014_Dieu_14_Khoan_1"]),
    ("mot_ben_dang_co_vo_hoac_chong", "Một bên đang có vợ hoặc chồng", "DieuKien", ["Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c"]),
    ("co_thoa_thuan_giua_cac_ben", "Các bên có thỏa thuận về tài sản, nghĩa vụ hoặc hợp đồng", "DieuKien", ["Luat_HNGD_2014_Dieu_16_Khoan_1"]),
    ("khong_co_thoa_thuan_giua_cac_ben", "Các bên không có thỏa thuận về tài sản, nghĩa vụ hoặc hợp đồng", "DieuKien", ["Luat_HNGD_2014_Dieu_16_Khoan_1"]),
    ("khong_phat_sinh_quyen_nghia_vu_vo_chong", "Việc chung sống không đăng ký không làm phát sinh quyền, nghĩa vụ giữa vợ và chồng", "HauQua", ["Luat_HNGD_2014_Dieu_14_Khoan_1"]),
    ("quyen_nghia_vu_voi_con_giai_quyet_theo_quy_dinh_cha_me_con", "Quyền, nghĩa vụ đối với con được giải quyết theo quy định về quyền, nghĩa vụ của cha mẹ và con", "HauQua", ["Luat_HNGD_2014_Dieu_14_Khoan_1", "Luat_HNGD_2014_Dieu_15"]),
    ("tai_san_nghia_vu_hop_dong_giai_quyet_theo_dieu_16", "Tài sản, nghĩa vụ và hợp đồng giữa các bên được giải quyết theo Điều 16", "HauQua", ["Luat_HNGD_2014_Dieu_14_Khoan_1", "Luat_HNGD_2014_Dieu_16"]),
    ("quan_he_hon_nhan_xac_lap_tu_thoi_diem_dang_ky", "Quan hệ hôn nhân được xác lập từ thời điểm đăng ký kết hôn", "HauQua", ["Luat_HNGD_2014_Dieu_14_Khoan_2"]),
    ("thoi_gian_chung_song_khong_tu_xac_lap_hon_nhan", "Thời gian chung sống trước đăng ký không tự làm phát sinh quan hệ hôn nhân", "HauQua", ["Luat_HNGD_2014_Dieu_14_Khoan_2"]),
    ("ap_dung_thoa_thuan_giua_cac_ben", "Áp dụng thỏa thuận giữa các bên để giải quyết tài sản, nghĩa vụ và hợp đồng", "HauQua", ["Luat_HNGD_2014_Dieu_16_Khoan_1"]),
    ("ap_dung_bo_luat_dan_su_va_phap_luat_lien_quan", "Khi không có thỏa thuận, áp dụng Bộ luật Dân sự và quy định pháp luật liên quan", "HauQua", ["Luat_HNGD_2014_Dieu_16_Khoan_1"]),
    ("bao_dam_quyen_loi_hop_phap_cua_phu_nu_va_con", "Việc giải quyết tài sản phải bảo đảm quyền, lợi ích hợp pháp của phụ nữ và con", "HauQua", ["Luat_HNGD_2014_Dieu_16_Khoan_2"]),
    ("cong_viec_noi_tro_duoc_coi_nhu_lao_dong_co_thu_nhap", "Công việc nội trợ và công việc duy trì đời sống chung được coi như lao động có thu nhập", "HauQua", ["Luat_HNGD_2014_Dieu_16_Khoan_2"]),
    ("quyen_cua_cha_me_va_con_theo_quy_dinh_chung", "Quyền giữa cha mẹ và con áp dụng như quy định chung của Luật Hôn nhân và gia đình", "Quyen", ["Luat_HNGD_2014_Dieu_15"]),
    ("nghia_vu_cua_cha_me_va_con_theo_quy_dinh_chung", "Nghĩa vụ giữa cha mẹ và con áp dụng như quy định chung của Luật Hôn nhân và gia đình", "NghiaVu", ["Luat_HNGD_2014_Dieu_15"]),
    ("nghia_vu_tai_san_giua_cac_ben_chung_song", "Nghĩa vụ tài sản giữa các bên chung sống không đăng ký kết hôn", "NghiaVu", ["Luat_HNGD_2014_Dieu_16_Khoan_1"]),
    ("thoa_thuan_tai_san_nghia_vu_hop_dong", "Thỏa thuận giữa các bên về tài sản, nghĩa vụ và hợp đồng", "ThoaThuan", ["Luat_HNGD_2014_Dieu_16_Khoan_1"]),
    ("chua_phat_sinh_quan_he_hon_nhan", "Chưa phát sinh quan hệ hôn nhân do chưa đăng ký kết hôn", "TinhTrangHonNhan", ["Luat_HNGD_2014_Dieu_14_Khoan_1", "Luat_HNGD_2014_Dieu_14_Khoan_2"]),
    ("quan_he_hon_nhan_phat_sinh_tu_dang_ky", "Quan hệ hôn nhân phát sinh kể từ thời điểm đăng ký kết hôn", "TinhTrangHonNhan", ["Luat_HNGD_2014_Dieu_14_Khoan_2"]),
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
    ("ChuThe", "nam_nu_chung_song_khong_dang_ky", "THUC_HIEN", "HanhVi", "chung_song_nhu_vo_chong_khong_dang_ky", {}),
    ("HanhVi", "chung_song_nhu_vo_chong_khong_dang_ky", "AP_DUNG_KHI", "DieuKien", "du_dieu_kien_ket_hon", {}),
    ("HanhVi", "chung_song_nhu_vo_chong_khong_dang_ky", "AP_DUNG_KHI", "DieuKien", "khong_dang_ky_ket_hon", {}),
    ("HanhVi", "chung_song_nhu_vo_chong_khong_dang_ky", "BI_CAM_KHI", "DieuKien", "mot_ben_dang_co_vo_hoac_chong", {}),
    ("DieuKien", "mot_ben_dang_co_vo_hoac_chong", "LIEN_QUAN", "HanhVi", "chung_song_voi_nguoi_dang_co_vo_chong", {}),
    ("HanhVi", "chung_song_nhu_vo_chong_khong_dang_ky", "DAN_TOI", "HauQua", "khong_phat_sinh_quyen_nghia_vu_vo_chong", {}),
    ("HanhVi", "chung_song_nhu_vo_chong_khong_dang_ky", "DAN_TOI", "HauQua", "quyen_nghia_vu_voi_con_giai_quyet_theo_quy_dinh_cha_me_con", {}),
    ("HanhVi", "chung_song_nhu_vo_chong_khong_dang_ky", "DAN_TOI", "HauQua", "tai_san_nghia_vu_hop_dong_giai_quyet_theo_dieu_16", {}),
    ("HauQua", "khong_phat_sinh_quyen_nghia_vu_vo_chong", "XAC_LAP", "TinhTrangHonNhan", "chua_phat_sinh_quan_he_hon_nhan", {}),
    ("HanhVi", "dang_ky_ket_hon_sau_thoi_gian_chung_song", "DAN_TOI", "HauQua", "quan_he_hon_nhan_xac_lap_tu_thoi_diem_dang_ky", {}),
    ("HauQua", "quan_he_hon_nhan_xac_lap_tu_thoi_diem_dang_ky", "XAC_LAP", "TinhTrangHonNhan", "quan_he_hon_nhan_phat_sinh_tu_dang_ky", {}),
    ("HauQua", "thoi_gian_chung_song_khong_tu_xac_lap_hon_nhan", "XAC_LAP", "TinhTrangHonNhan", "chua_phat_sinh_quan_he_hon_nhan", {}),
    ("ChuThe", "cha_me_khong_dang_ky_ket_hon", "CO_QUYEN", "Quyen", "quyen_cua_cha_me_va_con_theo_quy_dinh_chung", {}),
    ("ChuThe", "cha_me_khong_dang_ky_ket_hon", "CO_NGHIA_VU", "NghiaVu", "nghia_vu_cua_cha_me_va_con_theo_quy_dinh_chung", {}),
    ("ChuThe", "con_cua_nam_nu_chung_song", "CO_QUYEN", "Quyen", "quyen_cua_cha_me_va_con_theo_quy_dinh_chung", {}),
    ("ChuThe", "con_cua_nam_nu_chung_song", "CO_NGHIA_VU", "NghiaVu", "nghia_vu_cua_cha_me_va_con_theo_quy_dinh_chung", {}),
    ("HauQua", "quyen_nghia_vu_voi_con_giai_quyet_theo_quy_dinh_cha_me_con", "LIEN_QUAN", "Quyen", "quyen_cua_cha_me_va_con_theo_quy_dinh_chung", {}),
    ("HauQua", "quyen_nghia_vu_voi_con_giai_quyet_theo_quy_dinh_cha_me_con", "LIEN_QUAN", "NghiaVu", "nghia_vu_cua_cha_me_va_con_theo_quy_dinh_chung", {}),
    ("HanhVi", "giai_quyet_quan_he_tai_san", "UU_TIEN_AP_DUNG", "ThoaThuan", "thoa_thuan_tai_san_nghia_vu_hop_dong", {}),
    ("HanhVi", "giai_quyet_nghia_vu_giua_cac_ben", "UU_TIEN_AP_DUNG", "ThoaThuan", "thoa_thuan_tai_san_nghia_vu_hop_dong", {}),
    ("HanhVi", "giai_quyet_hop_dong_giua_cac_ben", "UU_TIEN_AP_DUNG", "ThoaThuan", "thoa_thuan_tai_san_nghia_vu_hop_dong", {}),
    ("ThoaThuan", "thoa_thuan_tai_san_nghia_vu_hop_dong", "AP_DUNG_KHI", "DieuKien", "co_thoa_thuan_giua_cac_ben", {}),
    ("ThoaThuan", "thoa_thuan_tai_san_nghia_vu_hop_dong", "DAN_TOI", "HauQua", "ap_dung_thoa_thuan_giua_cac_ben", {}),
    ("DieuKien", "khong_co_thoa_thuan_giua_cac_ben", "DAN_TOI", "HauQua", "ap_dung_bo_luat_dan_su_va_phap_luat_lien_quan", {}),
    ("HanhVi", "giai_quyet_quan_he_tai_san", "PHAI_BAO_DAM", "HauQua", "bao_dam_quyen_loi_hop_phap_cua_phu_nu_va_con", {}),
    ("ChuThe", "phu_nu_trong_quan_he_chung_song", "LIEN_QUAN", "HauQua", "bao_dam_quyen_loi_hop_phap_cua_phu_nu_va_con", {}),
    ("ChuThe", "con_cua_nam_nu_chung_song", "LIEN_QUAN", "HauQua", "bao_dam_quyen_loi_hop_phap_cua_phu_nu_va_con", {}),
    ("HanhVi", "thuc_hien_cong_viec_noi_tro_duy_tri_doi_song_chung", "DUOC_COI_NHU", "HauQua", "cong_viec_noi_tro_duoc_coi_nhu_lao_dong_co_thu_nhap", {}),
    ("HanhVi", "giai_quyet_nghia_vu_giua_cac_ben", "LIEN_QUAN", "NghiaVu", "nghia_vu_tai_san_giua_cac_ben_chung_song", {}),
    ("HauQua", "tai_san_nghia_vu_hop_dong_giai_quyet_theo_dieu_16", "LIEN_QUAN", "HanhVi", "giai_quyet_quan_he_tai_san", {}),
    ("HauQua", "tai_san_nghia_vu_hop_dong_giai_quyet_theo_dieu_16", "LIEN_QUAN", "HanhVi", "giai_quyet_nghia_vu_giua_cac_ben", {}),
    ("HauQua", "tai_san_nghia_vu_hop_dong_giai_quyet_theo_dieu_16", "LIEN_QUAN", "HanhVi", "giai_quyet_hop_dong_giua_cac_ben", {}),
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
