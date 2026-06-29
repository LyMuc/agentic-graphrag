"""Template — xác định con chung theo hôn nhân (Đ88)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.xac_dinh_cha_me_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("tinh_huong",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_88"]


class XacDinhConChungTheoHonNhanParams(BaseModel):
    tinh_huong: Literal[
        "sinh_trong_thoi_ky_hon_nhan",
        "co_thai_trong_thoi_ky_hon_nhan",
        "co_thai_truoc_ket_hon",
        "sinh_trong_300_ngay_sau_cham_dut_hon_nhan",
        "sinh_truoc_dang_ky_ket_hon_duoc_thua_nhan",
        "khong_thua_nhan_con",
        "tong_quat",
    ] = Field(
        description=(
            "Map: sinh/có thai trong hôn nhân; 300 ngày sau ly hôn; sinh trước đăng ký kết hôn "
            "được thừa nhận; cha mẹ phủ nhận con; không rõ → tong_quat."
        )
    )
    tinh_trang_hon_nhan: Literal[
        "dang_hon_nhan", "da_cham_dut", "ly_than", "chua_dang_ky_ket_hon", "khong_ro"
    ] = Field(description="ly thân → ly_than.")
    trong_300_ngay: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    cha_me_cung_thua_nhan: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    co_phu_nhan: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    co_chung_cu: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")


_SEED_BODY = f"""
WITH $tinh_huong AS th, $whitelist_dieu_ids AS wl

MATCH (anchor:QuyDinh:{TOPIC_LABEL} {{
  id: 'xac_dinh_con_chung_cua_vo_chong', topic: '{TOPIC}'
}})

OPTIONAL MATCH (dk_st:DieuKien:{TOPIC_LABEL} {{
  id: 'con_sinh_trong_thoi_ky_hon_nhan', topic: '{TOPIC}'
}}) WHERE th IN ['sinh_trong_thoi_ky_hon_nhan', 'co_thai_truoc_ket_hon']

OPTIONAL MATCH (dk_ct:DieuKien:{TOPIC_LABEL} {{
  id: 'nguoi_vo_co_thai_trong_thoi_ky_hon_nhan', topic: '{TOPIC}'
}}) WHERE th IN ['co_thai_trong_thoi_ky_hon_nhan', 'co_thai_truoc_ket_hon']

OPTIONAL MATCH (dk_300:DieuKien:{TOPIC_LABEL} {{
  id: 'con_sinh_trong_300_ngay_sau_cham_dut_hon_nhan', topic: '{TOPIC}'
}}) WHERE th = 'sinh_trong_300_ngay_sau_cham_dut_hon_nhan'

OPTIONAL MATCH (dk_truoc:DieuKien:{TOPIC_LABEL} {{
  id: 'con_sinh_truoc_dang_ky_ket_hon_duoc_cha_me_thua_nhan', topic: '{TOPIC}'
}}) WHERE th IN ['sinh_truoc_dang_ky_ket_hon_duoc_thua_nhan', 'co_thai_truoc_ket_hon']

OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{
  id: 'duoc_coi_la_con_chung_cua_vo_chong', topic: '{TOPIC}'
}}) WHERE th IN [
  'sinh_trong_thoi_ky_hon_nhan', 'co_thai_trong_thoi_ky_hon_nhan',
  'co_thai_truoc_ket_hon', 'sinh_trong_300_ngay_sau_cham_dut_hon_nhan',
  'sinh_truoc_dang_ky_ket_hon_duoc_thua_nhan'
]

OPTIONAL MATCH (hv:HanhVi:{TOPIC_LABEL} {{
  id: 'cha_me_khong_thua_nhan_con', topic: '{TOPIC}'
}}) WHERE th = 'khong_thua_nhan_con'

OPTIONAL MATCH (dk_cc:DieuKien:{TOPIC_LABEL} {{
  id: 'khong_thua_nhan_con_phai_co_chung_cu', topic: '{TOPIC}'
}}) WHERE th = 'khong_thua_nhan_con'

OPTIONAL MATCH (tq:ThamQuyen:{TOPIC_LABEL} {{
  id: 'toa_an_xac_dinh_khi_cha_me_khong_thua_nhan_con', topic: '{TOPIC}'
}}) WHERE th = 'khong_thua_nhan_con'

WITH wl, th, anchor, dk_st, dk_ct, dk_300, dk_truoc, hq, hv, dk_cc, tq,
  [x IN collect(DISTINCT anchor) + collect(DISTINCT dk_st) + collect(DISTINCT dk_ct)
       + collect(DISTINCT dk_300) + collect(DISTINCT dk_truoc) + collect(DISTINCT hq)
       + collect(DISTINCT hv) + collect(DISTINCT dk_cc) + collect(DISTINCT tq)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE th
    WHEN 'sinh_trong_thoi_ky_hon_nhan' THEN
      [x IN [dk_st, hq] WHERE x IS NOT NULL]
    WHEN 'co_thai_trong_thoi_ky_hon_nhan' THEN
      [x IN [dk_ct, hq] WHERE x IS NOT NULL]
    WHEN 'co_thai_truoc_ket_hon' THEN
      [x IN [dk_st, dk_truoc, hq] WHERE x IS NOT NULL]
    WHEN 'sinh_trong_300_ngay_sau_cham_dut_hon_nhan' THEN
      [x IN [dk_300, hq] WHERE x IS NOT NULL]
    WHEN 'sinh_truoc_dang_ky_ket_hon_duoc_thua_nhan' THEN
      [x IN [dk_truoc, hq] WHERE x IS NOT NULL]
    WHEN 'khong_thua_nhan_con' THEN
      [x IN [dk_cc, tq] WHERE x IS NOT NULL]
    ELSE []
  END AS leaf_seed_nodes
"""


def _params_builder(params: XacDinhConChungTheoHonNhanParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "tinh_huong": params.tinh_huong,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


xac_dinh_con_chung_theo_hon_nhan = CypherTemplate(
    name="xac_dinh_con_chung_theo_hon_nhan",
    description=(
        "Xác định con chung theo suy đoán Điều 88: sinh/có thai trong hôn nhân, "
        "sinh trong 300 ngày sau chấm dứt hôn nhân, sinh trước đăng ký kết hôn được thừa nhận; "
        "cha mẹ không thừa nhận con (chứng cứ, Tòa án). "
        "Ví dụ: 'sinh trong vòng 300 ngày'; 'chồng phủ nhận con sinh trong hôn nhân'."
    ),
    params_schema=XacDinhConChungTheoHonNhanParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
