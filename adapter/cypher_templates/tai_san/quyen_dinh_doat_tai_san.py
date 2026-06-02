"""Template 3 — QUYỀN ĐỊNH ĐOẠT TÀI SẢN (chung hoặc riêng).

Trả lời câu hỏi về quyền/nghĩa vụ khi bán, tặng, thế chấp, chuyển nhượng...
tài sản chung HOẶC tài sản riêng. Bao gồm:
- Đ35 — Chiếm hữu, sử dụng, định đoạt tài sản chung; yêu cầu văn bản cho BĐS/
  động sản đăng ký/tài sản tạo thu nhập chủ yếu.
- Đ44 — Quyền chiếm hữu, sử dụng, định đoạt tài sản riêng.
- Đ31 — Giao dịch nhà ở duy nhất (đặc biệt).
- Đ29 — Nguyên tắc bình đẳng (bổ trợ).

Coverage: Q1 (định đoạt tài sản chung trái phép), Q4 (bán đất là tài sản chung),
Q16 (chồng mua nhà cho nhân tình), Q23 (bán đất cần cả 2 vợ chồng ký).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.tai_san._common import assemble_cypher, assemble_simple_trace, assemble_semantic_viz


class QuyenDinhDoatTaiSanParams(BaseModel):
    loai_tai_san_dinh_doat: Literal["chung", "rieng", "tat_ca"] = Field(
        description=(
            "Tài sản đang được định đoạt là TÀI SẢN CHUNG hay TÀI SẢN RIÊNG:\n"
            "  • 'chung' khi câu hỏi nói rõ là tài sản chung (vd 'bán đất là "
            "tài sản chung của vợ chồng', 'chia tài sản chung của vợ chồng').\n"
            "  • 'rieng' khi câu hỏi nói rõ là tài sản riêng (vd 'tài sản riêng "
            "của chồng có cần xin phép vợ?', 'mua nhà trước khi cưới').\n"
            "  • 'tat_ca' khi câu hỏi không rõ ràng hoặc cần phân tích cả 2 "
            "hướng (vd 'chồng bán đất có cần sự đồng ý của vợ?' — đất có thể "
            "chung hoặc riêng)."
        )
    )
    loai_giao_dich: Literal[
        "ban_chuyen_nhuong",
        "tang_cho",
        "the_chap_cam_co",
        "dinh_doat_tong_quat",
        "su_dung",
    ] = Field(
        description=(
            "Loại giao dịch định đoạt:\n"
            "  • 'ban_chuyen_nhuong': bán, chuyển nhượng (nhà, đất, xe...).\n"
            "  • 'tang_cho': tặng cho, biếu.\n"
            "  • 'the_chap_cam_co': thế chấp, cầm cố, vay thế chấp.\n"
            "  • 'dinh_doat_tong_quat': câu hỏi chung về định đoạt mà không "
            "nêu rõ giao dịch cụ thể (vd 'cần thỏa thuận khi định đoạt tài "
            "sản chung không?').\n"
            "  • 'su_dung': chiếm hữu, sử dụng (không định đoạt)."
        )
    )
    asset_keyword: Optional[str] = Field(
        default=None,
        description=(
            "ID THUẬT NGỮ PHÁP LÝ chuẩn của loại tài sản cụ thể trong câu hỏi "
            "(snake_case). Để null nếu câu hỏi không nêu loại tài sản cụ thể.\n"
            "MAP từ ngôn ngữ thông tục → ID chuẩn:\n"
            "  • 'đất', 'thửa đất', 'sổ đỏ' → 'quyen_su_dung_dat'\n"
            "  • 'nhà', 'căn hộ', 'chung cư', 'bất động sản' → 'bat_dong_san'\n"
            "  • 'nhà ở duy nhất' → 'nha_o_duy_nhat'\n"
            "  • 'xe máy', 'ô tô' → 'dong_san_phai_dang_ky'\n"
            "  • 'sổ tiết kiệm', 'tài khoản ngân hàng' → 'tai_khoan_ngan_hang_chung_khoan'\n"
            "  • 'tài sản kinh doanh', 'nguồn thu nhập chủ yếu' → 'tai_san_tao_thu_nhap_chu_yeu'\n"
            "  • Câu hỏi tổng quát → null."
        ),
    )


_SEED_BLOCK = """
// ============================================================
// PHẦN 1 — SEED HanhVi định đoạt từ KG NGỮ NGHĨA
// ============================================================

WITH
  CASE $loai_tai_san_dinh_doat
    WHEN 'chung' THEN ['chung']
    WHEN 'rieng' THEN ['rieng']
    ELSE ['chung', 'rieng']
  END AS tinh_chat_list,
  $loai_giao_dich AS lgd

// 1a. Match HanhVi định đoạt theo loại giao dịch
UNWIND tinh_chat_list AS tc

OPTIONAL MATCH (hv:HanhVi:CheDoTaiSanCuaVoChong)
WHERE
  // Lọc HanhVi theo loại giao dịch
  (
    (lgd = 'ban_chuyen_nhuong' AND hv.loai IN ['ban', 'dinh_doat'])
    OR (lgd = 'tang_cho' AND hv.loai IN ['tang_cho', 'dinh_doat'])
    OR (lgd = 'the_chap_cam_co' AND hv.loai IN ['the_chap', 'dinh_doat'])
    OR (lgd = 'dinh_doat_tong_quat' AND hv.loai IN ['dinh_doat'])
    OR (lgd = 'su_dung' AND hv.loai IN ['su_dung'])
  )
  // Lọc theo tính chất tài sản & asset_keyword:
  //  - HanhVi có dấu hiệu chung/rieng qua tên (ban_chuyen_nhuong_bds vs
  //    ban_chuyen_nhuong_tai_san_rieng) hoặc qua liên kết tới LoaiTaiSan.
  //  - Chấp nhận target.tinh_chat = tc HOẶC target.tinh_chat = 'trung_lap'
  //    (vì BĐS có thể chung hoặc riêng tuỳ ngữ cảnh).
  AND (
    // Quick check qua tên HanhVi (đảm bảo phân nhánh chung/rieng đúng)
    (tc = 'chung' AND NOT (hv.id CONTAINS 'tai_san_rieng' OR hv.id CONTAINS 'tai_san_rieng_'))
    OR (tc = 'rieng' AND (hv.id CONTAINS 'tai_san_rieng' OR hv.id CONTAINS 'tai_san_rieng_'))
  )
  // asset_keyword là HINT mềm. Nhánh 'rieng' KHÔNG filter theo asset_keyword
  // (vì taxonomy HanhVi tài sản riêng không có granularity theo loại tài sản).
  // Nhánh 'chung' filter chặt hơn — nếu match TAC_DONG_LEN thì giữ; nếu HanhVi
  // không có edge tới asset_keyword thì vẫn giữ (HanhVi tổng quát như
  // `dinh_doat_tai_san_chung`).
  AND (
    $asset_keyword IS NULL
    OR tc = 'rieng'
    OR EXISTS {
      MATCH (hv)-[:TAC_DONG_LEN]->(target:LoaiTaiSan:CheDoTaiSanCuaVoChong)
      WHERE target.id = $asset_keyword
        OR EXISTS {
          MATCH (target)-[:LA_LOAI_CON_CUA*0..3]->(parent:LoaiTaiSan:CheDoTaiSanCuaVoChong {id: $asset_keyword})
        }
        OR EXISTS {
          MATCH (child:LoaiTaiSan:CheDoTaiSanCuaVoChong {id: $asset_keyword})-[:LA_LOAI_CON_CUA*0..3]->(target)
        }
    }
    OR NOT EXISTS {
      MATCH (hv)-[:TAC_DONG_LEN]->(:LoaiTaiSan:CheDoTaiSanCuaVoChong)
    }
  )

// 1b. Mở rộng: cùng lấy các node ngữ nghĩa liên quan (ThoaThuan, HauQua,
//     TruongHopNgoaiLe) để phục vụ trace + đảm bảo cover CAN_CU_TAI đầy đủ.
WITH collect(DISTINCT hv) AS hv_list, tc

UNWIND hv_list AS hv
WITH DISTINCT hv

OPTIONAL MATCH (hv)-[:YEU_CAU_THOA_THUAN]->(tt:ThoaThuan:CheDoTaiSanCuaVoChong)
OPTIONAL MATCH (hv)-[:DAN_TOI]->(hq:HauQua:CheDoTaiSanCuaVoChong)
OPTIONAL MATCH (hv)-[:CO_NGOAI_LE]->(nl:TruongHopNgoaiLe:CheDoTaiSanCuaVoChong)

WITH collect(DISTINCT hv) + collect(DISTINCT tt) + collect(DISTINCT hq) + collect(DISTINCT nl) AS seed_nodes

UNWIND seed_nodes AS sn
WITH sn WHERE sn IS NOT NULL

MATCH (sn)-[:CAN_CU_TAI]->(luat)
WITH DISTINCT luat AS n_goc
"""


quyen_dinh_doat_tai_san = CypherTemplate(
    name="quyen_dinh_doat_tai_san",
    description=(
        "Quyền định đoạt tài sản (bán, tặng, thế chấp, chuyển nhượng) — phân "
        "biệt theo tài sản chung (Đ35) hay tài sản riêng (Đ44). Bao gồm yêu "
        "cầu thỏa thuận bằng văn bản, ngoại lệ nhà ở duy nhất (Đ31), hậu quả "
        "khi định đoạt trái phép. Phù hợp với câu hỏi như: 'Bán đất là tài "
        "sản chung có cần đồng ý của vợ?', 'Chồng bán nhà cho nhân tình bằng "
        "tài sản chung — vợ làm gì?', 'Có cần cả 2 vợ chồng ký hợp đồng bán "
        "đất?'. KHÔNG dùng cho câu hỏi về phân loại tài sản (chung/riêng) — "
        "đó là 'phan_loai_tai_san'."
    ),
    params_schema=QuyenDinhDoatTaiSanParams,
    cypher=assemble_cypher(_SEED_BLOCK),
    trace_cypher=assemble_simple_trace(_SEED_BLOCK),
    viz_cypher=assemble_semantic_viz(_SEED_BLOCK),
)
