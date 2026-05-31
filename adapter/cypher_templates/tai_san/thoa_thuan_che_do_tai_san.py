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

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.tai_san._common import (
    EXPAND_AND_TIMEFILTER_CYPHER,
)


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


_KHIA_CANH_TO_DIEU = {
    "xac_lap": ["Luat_HNGD_2014_Dieu_47"],
    "noi_dung": ["Luat_HNGD_2014_Dieu_48"],
    "sua_doi": ["Luat_HNGD_2014_Dieu_49"],
    "vo_hieu": ["Luat_HNGD_2014_Dieu_50"],
    "tat_ca": [
        "Luat_HNGD_2014_Dieu_47",
        "Luat_HNGD_2014_Dieu_48",
        "Luat_HNGD_2014_Dieu_49",
        "Luat_HNGD_2014_Dieu_50",
    ],
}


_SEED_BLOCK = """
// ============================================================
// PHẦN 1 — SEED thỏa thuận chế độ tài sản (Đ47-50)
// ============================================================
WITH $khia_canh AS kc, $nhom_can_cu_vo_hieu_thoa_thuan AS nhom, $whitelist_dieu_ids AS wl

WITH kc, nhom, wl,
  (CASE WHEN kc IN ['xac_lap', 'tat_ca'] THEN [
      'thoa_thuan_che_do_tai_san',
      'xac_lap_thoa_thuan_che_do',
      'che_do_thoa_thuan',
      'lap_truoc_ket_hon',
      'co_cong_chung_hoac_chung_thuc'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['noi_dung', 'tat_ca'] THEN [
      'dieu_kien_phan_chia_khi_cham_dut_che_do',
      'lacuna_thoa_thuan',
      'lacuna_ap_dung_d29_d32_va_luat_dinh',
      'tai_san_chung',
      'tai_san_rieng',
      'quyen_dinh_doat_tai_san_rieng',
      'nghia_vu_dap_ung_nhu_cau_thiet_yeu_gia_dinh'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['sua_doi', 'tat_ca'] THEN [
      'sua_doi_bo_sung_thoa_thuan',
      'quyen_sua_doi_thoa_thuan'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca'] THEN ['vo_hieu_thoa_thuan'] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca']
             AND (nhom IS NULL OR nhom IN ['dieu_kien_giao_dich', 'tat_ca'])
        THEN ['vi_pham_dieu_kien_giao_dich_blds'] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca']
             AND (nhom IS NULL OR nhom IN ['vi_pham_d29_d32', 'tat_ca'])
        THEN ['vi_pham_dieu_29_30_31_32'] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca']
             AND (nhom IS NULL OR nhom IN ['quyen_thanh_vien_gia_dinh', 'tat_ca'])
        THEN ['vi_pham_quyen_thanh_vien_gia_dinh'] ELSE [] END
  ) AS allowed_semantic_ids

OPTIONAL MATCH (sn:CheDoTaiSanCuaVoChong)
WHERE sn.id IN allowed_semantic_ids
  AND (sn:ThoaThuan OR sn:HanhVi OR sn:Quyen OR sn:DieuKien OR sn:HauQua
       OR sn:ChePhapDoTaiSan OR sn:NghiaVu OR sn:LoaiTaiSan)

OPTIONAL MATCH (sn)-[:CAN_CU_TAI]->(luat_semantic)
WHERE luat_semantic IS NOT NULL

OPTIONAL MATCH (luat_whitelist:DieuLuat)
WHERE luat_whitelist.id IN wl

WITH collect(DISTINCT luat_semantic) + collect(DISTINCT luat_whitelist) AS all_seeds
UNWIND all_seeds AS n_goc
WITH DISTINCT n_goc
WHERE n_goc IS NOT NULL
"""


_TRACE_CYPHER = """
WITH $khia_canh AS kc, $nhom_can_cu_vo_hieu_thoa_thuan AS nhom, $whitelist_dieu_ids AS wl

WITH kc, nhom, wl,
  (CASE WHEN kc IN ['xac_lap', 'tat_ca'] THEN [
      'thoa_thuan_che_do_tai_san',
      'xac_lap_thoa_thuan_che_do',
      'che_do_thoa_thuan',
      'lap_truoc_ket_hon',
      'co_cong_chung_hoac_chung_thuc'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['noi_dung', 'tat_ca'] THEN [
      'dieu_kien_phan_chia_khi_cham_dut_che_do',
      'lacuna_thoa_thuan',
      'lacuna_ap_dung_d29_d32_va_luat_dinh',
      'tai_san_chung',
      'tai_san_rieng',
      'quyen_dinh_doat_tai_san_rieng',
      'nghia_vu_dap_ung_nhu_cau_thiet_yeu_gia_dinh'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['sua_doi', 'tat_ca'] THEN [
      'sua_doi_bo_sung_thoa_thuan',
      'quyen_sua_doi_thoa_thuan'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca'] THEN ['vo_hieu_thoa_thuan'] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca']
             AND (nhom IS NULL OR nhom IN ['dieu_kien_giao_dich', 'tat_ca'])
        THEN ['vi_pham_dieu_kien_giao_dich_blds'] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca']
             AND (nhom IS NULL OR nhom IN ['vi_pham_d29_d32', 'tat_ca'])
        THEN ['vi_pham_dieu_29_30_31_32'] ELSE [] END
   +
   CASE WHEN kc IN ['vo_hieu', 'tat_ca']
             AND (nhom IS NULL OR nhom IN ['quyen_thanh_vien_gia_dinh', 'tat_ca'])
        THEN ['vi_pham_quyen_thanh_vien_gia_dinh'] ELSE [] END
  ) AS allowed_semantic_ids

OPTIONAL MATCH (sn:CheDoTaiSanCuaVoChong)
WHERE sn.id IN allowed_semantic_ids
  AND (sn:ThoaThuan OR sn:HanhVi OR sn:Quyen OR sn:DieuKien OR sn:HauQua
       OR sn:ChePhapDoTaiSan OR sn:NghiaVu OR sn:LoaiTaiSan)

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


def _params_builder(params: ThoaThuanCheDoParams) -> dict[str, Any]:
    base = params.model_dump()
    base["whitelist_dieu_ids"] = _KHIA_CANH_TO_DIEU.get(params.khia_canh, [])
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
    cypher=_SEED_BLOCK.rstrip() + "\n\n" + EXPAND_AND_TIMEFILTER_CYPHER,
    trace_cypher=_TRACE_CYPHER,
    params_builder=_params_builder,
)
