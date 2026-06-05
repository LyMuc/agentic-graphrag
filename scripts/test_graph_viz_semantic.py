"""Unit test: semantic viz — ẩn legal_ref, pending edges, nâng cấp label."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.graph_viz import (
    _GraphBuilder,
    _apply_pending_legal_edges,
    _normalize_graph_payload,
    _parse_viz_cypher_result,
)

DIEU_43 = "Luat_HNGD_2014_Dieu_43"
DIEU_44_K1 = "Luat_HNGD_2014_Dieu_44_Khoan_1"
TAI_SAN_RIENG = "tai_san_rieng"
DINH_DOAT = "dinh_doat_tai_san_rieng"


def test_parse_viz_graph_skips_legal_nodes() -> None:
    data = {
        "viz_graph": {
            "nodes": [
                {"id": TAI_SAN_RIENG, "labels": ["LoaiTaiSan"]},
                {"id": DINH_DOAT, "labels": ["HanhVi"]},
                {"id": DIEU_43, "labels": ["DieuLuat"]},
                {"id": DIEU_44_K1, "labels": ["DieuKhoanLuat"]},
            ],
            "edges": [
                {"src": TAI_SAN_RIENG, "dst": DIEU_43, "type": "CAN_CU_TAI"},
                {"src": DINH_DOAT, "dst": DIEU_44_K1, "type": "CAN_CU_TAI"},
                {"src": TAI_SAN_RIENG, "dst": DINH_DOAT, "type": "LIEN_QUAN"},
            ],
        }
    }
    builder = _parse_viz_cypher_result(data)
    node_ids = set(builder._nodes)
    assert node_ids == {TAI_SAN_RIENG, DINH_DOAT}
    assert builder.pending_legal_edges == [
        (TAI_SAN_RIENG, DIEU_43, "CAN_CU_TAI"),
        (DINH_DOAT, DIEU_44_K1, "CAN_CU_TAI"),
    ]
    edges = builder.to_dict()["edges"]
    assert any(e["from"] == TAI_SAN_RIENG and e["to"] == DINH_DOAT for e in edges)


def test_pending_edges_only_when_dst_in_graph() -> None:
    semantic = _parse_viz_cypher_result(
        {
            "viz_graph": {
                "nodes": [
                    {"id": DINH_DOAT, "labels": ["HanhVi"]},
                    {"id": DIEU_43, "labels": ["DieuLuat"]},
                ],
                "edges": [
                    {"src": DINH_DOAT, "dst": DIEU_44_K1, "type": "CAN_CU_TAI"},
                    {"src": DINH_DOAT, "dst": DIEU_43, "type": "CAN_CU_TAI"},
                ],
            }
        }
    )
    merged = _GraphBuilder()
    merged.add_node(DIEU_44_K1, group="can_cu_chinh")
    merged.merge(semantic)
    _apply_pending_legal_edges(merged)

    edge_keys = {(e["from"], e["to"], e["label"]) for e in merged.to_dict()["edges"]}
    assert (DINH_DOAT, DIEU_44_K1, "CAN_CU_TAI") in edge_keys
    assert (DINH_DOAT, DIEU_43, "CAN_CU_TAI") not in edge_keys


def test_add_node_upgrades_label_from_node() -> None:
    builder = _GraphBuilder()
    builder.add_node(DIEU_44_K1, group="can_cu_chinh")
    assert builder._nodes[DIEU_44_K1]["label"] == "Node"
    builder.add_node(DIEU_44_K1, labels=["DieuKhoanLuat", "CheDoTaiSanCuaVoChong"])
    assert builder._nodes[DIEU_44_K1]["label"] == "DieuKhoanLuat"


def test_normalize_removes_legal_ref_and_orphan_edges() -> None:
    payload = {
        "meta": {"node_count": 3, "edge_count": 2},
        "nodes": [
            {"id": DIEU_43, "label": "DieuLuat", "group": "legal_ref"},
            {"id": DIEU_44_K1, "label": "DieuKhoanLuat", "group": "can_cu_chinh"},
            {"id": DINH_DOAT, "label": "HanhVi", "group": "semantic"},
        ],
        "edges": [
            {"from": DINH_DOAT, "to": DIEU_43, "label": "CAN_CU_TAI"},
            {"from": DINH_DOAT, "to": DIEU_44_K1, "label": "CAN_CU_TAI"},
        ],
    }
    out = _normalize_graph_payload(payload)
    ids = {n["id"] for n in out["nodes"]}
    assert DIEU_43 not in ids
    assert DIEU_44_K1 in ids
    assert len(out["edges"]) == 1
    assert out["edges"][0]["to"] == DIEU_44_K1


def test_seed_trace_legacy_skips_legal_nodes() -> None:
    builder = _parse_viz_cypher_result(
        {
            "seed_trace": [
                {
                    "src_id": TAI_SAN_RIENG,
                    "dst_id": DIEU_43,
                    "rel": "CAN_CU_TAI",
                    "src_label": "LoaiTaiSan",
                    "dst_label": "DieuLuat",
                }
            ]
        }
    )
    assert set(builder._nodes) == {TAI_SAN_RIENG}
    assert builder.pending_legal_edges == [(TAI_SAN_RIENG, DIEU_43, "CAN_CU_TAI")]


if __name__ == "__main__":
    test_parse_viz_graph_skips_legal_nodes()
    test_pending_edges_only_when_dst_in_graph()
    test_add_node_upgrades_label_from_node()
    test_normalize_removes_legal_ref_and_orphan_edges()
    test_seed_trace_legacy_skips_legal_nodes()
    print("OK: test_graph_viz_semantic")
