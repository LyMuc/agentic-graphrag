"""Registry các Cypher template cho topic dieu_kien_ket_hon."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry

from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon.hon_nhan_cung_gioi_tinh import (
    hon_nhan_cung_gioi_tinh,
)
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon.do_tuoi_ket_hon import do_tuoi_ket_hon
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon.cac_truong_hop_cam_ket_hon import (
    cac_truong_hop_cam_ket_hon,
)
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon.quan_he_huyet_thong_va_ba_doi import (
    quan_he_huyet_thong_va_ba_doi,
)
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon.quan_he_nuoi_duong_va_thong_gia_bi_cam import (
    quan_he_nuoi_duong_va_thong_gia_bi_cam,
)
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon.quan_he_thong_gia_khong_huyet_thong import (
    quan_he_thong_gia_khong_huyet_thong,
)
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon.xac_lap_quan_he_vo_chong_hop_phap import (
    xac_lap_quan_he_vo_chong_hop_phap,
)
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon.anh_huong_tinh_trang_ca_nhan import (
    anh_huong_tinh_trang_ca_nhan,
)
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon.yeu_to_xa_hoi_khong_phai_tro_ngai import (
    yeu_to_xa_hoi_khong_phai_tro_ngai,
)
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon.dieu_kien_ket_hon_tong_quat import (
    dieu_kien_ket_hon_tong_quat,
)


DIEU_KIEN_KET_HON_REGISTRY = TemplateRegistry(topic="dieu_kien_ket_hon")
DIEU_KIEN_KET_HON_REGISTRY.register(hon_nhan_cung_gioi_tinh)
DIEU_KIEN_KET_HON_REGISTRY.register(do_tuoi_ket_hon)
DIEU_KIEN_KET_HON_REGISTRY.register(cac_truong_hop_cam_ket_hon)
DIEU_KIEN_KET_HON_REGISTRY.register(quan_he_huyet_thong_va_ba_doi)
DIEU_KIEN_KET_HON_REGISTRY.register(quan_he_nuoi_duong_va_thong_gia_bi_cam)
DIEU_KIEN_KET_HON_REGISTRY.register(quan_he_thong_gia_khong_huyet_thong)
DIEU_KIEN_KET_HON_REGISTRY.register(xac_lap_quan_he_vo_chong_hop_phap)
DIEU_KIEN_KET_HON_REGISTRY.register(anh_huong_tinh_trang_ca_nhan)
DIEU_KIEN_KET_HON_REGISTRY.register(yeu_to_xa_hoi_khong_phai_tro_ngai)
DIEU_KIEN_KET_HON_REGISTRY.register(dieu_kien_ket_hon_tong_quat)


__all__ = [
    "DIEU_KIEN_KET_HON_REGISTRY",
    "hon_nhan_cung_gioi_tinh",
    "do_tuoi_ket_hon",
    "cac_truong_hop_cam_ket_hon",
    "quan_he_huyet_thong_va_ba_doi",
    "quan_he_nuoi_duong_va_thong_gia_bi_cam",
    "quan_he_thong_gia_khong_huyet_thong",
    "xac_lap_quan_he_vo_chong_hop_phap",
    "anh_huong_tinh_trang_ca_nhan",
    "yeu_to_xa_hoi_khong_phai_tro_ngai",
    "dieu_kien_ket_hon_tong_quat",
]
