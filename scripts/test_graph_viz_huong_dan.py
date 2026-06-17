"""Unit test: chiều và dedupe HUONG_DAN_BOI trong graph viz."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.graph_viz import _collect_ids_from_context

LUAT = "Luat_HNGD_2014_Dieu_35"
ND_DIEU = "NghiDinh_126_2014_ND_CP_Dieu_13"
ND_K1 = "NghiDinh_126_2014_ND_CP_Dieu_13_Khoan_1"
ND_K2 = "NghiDinh_126_2014_ND_CP_Dieu_13_Khoan_2"


def _huong_dan_edges(edges: list[dict]) -> list[tuple[str, str]]:
    return [
        (e["from"], e["to"])
        for e in edges
        if e.get("label") == "HUONG_DAN_BOI"
    ]


def test_lien_ket_huong_dan_direction_and_deduplicate() -> None:
    """Hai cặp Khoản → Luật gom thành một edge Luật → NĐ Điều."""
    context = {
        "can_cu_chinh": [],
        "lien_ket_huong_dan": [
            {"id_huong_dan": ND_K1, "id_duoc_huong_dan": LUAT},
            {"id_huong_dan": ND_K2, "id_duoc_huong_dan": LUAT},
        ],
    }
    builder, _ = _collect_ids_from_context(context)
    graph = builder.to_dict()
    hd_edges = _huong_dan_edges(graph["edges"])

    assert hd_edges == [(LUAT, ND_DIEU)]
    assert not any(
        src.startswith("NghiDinh") and dst == LUAT for src, dst in hd_edges
    )


def test_lien_ket_sap_hieu_luc_huong_dan_boi() -> None:
    """lien_ket_sap_hieu_luc HUONG_DAN_BOI cũng vẽ Luật → NĐ (cấp Điều)."""
    context = {
        "can_cu_chinh": [],
        "lien_ket_sap_hieu_luc": [
            {
                "id_van_ban": ND_K1,
                "id_duoc_tac_dong": LUAT,
                "loai_tac_dong": "HUONG_DAN_BOI",
            },
        ],
    }
    builder, _ = _collect_ids_from_context(context)
    graph = builder.to_dict()
    assert _huong_dan_edges(graph["edges"]) == [(LUAT, ND_DIEU)]


def test_can_cu_sap_hieu_luc_huong_dan_boi() -> None:
    """can_cu_sap_hieu_luc loại HUONG_DAN_BOI vẽ Luật → NĐ."""
    context = {
        "can_cu_chinh": [],
        "can_cu_sap_hieu_luc": [
            {
                "id": ND_K2,
                "id_duoc_tac_dong": LUAT,
                "loai_tac_dong": "HUONG_DAN_BOI",
            },
        ],
    }
    builder, _ = _collect_ids_from_context(context)
    graph = builder.to_dict()
    assert _huong_dan_edges(graph["edges"]) == [(LUAT, ND_DIEU)]


def test_other_tac_dong_unchanged() -> None:
    """Các loại tác động khác giữ chiều văn bản → căn cứ bị tác động."""
    context = {
        "can_cu_chinh": [],
        "lien_ket_sap_hieu_luc": [
            {
                "id_van_ban": "ND_SUA",
                "id_duoc_tac_dong": LUAT,
                "loai_tac_dong": "SUA_DOI_BOI",
            },
        ],
    }
    builder, _ = _collect_ids_from_context(context)
    graph = builder.to_dict()
    sua_edges = [
        (e["from"], e["to"], e["label"])
        for e in graph["edges"]
        if e.get("label") == "SUA_DOI_BOI"
    ]
    assert sua_edges == [("ND_SUA", LUAT, "SUA_DOI_BOI")]


def test_lien_ket_hien_hanh_paired_only() -> None:
    """Chỉ vẽ THAY_THE_BOI theo cặp lien_ket_hien_hanh, không nối chéo can_cu_chinh."""
    nd82 = "NghiDinh_82_2020_ND_CP_Dieu_58"
    luat5 = "Luat_HNGD_2014_Dieu_5"
    nd109 = "NghiDinh_109_2026_ND_CP_Dieu_61"
    context = {
        "can_cu_chinh": [
            {"id_thuc_te_ap_dung": nd82},
            {"id_thuc_te_ap_dung": luat5},
        ],
        "quy_dinh_hien_hanh_doi_chieu": [nd109],
        "lien_ket_hien_hanh": [
            {"id_hien_hanh": nd109, "id_duoc_thay_the": "NghiDinh_82_2020_ND_CP_Dieu_61"},
        ],
    }
    builder, _ = _collect_ids_from_context(context)
    graph = builder.to_dict()
    thay_the_edges = [
        (e["from"], e["to"])
        for e in graph["edges"]
        if e.get("label") == "THAY_THE_BOI"
    ]
    assert thay_the_edges == [("NghiDinh_82_2020_ND_CP_Dieu_61", nd109)]
    assert (luat5, nd109) not in thay_the_edges
    assert (nd82, nd109) not in thay_the_edges


if __name__ == "__main__":
    test_lien_ket_huong_dan_direction_and_deduplicate()
    test_lien_ket_sap_hieu_luc_huong_dan_boi()
    test_can_cu_sap_hieu_luc_huong_dan_boi()
    test_other_tac_dong_unchanged()
    test_lien_ket_hien_hanh_paired_only()
    print("OK: test_graph_viz_huong_dan")
