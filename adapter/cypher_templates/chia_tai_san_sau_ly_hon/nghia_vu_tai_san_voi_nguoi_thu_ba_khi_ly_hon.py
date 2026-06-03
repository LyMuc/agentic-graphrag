"""Template 3 — NGHĨA VỤ TÀI SẢN VỚI NGƯỜI THỨ BA KHI LY HÔN (Đ60).

Coverage feat_llm stt: 10,11,26,27.
Seed kiểu semantic graph: DAN_TOI + AP_DUNG_KHI (tranh chấp).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.chia_tai_san_sau_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("loai_nghia_vu",)
_DIEU_60_WHITELIST = ["Luat_HNGD_2014_Dieu_60"]


class NghiaVuTaiSanVoiNguoiThuBaParams(BaseModel):
    loai_nghia_vu: Literal[
        "no_chung",
        "vay_kinh_doanh",
        "vay_ca_nhan",
        "tranh_chap",
        "quyen_nghia_vu_nguoi_thu_ba",
        "khong_ro",
    ] = Field(
        default="khong_ro",
        description=(
            "Loại nghĩa vụ. Map: 'nợ chung'→no_chung; 'vay làm ăn/kinh doanh'→vay_kinh_doanh; "
            "'vay riêng/không sử dụng'→vay_ca_nhan; 'tranh chấp'→tranh_chap."
        ),
    )
    nguoi_thu_ba: Literal["ngan_hang", "chu_no", "nguoi_thu_ba", "khong_ro"] = Field(
        default="khong_ro",
        description="Map 'ngân hàng'→ngan_hang; 'chủ nợ'→chu_no.",
    )
    thoi_diem_no: Literal[
        "truoc_hon_nhan", "trong_hon_nhan", "sau_ly_hon", "khong_ro"
    ] = Field(default="khong_ro")
    muc_dich_no: Literal[
        "kinh_doanh", "nhu_cau_gia_dinh", "ca_nhan", "khong_ro"
    ] = Field(default="khong_ro")


_SEED_BODY = f"""
// ============================================================
// PHẦN 1 — SEED semantic graph (nghĩa vụ người thứ ba — Đ60)
// ============================================================
WITH $loai_nghia_vu AS lnv, $whitelist_dieu_ids AS wl

MATCH (anchor:HanhVi:{TOPIC_LABEL} {{
  id: 'giai_quyet_quyen_nghia_vu_nguoi_thu_ba_khi_ly_hon',
  topic: '{TOPIC}'
}})

OPTIONAL MATCH (anchor)-[:DAN_TOI]->(hq:HauQua:{TOPIC_LABEL} {{
  id: 'quyen_nghia_vu_voi_nguoi_thu_ba_van_hieu_luc'
}})

OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{id: 'co_tranh_chap_quyen_nghia_vu_tai_san'}})
      -[:AP_DUNG_KHI]->(anchor)
WHERE lnv IN ['tranh_chap', 'vay_ca_nhan', 'khong_ro']

WITH wl, lnv,
  CASE
    WHEN lnv = 'tranh_chap' THEN
      [x IN collect(DISTINCT hq) + collect(DISTINCT dk) WHERE x IS NOT NULL]
    WHEN lnv = 'vay_ca_nhan' THEN
      [x IN collect(DISTINCT hq) + collect(DISTINCT dk) WHERE x IS NOT NULL]
    WHEN lnv IN ['no_chung', 'vay_kinh_doanh', 'quyen_nghia_vu_nguoi_thu_ba'] THEN
      [x IN collect(DISTINCT hq) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT anchor) + collect(DISTINCT hq) + collect(DISTINCT dk)
       WHERE x IS NOT NULL]
  END AS seed_nodes
"""


def _params_builder(params: NghiaVuTaiSanVoiNguoiThuBaParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "whitelist_dieu_ids": _DIEU_60_WHITELIST if use_wl else [],
        **params.model_dump(),
    }


nghia_vu_tai_san_voi_nguoi_thu_ba_khi_ly_hon = CypherTemplate(
    name="nghia_vu_tai_san_voi_nguoi_thu_ba_khi_ly_hon",
    description=(
        "Quyền, nghĩa vụ tài sản của vợ chồng với người thứ ba khi ly hôn (Đ60): "
        "nợ, vay ngân hàng, chủ nợ, hiệu lực sau ly hôn, tranh chấp quyền nghĩa vụ. "
        "Phù hợp khi câu hỏi có 'nợ', 'vay', 'trả nợ', 'ngân hàng', 'chủ nợ', "
        "'người thứ ba', 'nghĩa vụ tài sản'."
    ),
    params_schema=NghiaVuTaiSanVoiNguoiThuBaParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
