"""Load router tool schemas from retriever ``*_description`` constants.

Maps each spec name to the description dict authored in
``server/agents/retrievers``.
"""

from __future__ import annotations

import copy
import importlib
from dataclasses import replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from application.retriever_catalog import RetrieverSpec

# spec name -> (module path, description attribute name)
ADAPTER_DESCRIPTION_SOURCES: dict[str, tuple[str, str]] = {
    "quy_dinh_chung_khai_niem_phap_ly": (
        "server.agents.retrievers.quy_dinh_chung_khai_niem_phap_ly",
        "quy_dinh_chung_khai_niem_phap_ly_description",
    ),
    "dieu_kien_ket_hon": (
        "server.agents.retrievers.ket_hon.dieu_kien_ket_hon",
        "dieu_kien_ket_hon_description",
    ),
    "dang_ky_ket_hon": (
        "server.agents.retrievers.ket_hon.dang_ky_ket_hon",
        "dang_ky_ket_hon_description",
    ),
    "ket_hon_trai_phap_luat": (
        "server.agents.retrievers.ket_hon.ket_hon_trai_phap_luat",
        "ket_hon_trai_phap_luat_description",
    ),
    "chung_song_nhu_vo_chong": (
        "server.agents.retrievers.ket_hon.chung_song_nhu_vo_chong",
        "chung_song_nhu_vo_chong_description",
    ),
    "hon_nhan_cham_dut_do_vo_chong_chet": (
        "server.agents.retrievers.hon_nhan_cham_dut_do_vo_chong_chet",
        "hon_nhan_cham_dut_do_vo_chong_chet_description",
    ),
    "quy_dinh_chung_ly_hon": (
        "server.agents.retrievers.ly_hon.quy_dinh_chung_ly_hon",
        "quy_dinh_chung_ly_hon_description",
    ),
    "chia_tai_san_sau_ly_hon": (
        "server.agents.retrievers.ly_hon.chia_tai_san_sau_ly_hon",
        "chia_tai_san_sau_ly_hon_description",
    ),
    "cha_me_con_sau_ly_hon": (
        "server.agents.retrievers.ly_hon.cha_me_con_sau_ly_hon",
        "cha_me_con_sau_ly_hon_description",
    ),
    "cap_duong": (
        "server.agents.retrievers.cap_duong",
        "cap_duong_description",
    ),
    "che_do_tai_san_cua_vo_chong": (
        "server.agents.retrievers.quan_he_giua_vo_va_chong.che_do_tai_san_cua_vo_chong",
        "che_do_tai_san_cua_vo_chong_description",
    ),
    "dai_dien_trach_nhiem_vo_chong": (
        "server.agents.retrievers.quan_he_giua_vo_va_chong.dai_dien_trach_nhiem_vo_chong",
        "dai_dien_trach_nhiem_vo_chong_description",
    ),
    "quyen_nghia_vu_vo_chong": (
        "server.agents.retrievers.quan_he_giua_vo_va_chong.quyen_nghia_vu_vo_chong",
        "quyen_nghia_vu_vo_chong_description",
    ),
    "quyen_nghia_vu_cha_me_con": (
        "server.agents.retrievers.quyen_nghia_vu_cha_me_con",
        "quyen_nghia_vu_cha_me_con_description",
    ),
    "han_che_quyen_cha_me_con_chua_thanh_nien": (
        "server.agents.retrievers.han_che_quyen_cha_me_con_chua_thanh_nien",
        "han_che_quyen_cha_me_con_chua_thanh_nien_description",
    ),
    "xac_dinh_cha_me_con": (
        "server.agents.retrievers.xac_dinh_cha_me_con",
        "xac_dinh_cha_me_con_description",
    ),
    "tai_san_rieng_cua_con": (
        "server.agents.retrievers.tai_san_rieng_cua_con",
        "tai_san_rieng_cua_con_description",
    ),
    "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh": (
        "server.agents.retrievers.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh",
        "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh_description",
    ),
    "quan_he_hon_nhan_co_yeu_to_nuoc_ngoai": (
        "server.agents.retrievers.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai",
        "quan_he_hon_nhan_co_yeu_to_nuoc_ngoai_description",
    ),
    "xu_phat_vi_pham": (
        "server.agents.retrievers.vi_pham.xu_phat_vi_pham",
        "xu_phat_vi_pham_description",
    ),
}


def _load_adapter_description_schema(spec_name: str) -> dict[str, Any] | None:
    source = ADAPTER_DESCRIPTION_SOURCES.get(spec_name)
    if not source:
        return None
    module_path, attr_name = source
    module = importlib.import_module(module_path)
    schema = getattr(module, attr_name, None)
    if not isinstance(schema, dict):
        return None
    if schema.get("type") != "function" or not isinstance(schema.get("function"), dict):
        return None
    return copy.deepcopy(schema)


def enrich_specs_with_adapter_descriptions(
    specs: dict[str, "RetrieverSpec"],
) -> dict[str, "RetrieverSpec"]:
    """Attach adapter-authored router schemas to each RetrieverSpec."""

    enriched: dict[str, RetrieverSpec] = {}
    for name, spec in specs.items():
        schema = _load_adapter_description_schema(name)
        if schema is None:
            enriched[name] = spec
            continue
        enriched[name] = replace(spec, router_description_schema=schema)
    return enriched
