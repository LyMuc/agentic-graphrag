"""Template 1 — PHÂN LOẠI TÀI SẢN.

Trả lời câu hỏi: "X là tài sản chung hay riêng?", "Tài sản chung gồm những gì?",
"Quyền sử dụng đất sau kết hôn là tài sản chung hay riêng?", "Tiền trúng số có
phải tài sản chung không?", v.v.

Cách hoạt động (KG mới):
1. Match `LoaiTaiSan` theo `tinh_chat` (chung/riêng/cả hai).
2. Nếu user nêu loại tài sản cụ thể (`asset_keyword`), match đúng `id` hoặc
   match con-cháu qua `LA_LOAI_CON_CUA`.
3. Tất cả `LoaiTaiSan` match được đều `CAN_CU_TAI` về `DieuLuat/DieuKhoanLuat/
   DieuKhoanDiemLuat` (Đ33, Đ43, Đ40 cho hoa lợi sau chia) → đưa vào EXPAND chung.

Coverage: Q3, Q7, Q8, Q14, Q17 (một phần), Q18.

Ví dụ:
- "Tài sản chung trong thời kì hôn nhân bao gồm những tài sản nào?"
  -> loai_tai_san='chung', asset_keyword=None  (seed: Đ33 và các Khoản)
- "Quyền sử dụng đất sau kết hôn là tài sản chung hay riêng?"
  -> loai_tai_san='tat_ca', asset_keyword='quyen_su_dung_dat'
- "Tiền trúng số có phải tài sản chung?"
  -> loai_tai_san='chung', asset_keyword='thu_nhap_hop_phap_khac'
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.tai_san._common import assemble_cypher, assemble_simple_trace, assemble_semantic_viz


class PhanLoaiTaiSanParams(BaseModel):
    loai_tai_san: Literal["chung", "rieng", "tat_ca"] = Field(
        description=(
            "Loại tài sản người dùng đang quan tâm.\n"
            "  • 'chung' nếu chỉ hỏi về tài sản chung.\n"
            "  • 'rieng' nếu chỉ hỏi về tài sản riêng.\n"
            "  • 'tat_ca' khi câu hỏi yêu cầu phân biệt cả hai (vd 'X là tài "
            "sản chung hay riêng?', hoặc 'tài sản chung/riêng gồm những gì?')."
        )
    )
    asset_keyword: Optional[str] = Field(
        default=None,
        description=(
            "ID THUẬT NGỮ PHÁP LÝ chuẩn trong KG (snake_case) — KHÔNG dùng từ "
            "thông tục/đời thường. BẮT BUỘC map từ ngữ trong câu hỏi sang ID "
            "chuẩn dưới đây trước khi điền (giữ nguyên dấu tiếng Việt KHÔNG có):\n"
            "  • 'lương', 'tiền lương', 'thu nhập đi làm' → 'thu_nhap_lao_dong'\n"
            "  • 'thu nhập kinh doanh', 'doanh thu' → 'thu_nhap_san_xuat_kinh_doanh'\n"
            "  • 'tiền trúng số', 'tiền thưởng', 'tiền trợ cấp' → "
            "'thu_nhap_hop_phap_khac'\n"
            "  • 'hoa lợi', 'lợi tức', 'tiền cho thuê tài sản riêng', 'cổ tức' "
            "→ 'hoa_loi_loi_tuc'\n"
            "  • 'đất', 'thửa đất', 'sổ đỏ', 'quyền sử dụng đất' (sau kết hôn) "
            "→ 'quyen_su_dung_dat'\n"
            "  • 'nhà', 'căn hộ', 'chung cư', 'bất động sản' → 'bat_dong_san'\n"
            "  • 'nhà ở duy nhất', 'nơi ở duy nhất' → 'nha_o_duy_nhat'\n"
            "  • 'ô tô', 'xe máy', 'động sản phải đăng ký' → 'dong_san_phai_dang_ky'\n"
            "  • 'sổ tiết kiệm', 'tài khoản ngân hàng' → 'tai_khoan_ngan_hang_chung_khoan'\n"
            "  • 'thừa kế chung', 'di sản hai vợ chồng cùng nhận' → "
            "'tai_san_thua_ke_chung'\n"
            "  • 'thừa kế riêng' → 'tai_san_thua_ke_rieng'\n"
            "  • 'tặng cho chung' → 'tai_san_tang_cho_chung'\n"
            "  • 'tặng cho riêng' → 'tai_san_tang_cho_rieng'\n"
            "  • 'tài sản trước hôn nhân', 'tài sản trước khi cưới' → "
            "'tai_san_truoc_ket_hon'\n"
            "  • 'tài sản phục vụ nhu cầu cá nhân', 'đồ dùng cá nhân' → "
            "'tai_san_phuc_vu_nhu_cau_thiet_yeu_ca_nhan'\n"
            "  • 'tài sản đang tranh chấp' → 'tai_san_dang_tranh_chap'\n"
            "  • Câu hỏi tổng quát hoặc không xác định → null.\n"
            "VÍ DỤ: 'Tiền trúng số có phải tài sản chung?' → 'thu_nhap_hop_phap_khac'; "
            "'Quyền sử dụng đất sau kết hôn là tài sản gì?' → 'quyen_su_dung_dat'; "
            "'Tài sản chung gồm những gì?' → null."
        ),
    )


_SEED_BLOCK = """
// ============================================================
// PHẦN 1 — SEED LoaiTaiSan từ KG NGỮ NGHĨA
// ============================================================
// 1a. Lấy danh sách tinh_chat cần match
WITH
  CASE $loai_tai_san
    WHEN 'chung' THEN ['chung']
    WHEN 'rieng' THEN ['rieng']
    ELSE ['chung', 'rieng']
  END AS tinh_chat_list

// 1b. Match LoaiTaiSan theo tinh_chat
UNWIND tinh_chat_list AS tc
MATCH (lts:LoaiTaiSan:CheDoTaiSanCuaVoChong)
WHERE lts.tinh_chat = tc
  AND (
        $asset_keyword IS NULL
        OR lts.id = $asset_keyword
        OR EXISTS {
            MATCH (lts)-[:LA_LOAI_CON_CUA*0..3]->(parent:LoaiTaiSan:CheDoTaiSanCuaVoChong {id: $asset_keyword})
        }
        OR EXISTS {
            MATCH (child:LoaiTaiSan:CheDoTaiSanCuaVoChong {id: $asset_keyword})-[:LA_LOAI_CON_CUA*0..3]->(lts)
        }
        OR toLower(lts.id) CONTAINS toLower($asset_keyword)
      )

WITH collect(DISTINCT lts) AS seed_nodes
UNWIND seed_nodes AS sn
WITH sn WHERE sn IS NOT NULL

// 1c. Đi tới Điều/Khoản/Điểm gốc qua CAN_CU_TAI
MATCH (sn)-[:CAN_CU_TAI]->(luat)
WITH DISTINCT luat AS n_goc
"""


phan_loai_tai_san = CypherTemplate(
    name="phan_loai_tai_san",
    description=(
        "Phân loại tài sản: trả lời câu hỏi 'X là tài sản chung hay tài sản riêng?', "
        "'Tài sản chung gồm những gì?', 'Tài sản riêng gồm những gì?', "
        "'Y có phải tài sản chung trong thời kỳ hôn nhân không?', 'Tiền trúng số "
        "có phải tài sản chung không?'. Phù hợp khi câu hỏi tập trung vào việc "
        "XÁC ĐỊNH bản chất / phạm vi của khối tài sản, KHÔNG hỏi về quyền định "
        "đoạt, nghĩa vụ, hay chia tài sản."
    ),
    params_schema=PhanLoaiTaiSanParams,
    cypher=assemble_cypher(_SEED_BLOCK),
    trace_cypher=assemble_simple_trace(_SEED_BLOCK),
    viz_cypher=assemble_semantic_viz(_SEED_BLOCK),
)
