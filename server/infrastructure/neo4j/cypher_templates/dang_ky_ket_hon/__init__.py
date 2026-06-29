"""Registry các Cypher template cho topic dang_ky_ket_hon."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry

from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon.noi_va_tham_quyen_dang_ky_ket_hon import (
    noi_va_tham_quyen_dang_ky_ket_hon,
)
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon.dieu_kien_va_gia_tri_dang_ky_ket_hon import (
    dieu_kien_va_gia_tri_dang_ky_ket_hon,
)
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon.ket_hon_lai_sau_ly_hon import (
    ket_hon_lai_sau_ly_hon,
)
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon.thu_tuc_dang_ky_ket_hon import (
    thu_tuc_dang_ky_ket_hon,
)
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon.thoi_han_xac_minh_dang_ky_ket_hon import (
    thoi_han_xac_minh_dang_ky_ket_hon,
)
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon.tu_choi_dang_ky_ket_hon import (
    tu_choi_dang_ky_ket_hon,
)
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon.noi_dung_giay_chung_nhan_ket_hon import (
    noi_dung_giay_chung_nhan_ket_hon,
)
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon.cap_va_trao_giay_chung_nhan_ket_hon import (
    cap_va_trao_giay_chung_nhan_ket_hon,
)
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon.dang_ky_lai_ket_hon import (
    dang_ky_lai_ket_hon,
)


DANG_KY_KET_HON_REGISTRY = TemplateRegistry(topic="dang_ky_ket_hon")
DANG_KY_KET_HON_REGISTRY.register(noi_va_tham_quyen_dang_ky_ket_hon)
DANG_KY_KET_HON_REGISTRY.register(dieu_kien_va_gia_tri_dang_ky_ket_hon)
DANG_KY_KET_HON_REGISTRY.register(ket_hon_lai_sau_ly_hon)
DANG_KY_KET_HON_REGISTRY.register(thu_tuc_dang_ky_ket_hon)
DANG_KY_KET_HON_REGISTRY.register(thoi_han_xac_minh_dang_ky_ket_hon)
DANG_KY_KET_HON_REGISTRY.register(tu_choi_dang_ky_ket_hon)
DANG_KY_KET_HON_REGISTRY.register(noi_dung_giay_chung_nhan_ket_hon)
DANG_KY_KET_HON_REGISTRY.register(cap_va_trao_giay_chung_nhan_ket_hon)
DANG_KY_KET_HON_REGISTRY.register(dang_ky_lai_ket_hon)


__all__ = [
    "DANG_KY_KET_HON_REGISTRY",
    "noi_va_tham_quyen_dang_ky_ket_hon",
    "dieu_kien_va_gia_tri_dang_ky_ket_hon",
    "ket_hon_lai_sau_ly_hon",
    "thu_tuc_dang_ky_ket_hon",
    "thoi_han_xac_minh_dang_ky_ket_hon",
    "tu_choi_dang_ky_ket_hon",
    "noi_dung_giay_chung_nhan_ket_hon",
    "cap_va_trao_giay_chung_nhan_ket_hon",
    "dang_ky_lai_ket_hon",
]
