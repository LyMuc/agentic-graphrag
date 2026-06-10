"""Registry các Cypher template cho topic chung_song_nhu_vo_chong (Đ5, Đ14-16)."""
from __future__ import annotations

from adapter.cypher_templates import TemplateRegistry

from adapter.cypher_templates.chung_song_nhu_vo_chong.xac_dinh_tinh_hop_phap_chung_song import (
    xac_dinh_tinh_hop_phap_chung_song,
)
from adapter.cypher_templates.chung_song_nhu_vo_chong.hau_qua_phap_ly_chung_song import (
    hau_qua_phap_ly_chung_song,
)
from adapter.cypher_templates.chung_song_nhu_vo_chong.dang_ky_ket_hon_sau_chung_song import (
    dang_ky_ket_hon_sau_chung_song,
)
from adapter.cypher_templates.chung_song_nhu_vo_chong.quyen_nghia_vu_cha_me_con import (
    quyen_nghia_vu_cha_me_con,
)
from adapter.cypher_templates.chung_song_nhu_vo_chong.giai_quyet_tai_san_khi_chung_song import (
    giai_quyet_tai_san_khi_chung_song,
)
from adapter.cypher_templates.chung_song_nhu_vo_chong.giai_quyet_nghia_vu_va_hop_dong import (
    giai_quyet_nghia_vu_va_hop_dong,
)


CHUNG_SONG_NHU_VO_CHONG_REGISTRY = TemplateRegistry(topic="chung_song_nhu_vo_chong")
CHUNG_SONG_NHU_VO_CHONG_REGISTRY.register(xac_dinh_tinh_hop_phap_chung_song)
CHUNG_SONG_NHU_VO_CHONG_REGISTRY.register(hau_qua_phap_ly_chung_song)
CHUNG_SONG_NHU_VO_CHONG_REGISTRY.register(dang_ky_ket_hon_sau_chung_song)
CHUNG_SONG_NHU_VO_CHONG_REGISTRY.register(quyen_nghia_vu_cha_me_con)
CHUNG_SONG_NHU_VO_CHONG_REGISTRY.register(giai_quyet_tai_san_khi_chung_song)
CHUNG_SONG_NHU_VO_CHONG_REGISTRY.register(giai_quyet_nghia_vu_va_hop_dong)


__all__ = [
    "CHUNG_SONG_NHU_VO_CHONG_REGISTRY",
    "xac_dinh_tinh_hop_phap_chung_song",
    "hau_qua_phap_ly_chung_song",
    "dang_ky_ket_hon_sau_chung_song",
    "quyen_nghia_vu_cha_me_con",
    "giai_quyet_tai_san_khi_chung_song",
    "giai_quyet_nghia_vu_va_hop_dong",
]
