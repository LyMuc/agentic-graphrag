"""Template — không được trực tiếp nuôi con: giao thoa Điều 81 + Điều 85."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.han_che_quyen_cha_me_con_chua_thanh_nien._common import (
    GENERIC_ID_SEED_BODY,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("boi_canh_nuoi_con", "khia_canh_nuoi_con")
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_81", "Luat_HNGD_2014_Dieu_85"]

_HAN_CHE_ANCHOR = [
    "thuoc_truong_hop_han_che_quyen_dieu_85_khoan_1",
    "toa_an_ra_quyet_dinh_han_che_quyen_cha_me",
]
_GIAO_THOA_81 = [
    "giao_thoa_cha_me_khong_thoa_thuan_duoc_nguoi_truc_tiep_nuoi",
    "giao_thoa_bao_dam_quyen_loi_moi_mat_cua_con",
    "giao_thoa_toa_an_quyet_dinh_giao_con_cho_mot_ben_truc_tiep_nuoi",
    "giao_thoa_me_khong_du_dieu_kien_truc_tiep_nuoi_con",
    "giao_thoa_con_duoi_ba_muoi_sau_thang_khong_mac_dinh_giao_cho_me_khi_co_ngoai_le",
    "giao_thoa_con_tu_du_bay_tuoi_trong_viec_giao_nuoi",
    "giao_thoa_xem_xet_nguyen_vong_cua_con_tu_du_bay_tuoi",
    "giao_thoa_thoa_thuan_nguoi_truc_tiep_nuoi_con_sau_ly_hon",
]


class KhongDuocTrucTiepNuoiConVaHanCheQuyenParams(BaseModel):
    doi_tuong_phu_huynh: Literal["cha", "me", "khong_ro"] = Field(
        description='"bố/cha" -> cha; "mẹ" -> me.'
    )
    boi_canh_nuoi_con: Literal[
        "sau_ly_hon", "han_che_quyen", "giao_thoa", "khong_ro"
    ] = Field(
        description=(
            '"sau ly hôn/giành quyền nuôi" -> sau_ly_hon; '
            '"bị hạn chế/tước quyền" -> han_che_quyen; câu rộng -> giao_thoa.'
        )
    )
    do_tuoi_con: Literal["duoi_36_thang", "tu_du_7_tuoi", "khong_ro"] = Field(
        description='"dưới 36 tháng" -> duoi_36_thang; "từ 7 tuổi" -> tu_du_7_tuoi.'
    )
    khia_canh_nuoi_con: Literal[
        "dieu_kien_giao_con",
        "me_khong_du_dieu_kien",
        "cha_me_bi_han_che_quyen",
        "nguyen_vong_cua_con",
        "thoa_thuan",
        "tong_quat",
    ] = Field(
        description=(
            '"mẹ không đủ điều kiện" -> me_khong_du_dieu_kien; '
            '"bị hạn chế quyền" -> cha_me_bi_han_che_quyen; câu rộng -> tong_quat.'
        )
    )


def _resolve_ids(
    params: KhongDuocTrucTiepNuoiConVaHanCheQuyenParams,
) -> tuple[list[str], list[str]]:
    bc = params.boi_canh_nuoi_con
    kc = params.khia_canh_nuoi_con
    dt = params.do_tuoi_con

    if bc == "han_che_quyen" or kc == "cha_me_bi_han_che_quyen":
        leaf = _HAN_CHE_ANCHOR.copy()
        return leaf, leaf + ["khong_duoc_thuc_hien_quyen_trong_pham_vi_quyet_dinh"]

    leaf: list[str] = []
    extra: list[str] = []

    if bc in ("giao_thoa", "khong_ro") or kc == "tong_quat":
        leaf = _GIAO_THOA_81.copy() + _HAN_CHE_ANCHOR.copy()
    elif bc == "sau_ly_hon":
        leaf = [
            "giao_thoa_cha_me_khong_thoa_thuan_duoc_nguoi_truc_tiep_nuoi",
            "giao_thoa_bao_dam_quyen_loi_moi_mat_cua_con",
            "giao_thoa_toa_an_quyet_dinh_giao_con_cho_mot_ben_truc_tiep_nuoi",
        ]

    if kc == "me_khong_du_dieu_kien" or dt == "duoi_36_thang":
        for sid in (
            "giao_thoa_me_khong_du_dieu_kien_truc_tiep_nuoi_con",
            "giao_thoa_con_duoi_ba_muoi_sau_thang_khong_mac_dinh_giao_cho_me_khi_co_ngoai_le",
        ):
            if sid not in leaf:
                leaf.append(sid)

    if kc == "nguyen_vong_cua_con" or dt == "tu_du_7_tuoi":
        for sid in (
            "giao_thoa_con_tu_du_bay_tuoi_trong_viec_giao_nuoi",
            "giao_thoa_xem_xet_nguyen_vong_cua_con_tu_du_bay_tuoi",
        ):
            if sid not in leaf:
                leaf.append(sid)

    if kc == "thoa_thuan":
        leaf.append("giao_thoa_thoa_thuan_nguoi_truc_tiep_nuoi_con_sau_ly_hon")

    if not leaf:
        leaf = _GIAO_THOA_81.copy() + _HAN_CHE_ANCHOR.copy()

    extra = list(dict.fromkeys(leaf + _HAN_CHE_ANCHOR))
    return leaf, extra


def _params_builder(params: KhongDuocTrucTiepNuoiConVaHanCheQuyenParams) -> dict[str, Any]:
    leaf, extra = _resolve_ids(params)
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "leaf_ids": leaf,
        "extra_seed_ids": extra,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


khong_duoc_truc_tiep_nuoi_con_va_han_che_quyen = CypherTemplate(
    name="khong_duoc_truc_tiep_nuoi_con_va_han_che_quyen",
    description=(
        "Trả lời câu rộng 'cha/mẹ không được nuôi con' bằng cách đối chiếu song song "
        "cơ chế giao con sau ly hôn (Điều 81) và hạn chế quyền (Điều 85). "
        "Không suy luận mọi trường hợp không được nuôi đều là bị hạn chế quyền. "
        "Ví dụ: Trường hợp nào mẹ không được nuôi con theo quy định hiện nay?"
    ),
    params_schema=KhongDuocTrucTiepNuoiConVaHanCheQuyenParams,
    cypher=assemble_graph_seed_cypher(GENERIC_ID_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(GENERIC_ID_SEED_BODY),
    params_builder=_params_builder,
)
