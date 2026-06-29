"""Template — tranh chấp hỗ trợ sinh sản/mang thai hộ (Đ99)."""
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

_ROUTER_FIELDS = ("loai_vu_viec",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_99"]


class GiaiQuyetTranhChapHoTroSinhSanMangThaiHoParams(BaseModel):
    loai_vu_viec: Literal[
        "tranh_chap_ho_tro_sinh_san",
        "tranh_chap_mang_thai_ho",
        "tranh_chap_ho_tro_sinh_san_va_mang_thai_ho",
        "nhan_nuoi_khi_ben_nho_chet_hoac_mat_nang_luc",
        "giam_ho_cap_duong_khi_khong_nhan_nuoi",
        "khong_ro",
    ] = Field(default="khong_ro")
    tre_da_duoc_giao: Literal["co", "chua", "khong_ro"] = Field(default="khong_ro")
    tinh_trang_ben_nho_mang_thai_ho: Literal[
        "cung_chet", "cung_mat_nang_luc", "chet_hoac_mat_nang_luc", "khong_ro"
    ] = Field(default="khong_ro")
    ben_mang_thai_ho_nhan_nuoi: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")


_SEED_BODY = f"""
WITH $loai_vu_viec AS lv, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (dk_tc:DieuKien:{TOPIC_LABEL} {{
  id: 'tranh_chap_ho_tro_sinh_san_hoac_mang_thai_ho', topic: '{TOPIC}'
}})
WHERE lv IN [
  'tranh_chap_ho_tro_sinh_san', 'tranh_chap_mang_thai_ho',
  'tranh_chap_ho_tro_sinh_san_va_mang_thai_ho'
]

OPTIONAL MATCH (tq_tc:ThamQuyen:{TOPIC_LABEL} {{
  id: 'toa_an_giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho', topic: '{TOPIC}'
}})
WHERE lv IN [
  'tranh_chap_ho_tro_sinh_san', 'tranh_chap_mang_thai_ho',
  'tranh_chap_ho_tro_sinh_san_va_mang_thai_ho'
]

OPTIONAL MATCH (dk_nn:DieuKien:{TOPIC_LABEL} {{
  id: 'chua_giao_tre_va_ben_nho_mang_thai_ho_cung_chet_hoac_mat_nang_luc', topic: '{TOPIC}'
}})
WHERE lv = 'nhan_nuoi_khi_ben_nho_chet_hoac_mat_nang_luc'

OPTIONAL MATCH (q_nn:Quyen:{TOPIC_LABEL} {{
  id: 'ben_mang_thai_ho_co_quyen_nhan_nuoi_tre', topic: '{TOPIC}'
}})
WHERE lv = 'nhan_nuoi_khi_ben_nho_chet_hoac_mat_nang_luc'

OPTIONAL MATCH (dk_kn:DieuKien:{TOPIC_LABEL} {{
  id: 'ben_mang_thai_ho_khong_nhan_nuoi_tre', topic: '{TOPIC}'
}}) WHERE lv = 'giam_ho_cap_duong_khi_khong_nhan_nuoi'

OPTIONAL MATCH (hq_gh:HauQua:{TOPIC_LABEL} {{
  id: 'giam_ho_va_cap_duong_cho_tre_theo_quy_dinh', topic: '{TOPIC}'
}}) WHERE lv = 'giam_ho_cap_duong_khi_khong_nhan_nuoi'

WITH wl, lv, dk_tc, tq_tc, dk_nn, q_nn, dk_kn, hq_gh,
  [x IN collect(DISTINCT dk_tc) + collect(DISTINCT tq_tc)
       + collect(DISTINCT dk_nn) + collect(DISTINCT q_nn)
       + collect(DISTINCT dk_kn) + collect(DISTINCT hq_gh)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE lv
    WHEN 'tranh_chap_ho_tro_sinh_san' THEN [x IN [dk_tc, tq_tc] WHERE x IS NOT NULL]
    WHEN 'tranh_chap_mang_thai_ho' THEN [x IN [dk_tc, tq_tc] WHERE x IS NOT NULL]
    WHEN 'tranh_chap_ho_tro_sinh_san_va_mang_thai_ho' THEN [x IN [dk_tc, tq_tc] WHERE x IS NOT NULL]
    WHEN 'nhan_nuoi_khi_ben_nho_chet_hoac_mat_nang_luc' THEN [x IN [dk_nn, q_nn] WHERE x IS NOT NULL]
    WHEN 'giam_ho_cap_duong_khi_khong_nhan_nuoi' THEN [x IN [dk_kn, hq_gh] WHERE x IS NOT NULL]
    ELSE []
  END AS leaf_seed_nodes
"""


def _params_builder(
    params: GiaiQuyetTranhChapHoTroSinhSanMangThaiHoParams,
) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "loai_vu_viec": params.loai_vu_viec,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho = CypherTemplate(
    name="giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho",
    description=(
        "Thẩm quyền giải quyết tranh chấp hỗ trợ sinh sản/mang thai hộ và hậu quả khi bên nhờ "
        "mang thai hộ cùng chết hoặc mất năng lực trước khi giao trẻ (Đ99). "
        "Ví dụ: 'cơ quan giải quyết tranh chấp IVF'; "
        "'giám hộ và cấp dưỡng khi bên mang thai hộ không nhận nuôi'."
    ),
    params_schema=GiaiQuyetTranhChapHoTroSinhSanMangThaiHoParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
