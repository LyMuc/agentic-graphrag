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
    EXPAND_AND_TIMEFILTER_CYPHER,
    assemble_semantic_viz_from_trace_prefix,
)


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


# Mapping loai_nghia_vu → whitelist Điều luật chốt cứng (đảm bảo cover).
# Nhánh `tat_ca` whitelist 4 Điều cốt lõi vì các câu hỏi tổng quát và
# cross-cutting đều cần đủ cả 4 chiều để LLM trả lời đầy đủ.
_LOAI_TO_WHITELIST_DIEU: dict[str, list[str]] = {
    "chung": [],
    "rieng": [],
    "lien_doi": [],
    "tat_ca": [
        "Luat_HNGD_2014_Dieu_27",  # liên đới
        "Luat_HNGD_2014_Dieu_30",  # nhu cầu thiết yếu gia đình
        "Luat_HNGD_2014_Dieu_37",  # nghĩa vụ chung
        "Luat_HNGD_2014_Dieu_45",  # nghĩa vụ riêng
    ],
}


_SEED_BLOCK = """
// ============================================================
// PHẦN 1 — SEED NghiaVu từ KG NGỮ NGHĨA + whitelist Đ27/30/37/45 (cho tat_ca)
// ============================================================
WITH $loai_nghia_vu AS lnv_param,
     $tinh_huong_keyword AS thk,
     $whitelist_dieu_ids AS wl

// 1a. Suy ra danh sách loai_nghia_vu cần match
WITH lnv_param, thk, wl,
  CASE lnv_param
    WHEN 'chung' THEN ['chung']
    WHEN 'rieng' THEN ['rieng']
    WHEN 'lien_doi' THEN ['lien_doi']
    ELSE ['chung', 'rieng', 'lien_doi']
  END AS loai_list

UNWIND loai_list AS lnv

// 1b. Match NghiaVu theo loai_nghia_vu + tinh_huong_keyword (mềm)
OPTIONAL MATCH (nv:NghiaVu:CheDoTaiSanCuaVoChong)
WHERE nv.loai_nghia_vu = lnv
  AND (
    thk IS NULL
    OR toLower(nv.id) CONTAINS toLower(thk)
    OR EXISTS {
        MATCH (nv)-[:PHAT_SINH_TU]->(target:CheDoTaiSanCuaVoChong)
        WHERE toLower(target.id) CONTAINS toLower(thk)
    }
  )

WITH wl, collect(DISTINCT nv) AS nv_list

UNWIND nv_list AS nv
OPTIONAL MATCH (nv)-[:PHAT_SINH_TU]->(hv:HanhVi:CheDoTaiSanCuaVoChong)
OPTIONAL MATCH (nv)-[:THANH_TOAN_BANG]->(lts:LoaiTaiSan:CheDoTaiSanCuaVoChong)

WITH wl, collect(DISTINCT nv) + collect(DISTINCT hv) + collect(DISTINCT lts) AS seed_nodes

UNWIND seed_nodes AS sn
WITH wl, sn
WHERE sn IS NOT NULL

// 1c. Đi tới legal layer qua CAN_CU_TAI
OPTIONAL MATCH (sn)-[:CAN_CU_TAI]->(luat_semantic)
WHERE luat_semantic IS NOT NULL

// 1d. Whitelist DieuLuat (đảm bảo cover Đ27/30/37/45 cho nhánh tat_ca)
OPTIONAL MATCH (luat_whitelist:DieuLuat)
WHERE luat_whitelist.id IN wl

WITH collect(DISTINCT luat_semantic) + collect(DISTINCT luat_whitelist) AS all_seeds
UNWIND all_seeds AS n_goc
WITH DISTINCT n_goc
WHERE n_goc IS NOT NULL
"""


# Trace cypher — chạy riêng phần SEED và RETURN list triple (giống chia/thoa_thuan)
_TRACE_CYPHER = """
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

OPTIONAL MATCH (nv:NghiaVu:CheDoTaiSanCuaVoChong)
WHERE nv.loai_nghia_vu = lnv
  AND (
    thk IS NULL
    OR toLower(nv.id) CONTAINS toLower(thk)
    OR EXISTS {
        MATCH (nv)-[:PHAT_SINH_TU]->(target:CheDoTaiSanCuaVoChong)
        WHERE toLower(target.id) CONTAINS toLower(thk)
    }
  )

WITH wl, collect(DISTINCT nv) AS nv_list

UNWIND nv_list AS nv
OPTIONAL MATCH (nv)-[:PHAT_SINH_TU]->(hv:HanhVi:CheDoTaiSanCuaVoChong)
OPTIONAL MATCH (nv)-[:THANH_TOAN_BANG]->(lts:LoaiTaiSan:CheDoTaiSanCuaVoChong)

WITH wl, collect(DISTINCT nv) + collect(DISTINCT hv) + collect(DISTINCT lts) AS seed_nodes

UNWIND seed_nodes AS sn
WITH wl, sn
WHERE sn IS NOT NULL

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
    src_id: 'loai_nghia_vu',
    rel: 'WHITELIST',
    dst_label: 'DieuLuat',
    dst_id: wid
}) AS wl_triples

WITH semantic_triples + wl_triples AS seed_trace
RETURN seed_trace
"""


def _params_builder(params: NghiaVuTaiSanParams) -> dict[str, Any]:
    base = params.model_dump()
    base["whitelist_dieu_ids"] = _LOAI_TO_WHITELIST_DIEU.get(params.loai_nghia_vu, [])
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
    cypher=_SEED_BLOCK.rstrip() + "\n\n" + EXPAND_AND_TIMEFILTER_CYPHER,
    trace_cypher=_TRACE_CYPHER,
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_TRACE_CYPHER),
    params_builder=_params_builder,
)
