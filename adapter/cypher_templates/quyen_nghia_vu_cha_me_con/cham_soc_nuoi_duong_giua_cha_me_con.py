"""Template — chăm sóc, nuôi dưỡng hai chiều giữa cha mẹ và con (Đ71)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("chieu_cham_soc_nuoi_duong",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_71"]


class ChamSocNuoiDuongGiuaChaMeConParams(BaseModel):
    chieu_cham_soc_nuoi_duong: Literal[
        "cha_me_doi_voi_con",
        "con_doi_voi_cha_me",
        "cac_con_doi_voi_cha_me",
        "tong_quat",
    ] = Field(description="cha mẹ chăm con / con chăm cha mẹ / các con cùng chăm.")
    hoan_canh_can_cham_soc: Literal[
        "con_chua_thanh_nien",
        "con_mat_nang_luc_hanh_vi",
        "con_khong_co_kha_nang_tu_nuoi",
        "cha_me_gia_yeu",
        "cha_me_om_dau",
        "cha_me_khuyet_tat",
        "cha_me_mat_nang_luc_hanh_vi",
        "khong_ro",
    ] = Field(description="Map hoàn cảnh được nêu trong câu hỏi.")
    so_luong_con: Literal["mot_con", "nhieu_con", "khong_ro"] = Field(
        description="gia đình có nhiều con -> nhieu_con."
    )


_SEED_BODY = f"""
WITH $chieu AS chieu, $so_con AS so_con, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (leaf_cm:NghiaVu:{TOPIC_LABEL} {{
  id: 'cha_me_ngang_nhau_cung_cham_soc_nuoi_duong_con', topic: '{TOPIC}'
}})
WHERE chieu IN ['cha_me_doi_voi_con', 'tong_quat']

OPTIONAL MATCH (leaf_con:NghiaVu:{TOPIC_LABEL} {{
  id: 'con_cham_soc_nuoi_duong_cha_me', topic: '{TOPIC}'
}})
WHERE chieu IN ['con_doi_voi_cha_me', 'tong_quat']

OPTIONAL MATCH (leaf_cac:NghiaVu:{TOPIC_LABEL} {{
  id: 'cac_con_cung_nhau_cham_soc_nuoi_duong_cha_me', topic: '{TOPIC}'
}})
WHERE chieu = 'cac_con_doi_voi_cha_me' OR so_con = 'nhieu_con'

WITH wl, chieu,
  collect(DISTINCT leaf_cm) + collect(DISTINCT leaf_con) + collect(DISTINCT leaf_cac)
    AS seed_nodes,
  [x IN collect(DISTINCT leaf_cm) + collect(DISTINCT leaf_con) + collect(DISTINCT leaf_cac)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: ChamSocNuoiDuongGiuaChaMeConParams) -> dict[str, Any]:
    chieu = params.chieu_cham_soc_nuoi_duong
    if params.so_luong_con == "nhieu_con" and chieu == "con_doi_voi_cha_me":
        chieu = "cac_con_doi_voi_cha_me"
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "chieu": chieu,
        "so_con": params.so_luong_con,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


cham_soc_nuoi_duong_giua_cha_me_con = CypherTemplate(
    name="cham_soc_nuoi_duong_giua_cha_me_con",
    description=(
        "Trả lời Điều 71 theo hai chiều: cha mẹ ngang nhau cùng chăm sóc, nuôi dưỡng con; "
        "con chăm sóc, nuôi dưỡng cha mẹ khi già yếu, ốm đau, khuyết tật hoặc mất năng lực. "
        "Dùng khi hỏi cha mẹ ngang nhau chăm con chưa thành niên, con chăm cha mẹ già yếu, "
        "hoặc các con cùng nhau nuôi dưỡng bố/mẹ."
    ),
    params_schema=ChamSocNuoiDuongGiuaChaMeConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
