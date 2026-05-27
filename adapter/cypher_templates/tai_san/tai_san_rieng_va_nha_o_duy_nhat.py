"""Template 8 — TÀI SẢN RIÊNG & NHÀ Ở DUY NHẤT (Đ31, Đ43-46).

Trả lời câu hỏi tập trung vào TÀI SẢN RIÊNG và các đặc thù xoay quanh nó:
- Đ31: Giao dịch nhà ở duy nhất (đặc biệt, có cả nhà sở hữu riêng).
- Đ43: Phạm vi tài sản riêng.
- Đ44: Quyền chiếm hữu/sử dụng/định đoạt; nhập tài sản riêng vào chung.
- Đ45: Nghĩa vụ riêng (4 loại).
- Đ46: Nhập tài sản riêng vào tài sản chung — hậu quả.

Coverage: Q12 (để dành tài sản riêng), Q16 (nhà sở hữu riêng — bán cho nhân
tình), Q28 (hợp đồng tiền hôn nhân bảo vệ tài sản riêng).

Khác `phan_loai_tai_san`: template này tập trung vào QUYỀN/NGHĨA VỤ và GIAO
DỊCH liên quan tài sản riêng + nhà ở duy nhất, không chỉ liệt kê 'gì là tài
sản riêng'.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.tai_san._common import assemble_cypher, assemble_simple_trace


class TaiSanRiengNhaODuyNhatParams(BaseModel):
    khia_canh: Literal[
        "chiem_huu_su_dung",
        "dinh_doat",
        "nhap_vao_chung",
        "nha_o_duy_nhat",
        "nguon_song_duy_nhat",
        "tat_ca",
    ] = Field(
        description=(
            "Khía cạnh tài sản riêng / nhà ở duy nhất:\n"
            "  • 'chiem_huu_su_dung' (Đ44 K1, K2): quyền chiếm hữu, sử dụng "
            "tài sản riêng (gồm trường hợp bên kia quản lý thay).\n"
            "  • 'dinh_doat' (Đ44 K1): quyền bán, tặng, thế chấp tài sản "
            "riêng. KHÔNG cho câu hỏi tài sản chung (đó là 'quyen_dinh_doat_"
            "tai_san').\n"
            "  • 'nhap_vao_chung' (Đ46): nhập tài sản riêng vào tài sản chung; "
            "hậu quả về nghĩa vụ tài sản.\n"
            "  • 'nha_o_duy_nhat' (Đ31): giao dịch nhà ở duy nhất khi nhà là "
            "tài sản chung HOẶC tài sản riêng; nghĩa vụ bảo đảm chỗ ở.\n"
            "  • 'nguon_song_duy_nhat' (Đ44 K4): khi hoa lợi/lợi tức từ tài "
            "sản riêng là nguồn sống duy nhất của gia đình → cần đồng ý của "
            "bên kia khi định đoạt.\n"
            "  • 'tat_ca': khi câu hỏi tổng quát về tài sản riêng / nhà ở "
            "duy nhất."
        )
    )


_SEED_BLOCK = """
// ============================================================
// PHẦN 1 — SEED tài sản riêng & nhà ở duy nhất (Đ31, Đ43-46)
// ============================================================
WITH $khia_canh AS kc

WITH kc,
  (CASE WHEN kc IN ['chiem_huu_su_dung', 'tat_ca'] THEN [
      'chiem_huu_su_dung_tai_san_rieng',
      'quyen_chiem_huu_su_dung_tai_san_rieng',
      'quyen_quan_ly_thay',
      'khong_tu_quan_ly_va_khong_uy_quyen'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['dinh_doat', 'tat_ca'] THEN [
      'dinh_doat_tai_san_rieng',
      'ban_chuyen_nhuong_tai_san_rieng',
      'quyen_dinh_doat_tai_san_rieng',
      'quyen_nhap_hoac_khong_nhap_tai_san_rieng',
      'ngoai_le_dinh_doat_tai_san_rieng_la_nguon_song_duy_nhat',
      'nghia_vu_rieng_chiem_huu_dinh_doat_tai_san_rieng'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['nhap_vao_chung', 'tat_ca'] THEN [
      'nhap_tai_san_rieng_vao_chung',
      'thoa_thuan_nhap_tai_san_rieng',
      'chuyen_thanh_tai_san_chung',
      'chuyen_nghia_vu_sang_tai_san_chung'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['nha_o_duy_nhat', 'tat_ca'] THEN [
      'giao_dich_nha_o_duy_nhat',
      'nha_o_duy_nhat',
      'thoa_thuan_dinh_doat_nha_o_duy_nhat',
      'ngoai_le_nha_so_huu_rieng_duoc_tu_giao_dich',
      'nghia_vu_bao_dam_cho_o_cho_vo_chong',
      'tai_san_la_nha_o_duy_nhat',
      'nha_thuoc_so_huu_rieng',
      'bao_dam_cho_o'
   ] ELSE [] END
   +
   CASE WHEN kc IN ['nguon_song_duy_nhat', 'tat_ca'] THEN [
      'hoa_loi_la_nguon_song_duy_nhat',
      'dinh_doat_tai_san_rieng',
      'ngoai_le_dinh_doat_tai_san_rieng_la_nguon_song_duy_nhat'
   ] ELSE [] END
  ) AS allowed_semantic_ids

OPTIONAL MATCH (sn)
WHERE sn.id IN allowed_semantic_ids
  AND (sn:HanhVi OR sn:Quyen OR sn:NghiaVu OR sn:LoaiTaiSan
       OR sn:ThoaThuan OR sn:DieuKien OR sn:HauQua OR sn:TruongHopNgoaiLe)

WITH collect(DISTINCT sn) AS sn_list
UNWIND sn_list AS sn
WITH sn WHERE sn IS NOT NULL

MATCH (sn)-[:CAN_CU_TAI]->(luat)
WITH DISTINCT luat AS n_goc
"""


tai_san_rieng_va_nha_o_duy_nhat = CypherTemplate(
    name="tai_san_rieng_va_nha_o_duy_nhat",
    description=(
        "Tài sản riêng & nhà ở duy nhất — quyền/nghĩa vụ và giao dịch liên "
        "quan (Đ31, Đ43-46). Bao gồm:\n"
        "  • chiem_huu_su_dung (Đ44 K1, K2) — quyền chiếm hữu, sử dụng tài "
        "sản riêng; quản lý thay.\n"
        "  • dinh_doat (Đ44 K1) — định đoạt tài sản riêng.\n"
        "  • nhap_vao_chung (Đ46) — nhập tài sản riêng vào tài sản chung.\n"
        "  • nha_o_duy_nhat (Đ31) — giao dịch nhà ở duy nhất kể cả khi nhà "
        "là tài sản riêng.\n"
        "  • nguon_song_duy_nhat (Đ44 K4) — hoa lợi tài sản riêng là nguồn "
        "sống duy nhất.\n"
        "Phù hợp khi câu hỏi đề cập tới 'tài sản riêng', 'mua trước khi cưới', "
        "'nhà sở hữu riêng', 'nhà ở duy nhất', 'gộp/nhập tài sản', 'để dành "
        "tài sản riêng'. KHÔNG dùng cho câu hỏi PHÂN LOẠI tài sản chung/riêng "
        "(đó là 'phan_loai_tai_san')."
    ),
    params_schema=TaiSanRiengNhaODuyNhatParams,
    cypher=assemble_cypher(_SEED_BLOCK),
    trace_cypher=assemble_simple_trace(_SEED_BLOCK),
)
