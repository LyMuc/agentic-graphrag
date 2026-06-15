"""Template — bảo vệ quyền lợi quan hệ có yếu tố nước ngoài (Đ121)."""
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

_ROUTER_FIELDS = ("pham_vi_bao_ve",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_121"]


class BaoVeQuyenLoiParams(BaseModel):
    pham_vi_bao_ve: Literal[
        "tong_quat",
        "tai_viet_nam",
        "nguoi_nuoc_ngoai_tai_viet_nam",
        "cong_dan_viet_nam_o_nuoc_ngoai",
        "chinh_phu_quy_dinh_chi_tiet",
    ] = Field(
        description=(
            "tôn trọng/bảo vệ tại Việt Nam → tai_viet_nam; "
            "người nước ngoài tại Việt Nam → nguoi_nuoc_ngoai_tai_viet_nam; "
            "bảo hộ công dân VN ở nước ngoài → cong_dan_viet_nam_o_nuoc_ngoai; "
            "Chính phủ quy định chi tiết → chinh_phu_quy_dinh_chi_tiet."
        )
    )
    khia_canh_bao_ve: Literal[
        "quyen_loi",
        "quyen_nghia_vu",
        "can_cu",
        "tong_quat",
    ] = Field(description="quyền và nghĩa vụ → quyen_nghia_vu; căn cứ → can_cu.")


_SEED_BODY = f"""
WITH $pham_vi_bao_ve AS pv, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (l_tv:Quyen:{TOPIC_LABEL} {{id: 'ton_trong_va_bao_ve_tai_viet_nam', topic: '{TOPIC}'}})
WHERE pv = 'tai_viet_nam'
OPTIONAL MATCH (l_tv_dk:DieuKien:{TOPIC_LABEL} {{
  id: 'phu_hop_phap_luat_viet_nam_va_dieu_uoc_quoc_te', topic: '{TOPIC}'
}})
WHERE pv = 'tai_viet_nam'

OPTIONAL MATCH (l_nn_ct:ChuThe:{TOPIC_LABEL} {{
  id: 'nguoi_nuoc_ngoai_tai_viet_nam_trong_quan_he_voi_cong_dan_viet_nam', topic: '{TOPIC}'
}})
WHERE pv = 'nguoi_nuoc_ngoai_tai_viet_nam'
OPTIONAL MATCH (l_nn_qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'quyen_nghia_vu_nhu_cong_dan_viet_nam', topic: '{TOPIC}'
}})
WHERE pv = 'nguoi_nuoc_ngoai_tai_viet_nam'
OPTIONAL MATCH (l_nn_dk:DieuKien:{TOPIC_LABEL} {{
  id: 'ngoai_le_do_phap_luat_viet_nam_quy_dinh', topic: '{TOPIC}'
}})
WHERE pv = 'nguoi_nuoc_ngoai_tai_viet_nam'

OPTIONAL MATCH (l_cv_ct:ChuThe:{TOPIC_LABEL} {{id: 'cong_dan_viet_nam_o_nuoc_ngoai', topic: '{TOPIC}'}})
WHERE pv = 'cong_dan_viet_nam_o_nuoc_ngoai'
OPTIONAL MATCH (l_cv_q:Quyen:{TOPIC_LABEL} {{
  id: 'bao_ho_quyen_loi_cong_dan_viet_nam_o_nuoc_ngoai', topic: '{TOPIC}'
}})
WHERE pv = 'cong_dan_viet_nam_o_nuoc_ngoai'
OPTIONAL MATCH (l_cv_dk:DieuKien:{TOPIC_LABEL} {{
  id: 'phu_hop_phap_luat_viet_nam_nuoc_so_tai_va_quoc_te', topic: '{TOPIC}'
}})
WHERE pv = 'cong_dan_viet_nam_o_nuoc_ngoai'

OPTIONAL MATCH (l_cp:HanhVi:{TOPIC_LABEL} {{
  id: 'chinh_phu_quy_dinh_chi_tiet_giai_quyet', topic: '{TOPIC}'
}})
WHERE pv = 'chinh_phu_quy_dinh_chi_tiet'
OPTIONAL MATCH (l_cp_hq:HauQua:{TOPIC_LABEL} {{
  id: 'bao_dam_quyen_loi_va_thuc_hien_khoan_2_dieu_5', topic: '{TOPIC}'
}})
WHERE pv = 'chinh_phu_quy_dinh_chi_tiet'

OPTIONAL MATCH (l_tq:Quyen:{TOPIC_LABEL} {{id: 'bao_ve_quyen_loi_cac_ben', topic: '{TOPIC}'}})
WHERE pv IN ['tong_quat', 'khong_ro']

WITH wl, pv,
  collect(DISTINCT l_tv) + collect(DISTINCT l_tv_dk)
    + collect(DISTINCT l_nn_ct) + collect(DISTINCT l_nn_qd) + collect(DISTINCT l_nn_dk)
    + collect(DISTINCT l_cv_ct) + collect(DISTINCT l_cv_q) + collect(DISTINCT l_cv_dk)
    + collect(DISTINCT l_cp) + collect(DISTINCT l_cp_hq)
    + collect(DISTINCT l_tq) AS seed_nodes,
  CASE
    WHEN pv = 'tai_viet_nam' THEN
      [x IN collect(DISTINCT l_tv) + collect(DISTINCT l_tv_dk) WHERE x IS NOT NULL]
    WHEN pv = 'nguoi_nuoc_ngoai_tai_viet_nam' THEN
      [x IN collect(DISTINCT l_nn_ct) + collect(DISTINCT l_nn_qd) + collect(DISTINCT l_nn_dk)
       WHERE x IS NOT NULL]
    WHEN pv = 'cong_dan_viet_nam_o_nuoc_ngoai' THEN
      [x IN collect(DISTINCT l_cv_ct) + collect(DISTINCT l_cv_q) + collect(DISTINCT l_cv_dk)
       WHERE x IS NOT NULL]
    WHEN pv = 'chinh_phu_quy_dinh_chi_tiet' THEN
      [x IN collect(DISTINCT l_cp) + collect(DISTINCT l_cp_hq) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT l_tq) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: BaoVeQuyenLoiParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "pham_vi_bao_ve": params.pham_vi_bao_ve,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


bao_ve_quyen_loi_yeu_to_nuoc_ngoai = CypherTemplate(
    name="bao_ve_quyen_loi_yeu_to_nuoc_ngoai",
    description=(
        "Dùng cho nguyên tắc tôn trọng, bảo vệ, bảo hộ quyền lợi và quyền/nghĩa vụ "
        "của các bên theo Điều 121. Phân biệt quan hệ tại Việt Nam, người nước ngoài "
        "tại Việt Nam, công dân Việt Nam ở nước ngoài và trách nhiệm quy định chi tiết "
        "của Chính phủ. "
        "Ví dụ: Quan hệ có yếu tố nước ngoài tại Việt Nam được tôn trọng theo quy định nào?; "
        "Nhà nước Việt Nam bảo hộ công dân Việt Nam ở nước ngoài như thế nào?"
    ),
    params_schema=BaoVeQuyenLoiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
