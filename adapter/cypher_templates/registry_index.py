"""Index tập trung mọi TemplateRegistry — dùng cho graph_viz và tooling."""
from __future__ import annotations

from adapter.cypher_templates import TemplateRegistry
from adapter.cypher_templates.cap_duong import CAP_DUONG_REGISTRY
from adapter.cypher_templates.cha_me_con_sau_ly_hon import CHA_ME_CON_SAU_LY_HON_REGISTRY
from adapter.cypher_templates.chia_tai_san_sau_ly_hon import CHIA_TAI_SAN_SAU_LY_HON_REGISTRY
from adapter.cypher_templates.chung_song_nhu_vo_chong import CHUNG_SONG_NHU_VO_CHONG_REGISTRY
from adapter.cypher_templates.dang_ky_ket_hon import DANG_KY_KET_HON_REGISTRY
from adapter.cypher_templates.quy_dinh_chung_ly_hon import QUY_DINH_CHUNG_LY_HON_REGISTRY
from adapter.cypher_templates.tai_san import TAI_SAN_REGISTRY

_ALL: tuple[TemplateRegistry, ...] = (
    TAI_SAN_REGISTRY,
    CHIA_TAI_SAN_SAU_LY_HON_REGISTRY,
    DANG_KY_KET_HON_REGISTRY,
    QUY_DINH_CHUNG_LY_HON_REGISTRY,
    CHUNG_SONG_NHU_VO_CHONG_REGISTRY,
    CHA_ME_CON_SAU_LY_HON_REGISTRY,
    CAP_DUONG_REGISTRY,
)

ALL_TEMPLATE_REGISTRIES: dict[str, TemplateRegistry] = {
    reg.topic: reg for reg in _ALL
}

__all__ = ["ALL_TEMPLATE_REGISTRIES"]
