"""Template — đại diện tài sản chung có GCN chỉ ghi tên một bên (Đ26 k1)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.dai_dien_trach_nhiem_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("loai_giay_chung_nhan",)
_DIEU_26_WHITELIST = ["Luat_HNGD_2014_Dieu_26"]


class DaiDienTaiSanChungGcnMotBenParams(BaseModel):
    loai_giay_chung_nhan: Literal[
        "gcn_quyen_so_huu", "gcn_quyen_su_dung", "khong_ro"
    ] = Field(default="khong_ro")
    nguoi_dung_ten: Literal["vo", "chong", "mot_ben", "khong_ro"] = Field(
        default="khong_ro"
    )
    hanh_vi_giao_dich: Literal[
        "xac_lap", "thuc_hien", "cham_dut", "ban_chuyen_nhuong", "tong_quat"
    ] = Field(default="tong_quat")
    co_su_dong_y_ben_kia: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")


_SEED_BODY = f"""
WITH $loai_giay_chung_nhan AS lgc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (hv:HanhVi:{TOPIC_LABEL} {{
  id: 'giao_dich_tai_san_chung_gcn_mot_ben', topic: '{TOPIC}'
}})
OPTIONAL MATCH (lts:LoaiTaiSan:{TOPIC_LABEL} {{
  id: 'tai_san_chung_co_gcn_chi_ghi_ten_mot_ben', topic: '{TOPIC}'
}})
OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{
  id: 'gcn_chi_ghi_ten_mot_ben', topic: '{TOPIC}'
}})
OPTIONAL MATCH (vb_sh:VanBanPhapLy:{TOPIC_LABEL} {{
  id: 'gcn_quyen_so_huu_chi_ghi_ten_mot_ben', topic: '{TOPIC}'
}})
OPTIONAL MATCH (vb_sd:VanBanPhapLy:{TOPIC_LABEL} {{
  id: 'gcn_quyen_su_dung_chi_ghi_ten_mot_ben', topic: '{TOPIC}'
}})
OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{
  id: 'ap_dung_quy_dinh_dai_dien_dieu_24_25', topic: '{TOPIC}'
}})

WITH wl, lgc,
  [x IN collect(DISTINCT hv) + collect(DISTINCT lts) + collect(DISTINCT dk)
      + collect(DISTINCT vb_sh) + collect(DISTINCT vb_sd) + collect(DISTINCT hq)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE lgc
    WHEN 'gcn_quyen_so_huu' THEN
      [x IN collect(DISTINCT vb_sh) WHERE x IS NOT NULL]
    WHEN 'gcn_quyen_su_dung' THEN
      [x IN collect(DISTINCT vb_sd) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT vb_sh) + collect(DISTINCT vb_sd)
          + collect(DISTINCT hq)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: DaiDienTaiSanChungGcnMotBenParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "whitelist_dieu_ids": _DIEU_26_WHITELIST if use_wl else [],
        **params.model_dump(),
    }


dai_dien_tai_san_chung_gcn_mot_ben = CypherTemplate(
    name="dai_dien_tai_san_chung_gcn_mot_ben",
    description=(
        "Quy tắc đại diện khi tài sản chung có GCN quyền sở hữu/sử dụng chỉ ghi "
        "tên một bên (Đ26 k1). Phù hợp khi có 'sổ đỏ', 'sổ hồng', 'chỉ đứng tên' "
        "mà KHÔNG hỏi hiệu lực/vô hiệu/ngay tình (Đ26 k2)."
    ),
    params_schema=DaiDienTaiSanChungGcnMotBenParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
