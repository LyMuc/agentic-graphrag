#!/usr/bin/env python3
"""Import graph chế độ tài sản vợ chồng (hngd_run/extracted_json) vào Neo4j.

Mọi node semantic (ChuThe, TaiSan, HanhViPhapLy, ...) được gắn thêm label CheDoTaiSanCuaVoChong.
Quan hệ CAN_CU_THEO chỉ MATCH node điều khoản đã có sẵn trong DB theo id (vd. Luat_HNGD_2014_Dieu_33_Khoan_1).

Usage:
    # Từ thư mục Knowledge-Graph-Builder-main
    python scripts/fix_provision_ids.py --input outputs/hngd_run/extracted_json --in-place
    python scripts/import_hngd_graph_to_neo4j.py --input outputs/hngd_run/extracted_json --clear

Yêu cầu biến môi trường (file .env ở root repo):
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
    NEO4J_DATABASE (tuỳ chọn)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT_REPO = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_REPO / ".env")

DOMAIN_LABEL = "CheDoTaiSanCuaVoChong"
CAN_CU_THEO = "CAN_CU_THEO"


@dataclass
class GraphBundle:
    nodes: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    entity_relationships: list[dict[str, str]] = field(default_factory=list)
    provision_links: list[dict[str, str]] = field(default_factory=list)
    skipped_relationships: list[str] = field(default_factory=list)


def load_extracted_graph(input_dir: Path, strict: bool) -> GraphBundle:
    bundle = GraphBundle()
    node_ids: set[str] = set()

    for path in sorted(input_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not payload:
            continue

        block = payload[0] if isinstance(payload, list) else payload
        source_file = path.name

        for node in block.get("nodes", []):
            label = node["label"]
            node_id = node["id"]
            node_ids.add(node_id)
            key = (label, node_id)
            bundle.nodes.setdefault(
                key,
                {
                    "label": label,
                    "id": node_id,
                    "source_files": {source_file},
                },
            )["source_files"].add(source_file)

        for rel in block.get("relationships", []):
            rel_type = rel["relationship"]
            source_id = rel["source_id"]
            target_id = rel["target_id"]

            if rel_type == CAN_CU_THEO:
                if source_id not in node_ids:
                    msg = f"{source_file}: CAN_CU_THEO source không tồn tại -> {source_id}"
                    if strict:
                        raise ValueError(msg)
                    bundle.skipped_relationships.append(msg)
                    continue
                bundle.provision_links.append(
                    {
                        "source_id": source_id,
                        "target_id": target_id,
                        "source_file": source_file,
                    }
                )
                continue

            if source_id not in node_ids or target_id not in node_ids:
                msg = (
                    f"{source_file}: {rel_type} tham chiếu node thiếu "
                    f"({source_id} -> {target_id})"
                )
                if strict:
                    raise ValueError(msg)
                bundle.skipped_relationships.append(msg)
                continue

            bundle.entity_relationships.append(
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "relationship": rel_type,
                    "source_file": source_file,
                }
            )

    return bundle


def _index_nodes_by_id(bundle: GraphBundle) -> dict[str, list[str]]:
    by_id: dict[str, list[str]] = {}
    for label, node_id in bundle.nodes:
        by_id.setdefault(node_id, []).append(label)
    return by_id


def validate_bundle(bundle: GraphBundle) -> None:
    id_to_labels = _index_nodes_by_id(bundle)
    duplicate_ids = {node_id: labels for node_id, labels in id_to_labels.items() if len(labels) > 1}
    if duplicate_ids:
        examples = list(duplicate_ids.items())[:5]
        details = ", ".join(f"{node_id} ({'/'.join(labels)})" for node_id, labels in examples)
        raise ValueError(
            "Phát hiện cùng một id nhưng khác label — cần xử lý thủ công trước khi import. "
            f"Ví dụ: {details}"
        )


def clear_domain_graph(session, domain_label: str) -> int:
    result = session.run(
        f"""
        MATCH (n:{domain_label})
        DETACH DELETE n
        RETURN count(*) AS deleted
        """
    )
    record = result.single()
    return record["deleted"] if record else 0


def import_nodes(session, nodes: dict[tuple[str, str], dict[str, Any]], batch_size: int = 100) -> int:
    node_list = [
        {
            "label": data["label"],
            "id": data["id"],
            "source_files": sorted(data["source_files"]),
        }
        for data in nodes.values()
    ]

    imported = 0
    for label in sorted({row["label"] for row in node_list}):
        rows = [row for row in node_list if row["label"] == label]
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            cypher = f"""
            UNWIND $rows AS row
            MERGE (n:{label} {{id: row.id}})
            SET n.source_files = row.source_files
            SET n:{DOMAIN_LABEL}
            RETURN count(n) AS cnt
            """
            session.run(cypher, rows=batch).consume()
            imported += len(batch)

    return imported


def import_entity_relationships(session, relationships: list[dict[str, str]], batch_size: int = 100) -> int:
    if not relationships:
        return 0

    imported = 0
    for rel_type in sorted({row["relationship"] for row in relationships}):
        rows = [row for row in relationships if row["relationship"] == rel_type]
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            cypher = f"""
            UNWIND $rows AS row
            MATCH (s:{DOMAIN_LABEL} {{id: row.source_id}})
            MATCH (t:{DOMAIN_LABEL} {{id: row.target_id}})
            MERGE (s)-[r:{rel_type}]->(t)
            SET r.source_file = row.source_file
            RETURN count(r) AS cnt
            """
            session.run(cypher, rows=batch).consume()
            imported += len(batch)

    return imported


def import_provision_links(
    session,
    links: list[dict[str, str]],
    batch_size: int = 100,
    strict: bool = False,
) -> tuple[int, list[str]]:
    """Nối CAN_CU_THEO tới node điều khoản đã có sẵn (match theo id, không lọc label)."""
    if not links:
        return 0, []

    imported = 0
    missing: list[str] = []

    for i in range(0, len(links), batch_size):
        batch = links[i : i + batch_size]
        result = session.run(
            f"""
            UNWIND $rows AS row
            MATCH (s:{DOMAIN_LABEL} {{id: row.source_id}})
            OPTIONAL MATCH (p {{id: row.target_id}})
            WITH row, s, p
            WHERE p IS NOT NULL
            MERGE (s)-[r:{CAN_CU_THEO}]->(p)
            SET r.source_file = row.source_file
            RETURN row.source_id AS source_id, row.target_id AS provision_id
            """,
            rows=batch,
        )
        linked_pairs = {
            (record["source_id"], record["provision_id"]) for record in result
        }
        imported += len(linked_pairs)

        for row in batch:
            pair = (row["source_id"], row["target_id"])
            if pair in linked_pairs:
                continue
            msg = (
                f"{row['source_file']}: CAN_CU_THEO {row['source_id']} -> {row['target_id']} "
                f"(không tìm thấy node điều khoản id={row['target_id']} hoặc source :{DOMAIN_LABEL})"
            )
            missing.append(msg)
            if strict:
                raise ValueError(msg)

    return imported, missing


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Import hngd_run extracted graph vào Neo4j.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("outputs/hngd_run/extracted_json"),
        help="Thư mục chứa JSON đã trích xuất.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help=f"Xóa toàn bộ node :{DOMAIN_LABEL} trước khi import.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Dừng import nếu phát hiện quan hệ tham chiếu node không tồn tại.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ đọc và validate, không ghi vào Neo4j.",
    )
    args = parser.parse_args()

    input_dir = args.input.resolve()
    if not input_dir.is_dir():
        raise SystemExit(f"Không tìm thấy thư mục input: {input_dir}")

    bundle = load_extracted_graph(input_dir, strict=args.strict)
    validate_bundle(bundle)

    print(
        f"Đã load {len(bundle.nodes)} node, "
        f"{len(bundle.entity_relationships)} quan hệ entity, "
        f"{len(bundle.provision_links)} liên kết CAN_CU_THEO."
    )
    if bundle.skipped_relationships:
        print(f"Bỏ qua {len(bundle.skipped_relationships)} quan hệ lỗi (--strict để bắt lỗi).")
        for msg in bundle.skipped_relationships[:5]:
            print(f"  - {msg}")

    if args.dry_run:
        print("Dry-run: không import vào Neo4j.")
        return

    uri = os.environ.get("NEO4J_URI")
    username = os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    database = os.environ.get("NEO4J_DATABASE")

    if not all([uri, username, password]):
        raise SystemExit(
            "Thiếu cấu hình Neo4j. Cần NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD trong .env"
        )

    driver = GraphDatabase.driver(uri, auth=(username, password))
    session_kwargs: dict[str, Any] = {}
    if database:
        session_kwargs["database"] = database

    try:
        with driver.session(**session_kwargs) as session:
            if args.clear:
                deleted = clear_domain_graph(session, DOMAIN_LABEL)
                print(f"Đã xóa {deleted} node :{DOMAIN_LABEL} (và quan hệ liên quan).")

            node_count = import_nodes(session, bundle.nodes)
            rel_count = import_entity_relationships(session, bundle.entity_relationships)
            provision_count, missing_provisions = import_provision_links(
                session,
                bundle.provision_links,
                strict=args.strict,
            )

            stats = session.run(
                f"""
                MATCH (n:{DOMAIN_LABEL})
                RETURN count(n) AS nodes
                """
            ).single()
            rel_stats = session.run(
                f"""
                MATCH (a:{DOMAIN_LABEL})-[r]->(b:{DOMAIN_LABEL})
                RETURN count(r) AS entity_rels
                """
            ).single()
            can_cu_stats = session.run(
                f"""
                MATCH (:{DOMAIN_LABEL})-[r:{CAN_CU_THEO}]->(p)
                RETURN count(r) AS can_cu_rels
                """
            ).single()

            print("\nImport hoàn tất.")
            print(f"  Node semantic đã ghi (batch): {node_count}")
            print(f"  Quan hệ entity (batch): {rel_count}")
            print(f"  CAN_CU_THEO đã nối (batch): {provision_count}")
            if missing_provisions:
                print(f"  CAN_CU_THEO bỏ qua (không có node điều khoản): {len(missing_provisions)}")
                for msg in missing_provisions[:5]:
                    print(f"    - {msg}")
            print(f"  Tổng node :{DOMAIN_LABEL} trong DB: {stats['nodes']}")
            print(f"  Tổng quan hệ giữa entity: {rel_stats['entity_rels']}")
            print(f"  Tổng CAN_CU_THEO -> node điều khoản: {can_cu_stats['can_cu_rels']}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
