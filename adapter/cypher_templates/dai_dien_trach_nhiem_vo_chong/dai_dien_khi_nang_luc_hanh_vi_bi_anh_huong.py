"""Template — đại diện khi năng lực hành vi dân sự bị ảnh hưởng (Đ24 k3)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("tinh_trang_nang_luc", "boi_canh")
_DIEU_24_WHITELIST = ["Luat_HNGD_2014_Dieu_24"]


class DaiDienKhiNangLucHanhViBiAnhHuongParams(BaseModel):
    tinh_trang_nang_luc: Literal["mat_nang_luc", "han_che_nang_luc", "khong_ro"] = Field(
        default="khong_ro"
    )
    boi_canh: Literal[
        "giao_dich_dan_su", "quyen_nghia_vu_phai_tu_minh", "ly_hon", "khong_ro"
    ] = Field(default="khong_ro")
    can_cu_dai_dien: Literal[
        "du_dieu_kien_giam_ho",
        "toa_an_chi_dinh",
        "toa_an_chi_dinh_nguoi_khac",
        "chua_ro",
    ] = Field(default="chua_ro")


_SEED_BODY = f"""
WITH $tinh_trang_nang_luc AS ttnl, $boi_canh AS bc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (hv_mat:HanhVi:{TOPIC_LABEL} {{
  id: 'dai_dien_khi_mat_nang_luc_hanh_vi_dan_su', topic: '{TOPIC}'
}})
OPTIONAL MATCH (hv_hc:HanhVi:{TOPIC_LABEL} {{
  id: 'dai_dien_khi_han_che_nang_luc_hanh_vi_dan_su', topic: '{TOPIC}'
}})
OPTIONAL MATCH (hv_ly:HanhVi:{TOPIC_LABEL} {{
  id: 'toa_an_chi_dinh_nguoi_khac_dai_dien_khi_ly_hon', topic: '{TOPIC}'
}})
OPTIONAL MATCH (dk_mat:DieuKien:{TOPIC_LABEL} {{
  id: 'mat_nang_luc_hanh_vi_dan_su', topic: '{TOPIC}'
}})
OPTIONAL MATCH (dk_hc:DieuKien:{TOPIC_LABEL} {{
  id: 'han_che_nang_luc_hanh_vi_dan_su', topic: '{TOPIC}'
}})
OPTIONAL MATCH (dk_gh:DieuKien:{TOPIC_LABEL} {{
  id: 'ben_kia_du_dieu_kien_lam_nguoi_giam_ho', topic: '{TOPIC}'
}})
OPTIONAL MATCH (dk_ta:DieuKien:{TOPIC_LABEL} {{
  id: 'ben_kia_duoc_toa_an_chi_dinh_dai_dien', topic: '{TOPIC}'
}})
OPTIONAL MATCH (dk_ly:DieuKien:{TOPIC_LABEL} {{
  id: 'yeu_cau_ly_hon_khi_ben_kia_mat_nang_luc', topic: '{TOPIC}'
}})
OPTIONAL MATCH (nl:TruongHopNgoaiLe:{TOPIC_LABEL} {{
  id: 'quyen_nghia_vu_phai_tu_minh_thuc_hien', topic: '{TOPIC}'
}})

WITH wl, ttnl, bc,
  [x IN collect(DISTINCT hv_mat) + collect(DISTINCT hv_hc) + collect(DISTINCT hv_ly)
      + collect(DISTINCT dk_mat) + collect(DISTINCT dk_hc) + collect(DISTINCT dk_gh)
      + collect(DISTINCT dk_ta) + collect(DISTINCT dk_ly) + collect(DISTINCT nl)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN bc = 'quyen_nghia_vu_phai_tu_minh' THEN
      [x IN collect(DISTINCT nl) WHERE x IS NOT NULL]
    WHEN bc = 'ly_hon' THEN
      [x IN collect(DISTINCT dk_ly) + collect(DISTINCT hv_ly) WHERE x IS NOT NULL]
    WHEN ttnl = 'mat_nang_luc' THEN
      [x IN collect(DISTINCT hv_mat) + collect(DISTINCT dk_mat) + collect(DISTINCT dk_gh)
       WHERE x IS NOT NULL]
    WHEN ttnl = 'han_che_nang_luc' THEN
      [x IN collect(DISTINCT hv_hc) + collect(DISTINCT dk_hc) + collect(DISTINCT dk_ta)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hv_mat) + collect(DISTINCT hv_hc) + collect(DISTINCT hv_ly)
          + collect(DISTINCT dk_mat) + collect(DISTINCT dk_hc) + collect(DISTINCT nl)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: DaiDienKhiNangLucHanhViBiAnhHuongParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "whitelist_dieu_ids": _DIEU_24_WHITELIST if use_wl else [],
        **params.model_dump(),
    }


dai_dien_khi_nang_luc_hanh_vi_bi_anh_huong = CypherTemplate(
    name="dai_dien_khi_nang_luc_hanh_vi_bi_anh_huong",
    description=(
        "Đại diện khi mất/hạn chế năng lực hành vi dân sự, ngoại lệ phải tự mình "
        "thực hiện và chỉ định đại diện trong vụ ly hôn (Đ24 k3). Phù hợp khi có "
        "'mất năng lực', 'hạn chế năng lực', 'giám hộ', 'Tòa án chỉ định', "
        "'ai đại diện trong vụ ly hôn'."
    ),
    params_schema=DaiDienKhiNangLucHanhViBiAnhHuongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
