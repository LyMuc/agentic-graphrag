"""Structured legal-context encoding, deduplication, and rendering.

Template retrievers encode their Neo4j ``Context_Tho`` payloads as
``LegalContextBundle`` JSON strings.  The presentation layer can then merge
bundles from multiple templates, retrievers, or conversation turns before the
existing legal renderer produces text for the response LLM.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from utils.utils import (
    _collect_dieu_ids_from_context,
    _fetch_provision_effective_dates,
    _fetch_tvpl_links,
    chuan_hoa_Context_cho_LLM,
)


LEGAL_CONTEXT_SCHEMA_VERSION = 1
LEGAL_CONTEXT_PREFIX = "LEGAL_CONTEXT_BUNDLE_V1:"
_ROLE_PRIORITY = {"support": 1, "guidance": 2, "main": 3}


@dataclass(frozen=True)
class ContextPipelineResult:
    """Result of decoding, merging, and rendering a list of context strings.

    Attributes:
        rendered_text: Human-readable legal context sent to the response LLM.
        encoded_contexts: Deduplicated encoded bundles, one per temporal scope.
        legacy_contexts: Input strings that were not valid bundle encodings.
        bundles: Merged JSON-safe bundle dictionaries.
    """

    rendered_text: str
    encoded_contexts: list[str]
    legacy_contexts: list[str]
    bundles: list[dict[str, Any]]


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    """Return only dictionary elements from an arbitrary list-like value.

    Args:
        value: Raw value read from ``Context_Tho`` or an encoded bundle.

    Returns:
        A new list containing dictionary elements only. Non-list values and
        malformed elements are ignored to keep normalization fault tolerant.
    """

    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _unique_dicts(items: Iterable[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    """Deduplicate dictionaries by a stable tuple of selected fields.

    Args:
        items: Dictionaries to deduplicate while preserving first-seen order.
        keys: Field names that form the uniqueness key.

    Returns:
        A list containing the first dictionary for each unique field tuple.
    """

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
    """Build provenance metadata for one template execution.

    Args:
        retriever_name: Public retriever/tool name selected by the Router.
        template_name: Cypher template name executed inside that retriever.

    Returns:
        A JSON-safe dictionary identifying the retriever and template source.
    """

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
    """Add lightweight replacement provisions so modal can show effective dates.

    ``lien_ket_hien_hanh`` / ``quy_dinh_hien_hanh_doi_chieu`` reference
    replacements already effective at ``query_date``. Those nodes are absent
    from ``can_cu_chinh`` (``target_date`` scope) and ``can_cu_sap_hieu_luc``.
    """
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
    """Convert a raw legal item into the common provision contract.

    Args:
        item: Raw item from ``can_cu_chinh``, ``can_cu_huong_dan``, or
            ``can_cu_bo_tro``.
        role: Semantic role of the item: ``main``, ``guidance``, or ``support``.
        provenance: Retriever/template metadata attached to the provision.

    Returns:
        A JSON-safe provision dictionary, or ``None`` when the item has no
        usable legal provision identifier.
    """

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
    """Convert a future-effective item into a relation with embedded content.

    Args:
        item: Raw entry from ``can_cu_sap_hieu_luc``.
        provenance: Retriever/template metadata attached to the relation.

    Returns:
        A JSON-safe future relation, or ``None`` when the future provision has
        no identifier.
    """

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
    """Build a ``LegalContextBundle`` from one Neo4j ``Context_Tho`` payload.

    Args:
        context_tho: Structured legal data returned by a template Cypher query.
        target_date: ISO ``YYYY-MM-DD`` date used to select applicable law.
        is_user_provided_date: Whether the user explicitly supplied the date.
        retriever_name: Router tool/retriever that produced the context.
        template_name: Internal template that produced the context.
        citation_links: Optional preloaded mapping from provision IDs to TVPL
            URLs. When omitted, links are loaded from Neo4j in one batch.

    Returns:
        A JSON-safe bundle containing provisions, legal relations, conflicts,
        replacement IDs, citation links, temporal scope, and provenance.
    """

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
    """Serialize a validated bundle into the retriever ``contexts`` contract.

    Args:
        bundle: JSON-safe ``LegalContextBundle`` dictionary.

    Returns:
        A marker-prefixed compact JSON string that can coexist with legacy
        plain-text context strings.

    Raises:
        ValueError: If the bundle schema version is unsupported.
    """

    if bundle.get("schema_version") != LEGAL_CONTEXT_SCHEMA_VERSION:
        raise ValueError("Unsupported LegalContextBundle schema_version")
    return LEGAL_CONTEXT_PREFIX + json.dumps(
        bundle,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def decode_legal_context_bundle(value: str) -> dict[str, Any] | None:
    """Decode one context string when it contains a supported bundle.

    Args:
        value: Context string returned by a retriever or loaded from cache.

    Returns:
        The decoded bundle dictionary, or ``None`` for legacy text, malformed
        JSON, or an unsupported schema version. Malformed data is deliberately
        treated as legacy context so the response path remains available.
    """

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
    """Encode one template query record as a ``LegalContextBundle`` string.

    Args:
        record: Neo4j record dictionary containing a ``Context_Tho`` mapping.
        target_date: ISO date used by the template query.
        is_user_provided_date: Whether that date came from the user.
        retriever_name: Public retriever/tool name.
        template_name: Internal Cypher template name.

    Returns:
        Marker-prefixed JSON string suitable for the template retriever's
        ``contexts`` list.

    Raises:
        ValueError: If ``record`` does not contain a dictionary ``Context_Tho``.
    """

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


def _provision_version_key(provision: dict[str, Any]) -> tuple[str, str, str, str]:
    """Build the required cross-context provision-version deduplication key.

    Args:
        provision: Provision dictionary from a legal context bundle.

    Returns:
        Tuple ``(id, amendment_id, effective_from, effective_until)``. Different
        amendments or effective periods therefore remain separate.
    """

    return (
        str(provision.get("id") or ""),
        str(provision.get("amendment_id") or ""),
        str(provision.get("effective_from") or ""),
        str(provision.get("effective_until") or ""),
    )


def _merge_provenance(
    left: list[dict[str, Any]] | None,
    right: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Merge retriever/template provenance without duplicate source entries.

    Args:
        left: Existing provenance entries.
        right: Additional provenance entries.

    Returns:
        Deduplicated provenance ordered by first appearance.
    """

    return _unique_dicts([*(left or []), *(right or [])], ("retriever", "template"))


def _merge_provision(
    current: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Merge duplicate provision versions and retain the highest-priority role.

    Args:
        current: Provision already selected for a version key.
        candidate: Duplicate provision from another template/retriever.

    Returns:
        A merged provision. ``main`` outranks ``guidance``, which outranks
        ``support``; provenance from both inputs is preserved.
    """

    current_priority = _ROLE_PRIORITY.get(str(current.get("role")), 0)
    candidate_priority = _ROLE_PRIORITY.get(str(candidate.get("role")), 0)
    candidate_wins = candidate_priority > current_priority
    selected = dict(candidate if candidate_wins else current)
    other = current if candidate_wins else candidate
    if not selected.get("content") and other.get("content"):
        selected["content"] = other.get("content")
    if not selected.get("amended_content") and other.get("amended_content"):
        selected["amended_content"] = other.get("amended_content")
    selected["provenance"] = _merge_provenance(
        current.get("provenance"),
        candidate.get("provenance"),
    )
    return selected


def _merge_future_relations(
    relations: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate future relations while preserving embedded provision data.

    Args:
        relations: Future-effect relation dictionaries from one or more
            bundles. Some entries may contain only an edge while another entry
            for the same edge contains the future provision content.

    Returns:
        One relation per ``(source_id, target_id, relation_type)`` key. The
        relation carrying embedded provision content is preferred and all
        provenance entries are retained.
    """

    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for relation in relations:
        key = (
            str(relation.get("source_id") or ""),
            str(relation.get("target_id") or ""),
            str(relation.get("relation_type") or ""),
        )
        if not key[0]:
            continue
        current = by_key.get(key)
        if current is None:
            by_key[key] = dict(relation)
            continue
        selected = dict(
            relation
            if isinstance(relation.get("provision"), dict)
            and not isinstance(current.get("provision"), dict)
            else current
        )
        selected["provenance"] = _merge_provenance(
            current.get("provenance"),
            relation.get("provenance"),
        )
        by_key[key] = selected
    return list(by_key.values())


def merge_legal_context_bundles(
    bundles: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge bundles that share one temporal scope and deduplicate legal data.

    Args:
        bundles: Valid bundles with identical ``target_date`` and
            ``is_user_provided_date`` values.

    Returns:
        One merged bundle with role promotion, deduplicated relations,
        conflicts, replacement IDs, citation links, and combined provenance.

    Raises:
        ValueError: If no bundle is supplied or temporal scopes differ.
    """

    if not bundles:
        raise ValueError("At least one LegalContextBundle is required")
    target_date = bundles[0].get("target_date")
    is_user_provided_date = bool(bundles[0].get("is_user_provided_date"))
    for bundle in bundles:
        if bundle.get("target_date") != target_date:
            raise ValueError("Cannot merge LegalContextBundles with different target_date")
        if bool(bundle.get("is_user_provided_date")) != is_user_provided_date:
            raise ValueError(
                "Cannot merge LegalContextBundles with different date-source scopes"
            )

    provisions_by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    provenance: list[dict[str, Any]] = []
    guidance_relations: list[dict[str, Any]] = []
    future_relations: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    replacement_ids: list[str] = []
    replacement_relations: list[dict[str, Any]] = []
    citation_links: dict[str, str] = {}

    for bundle in bundles:
        provenance = _merge_provenance(provenance, bundle.get("provenance"))
        for provision in _as_dict_list(bundle.get("provisions")):
            key = _provision_version_key(provision)
            if not key[0]:
                continue
            if key in provisions_by_key:
                provisions_by_key[key] = _merge_provision(
                    provisions_by_key[key],
                    provision,
                )
            else:
                provisions_by_key[key] = dict(provision)
        guidance_relations.extend(_as_dict_list(bundle.get("guidance_relations")))
        future_relations.extend(_as_dict_list(bundle.get("future_relations")))
        conflicts.extend(_as_dict_list(bundle.get("conflicts")))
        for replacement_id in bundle.get("replacement_ids") or []:
            value = str(replacement_id or "")
            if value and value not in replacement_ids:
                replacement_ids.append(value)
        replacement_relations.extend(_as_dict_list(bundle.get("replacement_relations")))
        citation_links.update(
            {
                str(key): str(value)
                for key, value in (bundle.get("citation_links") or {}).items()
                if key and value
            }
        )

    return {
        "schema_version": LEGAL_CONTEXT_SCHEMA_VERSION,
        "target_date": str(target_date),
        "is_user_provided_date": is_user_provided_date,
        "provenance": provenance,
        "provisions": list(provisions_by_key.values()),
        "guidance_relations": _unique_dicts(
            guidance_relations,
            ("id_huong_dan", "id_duoc_huong_dan"),
        ),
        "future_relations": _merge_future_relations(future_relations),
        "conflicts": _unique_dicts(conflicts, ("id_nguon", "id_dich")),
        "replacement_ids": replacement_ids,
        "replacement_relations": _unique_dicts(
            replacement_relations,
            ("id_hien_hanh", "id_duoc_thay_the"),
        ),
        "citation_links": citation_links,
    }


def legal_context_bundle_to_context_tho(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    """Reconstruct the renderer-compatible ``Context_Tho`` representation.

    Args:
        bundle: Valid merged ``LegalContextBundle`` dictionary.

    Returns:
        A ``Context_Tho`` dictionary accepted by
        ``chuan_hoa_Context_cho_LLM``. Role promotion is reflected by placing
        each provision in exactly one of the main/guidance/support buckets.
    """

    context_tho: dict[str, Any] = {
        "can_cu_chinh": [],
        "can_cu_huong_dan": [],
        "can_cu_bo_tro": [],
        "lien_ket_huong_dan": _as_dict_list(bundle.get("guidance_relations")),
        "quy_dinh_hien_hanh_doi_chieu": list(bundle.get("replacement_ids") or []),
        "lien_ket_hien_hanh": _as_dict_list(bundle.get("replacement_relations")),
        "can_cu_sap_hieu_luc": [],
        "lien_ket_sap_hieu_luc": [],
        "can_cu_mau_thuan": _as_dict_list(bundle.get("conflicts")),
    }

    for provision in _as_dict_list(bundle.get("provisions")):
        role = str(provision.get("role") or "")
        common = {
            "id": provision.get("id"),
            "noidung": provision.get("content"),
            "cap_bac": provision.get("legal_rank"),
            "ngay_hieu_luc": provision.get("effective_from"),
            "ngay_het_hieu_luc": provision.get("effective_until"),
            "id_sua_doi": provision.get("amendment_id"),
            "noidung_sua_doi": provision.get("amended_content"),
            "ngay_hieu_luc_sua_doi": provision.get("amendment_effective_from"),
            "ngay_het_hieu_luc_sua_doi": provision.get("amendment_effective_until"),
        }
        if role == "main":
            context_tho["can_cu_chinh"].append(
                {
                    **common,
                    "id_goc_tu_router": provision.get("source_id"),
                    "id_thuc_te_ap_dung": provision.get("id"),
                    "het_hieu_luc": bool(provision.get("effective_until")),
                }
            )
        elif role == "guidance":
            context_tho["can_cu_huong_dan"].append(common)
        elif role == "support":
            context_tho["can_cu_bo_tro"].append(common)

    for relation in _as_dict_list(bundle.get("future_relations")):
        provision = relation.get("provision")
        if isinstance(provision, dict) and provision.get("id"):
            context_tho["can_cu_sap_hieu_luc"].append(
                {
                    "id": provision.get("id"),
                    "noidung": provision.get("content"),
                    "cap_bac": provision.get("legal_rank"),
                    "ngay_ban_hanh": provision.get("issued_at"),
                    "ngay_hieu_luc": provision.get("effective_from"),
                    "ngay_het_hieu_luc": provision.get("effective_until"),
                    "loai_tac_dong": relation.get("relation_type"),
                    "id_duoc_tac_dong": relation.get("target_id"),
                }
            )
        if relation.get("source_id") and relation.get("target_id"):
            context_tho["lien_ket_sap_hieu_luc"].append(
                {
                    "id_van_ban": relation.get("source_id"),
                    "id_duoc_tac_dong": relation.get("target_id"),
                    "loai_tac_dong": relation.get("relation_type"),
                }
            )
    return context_tho


def render_legal_context_bundle(bundle: dict[str, Any]) -> str:
    """Render a merged bundle using the system's established legal format.

    Args:
        bundle: Valid merged ``LegalContextBundle`` dictionary.

    Returns:
        Human-readable legal context with warnings, effective dates, main
        authorities, guidance, support, conflicts, future law, and TVPL links.
    """

    record = {"Context_Tho": legal_context_bundle_to_context_tho(bundle)}
    return chuan_hoa_Context_cho_LLM(
        record,
        str(bundle.get("target_date")),
        bool(bundle.get("is_user_provided_date")),
        citation_links=dict(bundle.get("citation_links") or {}),
    ).rstrip()


def process_context_strings(contexts: Iterable[Any]) -> ContextPipelineResult:
    """Decode, group, merge, and render retriever context values.

    Args:
        contexts: Arbitrary context values collected from one or more
            retrievers or cached conversation turns.

    Returns:
        ``ContextPipelineResult`` containing rendered text, merged encoded
        bundles, untouched legacy strings, and merged bundle dictionaries.
        Bundles with different dates are rendered separately and never merged.
    """

    grouped: dict[tuple[str, bool], list[dict[str, Any]]] = {}
    legacy_contexts: list[str] = []
    for raw in contexts:
        text = str(raw)
        bundle = decode_legal_context_bundle(text)
        if bundle is None:
            if text:
                legacy_contexts.append(text)
            continue
        key = (
            str(bundle.get("target_date")),
            bool(bundle.get("is_user_provided_date")),
        )
        grouped.setdefault(key, []).append(bundle)

    bundles = [
        merge_legal_context_bundles(group)
        for group in grouped.values()
    ]
    encoded_contexts = [encode_legal_context_bundle(bundle) for bundle in bundles]
    rendered_parts = [render_legal_context_bundle(bundle) for bundle in bundles]
    rendered_parts.extend(legacy_contexts)
    return ContextPipelineResult(
        rendered_text="\n\n".join(part for part in rendered_parts if part),
        encoded_contexts=encoded_contexts,
        legacy_contexts=legacy_contexts,
        bundles=bundles,
    )
