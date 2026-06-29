"""Template — người có quyền yêu cầu Tòa án hạn chế quyền (Điều 86)."""
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

_ROUTER_FIELDS = ("khia_canh_yeu_cau", "nhom_chu_the_yeu_cau")
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_86"]

_YEU_CAU_TRUC_TIEP = {
    "cha_hoac_me": "cha_hoac_me_co_quyen_yeu_cau_han_che",
    "nguoi_giam_ho": "nguoi_giam_ho_con_chua_thanh_nien_yeu_cau_han_che",
    "nguoi_than_thich": "nguoi_than_thich_yeu_cau_han_che",
    "co_quan_quan_ly_gia_dinh": "co_quan_quan_ly_gia_dinh_yeu_cau_han_che",
    "co_quan_quan_ly_tre_em": "co_quan_quan_ly_tre_em_yeu_cau_han_che",
    "hoi_lien_hiep_phu_nu": "hoi_lien_hiep_phu_nu_yeu_cau_han_che",
}
_ALL_YEU_CAU = list(_YEU_CAU_TRUC_TIEP.values())
_DE_NGHI_IDS = [
    "ca_nhan_co_quan_to_chuc_khac_phat_hien_vi_pham",
    "de_nghi_co_quan_to_chuc_yeu_cau_toa_an",
    "co_quan_quan_ly_gia_dinh_yeu_cau_han_che",
    "co_quan_quan_ly_tre_em_yeu_cau_han_che",
    "hoi_lien_hiep_phu_nu_yeu_cau_han_che",
]


class NguoiCoQuyenYeuCauHanCheQuyenParams(BaseModel):
    nhom_chu_the_yeu_cau: Literal[
        "cha_hoac_me",
        "nguoi_giam_ho",
        "nguoi_than_thich",
        "co_quan_quan_ly_gia_dinh",
        "co_quan_quan_ly_tre_em",
        "hoi_lien_hiep_phu_nu",
        "ca_nhan_co_quan_to_chuc_khac",
        "tat_ca",
        "khong_ro",
    ] = Field(
        description=(
            '"cha/mẹ" -> cha_hoac_me; "người giám hộ" -> nguoi_giam_ho; '
            '"ông bà/người thân" -> nguoi_than_thich; "hàng xóm" -> ca_nhan_co_quan_to_chuc_khac.'
        )
    )
    khia_canh_yeu_cau: Literal[
        "co_quyen_yeu_cau_truc_tiep",
        "co_quyen_de_nghi",
        "danh_sach_chu_the",
        "tong_quat",
    ] = Field(
        description=(
            '"ai được yêu cầu Tòa án" -> danh_sach_chu_the; '
            '"đề nghị/báo cơ quan" -> co_quyen_de_nghi.'
        )
    )


def _resolve_ids(params: NguoiCoQuyenYeuCauHanCheQuyenParams) -> tuple[list[str], list[str]]:
    kc = params.khia_canh_yeu_cau
    nhom = params.nhom_chu_the_yeu_cau

    if kc == "co_quyen_de_nghi" or nhom == "ca_nhan_co_quan_to_chuc_khac":
        leaf = _DE_NGHI_IDS.copy()
        extra = leaf + ["quyen_yeu_cau_toa_an_han_che_quyen", "yeu_cau_toa_an_han_che_quyen_cha_me"]
        return leaf, extra

    if nhom in ("tat_ca", "khong_ro") or kc in ("danh_sach_chu_the", "tong_quat"):
        leaf = _ALL_YEU_CAU.copy()
        extra = leaf + [
            "quyen_yeu_cau_toa_an_han_che_quyen",
            "yeu_cau_toa_an_han_che_quyen_cha_me",
            "toa_an_quyet_dinh_han_che_quyen",
        ]
        return leaf, extra

    chu_id = _YEU_CAU_TRUC_TIEP[nhom]
    leaf = [chu_id]
    extra = leaf + [
        "quyen_yeu_cau_toa_an_han_che_quyen",
        "yeu_cau_toa_an_han_che_quyen_cha_me",
        "toa_an_quyet_dinh_han_che_quyen",
    ]
    return leaf, extra


def _params_builder(params: NguoiCoQuyenYeuCauHanCheQuyenParams) -> dict[str, Any]:
    leaf, extra = _resolve_ids(params)
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "leaf_ids": leaf,
        "extra_seed_ids": extra,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


nguoi_co_quyen_yeu_cau_han_che_quyen = CypherTemplate(
    name="nguoi_co_quyen_yeu_cau_han_che_quyen",
    description=(
        "Trả lời ai có quyền yêu cầu Tòa án hạn chế quyền cha, mẹ theo Điều 86; "
        "phân biệt yêu cầu trực tiếp (khoản 1-2) và quyền đề nghị (khoản 3). "
        "Ví dụ: Ông bà có quyền yêu cầu hạn chế quyền của cha mẹ không?; "
        "Hàng xóm phát hiện cha đánh con thì báo cơ quan nào?"
    ),
    params_schema=NguoiCoQuyenYeuCauHanCheQuyenParams,
    cypher=assemble_graph_seed_cypher(GENERIC_ID_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(GENERIC_ID_SEED_BODY),
    params_builder=_params_builder,
)
