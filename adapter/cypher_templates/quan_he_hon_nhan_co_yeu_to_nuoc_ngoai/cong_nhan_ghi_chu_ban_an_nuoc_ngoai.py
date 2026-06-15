"""Template — công nhận và ghi chú bản án nước ngoài (Đ125)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("nhu_cau_thi_hanh",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_125"]


class CongNhanGhiChuBanAnParams(BaseModel):
    loai_quyet_dinh: Literal[
        "ban_an_quyet_dinh_toa_an_nuoc_ngoai",
        "quyet_dinh_co_quan_khac_nuoc_ngoai",
        "khong_ro",
    ] = Field(description="quyết định cơ quan khác nước ngoài → quyet_dinh_co_quan_khac_nuoc_ngoai.")
    nhu_cau_thi_hanh: Literal[
        "co_yeu_cau_thi_hanh_tai_viet_nam",
        "khong_yeu_cau_thi_hanh",
        "khong_ro",
    ] = Field(description="có/không yêu cầu thi hành tại Việt Nam.")
    co_don_yeu_cau_khong_cong_nhan: Literal["co", "khong", "khong_ro"] = Field(
        description="Chỉ seed điều kiện khi param là khong."
    )
    khia_canh_ban_an: Literal["cong_nhan", "ghi_so_ho_tich", "tong_quat"] = Field(
        description="ghi sổ hộ tịch → ghi_so_ho_tich."
    )


_SEED_BODY = f"""
WITH $nhu_cau_thi_hanh AS nth, $loai_quyet_dinh AS lqd, $co_don AS cd,
     $khia_canh_ban_an AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (l_co:QuyDinh:{TOPIC_LABEL} {{
  id: 'ban_an_quyet_dinh_toa_an_nuoc_ngoai_co_yeu_cau_thi_hanh', topic: '{TOPIC}'
}})
WHERE nth IN ['co_yeu_cau_thi_hanh_tai_viet_nam', 'khong_ro']
  OR kc = 'cong_nhan'
OPTIONAL MATCH (l_cn:HanhVi:{TOPIC_LABEL} {{
  id: 'cong_nhan_theo_bo_luat_to_tung_dan_su', topic: '{TOPIC}'
}})
WHERE nth IN ['co_yeu_cau_thi_hanh_tai_viet_nam', 'khong_ro']
  OR kc = 'cong_nhan'

OPTIONAL MATCH (l_khong:QuyDinh:{TOPIC_LABEL} {{
  id: 'ban_an_quyet_dinh_khong_yeu_cau_thi_hanh', topic: '{TOPIC}'
}})
WHERE nth IN ['khong_yeu_cau_thi_hanh', 'khong_ro']
  OR kc = 'ghi_so_ho_tich'
OPTIONAL MATCH (l_ghi:HanhVi:{TOPIC_LABEL} {{id: 'ghi_vao_so_ho_tich', topic: '{TOPIC}'}})
WHERE nth IN ['khong_yeu_cau_thi_hanh', 'khong_ro']
  OR kc = 'ghi_so_ho_tich'
OPTIONAL MATCH (l_dk:DieuKien:{TOPIC_LABEL} {{
  id: 'khong_co_don_yeu_cau_khong_cong_nhan_tai_viet_nam', topic: '{TOPIC}'
}})
WHERE cd = 'khong'
  AND nth IN ['khong_yeu_cau_thi_hanh', 'khong_ro']

OPTIONAL MATCH (l_cq:QuyDinh:{TOPIC_LABEL} {{
  id: 'quyet_dinh_co_quan_khac_co_tham_quyen_nuoc_ngoai', topic: '{TOPIC}'
}})
WHERE lqd = 'quyet_dinh_co_quan_khac_nuoc_ngoai'

WITH wl, nth, kc,
  collect(DISTINCT l_co) + collect(DISTINCT l_cn)
    + collect(DISTINCT l_khong) + collect(DISTINCT l_ghi)
    + collect(DISTINCT l_dk) + collect(DISTINCT l_cq) AS seed_nodes,
  CASE
    WHEN nth = 'co_yeu_cau_thi_hanh_tai_viet_nam' OR kc = 'cong_nhan' THEN
      [x IN collect(DISTINCT l_co) + collect(DISTINCT l_cn) WHERE x IS NOT NULL]
    WHEN nth = 'khong_yeu_cau_thi_hanh' OR kc = 'ghi_so_ho_tich' THEN
      [x IN collect(DISTINCT l_khong) + collect(DISTINCT l_ghi) + collect(DISTINCT l_dk)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT l_co) + collect(DISTINCT l_cn)
           + collect(DISTINCT l_khong) + collect(DISTINCT l_ghi)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: CongNhanGhiChuBanAnParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "nhu_cau_thi_hanh": params.nhu_cau_thi_hanh,
        "loai_quyet_dinh": params.loai_quyet_dinh,
        "co_don": params.co_don_yeu_cau_khong_cong_nhan,
        "khia_canh_ban_an": params.khia_canh_ban_an,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


cong_nhan_ghi_chu_ban_an_nuoc_ngoai = CypherTemplate(
    name="cong_nhan_ghi_chu_ban_an_nuoc_ngoai",
    description=(
        "Dùng cho bản án/quyết định hôn nhân và gia đình của Tòa án hoặc cơ quan có "
        "thẩm quyền nước ngoài. Phân biệt có yêu cầu thi hành tại Việt Nam (công nhận "
        "theo tố tụng dân sự) và không yêu cầu thi hành (ghi sổ hộ tịch). "
        "Ví dụ: Bản án nước ngoài có yêu cầu thi hành tại Việt Nam được công nhận thế nào?; "
        "Không yêu cầu thi hành thì ghi sổ hộ tịch ra sao?"
    ),
    params_schema=CongNhanGhiChuBanAnParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
