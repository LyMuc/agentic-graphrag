"""Template 6 — CHIA TÀI SẢN CHUNG TRONG THỜI KỲ HÔN NHÂN (Đ38-42).

Trả lời câu hỏi xoay quanh việc chia tài sản chung TRONG hôn nhân (không
phải khi ly hôn) — bao gồm:
- Đ38: Thỏa thuận chia, yêu cầu Tòa án.
- Đ39: Thời điểm có hiệu lực của việc chia.
- Đ40: Hậu quả pháp lý sau khi chia.
- Đ41: Chấm dứt hiệu lực của việc chia.
- Đ42: Các trường hợp việc chia bị vô hiệu (lợi ích gia đình, trốn nghĩa vụ).

Coverage: Q2, Q6, Q19 (nhánh chia chung), Q20, Q21.

KHÔNG dùng cho câu hỏi 'chia tài sản KHI LY HÔN' (Đ59, đó là tool khác).
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


class ChiaTaiSanParams(BaseModel):
    khia_canh: Literal[
        "thoa_thuan_chia",
        "thoi_diem_hieu_luc",
        "hau_qua",
        "cham_dut",
        "vo_hieu",
        "tat_ca",
    ] = Field(
        description=(
            "Khía cạnh chia tài sản chung trong thời kỳ hôn nhân:\n"
            "  • 'thoa_thuan_chia' (Đ38): cách thỏa thuận chia, yêu cầu văn "
            "bản, công chứng, vai trò Tòa án khi không thỏa thuận.\n"
            "  • 'thoi_diem_hieu_luc' (Đ39): khi nào việc chia có hiệu lực.\n"
            "  • 'hau_qua' (Đ40): tài sản sau chia trở thành riêng/chung, "
            "hoa lợi/lợi tức sau chia.\n"
            "  • 'cham_dut' (Đ41): chấm dứt hiệu lực việc chia, khôi phục "
            "xác định tài sản.\n"
            "  • 'vo_hieu' (Đ42): các trường hợp việc chia bị vô hiệu (ảnh "
            "hưởng gia đình, trốn nghĩa vụ).\n"
            "  • 'tat_ca': khi câu hỏi tổng quát hoặc bao gồm nhiều khía cạnh."
        )
    )
    nhom_can_cu_vo_hieu: Optional[Literal[
        "anh_huong_loi_ich_gia_dinh",
        "tron_nghia_vu",
        "tat_ca",
    ]] = Field(
        default="tat_ca",
        description=(
            "Chỉ dùng khi `khia_canh = 'vo_hieu'`. Lọc nhóm căn cứ vô hiệu:\n"
            "  • 'anh_huong_loi_ich_gia_dinh' (Đ42 K1): chỉ phần ảnh hưởng "
            "nghiêm trọng đến lợi ích gia đình hoặc quyền/lợi ích con.\n"
            "  • 'tron_nghia_vu' (Đ42 K2): chỉ phần trốn nghĩa vụ (nuôi dưỡng, "
            "cấp dưỡng, bồi thường, phá sản, trả nợ, thuế, nghĩa vụ khác).\n"
            "  • 'tat_ca' (mặc định): cả 2 nhóm."
        ),
    )


_DIEU_WHITELIST = [
    "Luat_HNGD_2014_Dieu_38",
    "Luat_HNGD_2014_Dieu_39",
    "Luat_HNGD_2014_Dieu_40",
    "Luat_HNGD_2014_Dieu_41",
    "Luat_HNGD_2014_Dieu_42",
]

_SEED_BODY = f"""
// ============================================================
// PHẦN 1 — SEED semantic graph (chia tài sản chung Đ38-42)
// ============================================================
WITH $khia_canh AS kc, $nhom_can_cu_vo_hieu AS nhom, $whitelist_dieu_ids AS wl

MATCH (anchor:HanhVi:{TOPIC_LABEL} {{id: 'chia_tai_san_chung_trong_hon_nhan'}})

OPTIONAL MATCH (anchor)-[:YEU_CAU_THOA_THUAN]->(tt_chia:ThoaThuan:{TOPIC_LABEL})
WHERE kc IN ['thoa_thuan_chia', 'tat_ca']

OPTIONAL MATCH (anchor)-[:LIEN_QUAN]->(quyen_toa:Quyen:{TOPIC_LABEL})
WHERE kc IN ['thoa_thuan_chia', 'tat_ca']
  AND quyen_toa.id = 'quyen_yeu_cau_toa_an_chia'

OPTIONAL MATCH (hv_kien:HanhVi:{TOPIC_LABEL} {{id: 'khoi_kien_tai_toa_an'}})
WHERE kc IN ['thoa_thuan_chia', 'tat_ca']
OPTIONAL MATCH (hv_kien)-[:AP_DUNG_KHI]->(dk_khong_tt:DieuKien:{TOPIC_LABEL})
WHERE kc IN ['thoa_thuan_chia', 'tat_ca']

OPTIONAL MATCH (anchor)-[:DAN_TOI]->(hq_hl_truc:HauQua:{TOPIC_LABEL})
WHERE kc IN ['thoi_diem_hieu_luc', 'tat_ca']
  AND hq_hl_truc.id STARTS WITH 'hieu_luc_chia'

OPTIONAL MATCH (dk_hl:DieuKien:{TOPIC_LABEL})-[:DAN_TOI]->(hq_hl:HauQua:{TOPIC_LABEL})
WHERE kc IN ['thoi_diem_hieu_luc', 'tat_ca']
  AND hq_hl.id STARTS WITH 'hieu_luc_chia'

OPTIONAL MATCH (hq_t3:HauQua:{TOPIC_LABEL} {{id: 'quyen_nghia_vu_voi_nguoi_thu_ba_truoc_chia_van_co_hieu_luc'}})
WHERE kc IN ['thoi_diem_hieu_luc', 'tat_ca']

OPTIONAL MATCH (anchor)-[:DAN_TOI]->(hq_hq:HauQua:{TOPIC_LABEL})
WHERE kc IN ['hau_qua', 'tat_ca']
  AND hq_hq.id IN [
    'chuyen_thanh_tai_san_rieng_phan_chia',
    'hoa_loi_loi_tuc_sau_chia_thanh_tai_san_rieng',
    'phan_con_lai_van_la_tai_san_chung'
  ]

OPTIONAL MATCH (lts_chia:LoaiTaiSan:{TOPIC_LABEL} {{id: 'tai_san_chia_rieng_trong_hon_nhan'}})
WHERE kc IN ['hau_qua', 'tat_ca']

OPTIONAL MATCH (anchor)-[:CO_NGOAI_LE]->(nl_hq:TruongHopNgoaiLe:{TOPIC_LABEL})
WHERE kc IN ['hau_qua', 'tat_ca']

OPTIONAL MATCH (anchor)-[:LIEN_QUAN]->(hv_cd:HanhVi:{TOPIC_LABEL})
WHERE kc IN ['cham_dut', 'tat_ca']
  AND hv_cd.id = 'cham_dut_hieu_luc_chia'

OPTIONAL MATCH (hv_cd)-[:DAN_TOI]->(hq_cd:HauQua:{TOPIC_LABEL})
WHERE kc IN ['cham_dut', 'tat_ca']

OPTIONAL MATCH (hv_cd)-[:YEU_CAU_THOA_THUAN]->(tt_cd:ThoaThuan:{TOPIC_LABEL})
WHERE kc IN ['cham_dut', 'tat_ca']

OPTIONAL MATCH (quyen_cd:Quyen:{TOPIC_LABEL} {{id: 'quyen_cham_dut_hieu_luc_chia'}})
WHERE kc IN ['cham_dut', 'tat_ca']

OPTIONAL MATCH (anchor)-[:LIEN_QUAN]->(hq_vh:HauQua:{TOPIC_LABEL})
WHERE kc IN ['vo_hieu', 'tat_ca']
  AND hq_vh.id = 'vo_hieu_chia_tai_san_chung'

OPTIONAL MATCH (dk_vh:DieuKien:{TOPIC_LABEL})-[:DAN_TOI]->(hq_vh2:HauQua:{TOPIC_LABEL} {{id: 'vo_hieu_chia_tai_san_chung'}})
WHERE kc IN ['vo_hieu', 'tat_ca']
  AND (
    nhom IS NULL OR nhom = 'tat_ca'
    OR (nhom = 'anh_huong_loi_ich_gia_dinh' AND dk_vh.id = 'anh_huong_loi_ich_gia_dinh')
    OR (nhom = 'tron_nghia_vu' AND dk_vh.id STARTS WITH 'tron_nghia_vu')
  )

WITH wl, kc, nhom,
  [x IN collect(DISTINCT anchor) + collect(DISTINCT tt_chia) + collect(DISTINCT quyen_toa)
       + collect(DISTINCT hv_kien) + collect(DISTINCT dk_khong_tt)
       + collect(DISTINCT hq_hl_truc) + collect(DISTINCT dk_hl) + collect(DISTINCT hq_hl)
       + collect(DISTINCT hq_t3)
       + collect(DISTINCT hq_hq) + collect(DISTINCT lts_chia) + collect(DISTINCT nl_hq)
       + collect(DISTINCT hv_cd) + collect(DISTINCT hq_cd) + collect(DISTINCT tt_cd)
       + collect(DISTINCT quyen_cd)
       + collect(DISTINCT hq_vh) + collect(DISTINCT dk_vh)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'thoa_thuan_chia' THEN
      [x IN collect(DISTINCT tt_chia) + collect(DISTINCT quyen_toa)
           + collect(DISTINCT hv_kien) + collect(DISTINCT dk_khong_tt)
       WHERE x IS NOT NULL]
    WHEN 'thoi_diem_hieu_luc' THEN
      [x IN collect(DISTINCT hq_hl_truc) + collect(DISTINCT hq_hl)
           + collect(DISTINCT dk_hl) + collect(DISTINCT hq_t3)
       WHERE x IS NOT NULL]
    WHEN 'hau_qua' THEN
      [x IN collect(DISTINCT hq_hq) + collect(DISTINCT lts_chia) + collect(DISTINCT nl_hq)
       WHERE x IS NOT NULL]
    WHEN 'cham_dut' THEN
      [x IN collect(DISTINCT hv_cd) + collect(DISTINCT hq_cd) + collect(DISTINCT tt_cd)
           + collect(DISTINCT quyen_cd)
       WHERE x IS NOT NULL]
    WHEN 'vo_hieu' THEN
      CASE
        WHEN nhom = 'anh_huong_loi_ich_gia_dinh' THEN
          [x IN collect(DISTINCT dk_vh) WHERE x IS NOT NULL AND x.id = 'anh_huong_loi_ich_gia_dinh']
        WHEN nhom = 'tron_nghia_vu' THEN
          [x IN collect(DISTINCT dk_vh) WHERE x IS NOT NULL AND x.id STARTS WITH 'tron_nghia_vu']
        ELSE
          [x IN collect(DISTINCT hq_vh) + collect(DISTINCT dk_vh) WHERE x IS NOT NULL]
      END
    ELSE
      [x IN collect(DISTINCT anchor) + collect(DISTINCT tt_chia) + collect(DISTINCT quyen_toa)
           + collect(DISTINCT hv_kien) + collect(DISTINCT dk_khong_tt)
           + collect(DISTINCT hq_hl_truc) + collect(DISTINCT dk_hl) + collect(DISTINCT hq_hl)
           + collect(DISTINCT hq_t3)
           + collect(DISTINCT hq_hq) + collect(DISTINCT lts_chia) + collect(DISTINCT nl_hq)
           + collect(DISTINCT hv_cd) + collect(DISTINCT hq_cd) + collect(DISTINCT tt_cd)
           + collect(DISTINCT quyen_cd)
           + collect(DISTINCT hq_vh) + collect(DISTINCT dk_vh)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ChiaTaiSanParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    base = params.model_dump()
    base["whitelist_dieu_ids"] = _DIEU_WHITELIST if use_wl else []
    return base


chia_tai_san_thoi_ky_hon_nhan = CypherTemplate(
    name="chia_tai_san_thoi_ky_hon_nhan",
    description=(
        "Chia tài sản chung TRONG THỜI KỲ HÔN NHÂN (Đ38-42, NOT 'chia tài sản "
        "khi ly hôn'). Gồm 5 khía cạnh:\n"
        "  • thoa_thuan_chia (Đ38) — cách thỏa thuận, yêu cầu Tòa án.\n"
        "  • thoi_diem_hieu_luc (Đ39) — khi nào việc chia có hiệu lực.\n"
        "  • hau_qua (Đ40) — tài sản sau chia trở thành riêng/chung.\n"
        "  • cham_dut (Đ41) — chấm dứt việc chia.\n"
        "  • vo_hieu (Đ42) — các trường hợp việc chia bị vô hiệu.\n"
        "Phù hợp khi câu hỏi đề cập tới 'chia tài sản chung', 'tách tài sản', "
        "'ly thân tài sản', 'phân chia trong hôn nhân' (KHÔNG phải ly hôn)."
    ),
    params_schema=ChiaTaiSanParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
