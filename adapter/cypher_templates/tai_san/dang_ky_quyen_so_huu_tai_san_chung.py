"""Template 4 — ĐĂNG KÝ QUYỀN SỞ HỮU TÀI SẢN CHUNG (Đ34).

Trả lời câu hỏi về việc đăng ký quyền sở hữu/sử dụng đối với tài sản chung
phải đăng ký, cụ thể:
- Đ34 K1: GCN ghi tên cả hai vợ chồng (trừ thỏa thuận khác).
- Đ34 K2: Trường hợp GCN chỉ ghi một bên — giao dịch theo Đ26, tranh chấp
  theo Đ33 K3.

Coverage: Q23 ("Bán đất có cần cả 2 vợ chồng ký?").
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.tai_san._common import assemble_cypher, assemble_simple_trace


class DangKyQuyenSoHuuParams(BaseModel):
    loai_tai_san_dang_ky: Literal[
        "bat_dong_san",
        "dong_san_phai_dang_ky",
        "tat_ca",
    ] = Field(
        description=(
            "Loại tài sản chung phải đăng ký quyền sở hữu/sử dụng:\n"
            "  • 'bat_dong_san': nhà, đất, căn hộ, chung cư.\n"
            "  • 'dong_san_phai_dang_ky': ô tô, xe máy.\n"
            "  • 'tat_ca': câu hỏi tổng quát, không nêu loại cụ thể."
        )
    )


_SEED_BLOCK = """
// ============================================================
// PHẦN 1 — SEED đăng ký quyền sở hữu/sử dụng tài sản chung (Đ34)
// ============================================================

WITH $loai_tai_san_dang_ky AS lts_dk

// 1a. Bắt đầu từ HanhVi đăng ký quyền sở hữu
MATCH (hv:HanhVi:CheDoTaiSanCuaVoChong {id: 'dang_ky_quyen_so_huu'})

// 1b. Match LoaiTaiSan theo loai_tai_san_dang_ky
OPTIONAL MATCH (hv)-[:TAC_DONG_LEN]->(lts:LoaiTaiSan:CheDoTaiSanCuaVoChong)
WHERE lts_dk = 'tat_ca'
   OR lts.id = lts_dk
   OR EXISTS {
       MATCH (lts)-[:LA_LOAI_CON_CUA*0..2]->(:LoaiTaiSan:CheDoTaiSanCuaVoChong {id: lts_dk})
   }

// 1c. Lấy ngoại lệ + thỏa thuận liên quan
OPTIONAL MATCH (hv)-[:CO_NGOAI_LE]->(nl:TruongHopNgoaiLe:CheDoTaiSanCuaVoChong)
OPTIONAL MATCH (hv)-[:YEU_CAU_THOA_THUAN]->(tt:ThoaThuan:CheDoTaiSanCuaVoChong)
OPTIONAL MATCH (vb:VanBanPhapLy:CheDoTaiSanCuaVoChong) WHERE vb.id IN ['gcn_quyen_so_huu', 'gcn_quyen_su_dung_dat']
OPTIONAL MATCH (dk:DieuKien:CheDoTaiSanCuaVoChong {id: 'tai_san_phai_dang_ky'})

WITH collect(DISTINCT hv) + collect(DISTINCT lts) + collect(DISTINCT nl)
     + collect(DISTINCT tt) + collect(DISTINCT vb) + collect(DISTINCT dk) AS seed_nodes

UNWIND seed_nodes AS sn
WITH sn WHERE sn IS NOT NULL

MATCH (sn)-[:CAN_CU_TAI]->(luat)
WITH DISTINCT luat AS n_goc
"""


dang_ky_quyen_so_huu_tai_san_chung = CypherTemplate(
    name="dang_ky_quyen_so_huu_tai_san_chung",
    description=(
        "Đăng ký quyền sở hữu, quyền sử dụng đối với tài sản chung của vợ "
        "chồng phải đăng ký (Đ34). Bao gồm: yêu cầu Giấy chứng nhận ghi tên "
        "cả hai vợ chồng, ngoại lệ thỏa thuận chỉ ghi tên một bên, hệ quả khi "
        "GCN chỉ ghi tên một bên (giao dịch theo Đ26, tranh chấp theo Đ33 K3). "
        "Phù hợp khi câu hỏi tập trung vào TÊN TRÊN GCN / SỔ ĐỎ, hoặc 'có cần "
        "cả 2 vợ chồng đứng tên/ký?', KHÔNG phải hỏi về quyền định đoạt/bán "
        "(đó là 'quyen_dinh_doat_tai_san')."
    ),
    params_schema=DangKyQuyenSoHuuParams,
    cypher=assemble_cypher(_SEED_BLOCK),
    trace_cypher=assemble_simple_trace(_SEED_BLOCK),
)
