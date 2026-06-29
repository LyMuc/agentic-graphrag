"""Registry các Cypher template cho topic chia_tai_san_sau_ly_hon (Đ59-64)."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry

from server.infrastructure.neo4j.cypher_templates.chia_tai_san_sau_ly_hon.nguyen_tac_chia_tai_san_ly_hon import (
    nguyen_tac_chia_tai_san_ly_hon,
)
from server.infrastructure.neo4j.cypher_templates.chia_tai_san_sau_ly_hon.tai_san_cu_the_khi_ly_hon import (
    tai_san_cu_the_khi_ly_hon,
)
from server.infrastructure.neo4j.cypher_templates.chia_tai_san_sau_ly_hon.nghia_vu_tai_san_voi_nguoi_thu_ba_khi_ly_hon import (
    nghia_vu_tai_san_voi_nguoi_thu_ba_khi_ly_hon,
)
from server.infrastructure.neo4j.cypher_templates.chia_tai_san_sau_ly_hon.chia_quyen_su_dung_dat_khi_ly_hon import (
    chia_quyen_su_dung_dat_khi_ly_hon,
)
from server.infrastructure.neo4j.cypher_templates.chia_tai_san_sau_ly_hon.truong_hop_nha_o_gia_dinh_va_luu_cu import (
    truong_hop_nha_o_gia_dinh_va_luu_cu,
)
from server.infrastructure.neo4j.cypher_templates.chia_tai_san_sau_ly_hon.tai_san_chung_dua_vao_kinh_doanh_khi_ly_hon import (
    tai_san_chung_dua_vao_kinh_doanh_khi_ly_hon,
)


CHIA_TAI_SAN_SAU_LY_HON_REGISTRY = TemplateRegistry(topic="chia_tai_san_sau_ly_hon")
CHIA_TAI_SAN_SAU_LY_HON_REGISTRY.register(nguyen_tac_chia_tai_san_ly_hon)
CHIA_TAI_SAN_SAU_LY_HON_REGISTRY.register(tai_san_cu_the_khi_ly_hon)
CHIA_TAI_SAN_SAU_LY_HON_REGISTRY.register(nghia_vu_tai_san_voi_nguoi_thu_ba_khi_ly_hon)
CHIA_TAI_SAN_SAU_LY_HON_REGISTRY.register(chia_quyen_su_dung_dat_khi_ly_hon)
CHIA_TAI_SAN_SAU_LY_HON_REGISTRY.register(truong_hop_nha_o_gia_dinh_va_luu_cu)
CHIA_TAI_SAN_SAU_LY_HON_REGISTRY.register(tai_san_chung_dua_vao_kinh_doanh_khi_ly_hon)


__all__ = [
    "CHIA_TAI_SAN_SAU_LY_HON_REGISTRY",
    "nguyen_tac_chia_tai_san_ly_hon",
    "tai_san_cu_the_khi_ly_hon",
    "nghia_vu_tai_san_voi_nguoi_thu_ba_khi_ly_hon",
    "chia_quyen_su_dung_dat_khi_ly_hon",
    "truong_hop_nha_o_gia_dinh_va_luu_cu",
    "tai_san_chung_dua_vao_kinh_doanh_khi_ly_hon",
]
