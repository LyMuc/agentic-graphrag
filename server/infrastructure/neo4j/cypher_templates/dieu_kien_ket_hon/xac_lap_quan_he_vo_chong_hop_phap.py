"""Template — xác lập quan hệ vợ chồng hợp pháp (Đ3, Đ8, Đ9)."""
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

_ROUTER_FIELDS = ("khia_canh_xac_lap",)
_DIEU_WHITELIST = [
    "Luat_HNGD_2014_Dieu_3",
    "Luat_HNGD_2014_Dieu_8",
    "Luat_HNGD_2014_Dieu_9",
]


class XacLapQuanHeVoChongHopPhapParams(BaseModel):
    tinh_trang_dang_ky: Literal[
        "chi_co_dam_cuoi",
        "da_dang_ky_hop_le",
        "chua_dang_ky",
        "khong_ro",
    ] = Field(
        description=(
            "chỉ có đám cưới/lễ cưới -> chi_co_dam_cuoi; "
            "đã đăng ký/có giấy kết hôn -> da_dang_ky_hop_le; "
            "chưa đăng ký -> chua_dang_ky."
        )
    )
    khia_canh_xac_lap: Literal[
        "dam_cuoi_co_du_khong",
        "khi_nao_la_vo_chong_hop_phap",
        "co_can_dang_ky",
        "tong_quat",
    ] = Field(
        description=(
            "phải có đám cưới/đám cưới có đủ -> dam_cuoi_co_du_khong; "
            "khi nào được coi -> khi_nao_la_vo_chong_hop_phap; "
            "có cần đăng ký -> co_can_dang_ky."
        )
    )


_SEED_BODY = f"""
WITH $td AS td, $kc AS kc, $whitelist_dieu_ids AS wl

MATCH (qd_dn:QuyDinh:{TOPIC_LABEL} {{id: 'dinh_nghia_ket_hon', topic: '{TOPIC}'}})
MATCH (hv_kh:HanhVi:{TOPIC_LABEL} {{id: 'ket_hon', topic: '{TOPIC}'}})
MATCH (dk:DieuKien:{TOPIC_LABEL} {{id: 'du_dieu_kien_ket_hon', topic: '{TOPIC}'}})

OPTIONAL MATCH (qd_dc:QuyDinh:{TOPIC_LABEL} {{
  id: 'dam_cuoi_khong_thay_the_dang_ky_ket_hon', topic: '{TOPIC}'
}})
WHERE kc IN ['dam_cuoi_co_du_khong', 'co_can_dang_ky', 'tong_quat']
   OR td IN ['chi_co_dam_cuoi', 'chua_dang_ky']

OPTIONAL MATCH (hv_dk:HanhVi:{TOPIC_LABEL} {{id: 'thuc_hien_dang_ky_ket_hon', topic: '{TOPIC}'}})
WHERE qd_dc IS NOT NULL

OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{
  id: 'quan_he_vo_chong_duoc_xac_lap_khi_du_dieu_kien_va_dang_ky_hop_le', topic: '{TOPIC}'
}})
WHERE kc IN ['khi_nao_la_vo_chong_hop_phap', 'co_can_dang_ky', 'tong_quat']
   OR td = 'da_dang_ky_hop_le'

WITH wl, kc,
  [x IN collect(DISTINCT qd_dn) + collect(DISTINCT hv_kh) + collect(DISTINCT dk)
       + collect(DISTINCT qd_dc) + collect(DISTINCT hv_dk) + collect(DISTINCT hq)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'dam_cuoi_co_du_khong' THEN
      [x IN collect(DISTINCT qd_dc) + collect(DISTINCT hv_dk) WHERE x IS NOT NULL]
    WHEN 'khi_nao_la_vo_chong_hop_phap' THEN
      [x IN collect(DISTINCT hq) WHERE x IS NOT NULL]
    WHEN 'co_can_dang_ky' THEN
      [x IN collect(DISTINCT qd_dc) + collect(DISTINCT hv_dk) + collect(DISTINCT hq)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT qd_dc) + collect(DISTINCT hq) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: XacLapQuanHeVoChongHopPhapParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "td": params.tinh_trang_dang_ky,
        "kc": params.khia_canh_xac_lap,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


xac_lap_quan_he_vo_chong_hop_phap = CypherTemplate(
    name="xac_lap_quan_he_vo_chong_hop_phap",
    description=(
        "Trả lời đám cưới/lễ cưới có đủ để được công nhận là vợ chồng hay không và "
        "khi nào quan hệ vợ chồng hợp pháp được xác lập. Template kết hợp định nghĩa "
        "kết hôn, điều kiện tại Điều 8 và yêu cầu đăng ký tại Điều 9 khoản 1. "
        "Ví dụ: Phải có đám cưới mới được công nhận là vợ chồng không?; "
        "Khi nào được coi là vợ chồng hợp pháp?"
    ),
    params_schema=XacLapQuanHeVoChongHopPhapParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
