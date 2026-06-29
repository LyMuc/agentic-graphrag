"""Registry các Cypher template cho topic cap_duong (Đ107-120, Đ82 K2)."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry

from server.infrastructure.neo4j.cypher_templates.cap_duong.nghia_vu_cap_duong_theo_quan_he import (
    nghia_vu_cap_duong_theo_quan_he,
)
from server.infrastructure.neo4j.cypher_templates.cap_duong.cap_duong_cho_con_sau_ly_hon import (
    cap_duong_cho_con_sau_ly_hon,
)
from server.infrastructure.neo4j.cypher_templates.cap_duong.muc_va_phan_bo_cap_duong import (
    muc_va_phan_bo_cap_duong,
)
from server.infrastructure.neo4j.cypher_templates.cap_duong.phuong_thuc_va_tam_ngung_cap_duong import (
    phuong_thuc_va_tam_ngung_cap_duong,
)
from server.infrastructure.neo4j.cypher_templates.cap_duong.cham_dut_nghia_vu_cap_duong import (
    cham_dut_nghia_vu_cap_duong,
)
from server.infrastructure.neo4j.cypher_templates.cap_duong.quyen_yeu_cau_va_cuong_che_cap_duong import (
    quyen_yeu_cau_va_cuong_che_cap_duong,
)


CAP_DUONG_REGISTRY = TemplateRegistry(topic="cap_duong")
CAP_DUONG_REGISTRY.register(nghia_vu_cap_duong_theo_quan_he)
CAP_DUONG_REGISTRY.register(cap_duong_cho_con_sau_ly_hon)
CAP_DUONG_REGISTRY.register(muc_va_phan_bo_cap_duong)
CAP_DUONG_REGISTRY.register(phuong_thuc_va_tam_ngung_cap_duong)
CAP_DUONG_REGISTRY.register(cham_dut_nghia_vu_cap_duong)
CAP_DUONG_REGISTRY.register(quyen_yeu_cau_va_cuong_che_cap_duong)


__all__ = [
    "CAP_DUONG_REGISTRY",
    "nghia_vu_cap_duong_theo_quan_he",
    "cap_duong_cho_con_sau_ly_hon",
    "muc_va_phan_bo_cap_duong",
    "phuong_thuc_va_tam_ngung_cap_duong",
    "cham_dut_nghia_vu_cap_duong",
    "quyen_yeu_cau_va_cuong_che_cap_duong",
]
