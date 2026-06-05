"""Xây graph payload từ Context_Tho + viz_cypher cho trang visualize."""
from __future__ import annotations

import json
from typing import Any

from adapter.config import driver
from adapter.cypher_templates import CypherTemplate, TemplateRegistry
from adapter.cypher_templates.chia_tai_san_sau_ly_hon import CHIA_TAI_SAN_SAU_LY_HON_REGISTRY
from adapter.cypher_templates.tai_san import TAI_SAN_REGISTRY
from adapter.viz_store import load_snapshot, save_snapshot, update_snapshot
from utils.utils import _dieu_level_id

_LEGAL_LABELS = frozenset({
    "DieuLuat",
    "DieuKhoanLuat",
    "DieuKhoanDiemLuat",
    "NghiDinh",
    "ThongTu",
    "NghiQuyet",
})

_GROUP_COLORS = {
    "can_cu_chinh": "#4C8BF5",
    "huong_dan": "#F5A623",
    "bo_tro": "#7ED321",
    "sap_hieu_luc": "#BD10E0",
    "hien_hanh_doi_chieu": "#50E3C2",
    "semantic": "#9013FE",
    "mau_thuan": "#D0021B",
    "default": "#9B9B9B",
}

_DEPRECATED_GROUPS = frozenset({"legal_ref", "legal"})

_BATCH_EDGE_CYPHER = """
UNWIND $ids AS nid
MATCH (n {id: nid})
WITH collect(DISTINCT n) AS matched
UNWIND matched AS n
OPTIONAL MATCH (n)-[r]-(m)
WHERE m IN matched
WITH n, r, m
WHERE r IS NOT NULL
RETURN
  collect(DISTINCT {id: n.id, labels: labels(n)}) +
  collect(DISTINCT CASE WHEN m IS NOT NULL THEN {id: m.id, labels: labels(m)} END) AS nodes,
  collect(DISTINCT {src: startNode(r).id, dst: endNode(r).id, type: type(r)}) AS edges
"""

_VIZ_REGISTRIES: dict[str, TemplateRegistry] = {
    "chia_tai_san_sau_ly_hon": CHIA_TAI_SAN_SAU_LY_HON_REGISTRY,
    "tai_san": TAI_SAN_REGISTRY,
}


def _primary_label(labels: list[str] | None) -> str:
    if not labels:
        return "Node"
    for label in labels:
        if label not in ("CheDoTaiSanCuaVoChong", "ChiaTaiSanSauLyHon"):
            return label
    return labels[0]


def _is_legal_labels(labels: list[str] | None) -> bool:
    return bool(labels and set(labels) & _LEGAL_LABELS)


def _infer_group(labels: list[str] | None, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    if not labels:
        return "default"
    label_set = set(labels)
    if label_set & _LEGAL_LABELS:
        return "bo_tro"
    if (
        "LoaiTaiSan" in label_set
        or "HanhVi" in label_set
        or "NghiaVu" in label_set
        or "Quyen" in label_set
    ):
        return "semantic"
    return "default"


def _make_node(node_id: str, labels: list[str] | None = None, group: str | None = None) -> dict[str, Any]:
    primary = _primary_label(labels)
    grp = _infer_group(labels, group)
    node: dict[str, Any] = {
        "id": node_id,
        "label": primary,
        "group": grp,
        "caption": node_id,
        "color": _GROUP_COLORS.get(grp, _GROUP_COLORS["default"]),
    }
    if labels:
        node["_labels"] = labels
    return node


def _make_edge(src: str, dst: str, rel_type: str, edge_id: str | None = None) -> dict[str, Any]:
    return {
        "id": edge_id or f"{src}|{rel_type}|{dst}",
        "from": src,
        "to": dst,
        "label": rel_type,
    }


class _GraphBuilder:
    def __init__(self) -> None:
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: dict[str, dict[str, Any]] = {}
        self.pending_legal_edges: list[tuple[str, str, str]] = []

    def add_node(self, node_id: str | None, labels: list[str] | None = None, group: str | None = None) -> None:
        if not node_id:
            return
        nid = str(node_id)
        if nid not in self._nodes:
            self._nodes[nid] = _make_node(nid, labels, group)
            return
        existing = self._nodes[nid]
        if labels:
            if existing.get("label") == "Node":
                existing["label"] = _primary_label(labels)
            existing["_labels"] = labels
        if group:
            cur = existing.get("group")
            if cur in ("default", "legal", "legal_ref", "bo_tro") and group not in _DEPRECATED_GROUPS:
                if cur in ("default", "legal", "legal_ref") or group != "bo_tro":
                    existing["group"] = group
                    existing["color"] = _GROUP_COLORS.get(group, _GROUP_COLORS["default"])

    def add_edge(self, src: str | None, dst: str | None, rel_type: str) -> None:
        if not src or not dst or not rel_type:
            return
        key = f"{src}|{rel_type}|{dst}"
        if key not in self._edges:
            self._edges[key] = _make_edge(str(src), str(dst), rel_type, key)

    def merge(self, other: "_GraphBuilder") -> None:
        for nid, node in other._nodes.items():
            self.add_node(nid, labels=node.get("_labels"), group=node.get("group"))
        for eid, edge in other._edges.items():
            if eid not in self._edges:
                self._edges[eid] = edge
        self.pending_legal_edges.extend(other.pending_legal_edges)

    def to_dict(self) -> dict[str, list]:
        nodes = [{k: v for k, v in n.items() if k != "_labels"} for n in self._nodes.values()]
        return {
            "nodes": nodes,
            "edges": list(self._edges.values()),
        }


def _add_huong_dan_boi_edge(
    builder: _GraphBuilder,
    law_id: str | None,
    guide_id: str | None,
    legal_ids: list[str],
    seen: set[tuple[str, str]],
) -> None:
    """Luật → văn bản hướng dẫn (cấp Điều), khớp chiều Neo4j HUONG_DAN_BOI."""
    if not law_id or not guide_id:
        return
    goc = _dieu_level_id(law_id) or str(law_id)
    hd = _dieu_level_id(guide_id) or str(guide_id)
    key = (goc, hd)
    if key in seen:
        return
    seen.add(key)
    builder.add_node(goc, group="can_cu_chinh")
    legal_ids.append(goc)
    builder.add_node(hd, group="huong_dan")
    legal_ids.append(hd)
    builder.add_edge(goc, hd, "HUONG_DAN_BOI")


def _collect_ids_from_context(context_tho: dict[str, Any]) -> tuple[_GraphBuilder, list[str]]:
    builder = _GraphBuilder()
    legal_ids: list[str] = []
    seen_huong_dan: set[tuple[str, str]] = set()

    for item in context_tho.get("can_cu_chinh", []) or []:
        if not isinstance(item, dict):
            continue
        for key in ("id_goc_tu_router", "id_thuc_te_ap_dung", "id"):
            nid = item.get(key)
            if nid:
                builder.add_node(nid, group="can_cu_chinh")
                legal_ids.append(nid)
        sua_doi = item.get("id_sua_doi")
        if sua_doi:
            builder.add_node(sua_doi, group="huong_dan")
            legal_ids.append(sua_doi)
            main_id = item.get("id_thuc_te_ap_dung") or item.get("id")
            builder.add_edge(main_id, sua_doi, "DUOC_SUA_DOI_BOI")

    for item in context_tho.get("can_cu_huong_dan", []) or []:
        if isinstance(item, dict) and item.get("id"):
            builder.add_node(item["id"], group="huong_dan")
            legal_ids.append(item["id"])
            if item.get("id_sua_doi"):
                builder.add_node(item["id_sua_doi"], group="huong_dan")
                legal_ids.append(item["id_sua_doi"])
                builder.add_edge(item["id"], item["id_sua_doi"], "DUOC_SUA_DOI_BOI")

    for item in context_tho.get("can_cu_bo_tro", []) or []:
        if isinstance(item, dict) and item.get("id"):
            builder.add_node(item["id"], group="bo_tro")
            legal_ids.append(item["id"])

    for item in context_tho.get("can_cu_sap_hieu_luc", []) or []:
        if isinstance(item, dict) and item.get("id"):
            builder.add_node(item["id"], group="sap_hieu_luc")
            legal_ids.append(item["id"])
            tac_dong = item.get("id_duoc_tac_dong")
            loai = item.get("loai_tac_dong") or "SAP_HIEU_LUC"
            if tac_dong:
                if str(loai) == "HUONG_DAN_BOI":
                    _add_huong_dan_boi_edge(
                        builder, tac_dong, item["id"], legal_ids, seen_huong_dan
                    )
                else:
                    builder.add_node(tac_dong, group="can_cu_chinh")
                    legal_ids.append(tac_dong)
                    builder.add_edge(item["id"], tac_dong, str(loai))

    for item in context_tho.get("can_cu_mau_thuan", []) or []:
        if not isinstance(item, dict):
            continue
        src = item.get("id_nguon")
        dst = item.get("id_dich")
        if src:
            builder.add_node(src, group="can_cu_chinh")
            legal_ids.append(src)
        if dst:
            builder.add_node(dst, group="mau_thuan")
            legal_ids.append(dst)
        builder.add_edge(src, dst, "MAU_THUAN_VOI")

    for pair in context_tho.get("lien_ket_huong_dan", []) or []:
        if not isinstance(pair, dict):
            continue
        _add_huong_dan_boi_edge(
            builder,
            pair.get("id_duoc_huong_dan"),
            pair.get("id_huong_dan"),
            legal_ids,
            seen_huong_dan,
        )

    for pair in context_tho.get("lien_ket_sap_hieu_luc", []) or []:
        if not isinstance(pair, dict):
            continue
        vb = pair.get("id_van_ban")
        goc = pair.get("id_duoc_tac_dong")
        loai = pair.get("loai_tac_dong") or "SAP_HIEU_LUC"
        if str(loai) == "HUONG_DAN_BOI":
            _add_huong_dan_boi_edge(builder, goc, vb, legal_ids, seen_huong_dan)
            continue
        if vb:
            builder.add_node(vb, group="sap_hieu_luc")
            legal_ids.append(vb)
        if goc:
            builder.add_node(goc, group="can_cu_chinh")
            legal_ids.append(goc)
        builder.add_edge(vb, goc, str(loai))

    hien_hanh_ids = context_tho.get("quy_dinh_hien_hanh_doi_chieu") or []
    main_ids = [
        item.get("id_thuc_te_ap_dung") or item.get("id")
        for item in context_tho.get("can_cu_chinh", []) or []
        if isinstance(item, dict)
    ]
    for hh_id in hien_hanh_ids:
        if hh_id:
            builder.add_node(hh_id, group="hien_hanh_doi_chieu")
            legal_ids.append(hh_id)
            for mid in main_ids:
                if mid and mid != hh_id:
                    builder.add_edge(mid, hh_id, "THAY_THE_BOI")

    unique_legal = list(dict.fromkeys(i for i in legal_ids if i))
    return builder, unique_legal


def _fetch_neo4j_edges(legal_ids: list[str]) -> _GraphBuilder:
    builder = _GraphBuilder()
    if not legal_ids:
        return builder
    try:
        records, _, _ = driver.execute_query(_BATCH_EDGE_CYPHER, ids=legal_ids)
    except Exception as exc:
        print(f"[graph_viz] Batch edge query error: {exc}")
        return builder
    if not records:
        return builder
    row = records[0].data()
    for raw in row.get("nodes") or []:
        if raw and raw.get("id"):
            builder.add_node(raw["id"], labels=raw.get("labels"))
    for raw in row.get("edges") or []:
        if raw and raw.get("src") and raw.get("dst"):
            builder.add_edge(raw["src"], raw["dst"], raw.get("type") or "RELATED")
    return builder


def _apply_pending_legal_edges(builder: _GraphBuilder) -> None:
    """Chỉ thêm edge semantic→legal khi node đích đã có từ retrieval/context."""
    for src, dst, rel in builder.pending_legal_edges:
        if src in builder._nodes and dst in builder._nodes:
            builder.add_edge(src, dst, rel)


def _prune_semantic_subgraph(builder: _GraphBuilder, leaf_seed_ids: list[str]) -> None:
    """Giữ node semantic trên đường đi ngược từ leaf_seed_nodes hợp lệ."""
    if not leaf_seed_ids:
        return
    semantic_ids = {
        nid for nid, node in builder._nodes.items() if node.get("group") == "semantic"
    }
    allowed = {str(x) for x in leaf_seed_ids} & semantic_ids
    if not allowed:
        return

    reverse_adj: dict[str, list[str]] = {nid: [] for nid in semantic_ids}
    for edge in builder._edges.values():
        src = edge.get("from")
        dst = edge.get("to")
        if src in semantic_ids and dst in semantic_ids and dst is not None and src is not None:
            reverse_adj[str(dst)].append(str(src))

    keep: set[str] = set()
    queue = list(allowed)
    while queue:
        nid = queue.pop()
        if nid in keep:
            continue
        keep.add(nid)
        for parent in reverse_adj.get(nid, []):
            if parent not in keep:
                queue.append(parent)

    remove = semantic_ids - keep
    for nid in remove:
        del builder._nodes[nid]
    for eid in [
        eid
        for eid, edge in builder._edges.items()
        if edge.get("from") in remove or edge.get("to") in remove
    ]:
        del builder._edges[eid]
    builder.pending_legal_edges = [
        (src, dst, rel) for src, dst, rel in builder.pending_legal_edges if src in keep
    ]


def _parse_viz_cypher_result(data: dict[str, Any]) -> _GraphBuilder:
    builder = _GraphBuilder()
    if "viz_graph" in data:
        graph = data["viz_graph"] or {}
        legal_ids: set[str] = set()
        for raw in graph.get("nodes") or []:
            if raw and raw.get("id"):
                labels = raw.get("labels")
                if _is_legal_labels(labels):
                    legal_ids.add(str(raw["id"]))
                    continue
                builder.add_node(raw["id"], labels=labels, group="semantic")
        for raw in graph.get("edges") or []:
            if not raw or not raw.get("src") or not raw.get("dst"):
                continue
            src = str(raw["src"])
            dst = str(raw["dst"])
            rel = raw.get("type") or "RELATED"
            if dst in legal_ids:
                builder.pending_legal_edges.append((src, dst, rel))
            elif src in legal_ids:
                continue
            else:
                builder.add_edge(src, dst, rel)
        leaf_seed_ids = graph.get("leaf_seed_ids") or []
        _prune_semantic_subgraph(builder, leaf_seed_ids)
        return builder

    triples = data.get("seed_trace") or []
    for t in triples:
        if not isinstance(t, dict):
            continue
        src = t.get("src_id")
        dst = t.get("dst_id")
        rel = t.get("rel") or "RELATED"
        src_label = t.get("src_label")
        dst_label = t.get("dst_label")
        src_is_legal = src_label in _LEGAL_LABELS
        dst_is_legal = dst_label in _LEGAL_LABELS
        if not src_is_legal and src:
            builder.add_node(src, labels=[src_label] if src_label else None, group="semantic")
        if not dst_is_legal and dst and dst_label != "WHITELIST":
            builder.add_node(dst, labels=[dst_label] if dst_label else None, group="semantic")
        if dst_is_legal and src and dst:
            builder.pending_legal_edges.append((str(src), str(dst), rel))
        elif not src_is_legal:
            builder.add_edge(src, dst, rel)
    return builder


def _run_viz_cypher(template: CypherTemplate, runtime_params: dict[str, Any]) -> _GraphBuilder:
    if not template.viz_cypher:
        return _GraphBuilder()
    try:
        records, _, _ = driver.execute_query(template.viz_cypher, **runtime_params)
    except Exception as exc:
        print(f"[graph_viz] viz_cypher error ({template.name}): {exc}")
        return _GraphBuilder()
    if not records:
        return _GraphBuilder()
    return _parse_viz_cypher_result(records[0].data())


def build_graph_payload(
    context_tho: dict[str, Any],
    template: CypherTemplate,
    runtime_params: dict[str, Any],
    target_date: str,
    query: str = "",
) -> dict[str, Any]:
    """Xây graph payload đầy đủ từ Context_Tho + viz_cypher + batch Neo4j edges."""
    ctx_builder, legal_ids = _collect_ids_from_context(context_tho)
    neo4j_builder = _fetch_neo4j_edges(legal_ids)
    semantic_builder = _run_viz_cypher(template, runtime_params)

    merged = _GraphBuilder()
    merged.merge(ctx_builder)
    merged.merge(neo4j_builder)
    merged.merge(semantic_builder)
    _apply_pending_legal_edges(merged)

    graph = merged.to_dict()
    display_params = {
        k: v
        for k, v in runtime_params.items()
        if "whitelist" not in k.lower() and "allowed_semantic" not in k.lower()
    }
    return {
        "meta": {
            "template": template.name,
            "params": display_params,
            "target_date": target_date,
            "query": query,
            "node_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"]),
        },
        "nodes": graph["nodes"],
        "edges": graph["edges"],
    }


def merge_graph_payloads(payloads: list[dict[str, Any]], query: str = "") -> dict[str, Any]:
    """Gộp nhiều payload (khi classify 2 template) thành một."""
    if not payloads:
        return {"meta": {}, "nodes": [], "edges": []}
    if len(payloads) == 1:
        return payloads[0]

    merged = _GraphBuilder()
    templates: list[str] = []
    for payload in payloads:
        templates.append(payload.get("meta", {}).get("template", ""))
        temp = _GraphBuilder()
        for node in payload.get("nodes") or []:
            label = node.get("label")
            labels = (
                [label]
                if label and label != "Node"
                else None
            )
            temp.add_node(node["id"], labels=labels, group=node.get("group"))
        for edge in payload.get("edges") or []:
            temp.add_edge(edge.get("from"), edge.get("to"), edge.get("label", "RELATED"))
        merged.merge(temp)

    graph = merged.to_dict()
    return {
        "meta": {
            "template": " + ".join(t for t in templates if t),
            "params": [p.get("meta", {}).get("params") for p in payloads],
            "target_date": payloads[0].get("meta", {}).get("target_date"),
            "query": query,
            "node_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"]),
        },
        "nodes": graph["nodes"],
        "edges": graph["edges"],
    }


def save_graph_viz(payload: dict[str, Any]) -> str:
    """Lưu snapshot, trả viz_id."""
    return save_snapshot(payload)


def save_lazy_viz_stub(
    sources: list[dict[str, Any]],
    query: str,
    target_date: str,
) -> str:
    """Lưu stub lazy viz — materialize khi user mở /api/viz/{id}."""
    stub: dict[str, Any] = {
        "lazy": True,
        "meta": {"query": query, "target_date": target_date},
        "sources": sources,
    }
    return save_snapshot(stub)


def materialize_viz_payload(stub: dict[str, Any]) -> dict[str, Any]:
    """Chạy viz_cypher + batch edges từ lazy stub."""
    sources = stub.get("sources") or []
    meta = stub.get("meta") or {}
    query = str(meta.get("query") or "")
    target_date = str(meta.get("target_date") or "")

    payloads: list[dict[str, Any]] = []
    for src in sources:
        if not isinstance(src, dict):
            continue
        topic = src.get("topic")
        template_name = src.get("template")
        context_tho = src.get("context_tho")
        params = src.get("params")
        if not topic or not template_name or not context_tho or not params:
            continue
        registry = _VIZ_REGISTRIES.get(str(topic))
        if registry is None:
            print(f"[graph_viz] Unknown viz topic: {topic}")
            continue
        template = registry.get(str(template_name))
        if template is None:
            print(f"[graph_viz] Unknown template {template_name} in {topic}")
            continue
        payloads.append(
            build_graph_payload(
                context_tho=context_tho,
                template=template,
                runtime_params=params,
                target_date=target_date,
                query=query,
            )
        )

    if not payloads:
        raise ValueError("Lazy stub has no valid sources to materialize")
    if len(payloads) == 1:
        return payloads[0]
    return merge_graph_payloads(payloads, query=query)


def _normalize_graph_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Loại node/edge deprecated (legal_ref, legal) từ snapshot cũ."""
    nodes = payload.get("nodes") or []
    edges = payload.get("edges") or []
    new_nodes = [n for n in nodes if n.get("group") not in _DEPRECATED_GROUPS]
    valid_ids = {n["id"] for n in new_nodes if n.get("id")}
    new_edges = [
        e
        for e in edges
        if e.get("from") in valid_ids and e.get("to") in valid_ids
    ]
    meta = dict(payload.get("meta") or {})
    meta["node_count"] = len(new_nodes)
    meta["edge_count"] = len(new_edges)
    return {**payload, "meta": meta, "nodes": new_nodes, "edges": new_edges}


def resolve_viz_snapshot(viz_id: str) -> dict[str, Any] | None:
    """Load snapshot; materialize và cache nếu là lazy stub."""
    raw = load_snapshot(viz_id)
    if raw is None:
        return None
    if not raw.get("lazy"):
        return _normalize_graph_payload(raw)
    try:
        payload = materialize_viz_payload(raw)
        update_snapshot(viz_id, payload)
        return payload
    except Exception as exc:
        print(f"[graph_viz] materialize error ({viz_id}): {exc}")
        return None


def collect_viz_links(tool_response: list[Any]) -> list[tuple[str, str, int]]:
    """Trích (viz_id, retriever_name, node_count) từ tool_response."""
    links: list[tuple[str, str, int]] = []
    for res in tool_response:
        if not isinstance(res, dict):
            continue
        viz_id = res.get("graph_viz_id")
        if viz_id:
            links.append(
                (
                    viz_id,
                    str(res.get("retriever_name") or "unknown"),
                    int(res.get("graph_viz_node_count") or 0),
                )
            )
    return links


def params_for_display(runtime_params: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v
        for k, v in runtime_params.items()
        if "whitelist" not in k.lower() and "allowed_semantic" not in k.lower()
    }
