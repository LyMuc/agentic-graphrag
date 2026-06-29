"""Template — hôn nhân cùng giới: cấm hay không được thừa nhận (Đ5, Đ8 K2)."""
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

_ROUTER_FIELDS = ("khia_canh_cung_gioi",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_5", "Luat_HNGD_2014_Dieu_8"]


class HonNhanCungGioiTinhParams(BaseModel):
    gioi_tinh_hai_ben: Literal["cung_gioi", "khac_gioi", "khong_ro"] = Field(
        description=(
            "đồng giới/cùng giới/hai nam/hai nữ -> cung_gioi; "
            "nam và nữ/khác giới -> khac_gioi."
        )
    )
    khia_canh_cung_gioi: Literal[
        "co_bi_cam",
        "co_duoc_thua_nhan",
        "phan_biet_cam_va_khong_thua_nhan",
        "tong_quat",
    ] = Field(
        description=(
            "có bị cấm/hành vi cấm -> co_bi_cam; "
            "có chấp nhận/công nhận/thừa nhận -> co_duoc_thua_nhan; "
            "câu chứa cả hai -> phan_biet_cam_va_khong_thua_nhan."
        )
    )


_SEED_BODY = f"""
WITH $kc AS kc, $whitelist_dieu_ids AS wl

MATCH (qh:QuanHe:{TOPIC_LABEL} {{id: 'hon_nhan_cung_gioi_tinh', topic: '{TOPIC}'}})

OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{
  id: 'hon_nhan_cung_gioi_khong_duoc_nha_nuoc_thua_nhan', topic: '{TOPIC}'
}})
WHERE kc IN ['co_duoc_thua_nhan', 'tong_quat']

OPTIONAL MATCH (qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'phan_biet_khong_thua_nhan_va_hanh_vi_cam_hon_nhan_cung_gioi', topic: '{TOPIC}'
}})
WHERE kc IN ['co_bi_cam', 'phan_biet_cam_va_khong_thua_nhan', 'tong_quat']

WITH wl, kc,
  [x IN collect(DISTINCT qh) + collect(DISTINCT hq) + collect(DISTINCT qd)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'co_duoc_thua_nhan' THEN
      [x IN collect(DISTINCT hq) WHERE x IS NOT NULL]
    WHEN 'co_bi_cam' THEN
      [x IN collect(DISTINCT qd) WHERE x IS NOT NULL]
    WHEN 'phan_biet_cam_va_khong_thua_nhan' THEN
      [x IN collect(DISTINCT hq) + collect(DISTINCT qd) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hq) + collect(DISTINCT qd) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: HonNhanCungGioiTinhParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "kc": params.khia_canh_cung_gioi,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


hon_nhan_cung_gioi_tinh = CypherTemplate(
    name="hon_nhan_cung_gioi_tinh",
    description=(
        "Phân biệt hai câu hỏi pháp lý khác nhau: hôn nhân cùng giới có phải hành vi bị cấm "
        "hay không, và Nhà nước có thừa nhận quan hệ đó hay không. Câu trả lời phải seed "
        "Điều 8 khoản 2 và, khi hỏi bị cấm, đối chiếu danh sách điểm a-d khoản 2 Điều 5 "
        "để không đánh đồng không thừa nhận với cấm. "
        "Ví dụ: Hành vi kết hôn với người đồng giới có phải là hành vi cấm không?; "
        "Việt Nam có chấp nhận hôn nhân đồng giới không?"
    ),
    params_schema=HonNhanCungGioiTinhParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
