"""Template 1 — NGUYÊN TẮC CHIA TÀI SẢN KHI LY HÔN (Đ59).

Coverage feat_llm stt: 1,2,3,4,6,7,8,9,29.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.chia_tai_san_sau_ly_hon._common import (
    EXPAND_AND_TIMEFILTER_CYPHER,
    assemble_semantic_viz_all_seeds,
)

_KHIA_CANH_IDS: dict[str, list[str]] = {
    "tong_quat": [
        "giai_quyet_tai_san_khi_ly_hon",
        "thoa_thuan_giai_quyet_tai_san_ly_hon",
        "toa_an_giai_quyet_tai_san_ly_hon",
    ],
    "thoa_thuan": ["thoa_thuan_giai_quyet_tai_san_ly_hon"],
    "chia_doi": ["chia_tai_san_chung_khi_ly_hon"],
    "yeu_to_chia": [
        "hoan_canh_gia_dinh_vo_chong",
        "cong_suc_dong_gop_tao_lap_duy_tri_phat_trien",
        "lao_dong_gia_dinh_duoc_coi_nhu_lao_dong_co_thu_nhap",
        "bao_ve_loi_ich_san_xuat_kinh_doanh_nghe_nghiep",
        "loi_vi_pham_quyen_nghia_vu_vo_chong",
    ],
    "cong_suc_noi_tro": [
        "lao_dong_gia_dinh_duoc_coi_nhu_lao_dong_co_thu_nhap",
        "cong_suc_dong_gop_tao_lap_duy_tri_phat_trien",
    ],
    "loi_vi_pham": ["loi_vi_pham_quyen_nghia_vu_vo_chong"],
    "chia_hien_vat_gia_tri": ["chia_bang_hien_vat", "thanh_toan_chenh_lech_gia_tri"],
    "tai_san_rieng_nhap_chung": [
        "xac_dinh_tai_san_rieng_khi_ly_hon",
        "chia_gia_tri_tai_san_rieng_da_sap_nhap",
    ],
    "bao_ve_vo_con": ["bao_ve_vo_con_yeu_the"],
    "tat_ca": [
        "giai_quyet_tai_san_khi_ly_hon",
        "thoa_thuan_giai_quyet_tai_san_ly_hon",
        "toa_an_giai_quyet_tai_san_ly_hon",
        "chia_tai_san_chung_khi_ly_hon",
        "chia_bang_hien_vat",
        "thanh_toan_chenh_lech_gia_tri",
        "xac_dinh_tai_san_rieng_khi_ly_hon",
        "chia_gia_tri_tai_san_rieng_da_sap_nhap",
        "hoan_canh_gia_dinh_vo_chong",
        "cong_suc_dong_gop_tao_lap_duy_tri_phat_trien",
        "lao_dong_gia_dinh_duoc_coi_nhu_lao_dong_co_thu_nhap",
        "bao_ve_loi_ich_san_xuat_kinh_doanh_nghe_nghiep",
        "loi_vi_pham_quyen_nghia_vu_vo_chong",
        "bao_ve_vo_con_yeu_the",
    ],
}


class NguyenTacChiaTaiSanLyHonParams(BaseModel):
    khia_canh: Literal[
        "tong_quat",
        "thoa_thuan",
        "chia_doi",
        "yeu_to_chia",
        "cong_suc_noi_tro",
        "loi_vi_pham",
        "chia_hien_vat_gia_tri",
        "tai_san_rieng_nhap_chung",
        "bao_ve_vo_con",
        "tat_ca",
    ] = Field(
        description=(
            "Khía cạnh nguyên tắc chia tài sản khi ly hôn (Đ59). Map: "
            "'nguyên tắc'→tong_quat; 'thỏa thuận'→thoa_thuan; "
            "'chia đều/chia đôi/50/50'→chia_doi; 'yếu tố nào'→yeu_to_chia; "
            "'nội trợ/chăm con'→cong_suc_noi_tro; 'lỗi/ngoại tình/gian dối'→loi_vi_pham; "
            "'hiện vật/chênh lệch'→chia_hien_vat_gia_tri; "
            "'sáp nhập/trộn lẫn'→tai_san_rieng_nhap_chung; "
            "'vợ con/con chưa thành niên'→bao_ve_vo_con; không rõ→tat_ca."
        )
    )


_SEED_BLOCK = """
WITH $allowed_semantic_ids AS allowed, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (sn:ChiaTaiSanSauLyHon)
WHERE sn.id IN allowed AND sn.topic = 'chia_tai_san_sau_ly_hon'
  AND (sn:HanhVi OR sn:DieuKien OR sn:HauQua OR sn:ThoaThuan)

OPTIONAL MATCH (sn)-[:CAN_CU_TAI]->(luat_semantic)
WHERE luat_semantic IS NOT NULL

OPTIONAL MATCH (luat_whitelist)
WHERE (luat_whitelist:DieuLuat OR luat_whitelist:DieuKhoanLuat
       OR luat_whitelist:DieuKhoanDiemLuat)
  AND luat_whitelist.id IN wl

WITH collect(DISTINCT luat_semantic) + collect(DISTINCT luat_whitelist) AS all_seeds
UNWIND all_seeds AS n_goc
WITH DISTINCT n_goc
WHERE n_goc IS NOT NULL
"""


def _params_builder(params: NguyenTacChiaTaiSanLyHonParams) -> dict[str, Any]:
    return {
        "khia_canh": params.khia_canh,
        "allowed_semantic_ids": _KHIA_CANH_IDS.get(params.khia_canh, _KHIA_CANH_IDS["tat_ca"]),
        "whitelist_dieu_ids": ["Luat_HNGD_2014_Dieu_59"],
    }


nguyen_tac_chia_tai_san_ly_hon = CypherTemplate(
    name="nguyen_tac_chia_tai_san_ly_hon",
    description=(
        "Nguyên tắc giải quyết tài sản của vợ chồng khi ly hôn (Đ59): thỏa thuận "
        "hoặc Tòa án giải quyết; chia tài sản chung có tính yếu tố (hoàn cảnh, "
        "công sức, lao động nội trợ, lỗi vi phạm); chia bằng hiện vật/thanh toán "
        "chênh lệch; tài sản riêng đã sáp nhập; bảo vệ vợ/con yếu thế. "
        "Phù hợp khi hỏi 'chia đôi có đúng không', 'yếu tố nào', 'nội trợ', "
        "'lỗi', 'nguyên tắc chia tài sản khi ly hôn'."
    ),
    params_schema=NguyenTacChiaTaiSanLyHonParams,
    cypher=_SEED_BLOCK.rstrip() + "\n\n" + EXPAND_AND_TIMEFILTER_CYPHER,
    viz_cypher=assemble_semantic_viz_all_seeds(_SEED_BLOCK),
    params_builder=_params_builder,
)
