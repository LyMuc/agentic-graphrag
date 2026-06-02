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

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.tai_san._common import (
    EXPAND_AND_TIMEFILTER_CYPHER,
    assemble_semantic_viz_from_trace_prefix,
)


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


_KHIA_CANH_TO_DIEU = {
    "thoa_thuan_chia": ["Luat_HNGD_2014_Dieu_38"],
    "thoi_diem_hieu_luc": ["Luat_HNGD_2014_Dieu_39"],
    "hau_qua": ["Luat_HNGD_2014_Dieu_40"],
    "cham_dut": ["Luat_HNGD_2014_Dieu_41"],
    "vo_hieu": ["Luat_HNGD_2014_Dieu_42"],
    "tat_ca": [
        "Luat_HNGD_2014_Dieu_38",
        "Luat_HNGD_2014_Dieu_39",
        "Luat_HNGD_2014_Dieu_40",
        "Luat_HNGD_2014_Dieu_41",
        "Luat_HNGD_2014_Dieu_42",
    ],
}


# Cypher SEED — combine semantic match (via allowed IDs list) + DieuLuat whitelist
_SEED_BLOCK = """
// ============================================================
// PHẦN 1 — SEED chia tài sản chung trong hôn nhân (Đ38-42)
// ============================================================
WITH $khia_canh AS kc, $nhom_can_cu_vo_hieu AS nhom, $whitelist_dieu_ids AS wl

// 1a. Build danh sách semantic IDs cần match theo khía cạnh
WITH kc, nhom, wl,
  (CASE WHEN kc IN ['thoa_thuan_chia', 'tat_ca'] THEN [
      'chia_tai_san_chung_trong_hon_nhan',
      'thoa_thuan_chia_tai_san_chung',
      'quyen_yeu_cau_toa_an_chia',
      'khoi_kien_tai_toa_an',
      'khong_thoa_thuan_duoc_chia'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['thoi_diem_hieu_luc', 'tat_ca'] THEN [
      'hieu_luc_chia_tai_san_thoi_diem_thoa_thuan',
      'hieu_luc_chia_tai_san_ngay_lap_van_ban',
      'hieu_luc_chia_tai_san_thoi_diem_tuan_thu_hinh_thuc',
      'hieu_luc_chia_tai_san_ngay_ban_an_co_hieu_luc',
      'quyen_nghia_vu_voi_nguoi_thu_ba_truoc_chia_van_co_hieu_luc',
      'khong_xac_dinh_thoi_diem_van_ban',
      'tai_san_yeu_cau_hinh_thuc_giao_dich',
      'chia_boi_toa_an'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['hau_qua', 'tat_ca'] THEN [
      'chuyen_thanh_tai_san_rieng_phan_chia',
      'hoa_loi_loi_tuc_sau_chia_thanh_tai_san_rieng',
      'phan_con_lai_van_la_tai_san_chung',
      'tai_san_chia_rieng_trong_hon_nhan',
      'ngoai_le_hoa_loi_sau_chia_thanh_tai_san_chung_neu_thoa_thuan'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['cham_dut', 'tat_ca'] THEN [
      'cham_dut_hieu_luc_chia',
      'quyen_cham_dut_hieu_luc_chia',
      'thoa_thuan_cham_dut_chia',
      'khoi_phuc_xac_dinh_theo_d33_d43',
      'phan_da_chia_van_la_tai_san_rieng'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca'] THEN ['vo_hieu_chia_tai_san_chung'] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca']
             AND (nhom IS NULL OR nhom IN ['anh_huong_loi_ich_gia_dinh', 'tat_ca'])
        THEN ['anh_huong_loi_ich_gia_dinh'] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca']
             AND (nhom IS NULL OR nhom IN ['tron_nghia_vu', 'tat_ca'])
        THEN [
            'tron_nghia_vu_nuoi_duong_cap_duong',
            'tron_nghia_vu_boi_thuong',
            'tron_nghia_vu_pha_san',
            'tron_nghia_vu_tra_no',
            'tron_nghia_vu_thue_tai_chinh_nha_nuoc',
            'tron_nghia_vu_khac'
        ] ELSE [] END
  ) AS allowed_semantic_ids

// 1b. Semantic seed via CAN_CU_TAI
OPTIONAL MATCH (sn:CheDoTaiSanCuaVoChong)
WHERE sn.id IN allowed_semantic_ids
  AND (sn:HanhVi OR sn:NghiaVu OR sn:Quyen OR sn:DieuKien OR sn:HauQua
       OR sn:ThoaThuan OR sn:TruongHopNgoaiLe OR sn:LoaiTaiSan)

OPTIONAL MATCH (sn)-[:CAN_CU_TAI]->(luat_semantic)
WHERE luat_semantic IS NOT NULL

// 1c. Whitelist seed
OPTIONAL MATCH (luat_whitelist:DieuLuat)
WHERE luat_whitelist.id IN wl

WITH collect(DISTINCT luat_semantic) + collect(DISTINCT luat_whitelist) AS all_seeds
UNWIND all_seeds AS n_goc
WITH DISTINCT n_goc
WHERE n_goc IS NOT NULL
"""

# Trace cypher — chỉ chạy seed (semantic + whitelist), không expand
_TRACE_CYPHER = """
WITH $khia_canh AS kc, $nhom_can_cu_vo_hieu AS nhom, $whitelist_dieu_ids AS wl

WITH kc, nhom, wl,
  (CASE WHEN kc IN ['thoa_thuan_chia', 'tat_ca'] THEN [
      'chia_tai_san_chung_trong_hon_nhan',
      'thoa_thuan_chia_tai_san_chung',
      'quyen_yeu_cau_toa_an_chia',
      'khoi_kien_tai_toa_an',
      'khong_thoa_thuan_duoc_chia'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['thoi_diem_hieu_luc', 'tat_ca'] THEN [
      'hieu_luc_chia_tai_san_thoi_diem_thoa_thuan',
      'hieu_luc_chia_tai_san_ngay_lap_van_ban',
      'hieu_luc_chia_tai_san_thoi_diem_tuan_thu_hinh_thuc',
      'hieu_luc_chia_tai_san_ngay_ban_an_co_hieu_luc',
      'quyen_nghia_vu_voi_nguoi_thu_ba_truoc_chia_van_co_hieu_luc',
      'khong_xac_dinh_thoi_diem_van_ban',
      'tai_san_yeu_cau_hinh_thuc_giao_dich',
      'chia_boi_toa_an'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['hau_qua', 'tat_ca'] THEN [
      'chuyen_thanh_tai_san_rieng_phan_chia',
      'hoa_loi_loi_tuc_sau_chia_thanh_tai_san_rieng',
      'phan_con_lai_van_la_tai_san_chung',
      'tai_san_chia_rieng_trong_hon_nhan',
      'ngoai_le_hoa_loi_sau_chia_thanh_tai_san_chung_neu_thoa_thuan'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['cham_dut', 'tat_ca'] THEN [
      'cham_dut_hieu_luc_chia',
      'quyen_cham_dut_hieu_luc_chia',
      'thoa_thuan_cham_dut_chia',
      'khoi_phuc_xac_dinh_theo_d33_d43',
      'phan_da_chia_van_la_tai_san_rieng'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca'] THEN ['vo_hieu_chia_tai_san_chung'] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca']
             AND (nhom IS NULL OR nhom IN ['anh_huong_loi_ich_gia_dinh', 'tat_ca'])
        THEN ['anh_huong_loi_ich_gia_dinh'] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca']
             AND (nhom IS NULL OR nhom IN ['tron_nghia_vu', 'tat_ca'])
        THEN [
            'tron_nghia_vu_nuoi_duong_cap_duong',
            'tron_nghia_vu_boi_thuong',
            'tron_nghia_vu_pha_san',
            'tron_nghia_vu_tra_no',
            'tron_nghia_vu_thue_tai_chinh_nha_nuoc',
            'tron_nghia_vu_khac'
        ] ELSE [] END
  ) AS allowed_semantic_ids

OPTIONAL MATCH (sn:CheDoTaiSanCuaVoChong)
WHERE sn.id IN allowed_semantic_ids
  AND (sn:HanhVi OR sn:NghiaVu OR sn:Quyen OR sn:DieuKien OR sn:HauQua
       OR sn:ThoaThuan OR sn:TruongHopNgoaiLe OR sn:LoaiTaiSan)

OPTIONAL MATCH (sn)-[:CAN_CU_TAI]->(luat)
WHERE luat IS NOT NULL

WITH wl, collect(DISTINCT {
    src_label: head(labels(sn)),
    src_id: sn.id,
    rel: 'CAN_CU_TAI',
    dst_label: head(labels(luat)),
    dst_id: luat.id
}) AS semantic_triples

UNWIND wl AS wid
WITH semantic_triples, collect({
    src_label: 'WHITELIST',
    src_id: 'khia_canh',
    rel: 'WHITELIST',
    dst_label: 'DieuLuat',
    dst_id: wid
}) AS wl_triples

WITH semantic_triples + wl_triples AS seed_trace
RETURN seed_trace
"""


def _params_builder(params: ChiaTaiSanParams) -> dict[str, Any]:
    base = params.model_dump()
    base["whitelist_dieu_ids"] = _KHIA_CANH_TO_DIEU.get(params.khia_canh, [])
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
    cypher=_SEED_BLOCK.rstrip() + "\n\n" + EXPAND_AND_TIMEFILTER_CYPHER,
    trace_cypher=_TRACE_CYPHER,
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_TRACE_CYPHER),
    params_builder=_params_builder,
)
