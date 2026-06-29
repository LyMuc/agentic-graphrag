"""Encode/decode ``LEGAL_CONTEXT_BUNDLE_V1`` shared between retrievers and application.

Tách từ ``utils/legal_context_codec.py`` trong Phase 1 refactor (domain layer).
"""
from __future__ import annotations

import json
from typing import Any, Iterable

from server.domain.legal.render import (
    _collect_dieu_ids_from_context,
    _fetch_provision_effective_dates,
    _fetch_tvpl_links,
)

LEGAL_CONTEXT_SCHEMA_VERSION = 1
LEGAL_CONTEXT_PREFIX = "LEGAL_CONTEXT_BUNDLE_V1:"


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    """Return only dictionary elements from an arbitrary list-like value."""
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _unique_dicts(items: Iterable[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        key = tuple(str(item.get(name) or "") for name in keys)
        if key in seen:
            continue
        seen.add(key)
        output.append(dict(item))
    return output


def _provenance_entry(retriever_name: str, template_name: str) -> dict[str, str]:
    return {
        "retriever": str(retriever_name or ""),
        "template": str(template_name or ""),
    }


def _attach_replacement_provisions(
    provisions: list[dict[str, Any]],
    replacement_ids: list[str],
    replacement_relations: list[dict[str, Any]],
    future_relations: list[dict[str, Any]],
    provenance: dict[str, str],
) -> list[dict[str, Any]]:
    known_ids = {str(p.get("id")) for p in provisions if p.get("id")}
    for relation in future_relations:
        provision = relation.get("provision")
        if isinstance(provision, dict) and provision.get("id") and provision.get("effective_from"):
            known_ids.add(str(provision["id"]))

    needed: set[str] = set()
    for replacement_id in replacement_ids:
        value = str(replacement_id or "")
        if value and value not in known_ids:
            needed.add(value)
    for relation in replacement_relations:
        replacement_id = str(relation.get("id_hien_hanh") or "")
        if replacement_id and replacement_id not in known_ids:
            needed.add(replacement_id)
    if not needed:
        return provisions

    effective_dates = _fetch_provision_effective_dates(needed)
    if not effective_dates:
        return provisions

    attached = list(provisions)
    for replacement_id in sorted(needed):
        effective_from = effective_dates.get(replacement_id)
        if not effective_from:
            continue
        attached.append(
            {
                "id": replacement_id,
                "content": None,
                "role": "replacement",
                "legal_rank": None,
                "effective_from": effective_from,
                "effective_until": None,
                "amendment_id": None,
                "amended_content": None,
                "amendment_effective_from": None,
                "amendment_effective_until": None,
                "source_id": None,
                "provenance": [dict(provenance)],
            }
        )
    return attached


def _provision_from_item(
    item: dict[str, Any],
    *,
    role: str,
    provenance: dict[str, str],
) -> dict[str, Any] | None:
    provision_id = item.get("id_thuc_te_ap_dung") or item.get("id")
    if not provision_id:
        return None
    return {
        "id": str(provision_id),
        "content": item.get("noidung"),
        "role": role,
        "legal_rank": item.get("cap_bac"),
        "effective_from": item.get("ngay_hieu_luc"),
        "effective_until": item.get("ngay_het_hieu_luc"),
        "amendment_id": item.get("id_sua_doi"),
        "amended_content": item.get("noidung_sua_doi"),
        "amendment_effective_from": item.get("ngay_hieu_luc_sua_doi"),
        "amendment_effective_until": item.get("ngay_het_hieu_luc_sua_doi"),
        "source_id": item.get("id_goc_tu_router"),
        "provenance": [dict(provenance)],
    }


def _future_relation_from_item(
    item: dict[str, Any],
    provenance: dict[str, str],
) -> dict[str, Any] | None:
    provision_id = item.get("id")
    if not provision_id:
        return None
    return {
        "source_id": str(provision_id),
        "target_id": item.get("id_duoc_tac_dong"),
        "relation_type": item.get("loai_tac_dong"),
        "provision": {
            "id": str(provision_id),
            "content": item.get("noidung"),
            "legal_rank": item.get("cap_bac"),
            "issued_at": item.get("ngay_ban_hanh"),
            "effective_from": item.get("ngay_hieu_luc"),
            "effective_until": item.get("ngay_het_hieu_luc"),
        },
        "provenance": [dict(provenance)],
    }


def build_legal_context_bundle(
    context_tho: dict[str, Any],
    target_date: str,
    is_user_provided_date: bool,
    *,
    retriever_name: str,
    template_name: str,
    citation_links: dict[str, str] | None = None,
) -> dict[str, Any]:
    provenance = _provenance_entry(retriever_name, template_name)
    provisions: list[dict[str, Any]] = []
    for item in _as_dict_list(context_tho.get("can_cu_chinh")):
        provision = _provision_from_item(item, role="main", provenance=provenance)
        if provision:
            provisions.append(provision)
    for item in _as_dict_list(context_tho.get("can_cu_huong_dan")):
        provision = _provision_from_item(item, role="guidance", provenance=provenance)
        if provision:
            provisions.append(provision)
    for item in _as_dict_list(context_tho.get("can_cu_bo_tro")):
        provision = _provision_from_item(item, role="support", provenance=provenance)
        if provision:
            provisions.append(provision)

    future_relations = [
        relation
        for item in _as_dict_list(context_tho.get("can_cu_sap_hieu_luc"))
        if (relation := _future_relation_from_item(item, provenance)) is not None
    ]
    for pair in _as_dict_list(context_tho.get("lien_ket_sap_hieu_luc")):
        future_relations.append(
            {
                "source_id": pair.get("id_van_ban"),
                "target_id": pair.get("id_duoc_tac_dong"),
                "relation_type": pair.get("loai_tac_dong"),
                "provision": None,
                "provenance": [dict(provenance)],
            }
        )

    if citation_links is None:
        citation_links = _fetch_tvpl_links(_collect_dieu_ids_from_context(context_tho))

    replacement_ids = [
        str(item)
        for item in (context_tho.get("quy_dinh_hien_hanh_doi_chieu") or [])
        if item
    ]
    replacement_relations = _unique_dicts(
        _as_dict_list(context_tho.get("lien_ket_hien_hanh")),
        ("id_hien_hanh", "id_duoc_thay_the"),
    )
    provisions = _attach_replacement_provisions(
        provisions,
        replacement_ids,
        replacement_relations,
        future_relations,
        provenance,
    )

    return {
        "schema_version": LEGAL_CONTEXT_SCHEMA_VERSION,
        "target_date": str(target_date),
        "is_user_provided_date": bool(is_user_provided_date),
        "provenance": [provenance],
        "provisions": provisions,
        "guidance_relations": _as_dict_list(context_tho.get("lien_ket_huong_dan")),
        "future_relations": future_relations,
        "conflicts": _as_dict_list(context_tho.get("can_cu_mau_thuan")),
        "replacement_ids": replacement_ids,
        "replacement_relations": replacement_relations,
        "citation_links": dict(citation_links or {}),
    }


def encode_legal_context_bundle(bundle: dict[str, Any]) -> str:
    if bundle.get("schema_version") != LEGAL_CONTEXT_SCHEMA_VERSION:
        raise ValueError("Unsupported LegalContextBundle schema_version")
    return LEGAL_CONTEXT_PREFIX + json.dumps(
        bundle,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def decode_legal_context_bundle(value: str) -> dict[str, Any] | None:
    if not isinstance(value, str) or not value.startswith(LEGAL_CONTEXT_PREFIX):
        return None
    try:
        bundle = json.loads(value[len(LEGAL_CONTEXT_PREFIX) :])
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(bundle, dict):
        return None
    if bundle.get("schema_version") != LEGAL_CONTEXT_SCHEMA_VERSION:
        return None
    if not bundle.get("target_date") or not isinstance(bundle.get("provisions"), list):
        return None
    return bundle


def encode_context_record(
    record: dict[str, Any],
    target_date: str,
    is_user_provided_date: bool,
    *,
    retriever_name: str,
    template_name: str,
) -> str:
    context_tho = record.get("Context_Tho")
    if not isinstance(context_tho, dict):
        raise ValueError("Template record is missing a dictionary Context_Tho")
    return encode_legal_context_bundle(
        build_legal_context_bundle(
            context_tho,
            target_date,
            is_user_provided_date,
            retriever_name=retriever_name,
            template_name=template_name,
        )
    )
