"""Template — nghĩa vụ và hợp đồng giữa các bên chung sống (Đ16 K1)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.chung_song_nhu_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("loai_quan_he",)
_DIEU_16_K1_WHITELIST = ["Luat_HNGD_2014_Dieu_16_Khoan_1"]


class GiaiQuyetNghiaVuVaHopDongParams(BaseModel):
    loai_quan_he: Literal["nghia_vu", "hop_dong", "ca_hai", "tong_quat"] = Field(
        description="Nợ/nghĩa vụ -> nghia_vu; hợp đồng -> hop_dong; cả hai -> ca_hai."
    )
    co_thoa_thuan: Literal["co", "khong", "khong_ro"] = Field(
        description="Có thỏa thuận -> co; không -> khong; không nêu -> khong_ro."
    )


_SEED_BODY = f"""
WITH $lq AS lq, $ct AS ct, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (hv_nv:HanhVi:{TOPIC_LABEL} {{id: 'giai_quyet_nghia_vu_giua_cac_ben', topic: '{TOPIC}'}})
WHERE lq IN ['nghia_vu', 'ca_hai', 'tong_quat']
OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_tai_san_giua_cac_ben_chung_song', topic: '{TOPIC}'}})
WHERE hv_nv IS NOT NULL

OPTIONAL MATCH (hv_hd:HanhVi:{TOPIC_LABEL} {{id: 'giai_quyet_hop_dong_giua_cac_ben', topic: '{TOPIC}'}})
WHERE lq IN ['hop_dong', 'ca_hai', 'tong_quat']

OPTIONAL MATCH (tt:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_tai_san_nghia_vu_hop_dong', topic: '{TOPIC}'}})
WHERE ct IN ['co', 'khong_ro']
OPTIONAL MATCH (dk_co:DieuKien:{TOPIC_LABEL} {{id: 'co_thoa_thuan_giua_cac_ben', topic: '{TOPIC}'}})
WHERE tt IS NOT NULL
OPTIONAL MATCH (hq_co:HauQua:{TOPIC_LABEL} {{id: 'ap_dung_thoa_thuan_giua_cac_ben', topic: '{TOPIC}'}})
WHERE tt IS NOT NULL

OPTIONAL MATCH (dk_khong:DieuKien:{TOPIC_LABEL} {{id: 'khong_co_thoa_thuan_giua_cac_ben', topic: '{TOPIC}'}})
WHERE ct IN ['khong', 'khong_ro']
OPTIONAL MATCH (hq_bl:HauQua:{TOPIC_LABEL} {{id: 'ap_dung_bo_luat_dan_su_va_phap_luat_lien_quan', topic: '{TOPIC}'}})
WHERE dk_khong IS NOT NULL

WITH wl, lq, ct,
  [x IN collect(DISTINCT hv_nv) + collect(DISTINCT nv)
       + collect(DISTINCT hv_hd) + collect(DISTINCT tt)
       + collect(DISTINCT dk_co) + collect(DISTINCT hq_co)
       + collect(DISTINCT dk_khong) + collect(DISTINCT hq_bl)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE ct
    WHEN 'co' THEN
      [x IN collect(DISTINCT tt) + collect(DISTINCT dk_co) + collect(DISTINCT hq_co)
       WHERE x IS NOT NULL]
    WHEN 'khong' THEN
      [x IN collect(DISTINCT dk_khong) + collect(DISTINCT hq_bl) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT tt) + collect(DISTINCT dk_co) + collect(DISTINCT hq_co)
           + collect(DISTINCT dk_khong) + collect(DISTINCT hq_bl)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: GiaiQuyetNghiaVuVaHopDongParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "lq": params.loai_quan_he,
        "ct": params.co_thoa_thuan,
        "whitelist_dieu_ids": _DIEU_16_K1_WHITELIST if use_wl else [],
    }


giai_quyet_nghia_vu_va_hop_dong = CypherTemplate(
    name="giai_quyet_nghia_vu_va_hop_dong",
    description=(
        "Giải quyết nợ, nghĩa vụ hoặc hợp đồng giữa các bên chung sống không đăng ký "
        "theo Đ16 K1: thỏa thuận trước, không có thì áp dụng BLDS. Không dùng cho "
        "câu chỉ hỏi chia tài sản — chọn template tài sản riêng."
    ),
    params_schema=GiaiQuyetNghiaVuVaHopDongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
