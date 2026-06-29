"""Template — xác định cha, mẹ, con có yếu tố nước ngoài (Đ128)."""
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

_ROUTER_FIELDS = ("co_tranh_chap",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_128"]


class XacDinhChaMeConParams(BaseModel):
    co_tranh_chap: Literal["co", "khong", "khong_ro"] = Field(
        description="có tranh chấp → co; cơ quan hộ tịch/không tranh chấp → khong."
    )
    nhom_chu_the: Literal[
        "cong_dan_viet_nam_voi_nguoi_nuoc_ngoai",
        "hai_cong_dan_viet_nam_mot_ben_dinh_cu_o_nuoc_ngoai",
        "hai_nguoi_nuoc_ngoai_mot_ben_thuong_tru_tai_viet_nam",
        "khong_ro",
    ] = Field(description="Nhóm chủ thể nếu xác định được.")
    khia_canh_xac_dinh: Literal["co_quan_giai_quyet", "truong_hop_ap_dung", "tong_quat"] = Field(
        description="hỏi cơ quan giải quyết → co_quan_giai_quyet."
    )


_SUBJECT_IDS = {
    "cong_dan_viet_nam_voi_nguoi_nuoc_ngoai": "cong_dan_viet_nam_voi_nguoi_nuoc_ngoai",
    "hai_cong_dan_viet_nam_mot_ben_dinh_cu_o_nuoc_ngoai": "hai_cong_dan_viet_nam_it_nhat_mot_ben_dinh_cu_o_nuoc_ngoai",
    "hai_nguoi_nuoc_ngoai_mot_ben_thuong_tru_tai_viet_nam": "hai_nguoi_nuoc_ngoai_it_nhat_mot_ben_thuong_tru_tai_viet_nam",
}


_SEED_BODY = f"""
WITH $co_tranh_chap AS tc, $subject_id AS sid, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (l_khong:HanhVi:{TOPIC_LABEL} {{
  id: 'xac_dinh_cha_me_con_khong_co_tranh_chap', topic: '{TOPIC}'
}})
WHERE tc IN ['khong', 'khong_ro']
OPTIONAL MATCH (l_ht:CoQuan:{TOPIC_LABEL} {{id: 'co_quan_dang_ky_ho_tich', topic: '{TOPIC}'}})
WHERE tc IN ['khong', 'khong_ro']

OPTIONAL MATCH (l_co:HanhVi:{TOPIC_LABEL} {{
  id: 'xac_dinh_cha_me_con_co_tranh_chap', topic: '{TOPIC}'
}})
WHERE tc IN ['co', 'khong_ro']
OPTIONAL MATCH (l_ta:CoQuan:{TOPIC_LABEL} {{
  id: 'toa_an_viet_nam_giai_quyet_xac_dinh_cha_me_con', topic: '{TOPIC}'
}})
WHERE tc IN ['co', 'khong_ro']
OPTIONAL MATCH (l_dk:DieuKien:{TOPIC_LABEL} {{
  id: 'truong_hop_luat_dan_chieu_ve_xac_dinh_cha_me_con', topic: '{TOPIC}'
}})
WHERE tc = 'co'

OPTIONAL MATCH (l_sub:ChuThe:{TOPIC_LABEL} {{id: sid, topic: '{TOPIC}'}})
WHERE sid <> ''

WITH wl, tc,
  collect(DISTINCT l_khong) + collect(DISTINCT l_ht)
    + collect(DISTINCT l_co) + collect(DISTINCT l_ta) + collect(DISTINCT l_dk)
    + collect(DISTINCT l_sub) AS seed_nodes,
  CASE
    WHEN tc = 'khong' THEN
      [x IN collect(DISTINCT l_khong) + collect(DISTINCT l_ht) + collect(DISTINCT l_sub)
       WHERE x IS NOT NULL]
    WHEN tc = 'co' THEN
      [x IN collect(DISTINCT l_co) + collect(DISTINCT l_ta) + collect(DISTINCT l_dk)
           + collect(DISTINCT l_sub)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT l_khong) + collect(DISTINCT l_ht)
           + collect(DISTINCT l_co) + collect(DISTINCT l_ta)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: XacDinhChaMeConParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    sid = _SUBJECT_IDS.get(params.nhom_chu_the or "", "")
    return {
        "co_tranh_chap": params.co_tranh_chap,
        "subject_id": sid,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


xac_dinh_cha_me_con_co_yeu_to_nuoc_ngoai = CypherTemplate(
    name="xac_dinh_cha_me_con_co_yeu_to_nuoc_ngoai",
    description=(
        "Dùng cho xác định cha, mẹ, con có yếu tố nước ngoài theo Điều 128. "
        "Không tranh chấp → cơ quan đăng ký hộ tịch; có tranh chấp → Tòa án. "
        "Ví dụ: Trường hợp không tranh chấp cơ quan hộ tịch giải quyết thế nào?; "
        "Có tranh chấp về cha của con thì Tòa án xử lý ra sao?"
    ),
    params_schema=XacDinhChaMeConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
