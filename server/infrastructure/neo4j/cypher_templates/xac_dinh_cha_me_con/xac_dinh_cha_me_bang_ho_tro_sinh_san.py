"""Template — xác định cha mẹ khi hỗ trợ sinh sản/mang thai hộ (Đ93)."""
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
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_93"]


class XacDinhChaMeBangHoTroSinhSanParams(BaseModel):
    tinh_huong: Literal[
        "vo_chong_ho_tro_sinh_san",
        "phu_nu_doc_than",
        "nguoi_cho_tinh_trung_noan_phoi",
        "mang_thai_ho_nhan_dao",
        "tong_quat",
    ] = Field(default="tong_quat")
    vat_lieu_hien_tang: Literal["tinh_trung", "noan", "phoi", "nhieu_loai", "khong_ro"] = Field(
        default="khong_ro"
    )
    quan_he_can_xac_dinh: Literal[
        "cha", "me", "cha_me", "khong_phat_sinh", "khong_ro"
    ] = Field(default="khong_ro")


_SEED_BODY = f"""
WITH $tinh_huong AS th, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (hv1:HanhVi:{TOPIC_LABEL} {{
  id: 'vo_chong_sinh_con_bang_ky_thuat_ho_tro_sinh_san', topic: '{TOPIC}'
}}) WHERE th = 'vo_chong_ho_tro_sinh_san'

OPTIONAL MATCH (qd1:QuyDinh:{TOPIC_LABEL} {{
  id: 'ap_dung_dieu_88_khi_vo_sinh_con_bang_ho_tro_sinh_san', topic: '{TOPIC}'
}}) WHERE th = 'vo_chong_ho_tro_sinh_san'

OPTIONAL MATCH (hv2:HanhVi:{TOPIC_LABEL} {{
  id: 'phu_nu_doc_than_sinh_con_bang_ky_thuat_ho_tro_sinh_san', topic: '{TOPIC}'
}}) WHERE th = 'phu_nu_doc_than'

OPTIONAL MATCH (qh2:QuanHe:{TOPIC_LABEL} {{
  id: 'phu_nu_doc_than_la_me_cua_con_duoc_sinh_ra', topic: '{TOPIC}'
}}) WHERE th = 'phu_nu_doc_than'

OPTIONAL MATCH (ct3:ChuThe:{TOPIC_LABEL} {{
  id: 'nguoi_cho_tinh_trung_noan_phoi', topic: '{TOPIC}'
}}) WHERE th = 'nguoi_cho_tinh_trung_noan_phoi'

OPTIONAL MATCH (hq3:HauQua:{TOPIC_LABEL} {{
  id: 'sinh_con_ho_tro_khong_phat_sinh_quan_he_voi_nguoi_cho', topic: '{TOPIC}'
}}) WHERE th = 'nguoi_cho_tinh_trung_noan_phoi'

OPTIONAL MATCH (hv4:HanhVi:{TOPIC_LABEL} {{
  id: 'mang_thai_ho_vi_muc_dich_nhan_dao', topic: '{TOPIC}'
}}) WHERE th = 'mang_thai_ho_nhan_dao'

OPTIONAL MATCH (qd4:QuyDinh:{TOPIC_LABEL} {{
  id: 'xac_dinh_cha_me_mang_thai_ho_ap_dung_dieu_94', topic: '{TOPIC}'
}}) WHERE th = 'mang_thai_ho_nhan_dao'

WITH wl, th, hv1, qd1, hv2, qh2, ct3, hq3, hv4, qd4,
  [x IN collect(DISTINCT hv1) + collect(DISTINCT qd1) + collect(DISTINCT hv2)
       + collect(DISTINCT qh2) + collect(DISTINCT ct3) + collect(DISTINCT hq3)
       + collect(DISTINCT hv4) + collect(DISTINCT qd4)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE th
    WHEN 'vo_chong_ho_tro_sinh_san' THEN [x IN [hv1, qd1] WHERE x IS NOT NULL]
    WHEN 'phu_nu_doc_than' THEN [x IN [hv2, qh2] WHERE x IS NOT NULL]
    WHEN 'nguoi_cho_tinh_trung_noan_phoi' THEN [x IN [ct3, hq3] WHERE x IS NOT NULL]
    WHEN 'mang_thai_ho_nhan_dao' THEN [x IN [hv4, qd4] WHERE x IS NOT NULL]
    ELSE []
  END AS leaf_seed_nodes
"""


def _params_builder(params: XacDinhChaMeBangHoTroSinhSanParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "tinh_huong": params.tinh_huong,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


xac_dinh_cha_me_bang_ho_tro_sinh_san = CypherTemplate(
    name="xac_dinh_cha_me_bang_ho_tro_sinh_san",
    description=(
        "Xác định cha, mẹ khi sinh con bằng kỹ thuật hỗ trợ sinh sản hoặc mang thai hộ nhân đạo "
        "(Đ93): vợ chồng, phụ nữ độc thân, người cho tinh trùng/noãn/phôi, mang thai hộ. "
        "Ví dụ: 'phụ nữ độc thân sinh con IVF ai là mẹ'; "
        "'người cho tinh trùng có phải cha pháp lý không'."
    ),
    params_schema=XacDinhChaMeBangHoTroSinhSanParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
