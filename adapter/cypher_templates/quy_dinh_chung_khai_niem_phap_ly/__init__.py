"""Registry các Cypher template cho topic quy_dinh_chung_khai_niem_phap_ly."""
from __future__ import annotations

from adapter.cypher_templates import TemplateRegistry

from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly.nguyen_tac_che_do_hon_nhan_gia_dinh import (
    nguyen_tac_che_do_hon_nhan_gia_dinh,
)
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly.trach_nhiem_nha_nuoc_xa_hoi import (
    trach_nhiem_nha_nuoc_xa_hoi,
)
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly.bao_ve_che_do_va_hanh_vi_bi_cam import (
    bao_ve_che_do_va_hanh_vi_bi_cam,
)
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly.pham_vi_ba_doi_va_quan_he_than_thich import (
    pham_vi_ba_doi_va_quan_he_than_thich,
)
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly.quy_dinh_chung_va_khai_niem_phap_ly import (
    quy_dinh_chung_va_khai_niem_phap_ly,
)


QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY = TemplateRegistry(
    topic="quy_dinh_chung_khai_niem_phap_ly"
)
QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY.register(nguyen_tac_che_do_hon_nhan_gia_dinh)
QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY.register(trach_nhiem_nha_nuoc_xa_hoi)
QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY.register(bao_ve_che_do_va_hanh_vi_bi_cam)
QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY.register(pham_vi_ba_doi_va_quan_he_than_thich)
QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY.register(quy_dinh_chung_va_khai_niem_phap_ly)


__all__ = [
    "QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY",
    "nguyen_tac_che_do_hon_nhan_gia_dinh",
    "trach_nhiem_nha_nuoc_xa_hoi",
    "bao_ve_che_do_va_hanh_vi_bi_cam",
    "pham_vi_ba_doi_va_quan_he_than_thich",
    "quy_dinh_chung_va_khai_niem_phap_ly",
]
