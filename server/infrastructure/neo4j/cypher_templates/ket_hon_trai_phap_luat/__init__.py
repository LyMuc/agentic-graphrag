"""Registry các Cypher template cho topic ket_hon_trai_phap_luat."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry

from server.infrastructure.neo4j.cypher_templates.ket_hon_trai_phap_luat.khai_niem_va_can_cu_ket_hon_trai_phap_luat import (
    khai_niem_va_can_cu_ket_hon_trai_phap_luat,
)
from server.infrastructure.neo4j.cypher_templates.ket_hon_trai_phap_luat.quyen_yeu_cau_huy_ket_hon_trai_phap_luat import (
    quyen_yeu_cau_huy_ket_hon_trai_phap_luat,
)
from server.infrastructure.neo4j.cypher_templates.ket_hon_trai_phap_luat.thu_ly_tham_quyen_va_ho_so_huy_ket_hon import (
    thu_ly_tham_quyen_va_ho_so_huy_ket_hon,
)
from server.infrastructure.neo4j.cypher_templates.ket_hon_trai_phap_luat.xu_ly_yeu_cau_huy_va_cong_nhan_hon_nhan import (
    xu_ly_yeu_cau_huy_va_cong_nhan_hon_nhan,
)
from server.infrastructure.neo4j.cypher_templates.ket_hon_trai_phap_luat.hau_qua_phap_ly_huy_ket_hon_trai_phap_luat import (
    hau_qua_phap_ly_huy_ket_hon_trai_phap_luat,
)


KET_HON_TRAI_PHAP_LUAT_REGISTRY = TemplateRegistry(topic="ket_hon_trai_phap_luat")
KET_HON_TRAI_PHAP_LUAT_REGISTRY.register(khai_niem_va_can_cu_ket_hon_trai_phap_luat)
KET_HON_TRAI_PHAP_LUAT_REGISTRY.register(quyen_yeu_cau_huy_ket_hon_trai_phap_luat)
KET_HON_TRAI_PHAP_LUAT_REGISTRY.register(thu_ly_tham_quyen_va_ho_so_huy_ket_hon)
KET_HON_TRAI_PHAP_LUAT_REGISTRY.register(xu_ly_yeu_cau_huy_va_cong_nhan_hon_nhan)
KET_HON_TRAI_PHAP_LUAT_REGISTRY.register(hau_qua_phap_ly_huy_ket_hon_trai_phap_luat)


__all__ = [
    "KET_HON_TRAI_PHAP_LUAT_REGISTRY",
    "khai_niem_va_can_cu_ket_hon_trai_phap_luat",
    "quyen_yeu_cau_huy_ket_hon_trai_phap_luat",
    "thu_ly_tham_quyen_va_ho_so_huy_ket_hon",
    "xu_ly_yeu_cau_huy_va_cong_nhan_hon_nhan",
    "hau_qua_phap_ly_huy_ket_hon_trai_phap_luat",
]
