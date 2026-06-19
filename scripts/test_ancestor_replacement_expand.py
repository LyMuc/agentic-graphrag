"""Smoke tests for heading-level replacement expansion in Cypher templates."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.cypher_templates.xu_phat_vi_pham import (  # noqa: E402
    XU_PHAT_VI_PHAM_REGISTRY,
)
from adapter.retrievers._context_tho_common import (  # noqa: E402
    ANCESTOR_REPLACEMENT_EXPAND_KG,
)


OLD_ANCESTOR_COLLECT = (
    "collect(DISTINCT heading_node) + collect(DISTINCT heading_moi) "
    "+ collect(DISTINCT heading_cu)"
)


def _target_common_files() -> list[Path]:
    files = []
    for path in sorted((ROOT / "adapter" / "cypher_templates").glob("*/_common.py")):
        text = path.read_text(encoding="utf-8")
        if "EXPAND_AND_TIMEFILTER_CYPHER" in text and "THAM_CHIEU_ANCESTOR_MATCH_KG" in text:
            files.append(path)
    return files


def test_all_common_templates_use_shared_ancestor_expansion() -> None:
    files = _target_common_files()
    assert len(files) == 20, f"Expected 20 shared common templates, got {len(files)}"

    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "ANCESTOR_REPLACEMENT_EXPAND_KG" in text, path
        assert "MAU_THUAN_MATCH_KG" in text, path
        assert "can_cu_mau_thuan:" in text, path
        assert OLD_ANCESTOR_COLLECT not in text, path


def test_shared_helper_expands_replacement_heading_descendants() -> None:
    helper = ANCESTOR_REPLACEMENT_EXPAND_KG
    assert "THAY_THE_BOI*1.." in helper
    assert "heading_moi)-[:CO_KHOAN]->(heading_khoan_moi)" in helper
    assert "heading_khoan_moi)-[:CO_DIEM]->(heading_diem_moi)" in helper
    assert "heading_moi)-[:CO_DIEM]->(heading_diem_k_moi)" in helper
    assert "heading_cu)-[:CO_KHOAN]->(heading_khoan_cu)" in helper
    assert "heading_khoan_cu)-[:CO_DIEM]->(heading_diem_cu)" in helper


def test_xu_phat_tao_hon_template_inlines_replacement_descendants() -> None:
    tpl = XU_PHAT_VI_PHAM_REGISTRY.get("tao_hon_va_to_chuc_tao_hon")
    cypher = tpl.cypher
    assert "OPTIONAL MATCH (heading_moi)-[:CO_KHOAN]->(heading_khoan_moi)" in cypher
    assert "OPTIONAL MATCH (heading_khoan_moi)-[:CO_DIEM]->(heading_diem_moi)" in cypher
    assert "OPTIONAL MATCH (heading_cu)-[:CO_KHOAN]->(heading_khoan_cu)" in cypher
    assert "MAU_THUAN_VOI" in cypher
    assert "can_cu_mau_thuan:" in cypher


def main() -> None:
    print("Running ancestor replacement expansion smoke tests...\n")
    test_all_common_templates_use_shared_ancestor_expansion()
    print("  [OK] all shared _common.py templates use helper")
    test_shared_helper_expands_replacement_heading_descendants()
    print("  [OK] shared helper expands replacement headings to descendants")
    test_xu_phat_tao_hon_template_inlines_replacement_descendants()
    print("  [OK] xu_phat_vi_pham tao_hon template inlines fixed Cypher")
    print("\nAll passed.")


if __name__ == "__main__":
    main()
