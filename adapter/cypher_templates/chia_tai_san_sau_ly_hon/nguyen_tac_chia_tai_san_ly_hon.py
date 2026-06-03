"""Template 1 — NGUYÊN TẮC CHIA TÀI SẢN KHI LY HÔN (Đ59).

Coverage feat_llm stt: 1,2,3,4,6,7,8,9,29.
Seed kiểu semantic graph: traverse DIEU_CHINH / THUC_HIEN / DAN_TOI / AP_DUNG_KHI.
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

_ROUTER_FIELDS = ("khia_canh",)
_DIEU_59_WHITELIST = ["Luat_HNGD_2014_Dieu_59"]


class NguyenTacChiaTaiSanLyHonParams(BaseModel):
    khia_canh: Literal[
        "tong_quat",
        "thoa_thuan",
        "chia_doi",
        "yeu_to_chia",
        "cong_suc_noi_tro",
        "loi_vi_pham",
        "chia_hien_vat_gia_tri",
        "tai_san_rieng_nhap_chung",
        "bao_ve_vo_con",
        "tat_ca",
    ] = Field(
        description=(
            "Khía cạnh nguyên tắc chia tài sản khi ly hôn (Đ59). Map: "
            "'nguyên tắc'→tong_quat; 'thỏa thuận'→thoa_thuan; "
            "'chia đều/chia đôi/50/50'→chia_doi; 'yếu tố nào'→yeu_to_chia; "
            "'nội trợ/chăm con'→cong_suc_noi_tro; 'lỗi/ngoại tình/gian dối'→loi_vi_pham; "
            "'hiện vật/chênh lệch'→chia_hien_vat_gia_tri; "
            "'sáp nhập/trộn lẫn'→tai_san_rieng_nhap_chung; "
            "'vợ con/con chưa thành niên'→bao_ve_vo_con; không rõ→tat_ca."
        )
    )


_SEED_BODY = f"""
// ============================================================
// PHẦN 1 — SEED semantic graph (nguyên tắc Đ59)
// ============================================================
WITH $khia_canh AS kc, $whitelist_dieu_ids AS wl

MATCH (anchor:HanhVi:{TOPIC_LABEL} {{id: 'giai_quyet_tai_san_khi_ly_hon', topic: '{TOPIC}'}})

OPTIONAL MATCH (tt:ThoaThuan:{TOPIC_LABEL})-[:DIEU_CHINH]->(anchor)
WHERE kc IN ['tong_quat', 'thoa_thuan', 'tat_ca']

OPTIONAL MATCH (toa:HanhVi:{TOPIC_LABEL})-[:THUC_HIEN]->(anchor)
WHERE kc IN ['tong_quat', 'tat_ca']

OPTIONAL MATCH (anchor)-[:DAN_TOI]->(chia:HanhVi:{TOPIC_LABEL} {{id: 'chia_tai_san_chung_khi_ly_hon'}})
WHERE kc IN ['tong_quat', 'chia_doi', 'yeu_to_chia', 'cong_suc_noi_tro', 'loi_vi_pham',
             'chia_hien_vat_gia_tri', 'tat_ca']

OPTIONAL MATCH (chia)-[:AP_DUNG_KHI]->(dk:DieuKien:{TOPIC_LABEL})
WHERE kc IN ['yeu_to_chia', 'tat_ca']
  AND (kc = 'yeu_to_chia' OR dk.nhom = 'yeu_to_chia')

OPTIONAL MATCH (chia)-[:AP_DUNG_KHI]->(dk_nt:DieuKien:{TOPIC_LABEL})
WHERE kc = 'cong_suc_noi_tro'
  AND dk_nt.id IN [
    'lao_dong_gia_dinh_duoc_coi_nhu_lao_dong_co_thu_nhap',
    'cong_suc_dong_gop_tao_lap_duy_tri_phat_trien'
  ]

OPTIONAL MATCH (chia)-[:AP_DUNG_KHI]->(dk_loi:DieuKien:{TOPIC_LABEL} {{id: 'loi_vi_pham_quyen_nghia_vu_vo_chong'}})
WHERE kc IN ['loi_vi_pham', 'tat_ca']

OPTIONAL MATCH (chia)-[:DAN_TOI]->(hv:HanhVi:{TOPIC_LABEL} {{id: 'chia_bang_hien_vat'}})
WHERE kc IN ['chia_hien_vat_gia_tri', 'tat_ca']
OPTIONAL MATCH (hv)-[:DAN_TOI]->(hq_tt:HauQua:{TOPIC_LABEL} {{id: 'thanh_toan_chenh_lech_gia_tri'}})
WHERE kc IN ['chia_hien_vat_gia_tri', 'tat_ca']

OPTIONAL MATCH (xac:HanhVi:{TOPIC_LABEL} {{id: 'xac_dinh_tai_san_rieng_khi_ly_hon'}})
WHERE kc IN ['tai_san_rieng_nhap_chung', 'tat_ca']
OPTIONAL MATCH (xac)-[:DAN_TOI]->(hq_rieng:HauQua:{TOPIC_LABEL} {{id: 'chia_gia_tri_tai_san_rieng_da_sap_nhap'}})
WHERE kc IN ['tai_san_rieng_nhap_chung', 'tat_ca']

OPTIONAL MATCH (anchor)-[:DAN_TOI]->(bv:HauQua:{TOPIC_LABEL} {{id: 'bao_ve_vo_con_yeu_the'}})
WHERE kc IN ['bao_ve_vo_con', 'tat_ca']

WITH wl, kc,
  CASE kc
    WHEN 'yeu_to_chia' THEN
      [x IN collect(DISTINCT dk) WHERE x IS NOT NULL]
    WHEN 'thoa_thuan' THEN
      [x IN collect(DISTINCT tt) WHERE x IS NOT NULL]
    WHEN 'chia_doi' THEN
      [x IN collect(DISTINCT chia) WHERE x IS NOT NULL]
    WHEN 'cong_suc_noi_tro' THEN
      [x IN collect(DISTINCT dk_nt) WHERE x IS NOT NULL]
    WHEN 'loi_vi_pham' THEN
      [x IN collect(DISTINCT dk_loi) WHERE x IS NOT NULL]
    WHEN 'chia_hien_vat_gia_tri' THEN
      [x IN collect(DISTINCT hv) + collect(DISTINCT hq_tt) WHERE x IS NOT NULL]
    WHEN 'tai_san_rieng_nhap_chung' THEN
      [x IN collect(DISTINCT xac) + collect(DISTINCT hq_rieng) WHERE x IS NOT NULL]
    WHEN 'bao_ve_vo_con' THEN
      [x IN collect(DISTINCT bv) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT anchor) + collect(DISTINCT tt) + collect(DISTINCT toa)
           + collect(DISTINCT chia) + collect(DISTINCT dk) + collect(DISTINCT dk_nt)
           + collect(DISTINCT dk_loi) + collect(DISTINCT hv) + collect(DISTINCT hq_tt)
           + collect(DISTINCT xac) + collect(DISTINCT hq_rieng) + collect(DISTINCT bv)
       WHERE x IS NOT NULL]
  END AS seed_nodes
"""


def _params_builder(params: NguyenTacChiaTaiSanLyHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "khia_canh": params.khia_canh,
        "whitelist_dieu_ids": _DIEU_59_WHITELIST if use_wl else [],
    }


nguyen_tac_chia_tai_san_ly_hon = CypherTemplate(
    name="nguyen_tac_chia_tai_san_ly_hon",
    description=(
        "Nguyên tắc giải quyết tài sản của vợ chồng khi ly hôn (Đ59): thỏa thuận "
        "hoặc Tòa án giải quyết; chia tài sản chung có tính yếu tố (hoàn cảnh, "
        "công sức, lao động nội trợ, lỗi vi phạm); chia bằng hiện vật/thanh toán "
        "chênh lệch; tài sản riêng đã sáp nhập; bảo vệ vợ/con yếu thế. "
        "Phù hợp khi hỏi 'chia đôi có đúng không', 'yếu tố nào', 'nội trợ', "
        "'lỗi', 'nguyên tắc chia tài sản khi ly hôn'."
    ),
    params_schema=NguyenTacChiaTaiSanLyHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
