"""Build structured legal-warning payloads for chat message metadata."""
from __future__ import annotations

import re
from typing import Any

from utils.utils import (
    _LOAI_TAC_DONG_LABEL,
    _LOAI_TAC_DONG_VAN_BAN_MOI,
    _format_date_vn,
    _to_dieu_id,
)

_EMPTY = "—"

_LAW_LABELS: dict[str, str] = {
    "Luat_HNGD_2014": "Luật HNGD 2014",
    "Luat_HoTich_2014": "Luật Hộ tịch 2014",
    "Luat_HoTich_2026": "Luật Hộ tịch 2026",
    "BoLuat_DanSu_2015": "Bộ luật Dân sự 2015",
    "NghiDinh_126_2014_ND_CP": "Nghị định 126/2014/NĐ-CP",
    "NghiDinh_123_2015_ND_CP": "Nghị định 123/2015/NĐ-CP",
}

_TOKEN_VI: dict[str, str] = {
    "HoTich": "Hộ tịch",
    "HNGD": "HNGD",
    "DanSu": "Dân sự",
    "NghiDinh": "Nghị định",
    "NghiQuyet": "Nghị quyết",
    "ThongTu": "Thông tư",
    "BoLuat": "Bộ luật",
    "Luat": "Luật",
}

_PROVISION_ID_RE = re.compile(
    r"^(?P<prefix>.+?)_Dieu_(?P<dieu>\d+[a-zA-Z]?)"
    r"(?:_Khoan_(?P<khoan>\d+))?"
    r"(?:_Diem_(?P<diem>[a-zA-Z]))?"
    r"$"
)


def _is_strict_ancestor(ancestor_id: str, node_id: str) -> bool:
    return bool(
        ancestor_id
        and node_id
        and node_id != ancestor_id
        and node_id.startswith(ancestor_id + "_")
    )


def dedupe_rows_by_ancestor(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    ids = {str(r[field]) for r in rows if r.get(field)}
    return [
        r
        for r in rows
        if not any(_is_strict_ancestor(a, str(r.get(field) or "")) for a in ids)
    ]


def _humanize_token(token: str) -> str:
    if token in _TOKEN_VI:
        return _TOKEN_VI[token]
    return token.replace("_", " ")


def _law_label_from_prefix(prefix: str) -> str:
    if prefix in _LAW_LABELS:
        return _LAW_LABELS[prefix]
    nd_match = re.fullmatch(r"NghiDinh_(\d+)_(\d{4})_ND_CP", prefix)
    if nd_match:
        return f"Nghị định {nd_match.group(1)}/{nd_match.group(2)}/NĐ-CP"
    nq_match = re.fullmatch(r"NghiQuyet_(\d+)_(\d{4})_NQ_HDTP", prefix)
    if nq_match:
        return f"Nghị quyết {nq_match.group(1)}/{nq_match.group(2)}/NQ-HĐTP"
    parts = prefix.split("_")
    if parts and parts[0] == "Luat" and len(parts) >= 3:
        name_parts = [_humanize_token(parts[0])] + [_humanize_token(p) for p in parts[1:]]
        return " ".join(name_parts)
    return " ".join(_humanize_token(part) for part in parts)


def format_provision_label(provision_id: str | None) -> str:
    if not provision_id:
        return _EMPTY
    match = _PROVISION_ID_RE.match(str(provision_id).strip())
    if not match:
        return str(provision_id).replace("_", " ")
    law = _law_label_from_prefix(match.group("prefix"))
    dieu = match.group("dieu")
    khoan = match.group("khoan")
    diem = match.group("diem")
    if diem and khoan:
        return f"Điểm {diem} Khoản {khoan} Điều {dieu} {law}"
    if khoan:
        return f"Khoản {khoan} Điều {dieu} {law}"
    return f"Điều {dieu} {law}"


def _fmt_date(value: Any) -> str:
    formatted = _format_date_vn(value)
    return formatted or _EMPTY


def _impact_type_label(relation_type: str | None) -> str:
    raw = _LOAI_TAC_DONG_LABEL.get(str(relation_type or ""), str(relation_type or ""))
    if not raw:
        return _EMPTY
    return raw[0].upper() + raw[1:] if raw else _EMPTY


def _provision_map(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for provision in bundle.get("provisions") or []:
        if not isinstance(provision, dict):
            continue
        pid = provision.get("id")
        if pid:
            mapping[str(pid)] = provision
    return mapping


def _provision_lookup(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map provision id → metadata from main provisions and future relations.

    Replacement provisions at ``query_date`` often appear only in
    ``future_relations`` (``can_cu_sap_hieu_luc``), not in ``provisions``
    filtered by ``target_date``.
    """
    mapping = _provision_map(bundle)
    for relation in bundle.get("future_relations") or []:
        if not isinstance(relation, dict):
            continue
        provision = relation.get("provision")
        if not isinstance(provision, dict):
            continue
        pid = provision.get("id")
        if not pid:
            continue
        pid_str = str(pid)
        existing = mapping.get(pid_str)
        if existing is None:
            mapping[pid_str] = provision
            continue
        for key in ("effective_from", "effective_until", "issued_at", "content"):
            if not existing.get(key) and provision.get(key):
                existing[key] = provision[key]
    return mapping


def _citation_url(citation_links: dict[str, str], provision_id: str | None) -> str | None:
    if not provision_id:
        return None
    dieu_id = _to_dieu_id(str(provision_id))
    if dieu_id and dieu_id in citation_links:
        return citation_links[dieu_id]
    return None


def _merge_expired_row(existing: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in candidate.items():
        if value and value != _EMPTY and (not merged.get(key) or merged.get(key) == _EMPTY):
            merged[key] = value
    return merged


def _build_expired_rows(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    provisions_by_id = _provision_lookup(bundle)
    citation_links = dict(bundle.get("citation_links") or {})
    by_basis: dict[str, dict[str, Any]] = {}

    for provision in bundle.get("provisions") or []:
        if not isinstance(provision, dict):
            continue
        if not provision.get("effective_until"):
            continue
        basis_id = str(provision.get("id") or "")
        if not basis_id:
            continue
        row = {
            "basis_id": basis_id,
            "basis_name": format_provision_label(basis_id),
            "expiry_date": _fmt_date(provision.get("effective_until")),
            "replacement_id": None,
            "replacement_name": None,
            "replacement_effective_date": _EMPTY,
            "replacement_content_url": None,
        }
        if basis_id in by_basis:
            by_basis[basis_id] = _merge_expired_row(by_basis[basis_id], row)
        else:
            by_basis[basis_id] = row

    for relation in bundle.get("replacement_relations") or []:
        if not isinstance(relation, dict):
            continue
        basis_id = str(relation.get("id_duoc_thay_the") or "")
        replacement_id = str(relation.get("id_hien_hanh") or "")
        if not basis_id:
            continue
        basis_prov = provisions_by_id.get(basis_id, {})
        replacement_prov = provisions_by_id.get(replacement_id, {})
        row = {
            "basis_id": basis_id,
            "basis_name": format_provision_label(basis_id),
            "expiry_date": _fmt_date(basis_prov.get("effective_until")),
            "replacement_id": replacement_id or None,
            "replacement_name": format_provision_label(replacement_id) if replacement_id else _EMPTY,
            "replacement_effective_date": _fmt_date(replacement_prov.get("effective_from")),
            "replacement_content_url": _citation_url(citation_links, replacement_id),
        }
        if basis_id in by_basis:
            by_basis[basis_id] = _merge_expired_row(by_basis[basis_id], row)
        else:
            by_basis[basis_id] = row

    rows = list(by_basis.values())
    for row in rows:
        if not row.get("replacement_name") or row.get("replacement_name") == _EMPTY:
            row["replacement_name"] = _EMPTY
            row["replacement_effective_date"] = _EMPTY
    return dedupe_rows_by_ancestor(rows, "basis_id")


def _build_future_rows(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    citation_links = dict(bundle.get("citation_links") or {})
    rows: list[dict[str, Any]] = []

    for relation in bundle.get("future_relations") or []:
        if not isinstance(relation, dict):
            continue
        relation_type = str(relation.get("relation_type") or "")
        if relation_type not in _LOAI_TAC_DONG_VAN_BAN_MOI:
            continue
        provision = relation.get("provision")
        if not isinstance(provision, dict) or not provision.get("id"):
            continue
        source_id = str(provision.get("id") or relation.get("source_id") or "")
        impacted_id = str(relation.get("target_id") or "")
        if not source_id:
            continue
        rows.append(
            {
                "source_id": source_id,
                "basis_name": format_provision_label(source_id),
                "issued_date": _fmt_date(provision.get("issued_at")),
                "effective_date": _fmt_date(provision.get("effective_from")),
                "impact_type": _impact_type_label(relation_type),
                "impacted_basis_id": impacted_id,
                "impacted_basis_name": format_provision_label(impacted_id),
                "content_url": _citation_url(citation_links, source_id),
            }
        )

    rows = dedupe_rows_by_ancestor(rows, "impacted_basis_id")
    rows = dedupe_rows_by_ancestor(rows, "source_id")
    return rows


def build_validity_warning_payload(bundle: dict[str, Any]) -> dict[str, Any] | None:
    expired_rows = _build_expired_rows(bundle)
    future_rows = _build_future_rows(bundle)
    if not expired_rows and not future_rows:
        return None
    payload: dict[str, Any] = {}
    if expired_rows:
        payload["expired_rows"] = expired_rows
    if future_rows:
        payload["future_rows"] = future_rows
    return payload or None


def build_conflict_warning_payload(bundle: dict[str, Any]) -> dict[str, Any] | None:
    provisions_by_id = _provision_map(bundle)
    items: list[dict[str, Any]] = []

    for conflict in bundle.get("conflicts") or []:
        if not isinstance(conflict, dict):
            continue
        id_nguon = str(conflict.get("id_nguon") or "")
        id_dich = str(conflict.get("id_dich") or "")
        if not id_nguon or not id_dich:
            continue
        nguon_content = provisions_by_id.get(id_nguon, {}).get("content") or ""
        items.append(
            {
                "provisions": [
                    {"id": id_nguon, "name": format_provision_label(id_nguon)},
                    {"id": id_dich, "name": format_provision_label(id_dich)},
                ],
                "summary": str(conflict.get("noidung_giai_thich") or _EMPTY),
                "details": [
                    {
                        "id": id_nguon,
                        "name": format_provision_label(id_nguon),
                        "content": str(nguon_content or _EMPTY),
                    },
                    {
                        "id": id_dich,
                        "name": format_provision_label(id_dich),
                        "content": str(conflict.get("noidung_dich") or _EMPTY),
                    },
                ],
            }
        )

    if not items:
        return None
    return {"items": items}


def _merge_expired_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_basis: dict[str, dict[str, Any]] = {}
    for row in rows:
        basis_id = str(row.get("basis_id") or "")
        if not basis_id:
            continue
        if basis_id in by_basis:
            by_basis[basis_id] = _merge_expired_row(by_basis[basis_id], row)
        else:
            by_basis[basis_id] = dict(row)
    merged = list(by_basis.values())
    return dedupe_rows_by_ancestor(merged, "basis_id")


def _merge_future_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, Any]] = []
    for row in rows:
        key = (
            str(row.get("source_id") or ""),
            str(row.get("impacted_basis_id") or ""),
            str(row.get("impact_type") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    unique = dedupe_rows_by_ancestor(unique, "impacted_basis_id")
    unique = dedupe_rows_by_ancestor(unique, "source_id")
    return unique


def build_legal_warning_metadata(bundles: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not bundles:
        return None

    all_expired: list[dict[str, Any]] = []
    all_future: list[dict[str, Any]] = []
    all_conflict_items: list[dict[str, Any]] = []

    for bundle in bundles:
        validity = build_validity_warning_payload(bundle)
        if validity:
            all_expired.extend(validity.get("expired_rows") or [])
            all_future.extend(validity.get("future_rows") or [])
        conflict = build_conflict_warning_payload(bundle)
        if conflict:
            all_conflict_items.extend(conflict.get("items") or [])

    metadata: dict[str, Any] = {}
    expired_rows = _merge_expired_rows(all_expired)
    future_rows = _merge_future_rows(all_future)
    if expired_rows or future_rows:
        validity_payload: dict[str, Any] = {}
        if expired_rows:
            validity_payload["expired_rows"] = expired_rows
        if future_rows:
            validity_payload["future_rows"] = future_rows
        metadata["validity"] = validity_payload

    if all_conflict_items:
        seen: set[tuple[str, str]] = set()
        unique_items: list[dict[str, Any]] = []
        for item in all_conflict_items:
            provs = item.get("provisions") or []
            if len(provs) >= 2:
                key = (str(provs[0].get("id") or ""), str(provs[1].get("id") or ""))
            else:
                key = (str(item.get("summary") or ""), "")
            if key in seen:
                continue
            seen.add(key)
            unique_items.append(item)
        metadata["conflict"] = {"items": unique_items}

    return metadata or None
