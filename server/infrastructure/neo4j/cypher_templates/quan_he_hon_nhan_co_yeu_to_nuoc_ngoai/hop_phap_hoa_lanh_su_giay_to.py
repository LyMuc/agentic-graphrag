"""Template — hợp pháp hóa lãnh sự giấy tờ nước ngoài (Đ124)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_hop_phap_hoa",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_124"]


class HopPhapHoaLanhSuParams(BaseModel):
    nguon_giay_to: Literal["co_quan_co_tham_quyen_nuoc_ngoai", "khong_ro"] = Field(
        description="giấy tờ/tài liệu nước ngoài → co_quan_co_tham_quyen_nuoc_ngoai."
    )
    muc_dich_su_dung: Literal[
        "giai_quyet_hon_nhan_gia_dinh", "muc_dich_khac", "khong_ro"
    ] = Field(description="Mục đích sử dụng giấy tờ.")
    can_cu_mien: Literal[
        "dieu_uoc_quoc_te", "nguyen_tac_co_di_co_lai", "khong_co", "khong_ro"
    ] = Field(description="điều ước quốc tế / có đi có lại → map tương ứng.")
    khia_canh_hop_phap_hoa: Literal[
        "co_phai_hop_phap_hoa", "truong_hop_mien", "tong_quat"
    ] = Field(
        description="có cần hợp pháp hóa → co_phai_hop_phap_hoa; được miễn → truong_hop_mien."
    )


_SEED_BODY = f"""
WITH $khia_canh_hop_phap_hoa AS kc, $can_cu_mien AS cm, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (l_qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'giay_to_nuoc_ngoai_dung_giai_quyet_vu_viec_hon_nhan_gia_dinh', topic: '{TOPIC}'
}})
OPTIONAL MATCH (l_nv:NghiaVu:{TOPIC_LABEL} {{id: 'hop_phap_hoa_lanh_su', topic: '{TOPIC}'}})
WHERE kc IN ['co_phai_hop_phap_hoa', 'tong_quat', 'khong_ro']

OPTIONAL MATCH (l_m1:DieuKien:{TOPIC_LABEL} {{
  id: 'mien_hop_phap_hoa_theo_dieu_uoc_quoc_te', topic: '{TOPIC}'
}})
WHERE kc = 'truong_hop_mien' AND cm IN ['dieu_uoc_quoc_te', 'khong_ro', 'khong_co']
OPTIONAL MATCH (l_m2:DieuKien:{TOPIC_LABEL} {{
  id: 'mien_hop_phap_hoa_theo_nguyen_tac_co_di_co_lai', topic: '{TOPIC}'
}})
WHERE kc = 'truong_hop_mien' AND cm IN ['nguyen_tac_co_di_co_lai', 'khong_ro', 'khong_co']

WITH wl, kc, cm,
  collect(DISTINCT l_qd) + collect(DISTINCT l_nv)
    + collect(DISTINCT l_m1) + collect(DISTINCT l_m2) AS seed_nodes,
  CASE
    WHEN kc = 'co_phai_hop_phap_hoa' THEN
      [x IN collect(DISTINCT l_qd) + collect(DISTINCT l_nv) WHERE x IS NOT NULL]
    WHEN kc = 'truong_hop_mien' THEN
      [x IN collect(DISTINCT l_m1) + collect(DISTINCT l_m2) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT l_qd) + collect(DISTINCT l_nv)
           + collect(DISTINCT l_m1) + collect(DISTINCT l_m2)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: HopPhapHoaLanhSuParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "khia_canh_hop_phap_hoa": params.khia_canh_hop_phap_hoa,
        "can_cu_mien": params.can_cu_mien,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


hop_phap_hoa_lanh_su_giay_to = CypherTemplate(
    name="hop_phap_hoa_lanh_su_giay_to",
    description=(
        "Dùng cho giấy tờ, tài liệu do cơ quan nước ngoài lập/cấp/xác nhận để giải quyết "
        "vụ việc hôn nhân và gia đình tại Việt Nam. Tách nghĩa vụ hợp pháp hóa khỏi hai "
        "căn cứ miễn: điều ước quốc tế và nguyên tắc có đi có lại. "
        "Ví dụ: Giấy tờ nước ngoài có cần hợp pháp hóa lãnh sự không?; "
        "Trường hợp nào được miễn hợp pháp hóa lãnh sự?"
    ),
    params_schema=HopPhapHoaLanhSuParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
