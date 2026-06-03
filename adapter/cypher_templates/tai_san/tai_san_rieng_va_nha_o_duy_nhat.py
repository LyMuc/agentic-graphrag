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

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.tai_san._common import (
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
)


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


_SEED_BODY = f"""
// ============================================================
// PHẦN 1 — SEED semantic graph (tài sản riêng & nhà ở duy nhất)
// ============================================================
WITH $khia_canh AS kc, [] AS wl

OPTIONAL MATCH (lts_rieng:LoaiTaiSan:{TOPIC_LABEL} {{id: 'tai_san_rieng'}})
WHERE kc IN ['chiem_huu_su_dung', 'dinh_doat', 'nhap_vao_chung', 'nguon_song_duy_nhat', 'tat_ca']

OPTIONAL MATCH (lts_rieng)-[:LIEN_QUAN]->(hv_rieng:HanhVi:{TOPIC_LABEL})
WHERE kc IN ['chiem_huu_su_dung', 'dinh_doat', 'nhap_vao_chung', 'nguon_song_duy_nhat', 'tat_ca']
  AND (
    (kc IN ['chiem_huu_su_dung', 'tat_ca'] AND hv_rieng.id IN [
      'chiem_huu_su_dung_tai_san_rieng',
      'ban_chuyen_nhuong_tai_san_rieng'
    ])
    OR (kc IN ['dinh_doat', 'nguon_song_duy_nhat', 'tat_ca'] AND hv_rieng.id = 'dinh_doat_tai_san_rieng')
    OR (kc IN ['nhap_vao_chung', 'tat_ca'] AND hv_rieng.id = 'nhap_tai_san_rieng_vao_chung')
  )

OPTIONAL MATCH (quyen_ch:Quyen:{TOPIC_LABEL})
WHERE kc IN ['chiem_huu_su_dung', 'dinh_doat', 'tat_ca']
  AND quyen_ch.id IN [
    'quyen_chiem_huu_su_dung_tai_san_rieng',
    'quyen_dinh_doat_tai_san_rieng',
    'quyen_quan_ly_thay',
    'quyen_nhap_hoac_khong_nhap_tai_san_rieng'
  ]
OPTIONAL MATCH (quyen_ch)-[:LIEN_QUAN]->(dk_ql:DieuKien:{TOPIC_LABEL})
WHERE kc IN ['chiem_huu_su_dung', 'tat_ca']
  AND quyen_ch.id = 'quyen_quan_ly_thay'

OPTIONAL MATCH (hv_rieng)-[:DAN_TOI]->(hq_nhap:HauQua:{TOPIC_LABEL})
WHERE kc IN ['nhap_vao_chung', 'tat_ca']
  AND hv_rieng.id = 'nhap_tai_san_rieng_vao_chung'

OPTIONAL MATCH (tt_nhap:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_nhap_tai_san_rieng'}})
WHERE kc IN ['nhap_vao_chung', 'tat_ca']

OPTIONAL MATCH (nv_rieng:NghiaVu:{TOPIC_LABEL})
WHERE kc IN ['dinh_doat', 'tat_ca']
  AND nv_rieng.id = 'nghia_vu_rieng_chiem_huu_dinh_doat_tai_san_rieng'

OPTIONAL MATCH (lts_nha:LoaiTaiSan:{TOPIC_LABEL} {{id: 'nha_o_duy_nhat'}})
WHERE kc IN ['nha_o_duy_nhat', 'tat_ca']

OPTIONAL MATCH (lts_nha)-[:LIEN_QUAN]->(hv_nha:HanhVi:{TOPIC_LABEL} {{id: 'giao_dich_nha_o_duy_nhat'}})
WHERE kc IN ['nha_o_duy_nhat', 'tat_ca']

OPTIONAL MATCH (hv_nha)-[:AP_DUNG_KHI]->(dk_nha:DieuKien:{TOPIC_LABEL})
WHERE kc IN ['nha_o_duy_nhat', 'tat_ca']

OPTIONAL MATCH (hv_nha)-[:DAN_TOI]->(hq_nha:HauQua:{TOPIC_LABEL})
WHERE kc IN ['nha_o_duy_nhat', 'tat_ca']

OPTIONAL MATCH (hv_nha)-[:CO_NGOAI_LE]->(nl_nha:TruongHopNgoaiLe:{TOPIC_LABEL})
WHERE kc IN ['nha_o_duy_nhat', 'tat_ca']

OPTIONAL MATCH (tt_nha:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_dinh_doat_nha_o_duy_nhat'}})
WHERE kc IN ['nha_o_duy_nhat', 'tat_ca']

OPTIONAL MATCH (nv_cho:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_bao_dam_cho_o_cho_vo_chong'}})
WHERE kc IN ['nha_o_duy_nhat', 'tat_ca']

OPTIONAL MATCH (hv_dd:HanhVi:{TOPIC_LABEL} {{id: 'dinh_doat_tai_san_rieng'}})
WHERE kc IN ['nguon_song_duy_nhat', 'tat_ca']
OPTIONAL MATCH (hv_dd)-[:AP_DUNG_KHI]->(dk_ns:DieuKien:{TOPIC_LABEL} {{id: 'hoa_loi_la_nguon_song_duy_nhat'}})
WHERE kc IN ['nguon_song_duy_nhat', 'tat_ca']
OPTIONAL MATCH (hv_dd)-[:CO_NGOAI_LE]->(nl_ns:TruongHopNgoaiLe:{TOPIC_LABEL})
WHERE kc IN ['nguon_song_duy_nhat', 'tat_ca']
  AND nl_ns.id = 'ngoai_le_dinh_doat_tai_san_rieng_la_nguon_song_duy_nhat'

WITH wl, kc,
  [x IN collect(DISTINCT lts_rieng) + collect(DISTINCT hv_rieng) + collect(DISTINCT quyen_ch)
       + collect(DISTINCT dk_ql) + collect(DISTINCT hq_nhap) + collect(DISTINCT tt_nhap)
       + collect(DISTINCT nv_rieng)
       + collect(DISTINCT lts_nha) + collect(DISTINCT hv_nha) + collect(DISTINCT dk_nha)
       + collect(DISTINCT hq_nha) + collect(DISTINCT nl_nha) + collect(DISTINCT tt_nha)
       + collect(DISTINCT nv_cho) + collect(DISTINCT hv_dd) + collect(DISTINCT dk_ns)
       + collect(DISTINCT nl_ns)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'chiem_huu_su_dung' THEN
      [x IN collect(DISTINCT hv_rieng) + collect(DISTINCT quyen_ch) + collect(DISTINCT dk_ql)
       WHERE x IS NOT NULL
         AND (x.id STARTS WITH 'chiem_huu' OR x.id STARTS WITH 'quyen_chiem'
              OR x.id STARTS WITH 'ban_chuyen_nhuong_tai_san_rieng'
              OR x.id = 'quyen_quan_ly_thay' OR x.id = 'khong_tu_quan_ly_va_khong_uy_quyen')]
    WHEN 'dinh_doat' THEN
      [x IN collect(DISTINCT hv_rieng) + collect(DISTINCT quyen_ch) + collect(DISTINCT nv_rieng)
       WHERE x IS NOT NULL
         AND (x.id CONTAINS 'dinh_doat' OR x.id CONTAINS 'nghia_vu_rieng')]
    WHEN 'nhap_vao_chung' THEN
      [x IN collect(DISTINCT hv_rieng) + collect(DISTINCT hq_nhap) + collect(DISTINCT tt_nhap)
       WHERE x IS NOT NULL AND x.id CONTAINS 'nhap']
    WHEN 'nha_o_duy_nhat' THEN
      [x IN collect(DISTINCT lts_nha) + collect(DISTINCT hv_nha) + collect(DISTINCT dk_nha)
           + collect(DISTINCT hq_nha) + collect(DISTINCT nl_nha) + collect(DISTINCT tt_nha)
           + collect(DISTINCT nv_cho)
       WHERE x IS NOT NULL]
    WHEN 'nguon_song_duy_nhat' THEN
      [x IN collect(DISTINCT hv_dd) + collect(DISTINCT dk_ns) + collect(DISTINCT nl_ns)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT lts_rieng) + collect(DISTINCT hv_rieng) + collect(DISTINCT quyen_ch)
           + collect(DISTINCT hq_nhap) + collect(DISTINCT tt_nhap) + collect(DISTINCT nv_rieng)
           + collect(DISTINCT lts_nha) + collect(DISTINCT hv_nha) + collect(DISTINCT dk_nha)
           + collect(DISTINCT hq_nha) + collect(DISTINCT nl_nha) + collect(DISTINCT tt_nha)
           + collect(DISTINCT nv_cho) + collect(DISTINCT hv_dd) + collect(DISTINCT dk_ns)
           + collect(DISTINCT nl_ns)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
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
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
)
