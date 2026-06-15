"""Registry các Cypher template cho topic dai_dien_trach_nhiem_vo_chong."""
from __future__ import annotations

from adapter.cypher_templates import TemplateRegistry

from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong.can_cu_xac_lap_dai_dien import (
    can_cu_xac_lap_dai_dien,
)
from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong.uy_quyen_giao_dich_can_dong_y import (
    uy_quyen_giao_dich_can_dong_y,
)
from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong.dai_dien_khi_nang_luc_hanh_vi_bi_anh_huong import (
    dai_dien_khi_nang_luc_hanh_vi_bi_anh_huong,
)
from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong.dai_dien_trong_quan_he_kinh_doanh import (
    dai_dien_trong_quan_he_kinh_doanh,
)
from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong.dua_tai_san_chung_vao_kinh_doanh import (
    dua_tai_san_chung_vao_kinh_doanh,
)
from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong.dai_dien_tai_san_chung_gcn_mot_ben import (
    dai_dien_tai_san_chung_gcn_mot_ben,
)
from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong.hieu_luc_giao_dich_trai_dai_dien import (
    hieu_luc_giao_dich_trai_dai_dien,
)
from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong.trach_nhiem_lien_doi_vo_chong import (
    trach_nhiem_lien_doi_vo_chong,
)

DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY = TemplateRegistry(
    topic="dai_dien_trach_nhiem_vo_chong"
)
DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY.register(can_cu_xac_lap_dai_dien)
DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY.register(uy_quyen_giao_dich_can_dong_y)
DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY.register(dai_dien_khi_nang_luc_hanh_vi_bi_anh_huong)
DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY.register(dai_dien_trong_quan_he_kinh_doanh)
DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY.register(dua_tai_san_chung_vao_kinh_doanh)
DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY.register(dai_dien_tai_san_chung_gcn_mot_ben)
DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY.register(hieu_luc_giao_dich_trai_dai_dien)
DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY.register(trach_nhiem_lien_doi_vo_chong)

__all__ = [
    "DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY",
    "can_cu_xac_lap_dai_dien",
    "uy_quyen_giao_dich_can_dong_y",
    "dai_dien_khi_nang_luc_hanh_vi_bi_anh_huong",
    "dai_dien_trong_quan_he_kinh_doanh",
    "dua_tai_san_chung_vao_kinh_doanh",
    "dai_dien_tai_san_chung_gcn_mot_ben",
    "hieu_luc_giao_dich_trai_dai_dien",
    "trach_nhiem_lien_doi_vo_chong",
]
