"""Template — giáo dục con (Đ72)."""
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

_ROUTER_FIELDS = ("khia_canh_giao_duc",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_72"]

_KHIA_TO_LEAF: dict[str, list[tuple[str, str]]] = {
    "giao_duc_tao_dieu_kien_hoc_tap": [
        ("NghiaVu", "cha_me_giao_duc_tao_dieu_kien_hoc_tap_cho_con"),
        ("NghiaVu", "tao_moi_truong_gia_dinh_lam_guong_phoi_hop_giao_duc"),
    ],
    "moi_truong_lam_guong_phoi_hop": [
        ("NghiaVu", "tao_moi_truong_gia_dinh_lam_guong_phoi_hop_giao_duc"),
    ],
    "huong_dan_ton_trong_chon_nghe": [
        ("NghiaVu", "huong_dan_va_ton_trong_quyen_chon_nghe_cua_con"),
    ],
    "de_nghi_ho_tro_khi_kho_khan": [
        ("Quyen", "de_nghi_co_quan_to_chuc_ho_tro_giao_duc_con"),
    ],
}


class GiaoDucConParams(BaseModel):
    khia_canh_giao_duc: Literal[
        "giao_duc_tao_dieu_kien_hoc_tap",
        "moi_truong_lam_guong_phoi_hop",
        "huong_dan_ton_trong_chon_nghe",
        "de_nghi_ho_tro_khi_kho_khan",
        "tong_quat",
    ] = Field(description="Map học tập/giáo dục, ép chọn nghề, nhờ cơ quan hỗ trợ.")
    muc_do_kho_khan: Literal[
        "co_the_tu_giai_quyet",
        "khong_the_tu_giai_quyet",
        "khong_ro",
    ] = Field(description="không tự giáo dục -> khong_the_tu_giai_quyet.")


def _leaf_ids(khia: str) -> list[str]:
    if khia == "tong_quat":
        return []
    return [sid for _, sid in _KHIA_TO_LEAF.get(khia, [])]


_SEED_BODY = f"""
WITH $khia AS khia, $leaf_ids AS leaf_ids, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (leaf)
WHERE leaf.topic = '{TOPIC}' AND '{TOPIC_LABEL}' IN labels(leaf)
  AND leaf.id IN leaf_ids

WITH wl, khia,
  collect(DISTINCT leaf) AS seed_nodes,
  [x IN collect(DISTINCT leaf) WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: GiaoDucConParams) -> dict[str, Any]:
    khia = params.khia_canh_giao_duc
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "khia": khia,
        "leaf_ids": _leaf_ids(khia),
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


giao_duc_con = CypherTemplate(
    name="giao_duc_con",
    description=(
        "Trả lời Điều 72 về giáo dục, tạo điều kiện học tập, môi trường gia đình, "
        "hướng dẫn nghề nhưng tôn trọng lựa chọn của con và quyền nhờ cơ quan/tổ chức hỗ trợ. "
        "Dùng khi hỏi nghĩa vụ giáo dục chung, cha mẹ có được ép chọn ngành nghề thay con, "
        "hoặc nhờ cơ quan hỗ trợ khi không thể tự giáo dục."
    ),
    params_schema=GiaoDucConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
