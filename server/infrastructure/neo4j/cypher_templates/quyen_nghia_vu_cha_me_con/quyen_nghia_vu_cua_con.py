"""Template — quyền và nghĩa vụ của con (Đ70)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_cha_me_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("nhom_quyen_nghia_vu_cua_con",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_70"]

_NHOM_TO_LEAF: dict[str, str] = {
    "duoc_thuong_yeu_hoc_tap_phat_trien": "con_duoc_thuong_yeu_ton_trong_hoc_tap_giao_duc_phat_trien",
    "hieu_thao_phung_duong_cha_me": "con_yeu_quy_kinh_trong_biet_on_hieu_thao_phung_duong_cha_me",
    "song_chung_duoc_cham_soc": "con_duoc_song_chung_trong_nom_nuoi_duong_cham_soc",
    "cong_viec_gia_dinh_phu_hop_lua_tuoi": "con_chua_thanh_nien_tham_gia_cong_viec_gia_dinh_phu_hop_lua_tuoi",
    "tu_do_nghe_nghiep_noi_cu_tru": "con_thanh_nien_tu_do_chon_nghe_noi_cu_tru_hoc_tap_hoat_dong",
    "dong_gop_khi_song_cung_cha_me": "con_song_cung_cha_me_tham_gia_cong_viec_dong_gop_thu_nhap",
    "quyen_tai_san_theo_cong_suc": "con_huong_quyen_tai_san_tuong_xung_cong_suc",
}


class QuyenNghiaVuCuaConParams(BaseModel):
    nhom_quyen_nghia_vu_cua_con: Literal[
        "duoc_thuong_yeu_hoc_tap_phat_trien",
        "hieu_thao_phung_duong_cha_me",
        "song_chung_duoc_cham_soc",
        "cong_viec_gia_dinh_phu_hop_lua_tuoi",
        "tu_do_nghe_nghiep_noi_cu_tru",
        "dong_gop_khi_song_cung_cha_me",
        "quyen_tai_san_theo_cong_suc",
        "tat_ca",
        "khong_ro",
    ] = Field(description="Map cụm câu hỏi tới khoản 1-5 Điều 70.")
    do_tuoi_nang_luc_cua_con: Literal[
        "chua_thanh_nien",
        "da_thanh_nien",
        "da_thanh_nien_mat_nang_luc_hanh_vi",
        "khong_co_kha_nang_tu_nuoi",
        "khong_ro",
    ] = Field(description="con nhỏ -> chua_thanh_nien; đã thành niên -> da_thanh_nien.")
    tinh_trang_hon_nhan_cua_cha_me: Literal[
        "co_dang_ky_ket_hon",
        "khong_dang_ky_ket_hon",
        "ngoai_hon_nhan",
        "ly_hon",
        "khong_ro",
    ] = Field(description="ngoài giá thú -> thêm leaf Điều 68 khoản 2.")


_SEED_BODY = f"""
WITH $nhom AS nhom, $leaf_id AS leaf_id, $seed_d68 AS seed_d68,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (anchor:QuyDinh:{TOPIC_LABEL} {{
  id: 'quyen_nghia_vu_cua_con', topic: '{TOPIC}'
}})
WHERE nhom IN ['tat_ca', 'khong_ro']

OPTIONAL MATCH (leaf)
WHERE leaf.id = leaf_id AND leaf.topic = '{TOPIC}'
  AND '{TOPIC_LABEL}' IN labels(leaf)

OPTIONAL MATCH (leaf_d68:Quyen:{TOPIC_LABEL} {{
  id: 'con_binh_dang_khong_phu_thuoc_hon_nhan_cha_me', topic: '{TOPIC}'
}})
WHERE seed_d68 = true

WITH wl, nhom,
  collect(DISTINCT anchor) + collect(DISTINCT leaf) + collect(DISTINCT leaf_d68)
    AS seed_nodes,
  [x IN collect(DISTINCT leaf) + collect(DISTINCT leaf_d68) WHERE x IS NOT NULL]
    AS leaf_seed_nodes
"""


def _params_builder(params: QuyenNghiaVuCuaConParams) -> dict[str, Any]:
    nhom = params.nhom_quyen_nghia_vu_cua_con
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    leaf_id = _NHOM_TO_LEAF.get(nhom, "")
    hn = params.tinh_trang_hon_nhan_cua_cha_me
    seed_d68 = hn in ("khong_dang_ky_ket_hon", "ngoai_hon_nhan")
    return {
        "nhom": nhom,
        "leaf_id": leaf_id,
        "seed_d68": seed_d68,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


quyen_nghia_vu_cua_con = CypherTemplate(
    name="quyen_nghia_vu_cua_con",
    description=(
        "Trả lời Điều 70 về quyền được yêu thương, học tập, sống chung/chăm sóc; bổn phận hiếu thảo; "
        "quyền tự do của con thành niên và quyền tài sản theo công sức. "
        "Dùng cho con ngoài giá thú, quyền sống chung/chăm sóc khi ly hôn, "
        "hoặc quyền tự do chọn nghề nghiệp và nơi cư trú của con đã thành niên."
    ),
    params_schema=QuyenNghiaVuCuaConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
