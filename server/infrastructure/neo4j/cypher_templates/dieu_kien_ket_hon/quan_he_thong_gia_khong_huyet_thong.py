"""Template — quan hệ thông gia không tự phát sinh huyết thống (Đ3, Đ5, Đ8)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_thong_gia",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_5", "Luat_HNGD_2014_Dieu_8"]

_RELATION_IDS: dict[str, str] = {
    "em_trai_chong_em_gai_vo": "em_trai_chong_voi_em_gai_vo",
    "em_chong_anh_vo": "em_chong_voi_anh_vo",
}


class QuanHeThongGiaKhongHuyetThongParams(BaseModel):
    loai_quan_he_thong_gia: Literal[
        "em_trai_chong_em_gai_vo",
        "em_chong_anh_vo",
        "thong_gia_khac",
        "khong_ro",
    ] = Field(
        description=(
            "em trai chồng-em gái vợ -> em_trai_chong_em_gai_vo; "
            "em chồng-anh vợ -> em_chong_anh_vo; thông gia chung -> thong_gia_khac."
        )
    )
    co_quan_he_huyet_thong_thuc_te: Literal["co", "khong", "khong_ro"] = Field(
        description=(
            "không cùng máu/chỉ là thông gia -> khong; "
            "có chung ông bà/cùng cha mẹ -> co; không nêu -> khong_ro."
        )
    )
    khia_canh_thong_gia: Literal[
        "co_bi_cam",
        "co_duoc_ket_hon",
        "dieu_kien_can_dap_ung",
        "kiem_tra_ba_doi",
        "tong_quat",
    ] = Field(
        description=(
            "có cấm/vi phạm -> co_bi_cam; "
            "điều kiện gì -> dieu_kien_can_dap_ung; ba đời -> kiem_tra_ba_doi."
        )
    )


_SEED_BODY = f"""
WITH $lqh AS lqh, $lrh AS lrh, $kc AS kc, $co_ht AS co_ht,
     $seed_dk AS seed_dk, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (qh:QuanHe:{TOPIC_LABEL} {{id: lqh, topic: '{TOPIC}'}})
WHERE lqh <> '' AND lrh IN ['em_trai_chong_em_gai_vo', 'em_chong_anh_vo']

MATCH (qh_nhom:QuanHe:{TOPIC_LABEL} {{
  id: 'quan_he_thong_gia_khong_tu_phat_sinh_huyet_thong', topic: '{TOPIC}'
}})

OPTIONAL MATCH (qh_ba:QuanHe:{TOPIC_LABEL} {{
  id: 'co_ho_trong_pham_vi_ba_doi', topic: '{TOPIC}'
}})
WHERE co_ht = 'co' OR kc = 'kiem_tra_ba_doi'

OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{id: 'du_dieu_kien_ket_hon', topic: '{TOPIC}'}})
WHERE seed_dk = true
OPTIONAL MATCH (dk)-[:BAO_GOM]->(dk_leaf:DieuKien:{TOPIC_LABEL})
WHERE dk IS NOT NULL AND seed_dk = true AND dk_leaf.topic = '{TOPIC}'

WITH wl, kc,
  [x IN collect(DISTINCT qh) + collect(DISTINCT qh_nhom) + collect(DISTINCT qh_ba)
       + collect(DISTINCT dk) + collect(DISTINCT dk_leaf)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'dieu_kien_can_dap_ung' THEN
      [x IN collect(DISTINCT qh) + collect(DISTINCT qh_nhom)
           + collect(DISTINCT dk) + collect(DISTINCT dk_leaf)
       WHERE x IS NOT NULL]
    WHEN 'kiem_tra_ba_doi' THEN
      [x IN collect(DISTINCT qh) + collect(DISTINCT qh_nhom) + collect(DISTINCT qh_ba)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT qh) + collect(DISTINCT qh_nhom) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: QuanHeThongGiaKhongHuyetThongParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    lrh = params.loai_quan_he_thong_gia
    lqh = _RELATION_IDS.get(lrh, "")
    seed_dk = params.khia_canh_thong_gia in (
        "dieu_kien_can_dap_ung",
        "co_duoc_ket_hon",
        "tong_quat",
    )
    return {
        "lqh": lqh,
        "lrh": lrh,
        "kc": params.khia_canh_thong_gia,
        "co_ht": params.co_quan_he_huyet_thong_thuc_te,
        "seed_dk": seed_dk,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


quan_he_thong_gia_khong_huyet_thong = CypherTemplate(
    name="quan_he_thong_gia_khong_huyet_thong",
    description=(
        "Đánh giá các cặp thông gia như em trai chồng-em gái vợ hoặc em chồng-anh vợ, "
        "vốn không tự phát sinh quan hệ huyết thống chỉ từ hôn nhân của người thân. "
        "Template đối chiếu Điều 3 khoản 17/18 và danh sách điểm d khoản 2 Điều 5, "
        "vẫn seed đầy đủ Điều 8 khi hỏi điều kiện cần đáp ứng. "
        "Ví dụ: Em trai chồng với em gái vợ có vi phạm ba đời không?; "
        "Em chồng và anh vợ có bị cấm kết hôn không?"
    ),
    params_schema=QuanHeThongGiaKhongHuyetThongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
