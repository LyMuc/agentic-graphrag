"""Template 5 — NGHĨA VỤ TÀI SẢN (chung / riêng / liên đới / tất cả).

Trả lời câu hỏi về nghĩa vụ tài sản của vợ chồng, bao gồm:
- Đ27 — Trách nhiệm liên đới của vợ chồng.
- Đ30 — Quyền/nghĩa vụ trong giao dịch đáp ứng nhu cầu thiết yếu gia đình.
- Đ37 — 6 loại nghĩa vụ chung.
- Đ45 — 4 loại nghĩa vụ riêng.

Coverage: Q5 (lấy tài sản chung trả nợ riêng), Q9 (chồng ôm nợ),
Q10 (nghĩa vụ chung), Q11 (nghĩa vụ chung), Q13 (cả chung và riêng),
Q15 (nghĩa vụ riêng).

NOTE quan trọng (Q5 — "tài sản chung trả nợ riêng"): câu hỏi mang tính
ĐỐI CHIẾU giữa nghĩa vụ chung và riêng (vì một khoản "nợ riêng" có thể
chuyển thành nghĩa vụ chung/liên đới nếu phục vụ nhu cầu thiết yếu gia
đình theo Đ27, Đ30). Với class câu hỏi này, dùng `loai_nghia_vu =
'tat_ca'` để KG trả về CẢ Đ27 + Đ30 + Đ37 + Đ45 — tránh trường hợp chỉ
trả về 1 chiều (vd chỉ Đ45) gây thiếu căn cứ.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.tai_san._common import (
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("loai_nghia_vu",)


class NghiaVuTaiSanParams(BaseModel):
    loai_nghia_vu: Literal["chung", "rieng", "lien_doi", "tat_ca"] = Field(
        description=(
            "Loại nghĩa vụ tài sản người dùng hỏi:\n"
            "  • 'chung' (Đ37): câu hỏi RÕ RÀNG chỉ về nghĩa vụ CHUNG, KHÔNG "
            "đối chiếu với nghĩa vụ riêng. Vd 'nghĩa vụ chung của vợ chồng "
            "gồm những gì?', 'tiền nuôi con có phải nợ chung không?'.\n"
            "  • 'rieng' (Đ45): câu hỏi RÕ RÀNG chỉ về nghĩa vụ RIÊNG, KHÔNG "
            "đối chiếu với nghĩa vụ chung. Vd 'nghĩa vụ riêng gồm những gì?', "
            "'nợ trước khi cưới là gì?', 'bồi thường do vi phạm pháp luật "
            "của một bên'.\n"
            "  • 'lien_doi' (Đ27): câu hỏi RÕ RÀNG về trách nhiệm liên đới — "
            "vd 'khi nào vợ chồng cùng chịu trách nhiệm liên đới?'.\n"
            "  • 'tat_ca' (Đ27 + Đ30 + Đ37 + Đ45): dùng cho 2 nhóm câu hỏi:\n"
            "      (a) TỔNG QUÁT — vd 'vợ chồng có những nghĩa vụ gì về tài "
            "sản?', 'kể các nghĩa vụ tài sản của vợ chồng'.\n"
            "      (b) ĐỐI CHIẾU / CROSS-CUTTING giữa chung và riêng — KHÔNG "
            "thể trả lời chỉ bằng 1 chiều vì nợ riêng có thể chuyển thành "
            "nghĩa vụ chung/liên đới nếu phục vụ nhu cầu thiết yếu gia đình. "
            "Ví dụ:\n"
            "          - 'Lấy/dùng tài sản chung để TRẢ NỢ RIÊNG có được "
            "không?' (vì nợ riêng có thể là chung nếu phục vụ nhu cầu gia "
            "đình)\n"
            "          - 'Lấy/dùng tài sản riêng để TRẢ NỢ CHUNG có được?'\n"
            "          - 'Nợ này là CHUNG HAY RIÊNG?' (cần phân biệt cả 2)\n"
            "          - 'Khi nào nợ của một bên trở thành nợ chung của 2 "
            "vợ chồng?'\n"
            "          - 'Vợ có phải trả nợ thay chồng không?' (cần kiểm tra "
            "liên đới + chung + riêng)\n"
            "QUY TẮC: nếu BAN ĐẦU bạn định chọn 'chung' hoặc 'rieng' nhưng "
            "câu hỏi có chứa cả từ 'chung' VÀ 'riêng' (vd 'tài sản CHUNG' để "
            "trả 'nợ RIÊNG'), HÃY ĐỔI sang 'tat_ca'."
        )
    )
    tinh_huong_keyword: Optional[str] = Field(
        default=None,
        description=(
            "Từ khoá tình huống/nguyên nhân nghĩa vụ — giúp lọc đúng Khoản. "
            "Map từ ngôn ngữ thông tục → keyword chuẩn (snake_case):\n"
            "  • 'tiền học cho con', 'nuôi con', 'tiền chợ', 'sinh hoạt' → "
            "'nhu_cau_thiet_yeu'\n"
            "  • 'vay tiêu dùng cá nhân', 'vay riêng', 'đầu tư cá nhân' → "
            "'giao_dich_ca_nhan'\n"
            "  • 'bồi thường do con gây ra' → 'con_gay_thiet_hai'\n"
            "  • 'bồi thường do vi phạm pháp luật', 'tai nạn giao thông gây "
            "thương tích' → 'vi_pham_phap_luat'\n"
            "  • 'nợ trước hôn nhân', 'nợ trước khi cưới' → 'truoc_ket_hon'\n"
            "  • 'thỏa thuận chung của vợ chồng' → 'giao_dich_thoa_thuan'\n"
            "  • 'chiếm hữu/sử dụng/định đoạt tài sản chung' → 'dinh_doat_tai_san_chung'\n"
            "  • Với câu hỏi 'tat_ca' (vd tổng quát hoặc đối chiếu chung-"
            "riêng như 'lấy tài sản chung trả nợ riêng'): ĐỂ NULL — vì câu "
            "hỏi không khoá tình huống cụ thể, cần expand toàn bộ.\n"
            "  • Câu hỏi tổng quát khác → null."
        ),
    )


_DIEU_WHITELIST = [
    "Luat_HNGD_2014_Dieu_27",
    "Luat_HNGD_2014_Dieu_30",
    "Luat_HNGD_2014_Dieu_37",
    "Luat_HNGD_2014_Dieu_45",
]

_SEED_BODY = f"""
// ============================================================
// PHẦN 1 — SEED semantic graph (NghiaVu Đ27/30/37/45)
// ============================================================
WITH $loai_nghia_vu AS lnv_param,
     $tinh_huong_keyword AS thk,
     $whitelist_dieu_ids AS wl

WITH lnv_param, thk, wl,
  CASE lnv_param
    WHEN 'chung' THEN ['chung']
    WHEN 'rieng' THEN ['rieng']
    WHEN 'lien_doi' THEN ['lien_doi']
    ELSE ['chung', 'rieng', 'lien_doi']
  END AS loai_list

UNWIND loai_list AS lnv

OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL})
WHERE nv.loai_nghia_vu = lnv
  AND (
    thk IS NULL
    OR toLower(nv.id) CONTAINS toLower(thk)
    OR EXISTS {{
        MATCH (nv)-[:PHAT_SINH_TU]->(target:CheDoTaiSanCuaVoChong)
        WHERE toLower(target.id) CONTAINS toLower(thk)
    }}
  )

OPTIONAL MATCH (nv)-[:PHAT_SINH_TU]->(hv:HanhVi:{TOPIC_LABEL})
OPTIONAL MATCH (nv)-[:THANH_TOAN_BANG]->(lts:LoaiTaiSan:{TOPIC_LABEL})

WITH wl, lnv_param, thk,
  collect(DISTINCT nv) AS nv_list,
  collect(DISTINCT hv) AS hv_list,
  collect(DISTINCT lts) AS lts_list

WITH wl, lnv_param, thk,
  [x IN nv_list + hv_list + lts_list WHERE x IS NOT NULL] AS seed_nodes,
  [x IN nv_list WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: NghiaVuTaiSanParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    base = params.model_dump()
    base["whitelist_dieu_ids"] = _DIEU_WHITELIST if use_wl else []
    return base


nghia_vu_tai_san = CypherTemplate(
    name="nghia_vu_tai_san",
    description=(
        "Nghĩa vụ tài sản của vợ chồng — bao gồm nghĩa vụ chung (Đ37, 6 loại: "
        "giao dịch chung, nhu cầu thiết yếu, chiếm hữu/định đoạt tài sản chung, "
        "dùng tài sản riêng phục vụ tài sản chung, bồi thường do con gây ra, "
        "nghĩa vụ khác theo luật), nghĩa vụ riêng (Đ45, 4 loại: trước hôn "
        "nhân, từ định đoạt tài sản riêng, từ giao dịch cá nhân không vì gia "
        "đình, từ vi phạm pháp luật), trách nhiệm liên đới Đ27, và nghĩa vụ "
        "đáp ứng nhu cầu thiết yếu gia đình Đ30.\n"
        "Phù hợp khi câu hỏi đề cập tới 'nợ chung/riêng', 'nghĩa vụ', 'trách "
        "nhiệm tài sản', 'bồi thường', 'ai trả nợ', 'lấy tài sản chung/riêng "
        "trả nợ riêng/chung'. Đặc biệt với câu hỏi MANG TÍNH ĐỐI CHIẾU chung-"
        "riêng (vd 'lấy tài sản chung trả nợ riêng được không?') hoặc câu hỏi "
        "TỔNG QUÁT, dùng `loai_nghia_vu='tat_ca'` để KG trả về cả Đ27 + Đ30 + "
        "Đ37 + Đ45 — đủ căn cứ cho LLM phân tích."
    ),
    params_schema=NghiaVuTaiSanParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
