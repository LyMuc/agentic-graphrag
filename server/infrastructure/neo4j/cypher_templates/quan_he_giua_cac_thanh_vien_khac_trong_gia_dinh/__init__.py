"""Registry các Cypher template cho topic quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry

from server.infrastructure.neo4j.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.quyen_nghia_vu_chung_thanh_vien_gia_dinh import (
    quyen_nghia_vu_chung_thanh_vien_gia_dinh,
)
from server.infrastructure.neo4j.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.nghia_vu_thanh_vien_song_chung import (
    nghia_vu_thanh_vien_song_chung,
)
from server.infrastructure.neo4j.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.quyen_nghia_vu_ong_ba_va_chau import (
    quyen_nghia_vu_ong_ba_va_chau,
)
from server.infrastructure.neo4j.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.nuoi_duong_giua_ong_ba_va_chau import (
    nuoi_duong_giua_ong_ba_va_chau,
)
from server.infrastructure.neo4j.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.quyen_nghia_vu_anh_chi_em import (
    quyen_nghia_vu_anh_chi_em,
)
from server.infrastructure.neo4j.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.nuoi_duong_giua_anh_chi_em import (
    nuoi_duong_giua_anh_chi_em,
)
from server.infrastructure.neo4j.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.quyen_nghia_vu_co_di_chu_cau_bac_ruot_va_chau_ruot import (
    quyen_nghia_vu_co_di_chu_cau_bac_ruot_va_chau_ruot,
)
from server.infrastructure.neo4j.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot import (
    nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot,
)


QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY = TemplateRegistry(
    topic="quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh"
)
QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.register(
    quyen_nghia_vu_chung_thanh_vien_gia_dinh
)
QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.register(
    nghia_vu_thanh_vien_song_chung
)
QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.register(
    quyen_nghia_vu_ong_ba_va_chau
)
QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.register(
    nuoi_duong_giua_ong_ba_va_chau
)
QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.register(
    quyen_nghia_vu_anh_chi_em
)
QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.register(
    nuoi_duong_giua_anh_chi_em
)
QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.register(
    quyen_nghia_vu_co_di_chu_cau_bac_ruot_va_chau_ruot
)
QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.register(
    nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot
)


__all__ = [
    "QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY",
    "quyen_nghia_vu_chung_thanh_vien_gia_dinh",
    "nghia_vu_thanh_vien_song_chung",
    "quyen_nghia_vu_ong_ba_va_chau",
    "nuoi_duong_giua_ong_ba_va_chau",
    "quyen_nghia_vu_anh_chi_em",
    "nuoi_duong_giua_anh_chi_em",
    "quyen_nghia_vu_co_di_chu_cau_bac_ruot_va_chau_ruot",
    "nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot",
]
