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

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.tai_san._common import assemble_cypher, assemble_simple_trace


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


_SEED_BLOCK = """
// ============================================================
// PHẦN 1 — SEED nguyên tắc chế độ tài sản (Đ29-32)
// ============================================================
// Dựa vào AP_DUNG_CHO_CHE_DO {che_do:'tat_ca'} để xác định Đ29-32,
// rồi lọc theo khía cạnh thông qua semantic node ngữ nghĩa liên kết.

WITH $khia_canh AS kc

// 1a. Match các Khoản / Điều thuộc Đ29-32 (gắn AP_DUNG_CHO_CHE_DO 'tat_ca')
MATCH (luat)-[:AP_DUNG_CHO_CHE_DO {che_do: 'tat_ca'}]->(:ChePhapDoTaiSan:CheDoTaiSanCuaVoChong)
WHERE (luat:DieuLuat OR luat:DieuKhoanLuat OR luat:DieuKhoanDiemLuat)

// 1b. Lấy danh sách semantic node ngữ nghĩa kết nối tới luat theo khía cạnh
OPTIONAL MATCH (sn:CheDoTaiSanCuaVoChong)-[:CAN_CU_TAI]->(luat)
WHERE sn IS NOT NULL
  AND (
    kc = 'tat_ca'
    // bình đẳng — Đ29 K1
    OR (kc = 'binh_dang' AND sn.id IN [
        'quyen_binh_dang_tai_san_chung',
        'tao_lap_chiem_huu_su_dung_dinh_doat_tai_san_chung'
    ])
    // nhu cầu thiết yếu — Đ29 K2, Đ30
    OR (kc = 'nhu_cau_thiet_yeu_gia_dinh' AND sn.id IN [
        'nghia_vu_dap_ung_nhu_cau_thiet_yeu_gia_dinh',
        'dap_ung_nhu_cau_thiet_yeu_gia_dinh',
        'nghia_vu_dong_gop_tai_san_rieng_khi_thieu_chung',
        'khong_du_tai_san_chung',
        'boi_thuong_thiet_hai_xam_pham'
    ])
    // nhà ở duy nhất — Đ31
    OR (kc = 'giao_dich_nha_o_duy_nhat' AND sn.id IN [
        'giao_dich_nha_o_duy_nhat',
        'nha_o_duy_nhat',
        'thoa_thuan_dinh_doat_nha_o_duy_nhat',
        'ngoai_le_nha_so_huu_rieng_duoc_tu_giao_dich',
        'nghia_vu_bao_dam_cho_o_cho_vo_chong',
        'tai_san_la_nha_o_duy_nhat',
        'nha_thuoc_so_huu_rieng',
        'bao_dam_cho_o'
    ])
    // người thứ ba ngay tình — Đ32
    OR (kc = 'giao_dich_nguoi_thu_ba_ngay_tinh' AND sn.id IN [
        'giao_dich_nguoi_thu_ba_ngay_tinh',
        'tai_khoan_ngan_hang_chung_khoan',
        'dong_san_khong_phai_dang_ky',
        'giao_dich_ngay_tinh',
        'nguoi_thu_ba_ngay_tinh',
        'bao_ve_nguoi_thu_ba'
    ])
  )

// 1c. Whitelist Khoản/Điều: nếu khía cạnh khớp luật cụ thể, vẫn lấy luật đó
//     ngay cả khi không match semantic node nào (đảm bảo coverage 100% cho
//     câu hỏi tổng quát).
WITH luat, sn, kc,
  CASE
    WHEN kc = 'tat_ca' THEN true
    WHEN kc = 'binh_dang' AND luat.id STARTS WITH 'Luat_HNGD_2014_Dieu_29_Khoan_1' THEN true
    WHEN kc = 'nhu_cau_thiet_yeu_gia_dinh' AND
         (luat.id STARTS WITH 'Luat_HNGD_2014_Dieu_29_Khoan_2'
          OR luat.id STARTS WITH 'Luat_HNGD_2014_Dieu_30') THEN true
    WHEN kc = 'giao_dich_nha_o_duy_nhat' AND luat.id STARTS WITH 'Luat_HNGD_2014_Dieu_31' THEN true
    WHEN kc = 'giao_dich_nguoi_thu_ba_ngay_tinh' AND luat.id STARTS WITH 'Luat_HNGD_2014_Dieu_32' THEN true
    ELSE false
  END AS luat_khop_khia_canh

WITH luat, sn, luat_khop_khia_canh
WHERE sn IS NOT NULL OR luat_khop_khia_canh

// 1d. Với row không có sn (chỉ whitelist luat), vẫn cần marker sn cho trace
WITH coalesce(sn, luat) AS sn, luat
WITH DISTINCT sn, luat AS n_goc
"""


# Riêng template này, Cypher SEED phức tạp hơn — match semantic + whitelist.
# Cuối SEED giữ `sn` để trace, marker đặc biệt: `WITH DISTINCT sn, luat AS n_goc`.

_CUSTOM_TRACE_TAIL = """
RETURN collect(DISTINCT {
    src_label: CASE WHEN sn = luat THEN 'WHITELIST' ELSE head(labels(sn)) END,
    src_id: CASE WHEN sn = luat THEN 'khia_canh:' + $khia_canh ELSE sn.id END,
    rel: CASE WHEN sn = luat THEN 'WHITELIST' ELSE 'CAN_CU_TAI' END,
    dst_label: head(labels(luat)),
    dst_id: luat.id
}) AS seed_trace
"""


def _build_trace(seed_block: str) -> str:
    """Strip marker cuối + giữ sn, luat trong scope rồi RETURN trace."""
    marker = "WITH DISTINCT sn, luat AS n_goc"
    body = seed_block.rsplit(marker, 1)[0].rstrip()
    # Thay marker bằng WITH sn, luat (giữ cả 2 biến cho trace tail)
    return body + "\nWITH DISTINCT sn, luat\n" + _CUSTOM_TRACE_TAIL


def _assemble_main(seed_block: str) -> str:
    """Chuyển marker đặc biệt → marker chuẩn rồi assemble với EXPAND."""
    standardized = seed_block.replace(
        "WITH DISTINCT sn, luat AS n_goc",
        "WITH DISTINCT luat AS n_goc",
    )
    return assemble_cypher(standardized)


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
    cypher=_assemble_main(_SEED_BLOCK),
    trace_cypher=_build_trace(_SEED_BLOCK),
)
