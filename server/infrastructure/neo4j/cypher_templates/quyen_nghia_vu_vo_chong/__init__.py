"""Registry các Cypher template cho topic quyen_nghia_vu_vo_chong."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry

from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_vo_chong.binh_dang_quyen_nghia_vu_vo_chong import (
    binh_dang_quyen_nghia_vu_vo_chong,
)
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_vo_chong.bao_ve_quyen_nghia_vu_nhan_than import (
    bao_ve_quyen_nghia_vu_nhan_than,
)
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_vo_chong.tinh_nghia_vo_chong import (
    tinh_nghia_vo_chong,
)
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_vo_chong.nghia_vu_song_chung import (
    nghia_vu_song_chung,
)
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_vo_chong.lua_chon_noi_cu_tru import (
    lua_chon_noi_cu_tru,
)
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_vo_chong.ton_trong_danh_du_nhan_pham_uy_tin import (
    ton_trong_danh_du_nhan_pham_uy_tin,
)
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_vo_chong.ton_trong_tu_do_tin_nguong_ton_giao import (
    ton_trong_tu_do_tin_nguong_ton_giao,
)
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_vo_chong.ho_tro_hoc_tap_lam_viec_hoat_dong_xa_hoi import (
    ho_tro_hoc_tap_lam_viec_hoat_dong_xa_hoi,
)


QUYEN_NGHIA_VU_VO_CHONG_REGISTRY = TemplateRegistry(topic="quyen_nghia_vu_vo_chong")
QUYEN_NGHIA_VU_VO_CHONG_REGISTRY.register(binh_dang_quyen_nghia_vu_vo_chong)
QUYEN_NGHIA_VU_VO_CHONG_REGISTRY.register(bao_ve_quyen_nghia_vu_nhan_than)
QUYEN_NGHIA_VU_VO_CHONG_REGISTRY.register(tinh_nghia_vo_chong)
QUYEN_NGHIA_VU_VO_CHONG_REGISTRY.register(nghia_vu_song_chung)
QUYEN_NGHIA_VU_VO_CHONG_REGISTRY.register(lua_chon_noi_cu_tru)
QUYEN_NGHIA_VU_VO_CHONG_REGISTRY.register(ton_trong_danh_du_nhan_pham_uy_tin)
QUYEN_NGHIA_VU_VO_CHONG_REGISTRY.register(ton_trong_tu_do_tin_nguong_ton_giao)
QUYEN_NGHIA_VU_VO_CHONG_REGISTRY.register(ho_tro_hoc_tap_lam_viec_hoat_dong_xa_hoi)


__all__ = [
    "QUYEN_NGHIA_VU_VO_CHONG_REGISTRY",
    "binh_dang_quyen_nghia_vu_vo_chong",
    "bao_ve_quyen_nghia_vu_nhan_than",
    "tinh_nghia_vo_chong",
    "nghia_vu_song_chung",
    "lua_chon_noi_cu_tru",
    "ton_trong_danh_du_nhan_pham_uy_tin",
    "ton_trong_tu_do_tin_nguong_ton_giao",
    "ho_tro_hoc_tap_lam_viec_hoat_dong_xa_hoi",
]
