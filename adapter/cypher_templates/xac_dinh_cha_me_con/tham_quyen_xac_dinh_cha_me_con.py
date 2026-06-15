"""Template — thẩm quyền xác định cha, mẹ, con (Đ101)."""
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

_ROUTER_FIELDS = ("tinh_trang_tranh_chap", "ket_qua_can_biet")
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_101"]


class ThamQuyenXacDinhChaMeConParams(BaseModel):
    tinh_trang_tranh_chap: Literal["khong_co", "co", "khong_ro"] = Field(default="khong_ro")
    nguoi_duoc_yeu_cau_da_chet: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    truong_hop_dieu_92: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    co_quan_du_kien: Literal["co_quan_dang_ky_ho_tich", "toa_an", "khong_ro"] = Field(
        default="khong_ro"
    )
    ket_qua_can_biet: Literal[
        "co_quan_co_tham_quyen", "gui_quyet_dinh_ghi_chu", "tong_quat"
    ] = Field(default="co_quan_co_tham_quyen")


_SEED_BODY = f"""
WITH $tinh_trang_tranh_chap AS ttc, $nguoi_duoc_yeu_cau_da_chet AS ndyc,
     $truong_hop_dieu_92 AS d92, $ket_qua_can_biet AS kq, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (dk_ht:DieuKien:{TOPIC_LABEL} {{
  id: 'xac_dinh_cha_me_con_khong_co_tranh_chap', topic: '{TOPIC}'
}}) WHERE ttc = 'khong_co'

OPTIONAL MATCH (tq_ht:ThamQuyen:{TOPIC_LABEL} {{
  id: 'tham_quyen_co_quan_dang_ky_ho_tich', topic: '{TOPIC}'
}}) WHERE ttc = 'khong_co'

OPTIONAL MATCH (dk_tc:DieuKien:{TOPIC_LABEL} {{
  id: 'xac_dinh_cha_me_con_co_tranh_chap', topic: '{TOPIC}'
}}) WHERE ttc = 'co'

OPTIONAL MATCH (dk_chet:DieuKien:{TOPIC_LABEL} {{
  id: 'nguoi_duoc_yeu_cau_xac_dinh_da_chet', topic: '{TOPIC}'
}}) WHERE ndyc = 'co' OR d92 = 'co'

OPTIONAL MATCH (tq_ta:ThamQuyen:{TOPIC_LABEL} {{
  id: 'tham_quyen_toa_an_xac_dinh_cha_me_con', topic: '{TOPIC}'
}})
WHERE ttc = 'co' OR ndyc = 'co' OR d92 = 'co'

OPTIONAL MATCH (hq_gc:HauQua:{TOPIC_LABEL} {{
  id: 'quyet_dinh_toa_an_duoc_gui_de_ghi_chu_ho_tich', topic: '{TOPIC}'
}}) WHERE kq = 'gui_quyet_dinh_ghi_chu' OR ttc = 'co' OR ndyc = 'co'

WITH wl, ttc, ndyc, d92, kq, dk_ht, tq_ht, dk_tc, dk_chet, tq_ta, hq_gc,
  [x IN collect(DISTINCT dk_ht) + collect(DISTINCT tq_ht)
       + collect(DISTINCT dk_tc) + collect(DISTINCT dk_chet)
       + collect(DISTINCT tq_ta) + collect(DISTINCT hq_gc)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN ttc = 'khong_co' THEN [x IN [dk_ht, tq_ht] WHERE x IS NOT NULL]
    WHEN ttc = 'co' OR ndyc = 'co' OR d92 = 'co' THEN
      [x IN [dk_tc, dk_chet, tq_ta]
           + CASE WHEN kq = 'gui_quyet_dinh_ghi_chu' THEN [hq_gc] ELSE [] END
       WHERE x IS NOT NULL]
    ELSE []
  END AS leaf_seed_nodes
"""


def _params_builder(params: ThamQuyenXacDinhChaMeConParams) -> dict[str, Any]:
    use_wl = (
        params.tinh_trang_tranh_chap == "khong_ro"
        and params.nguoi_duoc_yeu_cau_da_chet == "khong_ro"
        and params.truong_hop_dieu_92 == "khong_ro"
        and params.ket_qua_can_biet in ("tong_quat", "co_quan_co_tham_quyen")
    ) or params.ket_qua_can_biet == "tong_quat"
    if params.tinh_trang_tranh_chap in ("khong_co", "co"):
        use_wl = False
    if params.nguoi_duoc_yeu_cau_da_chet == "co" or params.truong_hop_dieu_92 == "co":
        use_wl = False
    return {
        "tinh_trang_tranh_chap": params.tinh_trang_tranh_chap,
        "nguoi_duoc_yeu_cau_da_chet": params.nguoi_duoc_yeu_cau_da_chet,
        "truong_hop_dieu_92": params.truong_hop_dieu_92,
        "ket_qua_can_biet": params.ket_qua_can_biet,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


tham_quyen_xac_dinh_cha_me_con = CypherTemplate(
    name="tham_quyen_xac_dinh_cha_me_con",
    description=(
        "Cơ quan có thẩm quyền xác định cha, mẹ, con (Đ101): không tranh chấp → hộ tịch; "
        "có tranh chấp, người được yêu cầu đã chết → Tòa án. "
        "Ví dụ: 'không tranh chấp cơ quan nào xác định'; "
        "'người được yêu cầu xác định đã chết thì ai giải quyết'."
    ),
    params_schema=ThamQuyenXacDinhChaMeConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
