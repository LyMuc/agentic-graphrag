"""Template — từ chối đăng ký kết hôn (NĐ123 Đ33)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_tu_choi",)
_DIEU_33_WHITELIST = ["NghiDinh_123_2015_ND_CP_Dieu_33"]


class TuChoiDangKyKetHonParams(BaseModel):
    cap_dang_ky: Literal["cap_xa", "cap_huyen", "khong_ro"] = Field(
        description="UBND huyện/quận -> cap_huyen; xã/phường -> cap_xa."
    )
    ly_do_tu_choi: Literal[
        "vi_pham_dieu_cam", "khong_du_dieu_kien", "ca_hai", "khong_ro"
    ] = Field(
        description=(
            "Thuộc điều cấm -> vi_pham_dieu_cam; không đủ điều kiện -> khong_du_dieu_kien; "
            "hỏi liệt kê chung -> ca_hai."
        )
    )
    khia_canh_tu_choi: Literal[
        "truong_hop_bi_tu_choi", "thong_bao_ly_do", "tong_quat"
    ] = Field(
        description=(
            "Trường hợp nào bị từ chối -> truong_hop_bi_tu_choi; "
            "phải trả lời bằng văn bản/nêu lý do -> thong_bao_ly_do."
        )
    )


_SEED_BODY = f"""
WITH $cap AS cap, $ly_do AS ly_do, $kc AS kc, $whitelist_dieu_ids AS wl

MATCH (hv:HanhVi:{TOPIC_LABEL} {{id: 'tu_choi_dang_ky_ket_hon', topic: '{TOPIC}'}})
OPTIONAL MATCH (hv)-[:DAN_TOI]->(hq:HauQua:{TOPIC_LABEL} {{id: 'dang_ky_bi_tu_choi', topic: '{TOPIC}'}})

OPTIONAL MATCH (dk_vi:DieuKien:{TOPIC_LABEL} {{id: 'vi_pham_dieu_cam_hoac_khong_du_dieu_kien', topic: '{TOPIC}'}})
WHERE ly_do IN ['vi_pham_dieu_cam', 'ca_hai', 'khong_ro', 'tong_quat']
OPTIONAL MATCH (dk_cam:DieuKien:{TOPIC_LABEL} {{id: 'khong_thuoc_truong_hop_cam_ket_hon', topic: '{TOPIC}'}})
WHERE ly_do IN ['vi_pham_dieu_cam', 'ca_hai', 'khong_ro', 'tong_quat']

OPTIONAL MATCH (dk_du:DieuKien:{TOPIC_LABEL} {{id: 'du_dieu_kien_ket_hon', topic: '{TOPIC}'}})
WHERE ly_do IN ['khong_du_dieu_kien', 'ca_hai', 'khong_ro', 'tong_quat']
OPTIONAL MATCH (dk_du)-[:LIEN_QUAN]->(dk_leaf:DieuKien:{TOPIC_LABEL})
WHERE dk_du IS NOT NULL AND dk_leaf.topic = '{TOPIC}'

OPTIONAL MATCH (pt:ChuThe:{TOPIC_LABEL} {{id: 'phong_tu_phap', topic: '{TOPIC}'}})
WHERE cap IN ['cap_huyen', 'khong_ro'] OR kc = 'thong_bao_ly_do'
OPTIONAL MATCH (pt)-[:CO_NGHIA_VU]->(nv:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_thong_bao_tu_choi_bang_van_ban', topic: '{TOPIC}'}})
WHERE pt IS NOT NULL

WITH wl, kc, ly_do,
  [x IN collect(DISTINCT hv) + collect(DISTINCT hq) + collect(DISTINCT dk_vi)
       + collect(DISTINCT dk_cam) + collect(DISTINCT dk_du) + collect(DISTINCT dk_leaf)
       + collect(DISTINCT pt) + collect(DISTINCT nv)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'thong_bao_ly_do' THEN
      [x IN collect(DISTINCT nv) + collect(DISTINCT pt) WHERE x IS NOT NULL]
    WHEN 'truong_hop_bi_tu_choi' THEN
      [x IN collect(DISTINCT hv) + collect(DISTINCT hq) + collect(DISTINCT dk_vi)
           + collect(DISTINCT dk_cam) + collect(DISTINCT dk_du)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hv) + collect(DISTINCT hq) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: TuChoiDangKyKetHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "cap": params.cap_dang_ky,
        "ly_do": params.ly_do_tu_choi,
        "kc": params.khia_canh_tu_choi,
        "whitelist_dieu_ids": _DIEU_33_WHITELIST if use_wl else [],
    }


tu_choi_dang_ky_ket_hon = CypherTemplate(
    name="tu_choi_dang_ky_ket_hon",
    description=(
        "Xác định khi nào yêu cầu đăng ký bị từ chối và nghĩa vụ thông báo lý do bằng văn bản "
        "ở cấp huyện (NĐ123 Đ33 cùng Đ8 HNGD). "
        "Ví dụ: Trường hợp nào bị từ chối đăng ký kết hôn?; "
        "Từ chối tại UBND cấp huyện có phải nêu lý do không?"
    ),
    params_schema=TuChoiDangKyKetHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
