"""Template — chấm dứt nghĩa vụ cấp dưỡng (Đ118)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.cap_duong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("ly_do_cham_dut",)
_DIEU_118_WHITELIST = ["Luat_HNGD_2014_Dieu_118"]

_LY_DO_TO_HQ = {
    "nguoi_duoc_cap_duong_tu_nuoi_minh": "cham_dut_khi_nguoi_duoc_cap_duong_tu_nuoi_minh",
    "duoc_nhan_lam_con_nuoi": "cham_dut_khi_duoc_nhan_lam_con_nuoi",
    "nguoi_cap_duong_truc_tiep_nuoi": "cham_dut_khi_nguoi_cap_duong_truc_tiep_nuoi",
    "mot_ben_chet": "cham_dut_khi_mot_ben_chet",
    "ben_duoc_cap_duong_tai_hon": "cham_dut_khi_ben_duoc_cap_duong_tai_hon",
    "truong_hop_khac": "cham_dut_theo_truong_hop_khac_cua_luat",
}

_QUAN_HE_TO_QH = {
    "cha_me_con": "cha_me_cho_con",
    "ong_ba_chau": "ong_ba_cho_chau",
    "anh_chi_em": "anh_chi_em_voi_nhau",
    "ho_hang_khac": "co_di_chu_cau_bac_cho_chau_ruot",
    "vo_chong_sau_ly_hon": "vo_chong_sau_ly_hon",
}


class ChamDutNghiaVuCapDuongParams(BaseModel):
    ly_do_cham_dut: Literal[
        "nguoi_duoc_cap_duong_tu_nuoi_minh",
        "duoc_nhan_lam_con_nuoi",
        "nguoi_cap_duong_truc_tiep_nuoi",
        "mot_ben_chet",
        "ben_duoc_cap_duong_tai_hon",
        "truong_hop_khac",
        "tat_ca",
    ] = Field(
        description=(
            "Lý do chấm dứt theo Đ118. Map: đủ tuổi/có việc/tự nuôi "
            "→ nguoi_duoc_cap_duong_tu_nuoi_minh; được nhận làm con nuôi "
            "→ duoc_nhan_lam_con_nuoi; chết → mot_ben_chet; tái hôn "
            "→ ben_duoc_cap_duong_tai_hon; hỏi liệt kê → tat_ca."
        )
    )
    quan_he: Literal[
        "cha_me_con",
        "ong_ba_chau",
        "anh_chi_em",
        "ho_hang_khac",
        "vo_chong_sau_ly_hon",
        "khong_ro",
    ] = Field(description="Quan hệ gia đình trong câu hỏi (bổ sung context).")


_SEED_BODY = f"""
WITH $ly_do AS ld, $hq_id AS hq_id, $qh_id AS qh_id, $whitelist_dieu_ids AS wl

MATCH (hv:HanhVi:{TOPIC_LABEL} {{id: 'cham_dut_nghia_vu_cap_duong', topic: '{TOPIC}'}})

OPTIONAL MATCH (hv)-[:DAN_TOI]->(hq:HauQua:{TOPIC_LABEL})
WHERE ld = 'tat_ca' OR hq.id = hq_id

OPTIONAL MATCH (qh:QuanHeCapDuong:{TOPIC_LABEL} {{id: qh_id, topic: '{TOPIC}'}})
WHERE qh_id <> ''

WITH wl, ld,
  [x IN collect(DISTINCT hv) + collect(DISTINCT hq) + collect(DISTINCT qh)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN ld = 'tat_ca' THEN
      [x IN collect(DISTINCT hq) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hq) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ChamDutNghiaVuCapDuongParams) -> dict[str, Any]:
    hq_id = _LY_DO_TO_HQ.get(params.ly_do_cham_dut, "")
    qh_id = _QUAN_HE_TO_QH.get(params.quan_he, "")
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "ly_do": params.ly_do_cham_dut,
        "hq_id": hq_id,
        "qh_id": qh_id,
        "whitelist_dieu_ids": _DIEU_118_WHITELIST if use_wl else [],
    }


cham_dut_nghia_vu_cap_duong = CypherTemplate(
    name="cham_dut_nghia_vu_cap_duong",
    description=(
        "Các trường hợp chấm dứt nghĩa vụ cấp dưỡng theo Điều 118. "
        "Ví dụ: nghĩa vụ cấp dưỡng chấm dứt trong các trường hợp nào; "
        "nghĩa vụ cấp dưỡng giữa cháu và ông bà chấm dứt khi nào."
    ),
    params_schema=ChamDutNghiaVuCapDuongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
