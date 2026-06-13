"""Template — hậu quả pháp lý sau khi bị hạn chế quyền (Điều 87)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.han_che_quyen_cha_me_con_chua_thanh_nien._common import (
    GENERIC_ID_SEED_BODY,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_hau_qua", "tinh_trang_cha_me")
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_87"]

_QUYEN_MAP = {
    "trong_nom": "quyen_trong_nom_con",
    "cham_soc": "quyen_cham_soc_con",
    "giao_duc": "quyen_giao_duc_con",
    "quan_ly_tai_san_rieng": "quyen_quan_ly_tai_san_rieng_cua_con",
    "dai_dien_theo_phap_luat": "quyen_dai_dien_theo_phap_luat_cho_con",
    "nuoi_duong": "nghia_vu_nuoi_duong_con_cua_ben_con_lai",
    "cap_duong": "nghia_vu_cap_duong_van_tiep_tuc",
}


class HauQuaPhapLySauKhiBiHanCheQuyenParams(BaseModel):
    tinh_trang_cha_me: Literal[
        "mot_ben_bi_han_che",
        "ca_hai_bi_han_che",
        "ben_con_lai_khong_du_dieu_kien",
        "khong_xac_dinh_ben_con_lai",
        "khong_ro",
    ] = Field(
        description=(
            '"chỉ một bên bị hạn chế" -> mot_ben_bi_han_che; '
            '"cả cha mẹ bị hạn chế" -> ca_hai_bi_han_che.'
        )
    )
    khia_canh_hau_qua: Literal[
        "ben_con_lai_thuc_hien_quyen",
        "giao_nguoi_giam_ho",
        "nghia_vu_cap_duong",
        "tong_quat",
    ] = Field(
        description=(
            '"ai chăm/đại diện cho con" -> ben_con_lai_thuc_hien_quyen; '
            '"giao cho giám hộ" -> giao_nguoi_giam_ho; "còn cấp dưỡng" -> nghia_vu_cap_duong.'
        )
    )
    quyen_nghia_vu_duoc_hoi: Literal[
        "trong_nom",
        "nuoi_duong",
        "cham_soc",
        "giao_duc",
        "quan_ly_tai_san_rieng",
        "dai_dien_theo_phap_luat",
        "cap_duong",
        "tat_ca",
        "khong_ro",
    ] = Field(description='"chu cấp/cấp dưỡng" -> cap_duong; "ai lo cho con" -> tat_ca.')


def _resolve_ids(
    params: HauQuaPhapLySauKhiBiHanCheQuyenParams,
) -> tuple[list[str], list[str]]:
    tt = params.tinh_trang_cha_me
    kc = params.khia_canh_hau_qua
    qn = params.quyen_nghia_vu_duoc_hoi

    if kc == "nghia_vu_cap_duong" or qn == "cap_duong":
        return ["nghia_vu_cap_duong_van_tiep_tuc"], [
            "nghia_vu_cap_duong_van_tiep_tuc",
            "cha_me_bi_xem_xet_han_che_quyen",
        ]

    if kc == "giao_nguoi_giam_ho" or tt in (
        "ca_hai_bi_han_che",
        "ben_con_lai_khong_du_dieu_kien",
        "khong_xac_dinh_ben_con_lai",
    ):
        dieu_kien = {
            "ca_hai_bi_han_che": "cha_va_me_deu_bi_han_che_quyen",
            "ben_con_lai_khong_du_dieu_kien": "ben_khong_bi_han_che_nhung_khong_du_dieu_kien",
            "khong_xac_dinh_ben_con_lai": "chua_xac_dinh_duoc_ben_cha_me_con_lai",
        }.get(tt, "cha_va_me_deu_bi_han_che_quyen")
        leaf = [
            dieu_kien,
            "giao_viec_cham_soc_quan_ly_tai_san_cho_nguoi_giam_ho",
            "nguoi_giam_ho_tiep_nhan_viec_cham_soc_con",
        ]
        extra = leaf + [
            "quyen_trong_nom_con",
            "quyen_cham_soc_con",
            "quyen_giao_duc_con",
            "quyen_quan_ly_tai_san_rieng_cua_con",
        ]
        return leaf, extra

    leaf = [
        "mot_ben_cha_me_bi_han_che_quyen",
        "ben_cha_me_con_lai_khong_bi_han_che",
        "ben_con_lai_thuc_hien_quyen_nghia_vu_doi_voi_con",
    ]
    extra = leaf.copy()
    if qn == "tat_ca" or kc == "tong_quat":
        extra += list(_QUYEN_MAP.values())
    elif qn in _QUYEN_MAP:
        extra.append(_QUYEN_MAP[qn])
    return leaf, list(dict.fromkeys(extra))


def _params_builder(params: HauQuaPhapLySauKhiBiHanCheQuyenParams) -> dict[str, Any]:
    leaf, extra = _resolve_ids(params)
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "leaf_ids": leaf,
        "extra_seed_ids": extra,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


hau_qua_phap_ly_sau_khi_bi_han_che_quyen = CypherTemplate(
    name="hau_qua_phap_ly_sau_khi_bi_han_che_quyen",
    description=(
        "Trả lời ai tiếp tục thực hiện quyền đối với con, khi nào giao cho người giám hộ "
        "và nghĩa vụ cấp dưỡng sau khi bị hạn chế quyền theo Điều 87. "
        "Ví dụ: Bố bị hạn chế quyền thì ai chăm sóc con?; "
        "Cả cha mẹ bị hạn chế thì giao con cho ai, còn phải cấp dưỡng không?"
    ),
    params_schema=HauQuaPhapLySauKhiBiHanCheQuyenParams,
    cypher=assemble_graph_seed_cypher(GENERIC_ID_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(GENERIC_ID_SEED_BODY),
    params_builder=_params_builder,
)
