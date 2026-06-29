"""Template 7 — THỎA THUẬN VỀ CHẾ ĐỘ TÀI SẢN CỦA VỢ CHỒNG (Đ47-50).

Trả lời câu hỏi về chế độ tài sản theo thỏa thuận (tiền hôn nhân hoặc các
loại thỏa thuận liên quan tới tài sản vợ chồng), bao gồm:
- Đ47: Thỏa thuận xác lập chế độ tài sản (hình thức, thời điểm hiệu lực).
- Đ48: Nội dung cơ bản của thỏa thuận.
- Đ49: Sửa đổi, bổ sung thỏa thuận.
- Đ50: Các trường hợp thỏa thuận bị vô hiệu.

Coverage: Q12 (một phần — để dành tài sản riêng), Q19 (nhánh thỏa thuận),
Q22 (nội dung Đ48), Q24 (viết tay không công chứng — vô hiệu), Q25 (cần công
chứng?), Q26 (hợp đồng phân chia bị vô hiệu).
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.tai_san._common import (
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh",)


class ThoaThuanCheDoParams(BaseModel):
    khia_canh: Literal[
        "xac_lap",
        "noi_dung",
        "sua_doi",
        "vo_hieu",
        "tat_ca",
    ] = Field(
        description=(
            "Khía cạnh thỏa thuận chế độ tài sản:\n"
            "  • 'xac_lap' (Đ47): hình thức (văn bản, công chứng, chứng thực), "
            "thời điểm lập (trước kết hôn), thời điểm có hiệu lực (ngày đăng ký "
            "kết hôn). Phù hợp với câu hỏi 'cần công chứng?', 'viết tay được "
            "không?', 'khi nào có hiệu lực?'.\n"
            "  • 'noi_dung' (Đ48): nội dung cơ bản — tài sản chung/riêng, "
            "quyền/nghĩa vụ, điều kiện phân chia, lacuna áp dụng Đ29-32.\n"
            "  • 'sua_doi' (Đ49): quyền sửa đổi/bổ sung, hình thức sửa đổi.\n"
            "  • 'vo_hieu' (Đ50): các trường hợp thỏa thuận bị Tòa án tuyên "
            "vô hiệu (vi phạm BLDS, Đ29-32, quyền thành viên gia đình).\n"
            "  • 'tat_ca': khi câu hỏi tổng quát hoặc bao gồm nhiều khía cạnh."
        )
    )
    nhom_can_cu_vo_hieu_thoa_thuan: Optional[Literal[
        "dieu_kien_giao_dich",
        "vi_pham_d29_d32",
        "quyen_thanh_vien_gia_dinh",
        "tat_ca",
    ]] = Field(
        default="tat_ca",
        description=(
            "Chỉ dùng khi `khia_canh = 'vo_hieu'`. Lọc nhóm căn cứ vô hiệu "
            "thỏa thuận (Đ50 K1 a/b/c):\n"
            "  • 'dieu_kien_giao_dich' (a): không tuân thủ điều kiện hiệu lực "
            "của giao dịch theo BLDS.\n"
            "  • 'vi_pham_d29_d32' (b): vi phạm Đ29, 30, 31, 32.\n"
            "  • 'quyen_thanh_vien_gia_dinh' (c): vi phạm nghiêm trọng quyền "
            "cấp dưỡng, thừa kế, quyền/lợi ích của cha/mẹ/con/thành viên gia "
            "đình.\n"
            "  • 'tat_ca' (mặc định): cả 3 nhóm."
        ),
    )


_DIEU_WHITELIST = [
    "Luat_HNGD_2014_Dieu_47",
    "Luat_HNGD_2014_Dieu_48",
    "Luat_HNGD_2014_Dieu_49",
    "Luat_HNGD_2014_Dieu_50",
]

_SEED_BODY = f"""
// ============================================================
// PHẦN 1 — SEED semantic graph (thỏa thuận chế độ tài sản Đ47-50)
// ============================================================
WITH $khia_canh AS kc, $nhom_can_cu_vo_hieu_thoa_thuan AS nhom, $whitelist_dieu_ids AS wl

MATCH (anchor:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_che_do_tai_san'}})

OPTIONAL MATCH (anchor)-[:THUOC_CHE_DO]->(che_do:ChePhapDoTaiSan:{TOPIC_LABEL})
WHERE kc IN ['xac_lap', 'tat_ca']

OPTIONAL MATCH (hv_xl:HanhVi:{TOPIC_LABEL})-[:YEU_CAU_THOA_THUAN]->(anchor)
WHERE kc IN ['xac_lap', 'tat_ca']
  AND hv_xl.id = 'xac_lap_thoa_thuan_che_do'

OPTIONAL MATCH (anchor)-[:AP_DUNG_KHI]->(dk_xl:DieuKien:{TOPIC_LABEL})
WHERE kc IN ['xac_lap', 'tat_ca']

OPTIONAL MATCH (anchor)-[:LIEN_QUAN]->(rel_xl:CheDoTaiSanCuaVoChong)
WHERE kc IN ['xac_lap', 'tat_ca']
  AND rel_xl.id IN ['che_do_thoa_thuan', 'lap_truoc_ket_hon', 'co_cong_chung_hoac_chung_thuc']

OPTIONAL MATCH (anchor)-[:LIEN_QUAN]->(lts_chung:LoaiTaiSan:{TOPIC_LABEL})
WHERE kc IN ['noi_dung', 'tat_ca']
  AND lts_chung.id IN ['tai_san_chung', 'tai_san_rieng']

OPTIONAL MATCH (anchor)-[:LIEN_QUAN]->(nv_nd:CheDoTaiSanCuaVoChong)
WHERE kc IN ['noi_dung', 'tat_ca']
  AND nv_nd.id IN [
    'nghia_vu_dap_ung_nhu_cau_thiet_yeu_gia_dinh',
    'quyen_dinh_doat_tai_san_rieng',
    'dieu_kien_phan_chia_khi_cham_dut_che_do',
    'lacuna_thoa_thuan',
    'lacuna_ap_dung_d29_d32_va_luat_dinh'
  ]

OPTIONAL MATCH (anchor)-[:LIEN_QUAN]->(hv_sd:HanhVi:{TOPIC_LABEL})
WHERE kc IN ['sua_doi', 'tat_ca']
  AND hv_sd.id = 'sua_doi_bo_sung_thoa_thuan'

OPTIONAL MATCH (quyen_sd:Quyen:{TOPIC_LABEL} {{id: 'quyen_sua_doi_thoa_thuan'}})
WHERE kc IN ['sua_doi', 'tat_ca']

OPTIONAL MATCH (anchor)-[:LIEN_QUAN]->(hq_vh:HauQua:{TOPIC_LABEL})
WHERE kc IN ['vo_hieu', 'tat_ca']
  AND hq_vh.id = 'vo_hieu_thoa_thuan'

OPTIONAL MATCH (dk_vh:DieuKien:{TOPIC_LABEL})-[:DAN_TOI]->(hq_vh2:HauQua:{TOPIC_LABEL} {{id: 'vo_hieu_thoa_thuan'}})
WHERE kc IN ['vo_hieu', 'tat_ca']
  AND (
    nhom IS NULL OR nhom = 'tat_ca'
    OR (nhom = 'dieu_kien_giao_dich' AND dk_vh.id = 'vi_pham_dieu_kien_giao_dich_blds')
    OR (nhom = 'vi_pham_d29_d32' AND dk_vh.id = 'vi_pham_dieu_29_30_31_32')
    OR (nhom = 'quyen_thanh_vien_gia_dinh' AND dk_vh.id = 'vi_pham_quyen_thanh_vien_gia_dinh')
  )

WITH wl, kc, nhom,
  [x IN collect(DISTINCT anchor) + collect(DISTINCT che_do) + collect(DISTINCT hv_xl)
       + collect(DISTINCT dk_xl) + collect(DISTINCT rel_xl)
       + collect(DISTINCT lts_chung) + collect(DISTINCT nv_nd)
       + collect(DISTINCT hv_sd) + collect(DISTINCT quyen_sd)
       + collect(DISTINCT hq_vh) + collect(DISTINCT dk_vh)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'xac_lap' THEN
      [x IN collect(DISTINCT anchor) + collect(DISTINCT che_do) + collect(DISTINCT hv_xl)
           + collect(DISTINCT dk_xl) + collect(DISTINCT rel_xl)
       WHERE x IS NOT NULL]
    WHEN 'noi_dung' THEN
      [x IN collect(DISTINCT lts_chung) + collect(DISTINCT nv_nd) WHERE x IS NOT NULL]
    WHEN 'sua_doi' THEN
      [x IN collect(DISTINCT hv_sd) + collect(DISTINCT quyen_sd) WHERE x IS NOT NULL]
    WHEN 'vo_hieu' THEN
      CASE
        WHEN nhom = 'dieu_kien_giao_dich' THEN
          [x IN collect(DISTINCT dk_vh) WHERE x IS NOT NULL AND x.id = 'vi_pham_dieu_kien_giao_dich_blds']
        WHEN nhom = 'vi_pham_d29_d32' THEN
          [x IN collect(DISTINCT dk_vh) WHERE x IS NOT NULL AND x.id = 'vi_pham_dieu_29_30_31_32']
        WHEN nhom = 'quyen_thanh_vien_gia_dinh' THEN
          [x IN collect(DISTINCT dk_vh) WHERE x IS NOT NULL AND x.id = 'vi_pham_quyen_thanh_vien_gia_dinh']
        ELSE
          [x IN collect(DISTINCT hq_vh) + collect(DISTINCT dk_vh) WHERE x IS NOT NULL]
      END
    ELSE
      [x IN collect(DISTINCT anchor) + collect(DISTINCT che_do) + collect(DISTINCT hv_xl)
           + collect(DISTINCT dk_xl) + collect(DISTINCT rel_xl)
           + collect(DISTINCT lts_chung) + collect(DISTINCT nv_nd)
           + collect(DISTINCT hv_sd) + collect(DISTINCT quyen_sd)
           + collect(DISTINCT hq_vh) + collect(DISTINCT dk_vh)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ThoaThuanCheDoParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    base = params.model_dump()
    base["whitelist_dieu_ids"] = _DIEU_WHITELIST if use_wl else []
    return base


thoa_thuan_che_do_tai_san = CypherTemplate(
    name="thoa_thuan_che_do_tai_san",
    description=(
        "Thỏa thuận về chế độ tài sản của vợ chồng (Đ47-50, chế độ tài sản "
        "theo thỏa thuận — KHÔNG phải chế độ luật định). Gồm 4 khía cạnh:\n"
        "  • xac_lap (Đ47) — hình thức, công chứng/chứng thực, lập trước kết "
        "hôn, hiệu lực từ ngày đăng ký kết hôn.\n"
        "  • noi_dung (Đ48) — tài sản chung/riêng, quyền/nghĩa vụ, phân chia.\n"
        "  • sua_doi (Đ49) — quyền sửa đổi thỏa thuận.\n"
        "  • vo_hieu (Đ50) — các trường hợp Tòa án tuyên vô hiệu.\n"
        "Phù hợp khi câu hỏi đề cập tới 'hợp đồng tài sản tiền hôn nhân', "
        "'thỏa thuận về tài sản', 'ký trước cưới', 'công chứng/chứng thực', "
        "'sửa đổi thỏa thuận', 'thỏa thuận vô hiệu'."
    ),
    params_schema=ThoaThuanCheDoParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
