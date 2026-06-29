"""Template — quyền nhận cha, mẹ, con (Đ90-91)."""
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

_ROUTER_FIELDS = ("chu_the_nhan",)
_DIEU_WHITELIST = [
    "Luat_HNGD_2014_Dieu_90",
    "Luat_HNGD_2014_Dieu_91",
]


class QuyenNhanChaMeConParams(BaseModel):
    chu_the_nhan: Literal["con", "cha", "me", "cha_hoac_me", "khong_ro"] = Field(
        description="con → Đ90; cha/me/cha_hoac_me → Đ91."
    )
    doi_tuong_nhan: Literal["cha", "me", "cha_me", "con", "khong_ro"] = Field(
        default="khong_ro"
    )
    doi_tuong_da_chet: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    chu_the_da_thanh_nien: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    dang_co_vo_chong: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    nguoi_khac_khong_dong_y: Literal["cha", "me", "vo", "chong", "khong_ro"] = Field(
        default="khong_ro"
    )
    muc_dich: Literal["nhan_quan_he", "tu_choi_quan_he", "khong_ro"] = Field(
        default="nhan_quan_he"
    )


_SEED_BODY = f"""
WITH $chu_the_nhan AS ctn, $doi_tuong_nhan AS dtn, $doi_tuong_da_chet AS ddc,
     $chu_the_da_thanh_nien AS ctni, $dang_co_vo_chong AS dvc,
     $nguoi_khac_khong_dong_y AS nkkdy, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (q_con:Quyen:{TOPIC_LABEL} {{
  id: 'con_co_quyen_nhan_cha_me', topic: '{TOPIC}'
}})
WHERE ctn = 'con' AND dtn IN ['cha', 'me', 'cha_me', 'khong_ro']

OPTIONAL MATCH (dk_cm_chet:DieuKien:{TOPIC_LABEL} {{
  id: 'cha_me_da_chet', topic: '{TOPIC}'
}})
WHERE ctn = 'con' AND ddc = 'co'

OPTIONAL MATCH (q_nhan_cha:Quyen:{TOPIC_LABEL} {{
  id: 'con_thanh_nien_nhan_cha_khong_can_me_dong_y', topic: '{TOPIC}'
}})
WHERE ctn = 'con' AND (ctni = 'co' OR nkkdy = 'me') AND dtn IN ['cha', 'cha_me', 'khong_ro']

OPTIONAL MATCH (q_nhan_me:Quyen:{TOPIC_LABEL} {{
  id: 'con_thanh_nien_nhan_me_khong_can_cha_dong_y', topic: '{TOPIC}'
}})
WHERE ctn = 'con' AND (ctni = 'co' OR nkkdy = 'cha') AND dtn IN ['me', 'cha_me', 'khong_ro']

OPTIONAL MATCH (q_cm:Quyen:{TOPIC_LABEL} {{
  id: 'cha_me_co_quyen_nhan_con', topic: '{TOPIC}'
}})
WHERE ctn IN ['cha', 'me', 'cha_hoac_me'] OR dtn = 'con'

OPTIONAL MATCH (dk_con_chet:DieuKien:{TOPIC_LABEL} {{
  id: 'con_da_chet', topic: '{TOPIC}'
}})
WHERE (ctn IN ['cha', 'me', 'cha_hoac_me'] OR dtn = 'con') AND ddc = 'co'

OPTIONAL MATCH (hv_vc:HanhVi:{TOPIC_LABEL} {{
  id: 'nguoi_dang_co_vo_chong_nhan_con', topic: '{TOPIC}'
}})
WHERE (ctn IN ['cha', 'me', 'cha_hoac_me'] OR dtn = 'con')
  AND (dvc = 'co' OR nkkdy IN ['vo', 'chong'])

OPTIONAL MATCH (hq_vc:HauQua:{TOPIC_LABEL} {{
  id: 'nhan_con_khong_can_vo_chong_dong_y', topic: '{TOPIC}'
}})
WHERE (ctn IN ['cha', 'me', 'cha_hoac_me'] OR dtn = 'con')
  AND (dvc = 'co' OR nkkdy IN ['vo', 'chong'])

WITH wl, ctn, q_con, dk_cm_chet, q_nhan_cha, q_nhan_me, q_cm, dk_con_chet, hv_vc, hq_vc,
  [x IN collect(DISTINCT q_con) + collect(DISTINCT dk_cm_chet)
       + collect(DISTINCT q_nhan_cha) + collect(DISTINCT q_nhan_me)
       + collect(DISTINCT q_cm) + collect(DISTINCT dk_con_chet)
       + collect(DISTINCT hv_vc) + collect(DISTINCT hq_vc)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE ctn
    WHEN 'con' THEN
      [x IN [q_con, dk_cm_chet, q_nhan_cha, q_nhan_me] WHERE x IS NOT NULL]
    WHEN 'cha' THEN
      [x IN [q_cm, dk_con_chet, hv_vc, hq_vc] WHERE x IS NOT NULL]
    WHEN 'me' THEN
      [x IN [q_cm, dk_con_chet, hv_vc, hq_vc] WHERE x IS NOT NULL]
    WHEN 'cha_hoac_me' THEN
      [x IN [q_cm, dk_con_chet, hv_vc, hq_vc] WHERE x IS NOT NULL]
    ELSE []
  END AS leaf_seed_nodes
"""


def _params_builder(params: QuyenNhanChaMeConParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "chu_the_nhan": params.chu_the_nhan,
        "doi_tuong_nhan": params.doi_tuong_nhan,
        "doi_tuong_da_chet": params.doi_tuong_da_chet,
        "chu_the_da_thanh_nien": params.chu_the_da_thanh_nien,
        "dang_co_vo_chong": params.dang_co_vo_chong,
        "nguoi_khac_khong_dong_y": params.nguoi_khac_khong_dong_y,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


quyen_nhan_cha_me_con = CypherTemplate(
    name="quyen_nhan_cha_me_con",
    description=(
        "Quyền của con nhận cha/mẹ và quyền của cha/mẹ nhận con (Đ90-91), kể cả người được "
        "nhận đã chết; không cần đồng ý cha/mẹ hoặc vợ/chồng. "
        "Ví dụ: 'con thành niên nhận cha có cần mẹ đồng ý'; "
        "'đã có vợ nhận con riêng nhưng vợ không đồng ý'."
    ),
    params_schema=QuyenNhanChaMeConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
