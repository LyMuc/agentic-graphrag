"""Template 4 — CHIA QUYỀN SỬ DỤNG ĐẤT KHI LY HÔN (Đ62).

Coverage feat_llm stt: 14,15,16,17.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.chia_tai_san_sau_ly_hon._common import (
    EXPAND_AND_TIMEFILTER_CYPHER,
    assemble_semantic_viz_all_seeds,
)

_ALL_D62_IDS = [
    "chia_quyen_su_dung_dat_khi_ly_hon",
    "qsd_dat_la_tai_san_rieng",
    "qsd_dat_la_tai_san_chung",
    "dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san",
    "qsd_dat_chung_voi_ho_gia_dinh",
    "dat_cay_lau_nam_dat_lam_nghiep_dat_o",
    "loai_dat_khac",
    "giai_quyet_quyen_loi_ben_khong_co_qsd_dat",
]


class ChiaQuyenSuDungDatParams(BaseModel):
    tinh_chat_qsd_dat: Literal["chung", "rieng", "khong_ro"] = Field(
        default="khong_ro",
        description="Map 'tài sản chung'→chung; 'tài sản riêng'→rieng.",
    )
    loai_dat: Literal[
        "dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san",
        "dat_cay_lau_nam_dat_lam_nghiep_dat_o",
        "loai_dat_khac",
        "khong_ro",
    ] = Field(default="khong_ro")
    ho_gia_dinh: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    nhu_cau_su_dung: Literal["ca_hai", "mot_ben", "khong_ro"] = Field(default="khong_ro")
    hanh_vi_context: Literal[
        "mua_dat_giau_vo", "dung_ten_mot_ben", "tong_quat", "khong_ro"
    ] = Field(default="khong_ro")


_SEED_BLOCK = """
WITH $allowed_semantic_ids AS allowed, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (sn:ChiaTaiSanSauLyHon)
WHERE sn.id IN allowed AND sn.topic = 'chia_tai_san_sau_ly_hon'
  AND (sn:HanhVi OR sn:LoaiTaiSan OR sn:HauQua)

OPTIONAL MATCH (sn)-[:CAN_CU_TAI]->(luat_semantic)
WHERE luat_semantic IS NOT NULL

OPTIONAL MATCH (luat_whitelist:DieuLuat)
WHERE luat_whitelist.id IN wl

WITH collect(DISTINCT luat_semantic) + collect(DISTINCT luat_whitelist) AS all_seeds
UNWIND all_seeds AS n_goc
WITH DISTINCT n_goc
WHERE n_goc IS NOT NULL
"""


def _params_builder(params: ChiaQuyenSuDungDatParams) -> dict[str, Any]:
    ids: list[str] = ["chia_quyen_su_dung_dat_khi_ly_hon"]

    if params.tinh_chat_qsd_dat == "khong_ro":
        ids = list(_ALL_D62_IDS)
    elif params.tinh_chat_qsd_dat == "rieng":
        ids.append("qsd_dat_la_tai_san_rieng")
    elif params.tinh_chat_qsd_dat == "chung":
        ids.extend([
            "qsd_dat_la_tai_san_chung",
            "dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san",
            "dat_cay_lau_nam_dat_lam_nghiep_dat_o",
            "loai_dat_khac",
        ])

    if params.loai_dat == "dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san":
        ids.append("dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san")
    elif params.loai_dat == "dat_cay_lau_nam_dat_lam_nghiep_dat_o":
        ids.append("dat_cay_lau_nam_dat_lam_nghiep_dat_o")
    elif params.loai_dat == "loai_dat_khac":
        ids.append("loai_dat_khac")

    if params.ho_gia_dinh == "co":
        ids.append("qsd_dat_chung_voi_ho_gia_dinh")

    if params.nhu_cau_su_dung == "mot_ben":
        ids.append("giai_quyet_quyen_loi_ben_khong_co_qsd_dat")

    return {
        "allowed_semantic_ids": list(dict.fromkeys(ids)),
        "whitelist_dieu_ids": ["Luat_HNGD_2014_Dieu_62"],
        **params.model_dump(),
    }


chia_quyen_su_dung_dat_khi_ly_hon = CypherTemplate(
    name="chia_quyen_su_dung_dat_khi_ly_hon",
    description=(
        "Chia quyền sử dụng đất khi ly hôn (Đ62): QSDĐ là tài sản riêng/chung, "
        "đất nông nghiệp, đất ở, đất chung hộ gia đình, quyền lợi bên không có "
        "QSDĐ, 'mua đất giấu vợ'. Phù hợp khi câu hỏi có 'quyền sử dụng đất', "
        "'đất', 'sổ đỏ', 'mua đất' và hỏi chia khi ly hôn."
    ),
    params_schema=ChiaQuyenSuDungDatParams,
    cypher=_SEED_BLOCK.rstrip() + "\n\n" + EXPAND_AND_TIMEFILTER_CYPHER,
    viz_cypher=assemble_semantic_viz_all_seeds(_SEED_BLOCK),
    params_builder=_params_builder,
)
