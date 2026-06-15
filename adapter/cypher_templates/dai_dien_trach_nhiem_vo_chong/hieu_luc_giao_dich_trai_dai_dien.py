"""Template — hiệu lực giao dịch trái quy định đại diện (Đ26 k2)."""
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

_ROUTER_FIELDS = ("trong_tam_hau_qua",)
_DIEU_26_WHITELIST = ["Luat_HNGD_2014_Dieu_26"]


class HieuLucGiaoDichTraiDaiDienParams(BaseModel):
    hanh_vi_giao_dich: Literal[
        "ban", "chuyen_nhuong", "xac_lap", "thuc_hien", "cham_dut", "khac"
    ] = Field(default="khac")
    tinh_trang_nguoi_thu_ba: Literal["ngay_tinh", "khong_ngay_tinh", "khong_ro"] = Field(
        default="khong_ro"
    )
    trong_tam_hau_qua: Literal[
        "vo_hieu", "bao_ve_ngay_tinh", "co_ngoai_le", "tong_quat"
    ] = Field(default="tong_quat")


_SEED_BODY = f"""
WITH $tinh_trang_nguoi_thu_ba AS ttnt, $trong_tam_hau_qua AS tthq, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (hv:HanhVi:{TOPIC_LABEL} {{
  id: 'mot_ben_tu_minh_giao_dich_trai_quy_dinh_dai_dien', topic: '{TOPIC}'
}})
OPTIONAL MATCH (gd_tb: GiaoDich:{TOPIC_LABEL} {{
  id: 'giao_dich_voi_nguoi_thu_ba', topic: '{TOPIC}'
}})
OPTIONAL MATCH (gd_mb:GiaoDich:{TOPIC_LABEL} {{
  id: 'giao_dich_mua_ban_chuyen_nhuong_tai_san_chung', topic: '{TOPIC}'
}})
OPTIONAL MATCH (hq_vh:HauQua:{TOPIC_LABEL} {{
  id: 'giao_dich_vo_hieu_do_trai_quy_dinh_dai_dien', topic: '{TOPIC}'
}})
OPTIONAL MATCH (nl:TruongHopNgoaiLe:{TOPIC_LABEL} {{
  id: 'ngoai_le_nguoi_thu_ba_ngay_tinh_duoc_bao_ve', topic: '{TOPIC}'
}})
OPTIONAL MATCH (ct:ChuThe:{TOPIC_LABEL} {{
  id: 'nguoi_thu_ba_ngay_tinh', topic: '{TOPIC}'
}})
OPTIONAL MATCH (hq_bv:HauQua:{TOPIC_LABEL} {{
  id: 'giao_dich_duoc_bao_ve_vi_nguoi_thu_ba_ngay_tinh', topic: '{TOPIC}'
}})

WITH wl, ttnt, tthq,
  [x IN collect(DISTINCT hv) + collect(DISTINCT gd_tb) + collect(DISTINCT gd_mb)
      + collect(DISTINCT hq_vh) + collect(DISTINCT nl) + collect(DISTINCT ct)
      + collect(DISTINCT hq_bv)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN ttnt = 'ngay_tinh' OR tthq = 'bao_ve_ngay_tinh' THEN
      [x IN collect(DISTINCT hq_vh) + collect(DISTINCT nl) + collect(DISTINCT ct)
          + collect(DISTINCT hq_bv)
       WHERE x IS NOT NULL]
    WHEN tthq = 'co_ngoai_le' THEN
      [x IN collect(DISTINCT hq_vh) + collect(DISTINCT nl) + collect(DISTINCT hq_bv)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hq_vh) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: HieuLucGiaoDichTraiDaiDienParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "whitelist_dieu_ids": _DIEU_26_WHITELIST if use_wl else [],
        **params.model_dump(),
    }


hieu_luc_giao_dich_trai_dai_dien = CypherTemplate(
    name="hieu_luc_giao_dich_trai_dai_dien",
    description=(
        "Hậu quả giao dịch trái quy định đại diện: vô hiệu và ngoại lệ bảo vệ "
        "người thứ ba ngay tình (Đ26 k2). Ưu tiên khi có 'vô hiệu', 'hiệu lực', "
        "'ngay tình', 'mọi trường hợp'."
    ),
    params_schema=HieuLucGiaoDichTraiDaiDienParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
