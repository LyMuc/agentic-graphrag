"""Template 2 — TÀI SẢN CỤ THỂ KHI LY HÔN (seed Đ59).

Coverage feat_llm stt: 5,13,21,22,23,24,25,28,30.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.chia_tai_san_sau_ly_hon._common import (
    EXPAND_AND_TIMEFILTER_CYPHER,
)

_BASE_SEMANTIC_IDS = [
    "chia_tai_san_chung_khi_ly_hon",
    "chia_bang_hien_vat",
    "thanh_toan_chenh_lech_gia_tri",
    "xac_dinh_tai_san_rieng_khi_ly_hon",
    "chia_gia_tri_tai_san_rieng_da_sap_nhap",
    "giai_quyet_tai_san_khi_ly_hon",
    "thoa_thuan_giai_quyet_tai_san_ly_hon",
]


class TaiSanCuTheKhiLyHonParams(BaseModel):
    loai_tai_san: Literal[
        "nha_mua_tra_gop",
        "bat_dong_san",
        "quyen_su_dung_dat",
        "tai_khoan_tiet_kiem_tro_cap",
        "tai_san_duoc_tang_cho_ngay_cuoi",
        "dong_san_phai_dang_ky",
        "tai_san_chung",
        "tai_san_rieng",
        "khac",
        "khong_ro",
    ] = Field(
        default="khong_ro",
        description=(
            "Loại tài sản cụ thể. Map: 'nhà trả góp'→nha_mua_tra_gop; "
            "'nhà/nhà đất'→bat_dong_san; 'đất/sổ đỏ'→quyen_su_dung_dat; "
            "'trợ cấp/sổ tiết kiệm'→tai_khoan_tiet_kiem_tro_cap; "
            "'cho ngày cưới'→tai_san_duoc_tang_cho_ngay_cuoi; "
            "'ô tô/xe'→dong_san_phai_dang_ky."
        ),
    )
    nguon_goc: Literal[
        "tra_gop",
        "tang_cho",
        "tang_cho_rieng",
        "trong_hon_nhan",
        "truoc_hon_nhan",
        "dung_ten_mot_ben",
        "ly_than",
        "da_chia_sau_ly_hon",
        "khong_ro",
    ] = Field(
        default="khong_ro",
        description=(
            "Nguồn gốc tài sản. Map: 'trả góp'→tra_gop; 'bố mẹ cho'→tang_cho; "
            "'cho riêng'→tang_cho_rieng; 'đứng tên một bên'→dung_ten_mot_ben; "
            "'ly thân'→ly_than; 'đã trả nửa/đã chia'→da_chia_sau_ly_hon."
        ),
    )
    tinh_chat_du_kien: Literal["chung", "rieng", "chua_ro"] = Field(
        default="chua_ro",
        description="Tính chất dự kiến nếu câu hỏi nói rõ chung/riêng.",
    )
    da_chia_va_thanh_toan: Literal["co", "khong", "khong_ro"] = Field(
        default="khong_ro",
        description="Map 'đã trả nửa/đã thanh toán/đã chia xong'→co.",
    )


_SEED_BLOCK = """
WITH $allowed_semantic_ids AS allowed, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (sn:ChiaTaiSanSauLyHon)
WHERE sn.id IN allowed AND sn.topic = 'chia_tai_san_sau_ly_hon'
  AND (sn:HanhVi OR sn:HauQua OR sn:ThoaThuan)

OPTIONAL MATCH (sn)-[:CAN_CU_TAI]->(luat_semantic)
WHERE luat_semantic IS NOT NULL

OPTIONAL MATCH (luat_whitelist:DieuLuat)
WHERE luat_whitelist.id IN wl

WITH collect(DISTINCT luat_semantic) + collect(DISTINCT luat_whitelist) AS all_seeds
UNWIND all_seeds AS n_goc
WITH DISTINCT n_goc
WHERE n_goc IS NOT NULL
"""


def _params_builder(params: TaiSanCuTheKhiLyHonParams) -> dict[str, Any]:
    ids = list(_BASE_SEMANTIC_IDS)
    if params.nguon_goc == "tang_cho_rieng" or params.tinh_chat_du_kien == "rieng":
        ids.extend(["xac_dinh_tai_san_rieng_khi_ly_hon"])
    if params.da_chia_va_thanh_toan == "co":
        ids.extend(["thanh_toan_chenh_lech_gia_tri", "giai_quyet_tai_san_khi_ly_hon"])
    if params.nguon_goc == "tra_gop" or params.loai_tai_san == "nha_mua_tra_gop":
        ids.extend(["chia_tai_san_chung_khi_ly_hon", "thanh_toan_chenh_lech_gia_tri"])
    return {
        "allowed_semantic_ids": list(dict.fromkeys(ids)),
        "whitelist_dieu_ids": ["Luat_HNGD_2014_Dieu_59"],
        **params.model_dump(),
    }


tai_san_cu_the_khi_ly_hon = CypherTemplate(
    name="tai_san_cu_the_khi_ly_hon",
    description=(
        "Tài sản cụ thể khi ly hôn (seed Đ59): nhà mua trả góp, nhà/đất đứng tên "
        "một bên, trợ cấp/sổ tiết kiệm, quà cưới, ô tô mua khi ly thân hoặc bằng "
        "tiền được cho riêng. Phù hợp khi câu hỏi nêu MỘT tài sản cụ thể (không "
        "phải hỏi chung về QSDĐ hay nguyên tắc). Nếu hỏi riêng về đất/sổ đỏ → "
        "dùng template chia_quyen_su_dung_dat_khi_ly_hon."
    ),
    params_schema=TaiSanCuTheKhiLyHonParams,
    cypher=_SEED_BLOCK.rstrip() + "\n\n" + EXPAND_AND_TIMEFILTER_CYPHER,
    params_builder=_params_builder,
)
