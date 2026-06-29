"""Template 2 — NGUYÊN TẮC CHẾ ĐỘ TÀI SẢN (Đ29-32, áp dụng cho mọi chế độ).

Trả lời câu hỏi về:
- Nguyên tắc bình đẳng giữa vợ và chồng về quyền/nghĩa vụ tài sản (Đ29 K1).
- Nghĩa vụ đảm bảo nhu cầu thiết yếu của gia đình (Đ29 K2, Đ30).
- Bồi thường thiệt hại khi xâm phạm quyền/lợi ích (Đ29 K3).
- Giao dịch liên quan đến nhà ở duy nhất (Đ31).
- Giao dịch với người thứ ba ngay tình về tài khoản ngân hàng/chứng khoán/
  động sản không phải đăng ký (Đ32).

Coverage: Q4 (một phần), Q17 (một phần) — phần "nguyên tắc chung".

Lưu ý: Đ29-32 áp dụng cho cả chế độ tài sản theo luật định LẪN theo thỏa thuận
(via AP_DUNG_CHO_CHE_DO {che_do:'tat_ca'}).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.tai_san._common import (
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh",)

_DIEU_WHITELIST = [
    "Luat_HNGD_2014_Dieu_29",
    "Luat_HNGD_2014_Dieu_30",
    "Luat_HNGD_2014_Dieu_31",
    "Luat_HNGD_2014_Dieu_32",
]


class NguyenTacCheDoTaiSanParams(BaseModel):
    khia_canh: Literal[
        "binh_dang",
        "nhu_cau_thiet_yeu_gia_dinh",
        "giao_dich_nha_o_duy_nhat",
        "giao_dich_nguoi_thu_ba_ngay_tinh",
        "tat_ca",
    ] = Field(
        description=(
            "Khía cạnh nguyên tắc chế độ tài sản mà câu hỏi tập trung:\n"
            "  • 'binh_dang' (Đ29 K1): bình đẳng vợ chồng về quyền/nghĩa vụ "
            "tài sản chung, không phân biệt lao động trong gia đình hay có thu "
            "nhập.\n"
            "  • 'nhu_cau_thiet_yeu_gia_dinh' (Đ29 K2 + Đ30): nghĩa vụ đáp ứng "
            "nhu cầu thiết yếu của gia đình; đóng góp tài sản riêng khi không "
            "đủ tài sản chung.\n"
            "  • 'giao_dich_nha_o_duy_nhat' (Đ31): giao dịch liên quan đến nhà "
            "ở duy nhất phải có thỏa thuận; ngoại lệ nhà là tài sản riêng.\n"
            "  • 'giao_dich_nguoi_thu_ba_ngay_tinh' (Đ32): người đứng tên tài "
            "khoản/chiếm hữu động sản không phải đăng ký được coi là có quyền "
            "trong giao dịch ngay tình.\n"
            "  • 'tat_ca': khi câu hỏi tổng quát về 'chế độ tài sản' hoặc 'các "
            "nguyên tắc' nói chung, không nhắc đến khía cạnh cụ thể."
        )
    )


_SEED_BODY = f"""
// ============================================================
// PHẦN 1 — SEED semantic graph (nguyên tắc Đ29-32)
// ============================================================
WITH $khia_canh AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (quyen_bd:Quyen:{TOPIC_LABEL} {{id: 'quyen_binh_dang_tai_san_chung'}})
WHERE kc IN ['binh_dang', 'tat_ca']
OPTIONAL MATCH (hv_bd:HanhVi:{TOPIC_LABEL} {{id: 'tao_lap_chiem_huu_su_dung_dinh_doat_tai_san_chung'}})
WHERE kc IN ['binh_dang', 'tat_ca']
OPTIONAL MATCH (hv_bd)-[:DAN_TOI]->(hq_bd:HauQua:{TOPIC_LABEL})
WHERE kc IN ['binh_dang', 'tat_ca']

OPTIONAL MATCH (hv_nc:HanhVi:{TOPIC_LABEL} {{id: 'dap_ung_nhu_cau_thiet_yeu_gia_dinh'}})
WHERE kc IN ['nhu_cau_thiet_yeu_gia_dinh', 'tat_ca']
OPTIONAL MATCH (hv_nc)-[:AP_DUNG_KHI]->(dk_nc:DieuKien:{TOPIC_LABEL})
WHERE kc IN ['nhu_cau_thiet_yeu_gia_dinh', 'tat_ca']
OPTIONAL MATCH (nv_nc:NghiaVu:{TOPIC_LABEL})
WHERE kc IN ['nhu_cau_thiet_yeu_gia_dinh', 'tat_ca']
  AND nv_nc.id IN [
    'nghia_vu_dap_ung_nhu_cau_thiet_yeu_gia_dinh',
    'nghia_vu_dong_gop_tai_san_rieng_khi_thieu_chung'
  ]

OPTIONAL MATCH (lts_nha:LoaiTaiSan:{TOPIC_LABEL} {{id: 'nha_o_duy_nhat'}})
WHERE kc IN ['giao_dich_nha_o_duy_nhat', 'tat_ca']
OPTIONAL MATCH (lts_nha)-[:LIEN_QUAN]->(hv_nha:HanhVi:{TOPIC_LABEL} {{id: 'giao_dich_nha_o_duy_nhat'}})
WHERE kc IN ['giao_dich_nha_o_duy_nhat', 'tat_ca']
OPTIONAL MATCH (hv_nha)-[:AP_DUNG_KHI]->(dk_nha:DieuKien:{TOPIC_LABEL})
WHERE kc IN ['giao_dich_nha_o_duy_nhat', 'tat_ca']
OPTIONAL MATCH (hv_nha)-[:DAN_TOI]->(hq_nha:HauQua:{TOPIC_LABEL})
WHERE kc IN ['giao_dich_nha_o_duy_nhat', 'tat_ca']
OPTIONAL MATCH (hv_nha)-[:CO_NGOAI_LE]->(nl_nha:TruongHopNgoaiLe:{TOPIC_LABEL})
WHERE kc IN ['giao_dich_nha_o_duy_nhat', 'tat_ca']
OPTIONAL MATCH (hv_nha)-[:YEU_CAU_THOA_THUAN]->(tt_nha:ThoaThuan:{TOPIC_LABEL})
WHERE kc IN ['giao_dich_nha_o_duy_nhat', 'tat_ca']

OPTIONAL MATCH (hv_nt3:HanhVi:{TOPIC_LABEL} {{id: 'giao_dich_nguoi_thu_ba_ngay_tinh'}})
WHERE kc IN ['giao_dich_nguoi_thu_ba_ngay_tinh', 'tat_ca']
OPTIONAL MATCH (hv_nt3)-[:TAC_DONG_LEN]->(lts_nt3:LoaiTaiSan:{TOPIC_LABEL})
WHERE kc IN ['giao_dich_nguoi_thu_ba_ngay_tinh', 'tat_ca']
OPTIONAL MATCH (hv_nt3)-[:AP_DUNG_KHI]->(dk_nt3:DieuKien:{TOPIC_LABEL})
WHERE kc IN ['giao_dich_nguoi_thu_ba_ngay_tinh', 'tat_ca']
OPTIONAL MATCH (hv_nt3)-[:DAN_TOI]->(hq_nt3:HauQua:{TOPIC_LABEL})
WHERE kc IN ['giao_dich_nguoi_thu_ba_ngay_tinh', 'tat_ca']

WITH wl, kc,
  [x IN collect(DISTINCT quyen_bd) + collect(DISTINCT hv_bd) + collect(DISTINCT hq_bd)
       + collect(DISTINCT hv_nc) + collect(DISTINCT dk_nc) + collect(DISTINCT nv_nc)
       + collect(DISTINCT lts_nha) + collect(DISTINCT hv_nha) + collect(DISTINCT dk_nha)
       + collect(DISTINCT hq_nha) + collect(DISTINCT nl_nha) + collect(DISTINCT tt_nha)
       + collect(DISTINCT hv_nt3) + collect(DISTINCT lts_nt3) + collect(DISTINCT dk_nt3)
       + collect(DISTINCT hq_nt3)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'binh_dang' THEN
      [x IN collect(DISTINCT quyen_bd) + collect(DISTINCT hv_bd) + collect(DISTINCT hq_bd)
       WHERE x IS NOT NULL]
    WHEN 'nhu_cau_thiet_yeu_gia_dinh' THEN
      [x IN collect(DISTINCT hv_nc) + collect(DISTINCT dk_nc) + collect(DISTINCT nv_nc)
       WHERE x IS NOT NULL]
    WHEN 'giao_dich_nha_o_duy_nhat' THEN
      [x IN collect(DISTINCT lts_nha) + collect(DISTINCT hv_nha) + collect(DISTINCT dk_nha)
           + collect(DISTINCT hq_nha) + collect(DISTINCT nl_nha) + collect(DISTINCT tt_nha)
       WHERE x IS NOT NULL]
    WHEN 'giao_dich_nguoi_thu_ba_ngay_tinh' THEN
      [x IN collect(DISTINCT hv_nt3) + collect(DISTINCT lts_nt3) + collect(DISTINCT dk_nt3)
           + collect(DISTINCT hq_nt3)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT quyen_bd) + collect(DISTINCT hv_bd) + collect(DISTINCT hq_bd)
           + collect(DISTINCT hv_nc) + collect(DISTINCT dk_nc) + collect(DISTINCT nv_nc)
           + collect(DISTINCT lts_nha) + collect(DISTINCT hv_nha) + collect(DISTINCT dk_nha)
           + collect(DISTINCT hq_nha) + collect(DISTINCT nl_nha) + collect(DISTINCT tt_nha)
           + collect(DISTINCT hv_nt3) + collect(DISTINCT lts_nt3) + collect(DISTINCT dk_nt3)
           + collect(DISTINCT hq_nt3)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: NguyenTacCheDoTaiSanParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "khia_canh": params.khia_canh,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


nguyen_tac_che_do_tai_san = CypherTemplate(
    name="nguyen_tac_che_do_tai_san",
    description=(
        "Nguyên tắc chế độ tài sản của vợ chồng (Điều 29-32) — áp dụng KHÔNG "
        "phụ thuộc chế độ luật định hay thỏa thuận. Bao gồm: nguyên tắc bình "
        "đẳng vợ chồng về tài sản chung (Đ29 K1); nghĩa vụ đáp ứng nhu cầu "
        "thiết yếu gia đình (Đ29 K2, Đ30); bồi thường khi xâm phạm quyền (Đ29 "
        "K3); giao dịch liên quan nhà ở duy nhất (Đ31); giao dịch với người "
        "thứ ba ngay tình về tài khoản/động sản không phải đăng ký (Đ32). "
        "Phù hợp khi câu hỏi hỏi VỀ NGUYÊN TẮC TỔNG QUÁT hoặc về 1 trong 4 "
        "khía cạnh trên."
    ),
    params_schema=NguyenTacCheDoTaiSanParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
