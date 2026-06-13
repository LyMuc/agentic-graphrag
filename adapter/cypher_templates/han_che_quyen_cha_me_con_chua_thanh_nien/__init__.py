"""Registry các Cypher template cho topic han_che_quyen_cha_me_con_chua_thanh_nien."""
from __future__ import annotations

from adapter.cypher_templates import TemplateRegistry

from adapter.cypher_templates.han_che_quyen_cha_me_con_chua_thanh_nien.truong_hop_pham_vi_thoi_han_han_che_quyen import (
    truong_hop_pham_vi_thoi_han_han_che_quyen,
)
from adapter.cypher_templates.han_che_quyen_cha_me_con_chua_thanh_nien.nguoi_co_quyen_yeu_cau_han_che_quyen import (
    nguoi_co_quyen_yeu_cau_han_che_quyen,
)
from adapter.cypher_templates.han_che_quyen_cha_me_con_chua_thanh_nien.hau_qua_phap_ly_sau_khi_bi_han_che_quyen import (
    hau_qua_phap_ly_sau_khi_bi_han_che_quyen,
)
from adapter.cypher_templates.han_che_quyen_cha_me_con_chua_thanh_nien.khong_duoc_truc_tiep_nuoi_con_va_han_che_quyen import (
    khong_duoc_truc_tiep_nuoi_con_va_han_che_quyen,
)


HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY = TemplateRegistry(
    topic="han_che_quyen_cha_me_con_chua_thanh_nien"
)
HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY.register(
    truong_hop_pham_vi_thoi_han_han_che_quyen
)
HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY.register(
    nguoi_co_quyen_yeu_cau_han_che_quyen
)
HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY.register(
    hau_qua_phap_ly_sau_khi_bi_han_che_quyen
)
HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY.register(
    khong_duoc_truc_tiep_nuoi_con_va_han_che_quyen
)

__all__ = [
    "HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY",
    "truong_hop_pham_vi_thoi_han_han_che_quyen",
    "nguoi_co_quyen_yeu_cau_han_che_quyen",
    "hau_qua_phap_ly_sau_khi_bi_han_che_quyen",
    "khong_duoc_truc_tiep_nuoi_con_va_han_che_quyen",
]
