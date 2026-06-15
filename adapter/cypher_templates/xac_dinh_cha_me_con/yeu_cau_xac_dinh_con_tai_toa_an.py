"""Template — yêu cầu Tòa án xác định là/không phải con (Đ89)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.xac_dinh_cha_me_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("huong_xac_dinh", "tinh_trang_ghi_nhan")
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_89"]


class YeuCauXacDinhConTaiToaAnParams(BaseModel):
    huong_xac_dinh: Literal["la_con_minh", "khong_phai_con_minh", "khong_ro"] = Field(
        description="la_con_minh → Đ89 k1; khong_phai_con_minh → Đ89 k2."
    )
    tinh_trang_ghi_nhan: Literal[
        "chua_duoc_nhan_la_cha_me",
        "dang_duoc_nhan_la_cha_me",
        "giay_khai_sinh_ghi_nguoi_khac",
        "khong_ro",
    ] = Field(description="khai sinh ghi người khác → giay_khai_sinh_ghi_nguoi_khac.")
    co_chung_cu: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    loai_chung_cu: Literal["adn", "giay_to_ho_tich", "khac", "khong_ro"] = Field(
        default="khong_ro"
    )


_SEED_BODY = f"""
WITH $huong_xac_dinh AS hx, $tinh_trang_ghi_nhan AS tgr, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (ct1:ChuThe:{TOPIC_LABEL} {{
  id: 'nguoi_khong_duoc_nhan_la_cha_me', topic: '{TOPIC}'
}})
WHERE hx = 'la_con_minh'
   OR tgr IN ['chua_duoc_nhan_la_cha_me', 'giay_khai_sinh_ghi_nguoi_khac']

OPTIONAL MATCH (q1:Quyen:{TOPIC_LABEL} {{
  id: 'yeu_cau_toa_an_xac_dinh_mot_nguoi_la_con_minh', topic: '{TOPIC}'
}})
WHERE hx = 'la_con_minh'
   OR tgr IN ['chua_duoc_nhan_la_cha_me', 'giay_khai_sinh_ghi_nguoi_khac']

OPTIONAL MATCH (ct2:ChuThe:{TOPIC_LABEL} {{
  id: 'nguoi_dang_duoc_nhan_la_cha_me', topic: '{TOPIC}'
}})
WHERE hx = 'khong_phai_con_minh' OR tgr = 'dang_duoc_nhan_la_cha_me'

OPTIONAL MATCH (q2:Quyen:{TOPIC_LABEL} {{
  id: 'yeu_cau_toa_an_xac_dinh_khong_phai_la_con_minh', topic: '{TOPIC}'
}})
WHERE hx = 'khong_phai_con_minh' OR tgr = 'dang_duoc_nhan_la_cha_me'

WITH wl, hx, tgr, ct1, q1, ct2, q2,
  [x IN collect(DISTINCT ct1) + collect(DISTINCT q1)
       + collect(DISTINCT ct2) + collect(DISTINCT q2)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN hx = 'la_con_minh'
      OR tgr IN ['chua_duoc_nhan_la_cha_me', 'giay_khai_sinh_ghi_nguoi_khac'] THEN
      [x IN [ct1, q1] WHERE x IS NOT NULL]
    WHEN hx = 'khong_phai_con_minh' OR tgr = 'dang_duoc_nhan_la_cha_me' THEN
      [x IN [ct2, q2] WHERE x IS NOT NULL]
    ELSE []
  END AS leaf_seed_nodes
"""


def _params_builder(params: YeuCauXacDinhConTaiToaAnParams) -> dict[str, Any]:
    use_wl = (
        params.huong_xac_dinh == "khong_ro"
        and params.tinh_trang_ghi_nhan == "khong_ro"
    )
    return {
        "huong_xac_dinh": params.huong_xac_dinh,
        "tinh_trang_ghi_nhan": params.tinh_trang_ghi_nhan,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


yeu_cau_xac_dinh_con_tai_toa_an = CypherTemplate(
    name="yeu_cau_xac_dinh_con_tai_toa_an",
    description=(
        "Yêu cầu Tòa án xác định một người là con mình hoặc không phải con mình (Đ89). "
        "Dấu hiệu: khai sinh ghi người khác, ADN, chưa/đang được ghi nhận là cha mẹ. "
        "Ví dụ: 'khai sinh ghi tên người khác'; 'ADN cho thấy không phải con ruột'."
    ),
    params_schema=YeuCauXacDinhConTaiToaAnParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
