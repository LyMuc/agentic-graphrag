#!/usr/bin/env python3
"""Regenerate auto-synced files in thesis-context/ from the live codebase.

Run from repo root:
    python scripts/sync_thesis_context.py

Only sections between AUTO-GENERATED markers are overwritten. Narrative files
(architecture.md, ch05-code-map.md, AGENT_WORKFLOW.md, ...) stay manual.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
THESIS_CTX = REPO_ROOT / "thesis-context"
RETRIEVER_ROOT = REPO_ROOT / "adapter" / "retrievers"
TEMPLATE_ROOT = REPO_ROOT / "adapter" / "cypher_templates"
CONTEXT_THO = RETRIEVER_ROOT / "_context_tho_common.py"
UTILS_PY = REPO_ROOT / "utils" / "utils.py"

AUTO_BEGIN = "<!-- BEGIN AUTO-GENERATED:sync_thesis_context.py -->"
AUTO_END = "<!-- END AUTO-GENERATED:sync_thesis_context.py -->"

NON_LEGAL_RELATIONSHIPS = frozenset({"CAN_CU_TAI"})
SCHEMA_ONLY_RELATIONSHIPS = frozenset({"CO_DIEU"})

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adapter.cypher_templates.registry_index import ALL_TEMPLATE_REGISTRIES  # noqa: E402
from application.retriever_catalog import (  # noqa: E402
    DIRECT_TOOLS,
    PRIMARY_RETRIEVER_SPECS,
    RETRIEVER_SPECS,
)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _replace_auto_section(content: str, body: str) -> str:
    block = f"{AUTO_BEGIN}\n{body.rstrip()}\n{AUTO_END}"
    pattern = re.compile(re.escape(AUTO_BEGIN) + r".*?" + re.escape(AUTO_END), re.DOTALL)
    if pattern.search(content):
        return pattern.sub(block, content, count=1)
    return content.rstrip() + "\n\n" + block + "\n"


def _find_retriever_module(tool_name: str) -> str | None:
    matches = sorted(RETRIEVER_ROOT.rglob(f"{tool_name}.py"))
    if matches:
        return matches[0].relative_to(REPO_ROOT).as_posix()
    return None


def _template_dirs_with_common() -> list[str]:
    dirs: list[str] = []
    for path in sorted(TEMPLATE_ROOT.iterdir()):
        if path.is_dir() and (path / "_common.py").exists():
            dirs.append(path.name)
    return dirs


def _extract_relationships() -> list[str]:
    rels = set(SCHEMA_ONLY_RELATIONSHIPS)
    source_files = [CONTEXT_THO, *sorted(TEMPLATE_ROOT.glob("*/_common.py"))]

    for path in source_files:
        text = path.read_text(encoding="utf-8")
        relationship_exprs = re.findall(
            r"\[(?::|[A-Za-z_][A-Za-z0-9_]*:)([A-Z][A-Z0-9_|]*)(?:\*[^\]]*)?\]",
            text,
        )
        for expression in relationship_exprs:
            rels.update(expression.split("|"))

    return sorted(rels - NON_LEGAL_RELATIONSHIPS)


def _extract_flags() -> list[str]:
    text = UTILS_PY.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"(FLAG_[A-Z0-9_]+)", text)))


def _template_dir_for_spec(spec) -> str | None:
    for key in (spec.topic_label, spec.domain_group):
        if key and (TEMPLATE_ROOT / key / "_common.py").exists():
            return f"adapter/cypher_templates/{key}/"
    if spec.name == "che_do_tai_san_cua_vo_chong" and (TEMPLATE_ROOT / "tai_san" / "_common.py").exists():
        return "adapter/cypher_templates/tai_san/"
    return None


def _tool_for_registry_topic(topic: str) -> str | None:
    if topic == "tai_san":
        return "che_do_tai_san_cua_vo_chong"
    for name, spec in PRIMARY_RETRIEVER_SPECS.items():
        if spec.topic_label == topic:
            return name
    for name, spec in PRIMARY_RETRIEVER_SPECS.items():
        if spec.domain_group == topic:
            return name
    return None


def _tool_to_retriever_map() -> dict[str, str | None]:
    return {topic: _tool_for_registry_topic(topic) for topic in ALL_TEMPLATE_REGISTRIES}


def _render_retriever_catalog() -> str:
    lines = [
        f"_Cập nhật lúc {_stamp()}_",
        "",
        "| Tool | topic_label | domain_group | File retriever | Templates |",
        "|---|---|---|---|---|",
    ]
    for name in sorted(PRIMARY_RETRIEVER_SPECS):
        spec = PRIMARY_RETRIEVER_SPECS[name]
        module = _find_retriever_module(name) or "—"
        tpl_dir = _template_dir_for_spec(spec)
        templates = f"`{tpl_dir}`" if tpl_dir else "—"
        lines.append(
            f"| `{name}` | `{spec.topic_label}` | `{spec.domain_group}` | `{module}` | {templates} |"
        )

    lines.extend(
        [
            "",
            "**Direct tools (không qua retriever):** "
            + ", ".join(f"`{t}`" for t in sorted(DIRECT_TOOLS)),
            "",
            f"Tổng retriever trong catalog: **{len(PRIMARY_RETRIEVER_SPECS)}** "
            f"(alias index: {len(RETRIEVER_SPECS)}).",
            "",
            "Nguồn code: `application/retriever_catalog.py`, `application/router_tool_registry.py`, "
            "`presentation/main.py`.",
        ]
    )
    return "\n".join(lines)


def _render_cypher_index() -> str:
    registered = ALL_TEMPLATE_REGISTRIES
    all_domains = _template_dirs_with_common()
    tool_map = _tool_to_retriever_map()

    lines = [
        f"_Cập nhật lúc {_stamp()}_",
        "",
        "Registry: `adapter/cypher_templates/registry_index.py` → `ALL_TEMPLATE_REGISTRIES`.",
        "",
        "## Domain trong ALL_TEMPLATE_REGISTRIES",
        "",
        "| topic | Thư mục | Retriever (tool) | Số template |",
        "|---|---|---|---|",
    ]
    for topic in sorted(registered):
        reg = registered[topic]
        tool = tool_map.get(topic) or "—"
        lines.append(
            f"| `{topic}` | `adapter/cypher_templates/{topic}/` | `{tool}` | {len(reg.names())} |"
        )

    unregistered = sorted(set(all_domains) - set(registered))
    if unregistered:
        lines.extend(["", "## Domain có `_common.py` nhưng chưa trong registry", ""])
        for topic in unregistered:
            tool = tool_map.get(topic) or "—"
            lines.append(f"- `{topic}/` — retriever liên quan: `{tool}`")

    lines.extend(
        [
            "",
            f"Tổng domain có `_common.py`: **{len(all_domains)}**; "
            f"đã đăng ký registry: **{len(registered)}**.",
        ]
    )
    return "\n".join(lines)


def _render_kg_legal_relationships() -> str:
    rels = _extract_relationships()
    lines = [
        f"_Cập nhật lúc {_stamp()}_",
        "",
        "Trích từ Cypher dùng chung đang hoạt động trong "
        "`adapter/retrievers/_context_tho_common.py` và "
        "`adapter/cypher_templates/*/_common.py`. `CO_DIEU` được giữ như "
        "quan hệ cấu trúc của schema dù các truy vấn retriever thường bắt đầu từ nút Điều:",
        "",
        "| Relationship |",
        "|---|",
    ]
    for rel in rels:
        lines.append(f"| `{rel}` |")
    lines.append("")
    lines.append(f"Tổng: **{len(rels)}** quan hệ legal trong bảng đồng bộ.")
    return "\n".join(lines)


def _render_flags_table() -> str:
    flags = _extract_flags()
    meanings = {
        "FLAG_CANH_BAO_SUA_DOI": "Có văn bản sửa đổi",
        "FLAG_CANH_BAO_THU_TU_UU_TIEN": "Nhiều cấp bậc pháp lý",
        "FLAG_CANH_BAO_LICH_SU": "Áp dụng luật tại mốc quá khứ",
        "FLAG_MAU_THUAN": "Căn cứ mâu thuẫn",
        "FLAG_VAN_BAN_SAP_HIEU_LUC": "Văn bản sắp có hiệu lực",
    }
    lines = [
        f"_Cập nhật lúc {_stamp()}_",
        "",
        "Trích từ `utils/utils.py` → `chuan_hoa_Context_cho_LLM`:",
        "",
        "| Flag trong code | Ý nghĩa (tóm tắt) |",
        "|---|---|",
    ]
    for flag in flags:
        meaning = meanings.get(flag, "—")
        lines.append(f"| `{flag}` | {meaning} |")
    return "\n".join(lines)


def _write_with_auto_section(path: Path, body: str) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(_replace_auto_section(current, body), encoding="utf-8")
    print(f"  updated {path.relative_to(REPO_ROOT)}")


def main() -> int:
    print("Sync thesis-context from codebase...")
    THESIS_CTX.mkdir(parents=True, exist_ok=True)

    _write_with_auto_section(THESIS_CTX / "retriever-catalog.md", _render_retriever_catalog())
    _write_with_auto_section(THESIS_CTX / "cypher-template-index.md", _render_cypher_index())
    _write_with_auto_section(THESIS_CTX / "kg-schema.md", _render_kg_legal_relationships())

    flags_path = THESIS_CTX / "legal-reasoning-flow.md"
    if flags_path.exists():
        _write_with_auto_section(flags_path, _render_flags_table())
    else:
        print(f"  skip {flags_path.name} (not found)")

    print("Done. Review git diff; edit manual sections / .tex as needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
