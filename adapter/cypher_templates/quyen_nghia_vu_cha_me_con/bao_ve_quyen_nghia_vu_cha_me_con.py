"""Template — bảo vệ và bình đẳng quyền, nghĩa vụ cha mẹ-con (Đ68)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_bao_ve",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_68"]


class BaoVeQuyenNghiaVuChaMeConParams(BaseModel):
    khia_canh_bao_ve: Literal[
        "bao_ve_tong_quat",
        "binh_dang_khong_phu_thuoc_hon_nhan",
        "quan_he_cha_me_nuoi_con_nuoi",
        "gioi_han_thoa_thuan",
        "tong_quat",
    ] = Field(
        description=(
            "được bảo vệ thế nào -> bao_ve_tong_quat; "
            "ngoài giá thú/chưa đăng ký kết hôn -> binh_dang_khong_phu_thuoc_hon_nhan; "
            "cha mẹ nuôi-con nuôi -> quan_he_cha_me_nuoi_con_nuoi; "
            "thỏa thuận ảnh hưởng quyền con -> gioi_han_thoa_thuan."
        )
    )
    doi_tuong_duoc_bao_ve: Literal[
        "con_chua_thanh_nien",
        "con_mat_nang_luc_hanh_vi",
        "con_khong_co_kha_nang_tu_nuoi",
        "cha_me_can_duoc_bao_ve",
        "tat_ca",
        "khong_ro",
    ] = Field(description="Phạm vi người được bảo vệ theo khoản 4 Điều 68.")


_SEED_BODY = f"""
WITH $kc AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (leaf_bv:QuyDinh:{TOPIC_LABEL} {{
  id: 'bao_ve_quyen_nghia_vu_cha_me_con', topic: '{TOPIC}'
}})
WHERE kc IN ['bao_ve_tong_quat', 'tong_quat']

OPTIONAL MATCH (leaf_bd:Quyen:{TOPIC_LABEL} {{
  id: 'con_binh_dang_khong_phu_thuoc_hon_nhan_cha_me', topic: '{TOPIC}'
}})
WHERE kc = 'binh_dang_khong_phu_thuoc_hon_nhan'

OPTIONAL MATCH (leaf_nc:QuyDinh:{TOPIC_LABEL} {{
  id: 'quan_he_cha_me_nuoi_con_nuoi_co_quyen_nghia_vu_cha_me_con', topic: '{TOPIC}'
}})
WHERE kc = 'quan_he_cha_me_nuoi_con_nuoi'

OPTIONAL MATCH (leaf_tt:DieuKien:{TOPIC_LABEL} {{
  id: 'thoa_thuan_khong_duoc_anh_huong_quyen_loi_nguoi_duoc_bao_ve', topic: '{TOPIC}'
}})
WHERE kc = 'gioi_han_thoa_thuan'

WITH wl, kc,
  collect(DISTINCT leaf_bv) + collect(DISTINCT leaf_bd)
    + collect(DISTINCT leaf_nc) + collect(DISTINCT leaf_tt)
    AS seed_nodes,
  [x IN collect(DISTINCT leaf_bv) + collect(DISTINCT leaf_bd)
        + collect(DISTINCT leaf_nc) + collect(DISTINCT leaf_tt)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: BaoVeQuyenNghiaVuChaMeConParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "kc": params.khia_canh_bao_ve,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


bao_ve_quyen_nghia_vu_cha_me_con = CypherTemplate(
    name="bao_ve_quyen_nghia_vu_cha_me_con",
    description=(
        "Trả lời nguyên tắc bảo vệ quyền, nghĩa vụ cha mẹ-con tại Điều 68: bảo vệ chung, "
        "bình đẳng của con không phụ thuộc tình trạng hôn nhân của cha mẹ và giới hạn thỏa thuận. "
        "Dùng cho câu hỏi Nhà nước bảo vệ các quyền này thế nào, con sinh khi cha mẹ chưa đăng ký kết hôn, "
        "hoặc thỏa thuận có được ảnh hưởng quyền con chưa thành niên không."
    ),
    params_schema=BaoVeQuyenNghiaVuChaMeConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
