"""Template — nghĩa vụ và quyền của cha mẹ (Đ69)."""
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

_ROUTER_FIELDS = ("nhom_nghia_vu_cha_me",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_69"]

_NHOM_TO_LEAF: dict[str, list[tuple[str, str]]] = {
    "thuong_yeu_ton_trong_giao_duc": [("NghiaVu", "thuong_yeu_ton_trong_y_kien_cham_lo_hoc_tap_giao_duc_con")],
    "trong_nom_nuoi_duong_cham_soc_bao_ve": [
        ("NghiaVu", "trong_nom_nuoi_duong_cham_soc_bao_ve_quyen_loi_con"),
    ],
    "giam_ho_dai_dien": [("NghiaVu", "giam_ho_hoac_dai_dien_cho_con")],
    "khong_phan_biet_doi_xu": [("NghiaVu", "khong_phan_biet_doi_xu_voi_con")],
    "khong_lam_dung_suc_lao_dong": [("NghiaVu", "khong_lam_dung_suc_lao_dong_cua_con")],
    "khong_xui_giuc_ep_buoc_trai_phap_luat": [
        ("NghiaVu", "khong_xui_giuc_ep_buoc_con_lam_viec_trai_phap_luat_dao_duc")
    ],
    "cac_hanh_vi_bi_cam_khoan_4": [
        ("NghiaVu", "khong_phan_biet_doi_xu_voi_con"),
        ("NghiaVu", "khong_lam_dung_suc_lao_dong_cua_con"),
        ("NghiaVu", "khong_xui_giuc_ep_buoc_con_lam_viec_trai_phap_luat_dao_duc"),
    ],
}


class NghiaVuQuyenCuaChaMeParams(BaseModel):
    nhom_nghia_vu_cha_me: Literal[
        "thuong_yeu_ton_trong_giao_duc",
        "trong_nom_nuoi_duong_cham_soc_bao_ve",
        "giam_ho_dai_dien",
        "khong_phan_biet_doi_xu",
        "khong_lam_dung_suc_lao_dong",
        "khong_xui_giuc_ep_buoc_trai_phap_luat",
        "cac_hanh_vi_bi_cam_khoan_4",
        "tat_ca",
        "khong_ro",
    ] = Field(description="Map hành vi cha mẹ theo khoản 1-4 Điều 69.")
    tinh_trang_cua_con: Literal[
        "chua_thanh_nien",
        "thanh_nien_mat_nang_luc_hanh_vi",
        "thanh_nien_khong_co_kha_nang_tu_nuoi",
        "khong_ro",
    ] = Field(description="con nhỏ/chưa thành niên -> chua_thanh_nien.")
    boi_canh_gia_dinh: Literal[
        "dang_chung_song",
        "ly_than",
        "ly_hon",
        "khong_ro",
    ] = Field(description="Giữ bối cảnh; ly thân/ly hôn không tự chuyển topic.")


def _leaf_ids_for_nhom(nhom: str) -> list[str]:
    if nhom in ("tat_ca", "khong_ro"):
        return []
    pairs = _NHOM_TO_LEAF.get(nhom, [])
    return [sid for _, sid in pairs]


_SEED_BODY = f"""
WITH $nhom AS nhom, $tt_con AS tt_con, $leaf_ids AS leaf_ids,
     $seed_chu_the AS seed_chu_the, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (anchor:QuyDinh:{TOPIC_LABEL} {{
  id: 'nghia_vu_quyen_cua_cha_me', topic: '{TOPIC}'
}})
WHERE nhom IN ['tat_ca', 'khong_ro']

OPTIONAL MATCH (leaf:NghiaVu:{TOPIC_LABEL})
WHERE leaf.topic = '{TOPIC}' AND leaf.id IN leaf_ids

OPTIONAL MATCH (ct1:ChuThe:{TOPIC_LABEL} {{
  id: 'con_chua_thanh_nien', topic: '{TOPIC}'
}})
WHERE seed_chu_the = 'con_chua_thanh_nien'

OPTIONAL MATCH (ct2:ChuThe:{TOPIC_LABEL} {{
  id: 'con_can_duoc_cham_soc_dac_biet', topic: '{TOPIC}'
}})
WHERE seed_chu_the = 'con_can_duoc_cham_soc_dac_biet'

WITH wl, nhom,
  collect(DISTINCT anchor) + collect(DISTINCT leaf)
    + collect(DISTINCT ct1) + collect(DISTINCT ct2)
    AS seed_nodes,
  [x IN collect(DISTINCT leaf) + collect(DISTINCT ct1) + collect(DISTINCT ct2)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: NghiaVuQuyenCuaChaMeParams) -> dict[str, Any]:
    nhom = params.nhom_nghia_vu_cha_me
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    tt = params.tinh_trang_cua_con
    seed_chu_the = ""
    if nhom == "trong_nom_nuoi_duong_cham_soc_bao_ve":
        if tt == "chua_thanh_nien":
            seed_chu_the = "con_chua_thanh_nien"
        elif tt in ("thanh_nien_mat_nang_luc_hanh_vi", "thanh_nien_khong_co_kha_nang_tu_nuoi"):
            seed_chu_the = "con_can_duoc_cham_soc_dac_biet"
    return {
        "nhom": nhom,
        "tt_con": tt,
        "leaf_ids": _leaf_ids_for_nhom(nhom),
        "seed_chu_the": seed_chu_the,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


nghia_vu_quyen_cua_cha_me = CypherTemplate(
    name="nghia_vu_quyen_cua_cha_me",
    description=(
        "Trả lời Điều 69 về thương yêu, giáo dục, trông nom, nuôi dưỡng, bảo vệ, giám hộ/đại diện "
        "và các hành vi cha mẹ không được làm với con. "
        "Dùng khi hỏi quyền trông nom/nuôi dưỡng (kể cả bối cảnh ly thân), toàn bộ Điều 69, "
        "hoặc phân biệt đối xử/lạm dụng lao động/xúi giục làm trái pháp luật tại khoản 4."
    ),
    params_schema=NghiaVuQuyenCuaChaMeParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
