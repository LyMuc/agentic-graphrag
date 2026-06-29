"""Template — quyền, nghĩa vụ người không trực tiếp nuôi con (Đ82-83)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.cha_me_con_sau_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_nguoi_khong_truc_tiep",)
_TONG_QUAT_WHITELIST = ["Luat_HNGD_2014_Dieu_82", "Luat_HNGD_2014_Dieu_83"]
_DIEU_82_K2 = "Luat_HNGD_2014_Dieu_82_Khoan_2"


class QuyenNghiaVuNguoiKhongTrucTiepNuoiParams(BaseModel):
    khia_canh_nguoi_khong_truc_tiep: Literal[
        "ton_trong_quyen_song_chung",
        "cap_duong_o_muc_nguyen_tac",
        "tham_nom",
        "quyen_nghia_vu_day_du",
        "tong_quat",
    ] = Field(
        description=(
            "Khía cạnh. Map: tôn trọng quyền con sống với người nuôi "
            "→ ton_trong_quyen_song_chung; cấp dưỡng nguyên tắc → cap_duong_o_muc_nguyen_tac; "
            "thăm nom → tham_nom; toàn bộ quyền nghĩa vụ → quyen_nghia_vu_day_du."
        )
    )
    nguoi_khong_truc_tiep_nuoi: Literal["cha", "me", "khong_ro"] = Field(
        description="Cha/bố/chồng cũ → cha; mẹ/vợ cũ → me."
    )
    tinh_trang_cap_duong: Literal[
        "co_thuc_hien",
        "khong_thuc_hien",
        "dang_tranh_chap",
        "khong_ro",
    ] = Field(
        description=(
            "Tình trạng cấp dưỡng (fact phụ). Không dùng để seed Đ107-120."
        )
    )
    co_can_tro_tham_nom: Literal["co", "khong", "khong_ro"] = Field(
        description="Có ngăn/cấm/không cho gặp con → co."
    )


_SEED_BODY = f"""
WITH $khia_canh_nguoi_khong_truc_tiep AS kc, $co_can_tro_tham_nom AS cct,
     $whitelist_dieu_ids AS wl

MATCH (ct:ChuThe:{TOPIC_LABEL} {{id: 'nguoi_khong_truc_tiep_nuoi_con', topic: '{TOPIC}'}})
MATCH (ct)-[:CO_NGHIA_VU]->(nv_grp:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_nguoi_khong_truc_tiep_nuoi_con', topic: '{TOPIC}'
}})

OPTIONAL MATCH (ct)-[:CO_NGHIA_VU]->(nv1:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_ton_trong_quyen_con_song_chung_voi_nguoi_nuoi', topic: '{TOPIC}'
}})
WHERE kc IN ['ton_trong_quyen_song_chung', 'quyen_nghia_vu_day_du', 'tong_quat']
OPTIONAL MATCH (nv1)-[:BAO_DAM]->(q1:Quyen:{TOPIC_LABEL})
WHERE kc IN ['ton_trong_quyen_song_chung', 'quyen_nghia_vu_day_du', 'tong_quat']

OPTIONAL MATCH (ct)-[:CO_NGHIA_VU]->(nv3:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_tham_nom_con', topic: '{TOPIC}'}})
WHERE kc IN ['tham_nom', 'quyen_nghia_vu_day_du', 'tong_quat']
OPTIONAL MATCH (ct)-[:CO_QUYEN]->(q3:Quyen:{TOPIC_LABEL} {{id: 'quyen_tham_nom_con_khong_bi_can_tro', topic: '{TOPIC}'}})
WHERE kc IN ['tham_nom', 'quyen_nghia_vu_day_du', 'tong_quat']
OPTIONAL MATCH (hv3:HanhVi:{TOPIC_LABEL} {{id: 'tham_nom_con_sau_ly_hon', topic: '{TOPIC}'}})
WHERE kc IN ['tham_nom', 'quyen_nghia_vu_day_du', 'tong_quat']

OPTIONAL MATCH (nv_grp)-[:LIEN_KET_CAP_DUONG]->(nv_cap:NghiaVu:CapDuong {{
  id: 'nghia_vu_cap_duong_cha_me_khong_truc_tiep_nuoi_con'
}})
WHERE kc IN ['cap_duong_o_muc_nguyen_tac', 'quyen_nghia_vu_day_du', 'tong_quat']

OPTIONAL MATCH (nt:ChuThe:{TOPIC_LABEL} {{id: 'nguoi_truc_tiep_nuoi_con', topic: '{TOPIC}'}})
WHERE cct = 'co' OR kc = 'quyen_nghia_vu_day_du'
OPTIONAL MATCH (nt)-[:CO_QUYEN]->(qy:Quyen:{TOPIC_LABEL})
WHERE cct = 'co' OR kc = 'quyen_nghia_vu_day_du'
OPTIONAL MATCH (nt)-[:CO_NGHIA_VU]->(nv83:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_khong_can_tro_tham_nom_cham_soc_con', topic: '{TOPIC}'
}})
WHERE cct = 'co'

WITH wl, kc,
  collect(DISTINCT ct) + collect(DISTINCT nv_grp) + collect(DISTINCT nv1)
    + collect(DISTINCT q1) + collect(DISTINCT nv3) + collect(DISTINCT q3)
    + collect(DISTINCT hv3) + collect(DISTINCT nv_cap)
    + collect(DISTINCT nt) + collect(DISTINCT qy) + collect(DISTINCT nv83) AS seed_nodes,
  CASE kc
    WHEN 'ton_trong_quyen_song_chung' THEN
      [x IN collect(DISTINCT nv1) + collect(DISTINCT q1) WHERE x IS NOT NULL]
    WHEN 'tham_nom' THEN
      [x IN collect(DISTINCT nv3) + collect(DISTINCT q3) + collect(DISTINCT hv3)
       WHERE x IS NOT NULL]
    WHEN 'cap_duong_o_muc_nguyen_tac' THEN
      [x IN collect(DISTINCT nv_grp) + collect(DISTINCT nv_cap) WHERE x IS NOT NULL]
    WHEN 'quyen_nghia_vu_day_du' THEN
      [x IN collect(DISTINCT nv_grp) + collect(DISTINCT nv1) + collect(DISTINCT nv3)
           + collect(DISTINCT q3) + collect(DISTINCT hv3) + collect(DISTINCT nv_cap)
           + collect(DISTINCT qy)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT nv_grp) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: QuyenNghiaVuNguoiKhongTrucTiepNuoiParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    wl = _TONG_QUAT_WHITELIST if use_wl else []
    if params.khia_canh_nguoi_khong_truc_tiep == "cap_duong_o_muc_nguyen_tac":
        wl = [_DIEU_82_K2]
    return {
        "khia_canh_nguoi_khong_truc_tiep": params.khia_canh_nguoi_khong_truc_tiep,
        "co_can_tro_tham_nom": params.co_can_tro_tham_nom,
        "whitelist_dieu_ids": wl,
    }


quyen_nghia_vu_nguoi_khong_truc_tiep_nuoi = CypherTemplate(
    name="quyen_nghia_vu_nguoi_khong_truc_tiep_nuoi",
    description=(
        "Toàn bộ hoặc từng nhóm quyền, nghĩa vụ của cha/mẹ không trực tiếp nuôi: "
        "tôn trọng quyền con sống với người nuôi, cấp dưỡng ở mức nguyên tắc Đ82 K2, "
        "và thăm nom con. Ví dụ: có bắt buộc cấp dưỡng sau ly hôn; đồng thời quyền "
        "thăm con và nghĩa vụ cấp dưỡng; toàn bộ quyền nghĩa vụ người không trực tiếp nuôi."
    ),
    params_schema=QuyenNghiaVuNguoiKhongTrucTiepNuoiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
