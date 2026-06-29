"""Template — trường hợp, phạm vi và thời hạn hạn chế quyền (Điều 85)."""
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

_ROUTER_FIELDS = ("khia_canh_han_che", "nhom_can_cu_hanh_vi")
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_85"]

_ANCHOR = "thuoc_truong_hop_han_che_quyen_dieu_85_khoan_1"
_LEAF_BY_NHOM = {
    "bi_ket_an_xam_pham_con": ["bi_ket_an_toi_xam_pham_con_voi_loi_co_y"],
    "vi_pham_nghiem_trong_nghia_vu_voi_con": ["vi_pham_nghiem_trong_nghia_vu_voi_con"],
    "pha_tan_tai_san_cua_con": ["pha_tan_tai_san_cua_con"],
    "loi_song_doi_truy": ["co_loi_song_doi_truy"],
    "xui_giuc_ep_buoc_con": ["xui_giuc_ep_buoc_con_lam_viec_trai_phap_luat_dao_duc"],
    "bi_ket_an_khong_ro_toi_danh": ["bi_ket_an_toi_xam_pham_con_voi_loi_co_y"],
    "tat_ca": [
        "bi_ket_an_toi_xam_pham_con_voi_loi_co_y",
        "vi_pham_nghiem_trong_nghia_vu_voi_con",
        "pha_tan_tai_san_cua_con",
        "co_loi_song_doi_truy",
        "xui_giuc_ep_buoc_con_lam_viec_trai_phap_luat_dao_duc",
    ],
    "khong_ro": [
        "bi_ket_an_toi_xam_pham_con_voi_loi_co_y",
        "vi_pham_nghiem_trong_nghia_vu_voi_con",
        "pha_tan_tai_san_cua_con",
        "co_loi_song_doi_truy",
        "xui_giuc_ep_buoc_con_lam_viec_trai_phap_luat_dao_duc",
    ],
}
_QUYEN_BY_FIELD = {
    "trong_nom": "quyen_trong_nom_con",
    "cham_soc": "quyen_cham_soc_con",
    "giao_duc": "quyen_giao_duc_con",
    "quan_ly_tai_san_rieng": "quyen_quan_ly_tai_san_rieng_cua_con",
    "dai_dien_theo_phap_luat": "quyen_dai_dien_theo_phap_luat_cho_con",
    "tham_nom_cach_noi_doi_thuong": "quyen_trong_nom_con",
    "tat_ca": [
        "quyen_trong_nom_con",
        "quyen_cham_soc_con",
        "quyen_giao_duc_con",
        "quyen_quan_ly_tai_san_rieng_cua_con",
        "quyen_dai_dien_theo_phap_luat_cho_con",
    ],
}


class TruongHopPhamViThoiHanHanCheQuyenParams(BaseModel):
    doi_tuong_bi_han_che: Literal["cha", "me", "cha_hoac_me", "khong_ro"] = Field(
        description='"bố/cha" -> cha; "mẹ" -> me; "cha mẹ" -> cha_hoac_me.'
    )
    khia_canh_han_che: Literal[
        "truong_hop",
        "doi_chieu_tinh_huong",
        "pham_vi_quyen",
        "thoi_han",
        "rut_ngan_thoi_han",
        "tong_quat",
    ] = Field(
        description=(
            '"trường hợp nào" -> truong_hop; "có bị hạn chế không" -> doi_chieu_tinh_huong; '
            '"bị hạn chế quyền gì" -> pham_vi_quyen; "bao lâu" -> thoi_han.'
        )
    )
    nhom_can_cu_hanh_vi: Literal[
        "bi_ket_an_xam_pham_con",
        "vi_pham_nghiem_trong_nghia_vu_voi_con",
        "pha_tan_tai_san_cua_con",
        "loi_song_doi_truy",
        "xui_giuc_ep_buoc_con",
        "bi_ket_an_khong_ro_toi_danh",
        "tat_ca",
        "khong_ro",
    ] = Field(
        description=(
            '"đi tù" không rõ tội -> bi_ket_an_khong_ro_toi_danh; '
            '"phá tài sản con" -> pha_tan_tai_san_cua_con; liệt kê chung -> tat_ca.'
        )
    )
    quyen_bi_hoi: Literal[
        "trong_nom",
        "cham_soc",
        "giao_duc",
        "quan_ly_tai_san_rieng",
        "dai_dien_theo_phap_luat",
        "tham_nom_cach_noi_doi_thuong",
        "tat_ca",
        "khong_ro",
    ] = Field(
        description=(
            '"trông nom" -> trong_nom; "thăm nom" (hạn chế quyền cha mẹ) -> '
            "tham_nom_cach_noi_doi_thuong — seed quyen_trong_nom_con."
        )
    )


def _resolve_leaf_ids(params: TruongHopPhamViThoiHanHanCheQuyenParams) -> list[str]:
    kc = params.khia_canh_han_che
    if kc == "pham_vi_quyen":
        qb = params.quyen_bi_hoi
        ids = _QUYEN_BY_FIELD.get(qb, _QUYEN_BY_FIELD["tat_ca"])
        return ids if isinstance(ids, list) else [ids]
    if kc == "thoi_han":
        return ["thoi_han_han_che_tu_mot_den_nam_nam"]
    if kc == "rut_ngan_thoi_han":
        return ["toa_an_co_the_rut_ngan_thoi_han_han_che"]
    nhom = params.nhom_can_cu_hanh_vi
    leaves = list(_LEAF_BY_NHOM.get(nhom, _LEAF_BY_NHOM["tat_ca"]))
    if kc in ("truong_hop", "tong_quat") or nhom in ("tat_ca", "khong_ro"):
        if _ANCHOR not in leaves:
            leaves.insert(0, _ANCHOR)
    return leaves


def _resolve_extra_ids(params: TruongHopPhamViThoiHanHanCheQuyenParams) -> list[str]:
    kc = params.khia_canh_han_che
    extra: list[str] = []
    if kc in ("pham_vi_quyen", "thoi_han", "rut_ngan_thoi_han", "tong_quat"):
        extra.append("toa_an_ra_quyet_dinh_han_che_quyen_cha_me")
    if kc == "pham_vi_quyen":
        qb = params.quyen_bi_hoi
        qids = _QUYEN_BY_FIELD.get(qb, _QUYEN_BY_FIELD["tat_ca"])
        if isinstance(qids, list):
            extra.extend(qids)
        else:
            extra.append(qids)
    if kc in ("thoi_han", "rut_ngan_thoi_han"):
        extra.append("thoi_han_han_che_tu_mot_den_nam_nam")
    if kc == "rut_ngan_thoi_han":
        extra.append("toa_an_co_the_rut_ngan_thoi_han_han_che")
    if kc in ("truong_hop", "doi_chieu_tinh_huong", "tong_quat"):
        extra.append(_ANCHOR)
        extra.append("khong_duoc_thuc_hien_quyen_trong_pham_vi_quyet_dinh")
    return list(dict.fromkeys(extra))


def _params_builder(params: TruongHopPhamViThoiHanHanCheQuyenParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "leaf_ids": _resolve_leaf_ids(params),
        "extra_seed_ids": _resolve_extra_ids(params),
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


truong_hop_pham_vi_thoi_han_han_che_quyen = CypherTemplate(
    name="truong_hop_pham_vi_thoi_han_han_che_quyen",
    description=(
        "Trả lời trường hợp cha, mẹ bị hạn chế quyền, đối chiếu hành vi cụ thể, "
        "phạm vi quyền bị hạn chế và thời hạn theo Điều 85. "
        "'Đi tù' chỉ là dữ kiện đối chiếu điểm a, không tự đủ căn cứ. "
        "Ví dụ: Cha, mẹ bị hạn chế quyền trong các trường hợp nào?; "
        "Bố đi tù thì có bị hạn chế quyền đối với con?"
    ),
    params_schema=TruongHopPhamViThoiHanHanCheQuyenParams,
    cypher=assemble_graph_seed_cypher(GENERIC_ID_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(GENERIC_ID_SEED_BODY),
    params_builder=_params_builder,
)
