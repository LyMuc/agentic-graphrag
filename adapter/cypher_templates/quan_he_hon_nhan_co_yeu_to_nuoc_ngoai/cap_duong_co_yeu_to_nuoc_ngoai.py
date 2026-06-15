"""Template — cấp dưỡng có yếu tố nước ngoài (Đ129)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_cap_duong",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_129"]


class CapDuongYeuToNuocNgoaiParams(BaseModel):
    tinh_trang_cu_tru_nguoi_yeu_cau: Literal[
        "co_noi_cu_tru_tai_viet_nam",
        "khong_co_noi_cu_tru_tai_viet_nam",
        "khong_ro",
    ] = Field(
        description=(
            "Seed theo nơi cư trú người yêu cầu cấp dưỡng; "
            "KHÔNG suy từ nơi làm việc/quốc tịch người có nghĩa vụ."
        )
    )
    quoc_gia_cu_tru_nguoi_yeu_cau: str | None = Field(default=None)
    quoc_tich_nguoi_yeu_cau: str | None = Field(default=None)
    khia_canh_cap_duong: Literal[
        "phap_luat_ap_dung",
        "co_quan_co_tham_quyen",
        "ca_hai",
        "tong_quat",
    ] = Field(description="cơ quan giải quyết → co_quan_co_tham_quyen.")


_SEED_BODY = f"""
WITH $tinh_trang_cu_tru_nguoi_yeu_cau AS tt, $khia_canh_cap_duong AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (l_cu_tru:QuyDinh:{TOPIC_LABEL} {{
  id: 'phap_luat_noi_nguoi_yeu_cau_cap_duong_cu_tru', topic: '{TOPIC}'
}})
WHERE kc IN ['phap_luat_ap_dung', 'ca_hai', 'tong_quat', 'khong_ro']
  AND tt IN ['co_noi_cu_tru_tai_viet_nam', 'khong_ro']
OPTIONAL MATCH (l_quoc_tich:QuyDinh:{TOPIC_LABEL} {{
  id: 'khong_co_noi_cu_tru_tai_viet_nam_ap_dung_phap_luat_quoc_tich', topic: '{TOPIC}'
}})
WHERE kc IN ['phap_luat_ap_dung', 'ca_hai', 'tong_quat', 'khong_ro']
  AND tt IN ['khong_co_noi_cu_tru_tai_viet_nam', 'khong_ro']

OPTIONAL MATCH (l_cq:CoQuan:{TOPIC_LABEL} {{
  id: 'co_quan_noi_nguoi_yeu_cau_cap_duong_cu_tru', topic: '{TOPIC}'
}})
WHERE kc IN ['co_quan_co_tham_quyen', 'ca_hai', 'tong_quat']

WITH wl, tt, kc,
  collect(DISTINCT l_cu_tru) + collect(DISTINCT l_quoc_tich) + collect(DISTINCT l_cq) AS seed_nodes,
  CASE
    WHEN kc = 'co_quan_co_tham_quyen' THEN
      [x IN collect(DISTINCT l_cq) WHERE x IS NOT NULL]
    WHEN tt = 'co_noi_cu_tru_tai_viet_nam' THEN
      [x IN collect(DISTINCT l_cu_tru) WHERE x IS NOT NULL]
    WHEN tt = 'khong_co_noi_cu_tru_tai_viet_nam' THEN
      [x IN collect(DISTINCT l_quoc_tich) WHERE x IS NOT NULL]
    WHEN kc = 'ca_hai' THEN
      [x IN collect(DISTINCT l_cu_tru) + collect(DISTINCT l_quoc_tich) + collect(DISTINCT l_cq)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT l_cu_tru) + collect(DISTINCT l_quoc_tich) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: CapDuongYeuToNuocNgoaiParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "tinh_trang_cu_tru_nguoi_yeu_cau": params.tinh_trang_cu_tru_nguoi_yeu_cau,
        "khia_canh_cap_duong": params.khia_canh_cap_duong,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


cap_duong_co_yeu_to_nuoc_ngoai = CypherTemplate(
    name="cap_duong_co_yeu_to_nuoc_ngoai",
    description=(
        "Dùng cho luật áp dụng và cơ quan giải quyết nghĩa vụ cấp dưỡng có yếu tố nước ngoài "
        "theo Điều 129. Mọi quyết định seed dựa trên nơi cư trú hoặc quốc tịch của người "
        "yêu cầu cấp dưỡng, không dựa trên quốc tịch/nơi làm việc của người có nghĩa vụ. "
        "Ví dụ: Pháp luật nước nào áp dụng cho cấp dưỡng có yếu tố nước ngoài?; "
        "Chồng là công dân Đức đang làm việc tại Việt Nam — cấp dưỡng theo luật nào?"
    ),
    params_schema=CapDuongYeuToNuocNgoaiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
