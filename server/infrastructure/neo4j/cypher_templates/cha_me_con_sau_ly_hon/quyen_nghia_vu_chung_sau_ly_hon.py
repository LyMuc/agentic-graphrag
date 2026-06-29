"""Template — quyền và nghĩa vụ chung của cha mẹ đối với con sau ly hôn (Đ81 K1)."""
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

_ROUTER_FIELDS = ("pham_vi",)
_TONG_QUAT_WHITELIST = [
    "Luat_HNGD_2014_Dieu_81",
    "Luat_HNGD_2014_Dieu_82",
    "Luat_HNGD_2014_Dieu_83",
]

_TINH_TRANG_TO_DK = {
    "chua_thanh_nien": "con_chua_thanh_nien",
    "thanh_nien_mat_nang_luc_hanh_vi": "con_thanh_nien_mat_nang_luc_hanh_vi_dan_su",
    "thanh_nien_khong_kha_nang_lao_dong_khong_tai_san": (
        "con_thanh_nien_khong_kha_nang_lao_dong_khong_tai_san"
    ),
}


class QuyenNghiaVuChungSauLyHonParams(BaseModel):
    pham_vi: Literal[
        "trong_nom_cham_soc_nuoi_duong_giao_duc",
        "quyen_nghia_vu_cua_ca_hai",
        "tinh_trang_quyen_lam_cha_me",
        "tong_quat",
    ] = Field(
        description=(
            "Phạm vi câu hỏi. Map: trông nom/chăm sóc/nuôi dưỡng/giáo dục "
            "→ trong_nom_cham_soc_nuoi_duong_giao_duc; cha mẹ còn quyền nghĩa vụ gì "
            "→ quyen_nghia_vu_cua_ca_hai; tước quyền làm cha/mẹ, còn là cha mẹ không "
            "→ tinh_trang_quyen_lam_cha_me; câu rộng → tong_quat."
        )
    )
    tinh_trang_con: Literal[
        "chua_thanh_nien",
        "thanh_nien_mat_nang_luc_hanh_vi",
        "thanh_nien_khong_kha_nang_lao_dong_khong_tai_san",
        "khong_ro",
    ] = Field(
        description=(
            "Tình trạng con. Map: trẻ em/con nhỏ → chua_thanh_nien; "
            "mất năng lực hành vi → thanh_nien_mat_nang_luc_hanh_vi; "
            "không lao động/không tài sản tự nuôi → thanh_nien_khong_kha_nang_...; "
            "không nêu → khong_ro."
        )
    )


_SEED_BODY = f"""
WITH $pham_vi AS pv, $tinh_trang_con AS tt, $dk_id AS dk_id, $whitelist_dieu_ids AS wl

MATCH (cm:ChuThe:{TOPIC_LABEL} {{id: 'cha_me_sau_ly_hon', topic: '{TOPIC}'}})
MATCH (cm)-[:CO_NGHIA_VU]->(nv:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_trong_nom_cham_soc_nuoi_duong_giao_duc_con', topic: '{TOPIC}'
}})

OPTIONAL MATCH (nv)-[:AP_DUNG_KHI]->(dk:DieuKien:{TOPIC_LABEL})
WHERE tt <> 'khong_ro' AND dk.id = dk_id

OPTIONAL MATCH (nt:ChuThe:{TOPIC_LABEL} {{id: 'nguoi_truc_tiep_nuoi_con', topic: '{TOPIC}'}})
WHERE pv IN ['tinh_trang_quyen_lam_cha_me', 'quyen_nghia_vu_cua_ca_hai', 'tong_quat']
OPTIONAL MATCH (nk:ChuThe:{TOPIC_LABEL} {{id: 'nguoi_khong_truc_tiep_nuoi_con', topic: '{TOPIC}'}})
WHERE pv IN ['tinh_trang_quyen_lam_cha_me', 'quyen_nghia_vu_cua_ca_hai', 'tong_quat']
OPTIONAL MATCH (nk)-[:CO_NGHIA_VU|CO_QUYEN]->(sub)
WHERE pv IN ['tinh_trang_quyen_lam_cha_me', 'quyen_nghia_vu_cua_ca_hai', 'tong_quat']
OPTIONAL MATCH (nt)-[:CO_NGHIA_VU|CO_QUYEN]->(sub2)
WHERE pv IN ['tinh_trang_quyen_lam_cha_me', 'quyen_nghia_vu_cua_ca_hai', 'tong_quat']

WITH wl, pv, tt,
  collect(DISTINCT cm) + collect(DISTINCT nv) + collect(DISTINCT dk)
    + collect(DISTINCT nt) + collect(DISTINCT nk)
    + collect(DISTINCT sub) + collect(DISTINCT sub2) AS seed_nodes,
  CASE
    WHEN tt <> 'khong_ro' AND size([x IN collect(DISTINCT dk) WHERE x IS NOT NULL]) > 0 THEN
      [x IN collect(DISTINCT dk) WHERE x IS NOT NULL]
    WHEN pv = 'tinh_trang_quyen_lam_cha_me' THEN
      [x IN collect(DISTINCT nt) + collect(DISTINCT nk) + collect(DISTINCT sub)
           + collect(DISTINCT sub2) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT cm) + collect(DISTINCT nv) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: QuyenNghiaVuChungSauLyHonParams) -> dict[str, Any]:
    dk_id = _TINH_TRANG_TO_DK.get(params.tinh_trang_con, "")
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "pham_vi": params.pham_vi,
        "tinh_trang_con": params.tinh_trang_con,
        "dk_id": dk_id,
        "whitelist_dieu_ids": _TONG_QUAT_WHITELIST if use_wl else [],
    }


quyen_nghia_vu_chung_sau_ly_hon = CypherTemplate(
    name="quyen_nghia_vu_chung_sau_ly_hon",
    description=(
        "Quyền và nghĩa vụ chung của cả cha và mẹ đối với con sau ly hôn, đặc biệt "
        "nghĩa vụ trông nom, chăm sóc, nuôi dưỡng, giáo dục và việc ly hôn không tự "
        "động xóa tư cách làm cha, mẹ. Ví dụ: Sau khi ly hôn có được tước quyền làm cha "
        "của chồng cũ không? Việc trông nom, chăm sóc, nuôi dưỡng, giáo dục con sau ly hôn."
    ),
    params_schema=QuyenNghiaVuChungSauLyHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
