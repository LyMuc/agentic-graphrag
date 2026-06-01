"""Gán thuộc tính `link` (Thư viện Pháp luật) cho DieuLuat / DieuKhoanLuat / DieuKhoanDiemLuat.

Mỗi node dùng cùng URL gốc của văn bản + anchor theo số Điều:
  {LINK_VAN_BAN}?anchor=dieu_{SO_DIEU}

Ví dụ Luật Hôn nhân và Gia đình 2014:
  python scripts/set_tvpl_links.py
  python scripts/set_tvpl_links.py --dry-run
  python scripts/set_tvpl_links.py --van-ban-id NghiDinh_126_2014 --link-van-ban "https://thuvienphapluat.vn/.../Nghi-dinh-126-....aspx"
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver  # noqa: E402

# --- Cấu hình mặc định (sửa trực tiếp hoặc truyền qua CLI) ---
VAN_BAN_ID = "Luat_HNGD_2014"
LINK_VAN_BAN = (
    "https://thuvienphapluat.vn/van-ban/Quyen-dan-su/Luat-Hon-nhan-va-gia-dinh-2014-238640.aspx"
)

LEGAL_LABELS = ("DieuLuat", "DieuKhoanLuat", "DieuKhoanDiemLuat")
_DIEU_FROM_ID_RE = re.compile(r"_Dieu_(\d+[a-zA-Z]?)(?:_|$)")


def _normalize_link_base(url: str) -> str:
    """Bỏ anchor/query cũ để chỉ giữ URL trang văn bản."""
    base = url.strip().split("#")[0]
    if "?" in base:
        base = base.split("?", 1)[0]
    return base.rstrip("/")


def _so_dieu_from_node(node_id: str, dieu_prop: Any) -> str | None:
    if dieu_prop is not None and str(dieu_prop).strip():
        return str(dieu_prop).strip()
    match = _DIEU_FROM_ID_RE.search(node_id or "")
    return match.group(1) if match else None


def build_anchor_link(link_van_ban: str, so_dieu: str) -> str:
    base = _normalize_link_base(link_van_ban)
    anchor = f"dieu_{so_dieu}".lower()
    return f"{base}?anchor={anchor}"


def fetch_legal_nodes(van_ban_id: str) -> list[dict[str, Any]]:
    """Lấy mọi node Điều/Khoản/Điểm thuộc văn bản (theo tiền tố id)."""
    prefix = f"{van_ban_id}_"
    cypher = """
    MATCH (n)
    WHERE (n:DieuLuat OR n:DieuKhoanLuat OR n:DieuKhoanDiemLuat)
      AND n.id STARTS WITH $prefix
    RETURN n.id AS id, n.dieu AS dieu, labels(n) AS labels
    ORDER BY n.id
    """
    records, _, _ = driver.execute_query(cypher, prefix=prefix)
    return [r.data() for r in records]


def apply_links(rows: list[dict[str, str]], batch_size: int = 500) -> int:
    """SET n.link theo lô UNWIND."""
    updated = 0
    cypher = """
    UNWIND $rows AS row
    MATCH (n {id: row.id})
    WHERE n:DieuLuat OR n:DieuKhoanLuat OR n:DieuKhoanDiemLuat
    SET n.link = row.link
    RETURN count(n) AS cnt
    """
    with driver.session() as session:
        for i in range(0, len(rows), batch_size):
            chunk = rows[i : i + batch_size]
            result = session.run(cypher, rows=chunk).single()
            updated += int(result["cnt"]) if result else 0
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gán link TVPL cho các node Điều/Khoản/Điểm của một văn bản."
    )
    parser.add_argument(
        "--van-ban-id",
        default=VAN_BAN_ID,
        help=f"ID gốc văn bản trong Neo4j (mặc định: {VAN_BAN_ID})",
    )
    parser.add_argument(
        "--link-van-ban",
        default=LINK_VAN_BAN,
        help="URL trang văn bản trên thuvienphapluat.vn (không kèm anchor)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ in mẫu, không ghi Neo4j",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=5,
        help="Số dòng in mẫu khi --dry-run (mặc định 5)",
    )
    args = parser.parse_args()

    link_base = _normalize_link_base(args.link_van_ban)
    nodes = fetch_legal_nodes(args.van_ban_id)

    if not nodes:
        print(f"Khong tim thay node nao voi id bat dau bang '{args.van_ban_id}_'.")
        sys.exit(1)

    rows: list[dict[str, str]] = []
    skipped: list[str] = []

    for node in nodes:
        node_id = node["id"]
        so_dieu = _so_dieu_from_node(node_id, node.get("dieu"))
        if not so_dieu:
            skipped.append(node_id)
            continue
        rows.append({
            "id": node_id,
            "link": build_anchor_link(link_base, so_dieu),
        })

    print(f"Van ban: {args.van_ban_id}")
    print(f"LINK_VAN_BAN: {link_base}")
    print(f"Tong node: {len(nodes)} | Gan link: {len(rows)} | Bo qua: {len(skipped)}")

    if skipped:
        print("Khong xac dinh SO_DIEU (toi da 10 id dau):")
        for sid in skipped[:10]:
            print(f"  - {sid}")

    if args.dry_run:
        print("\n--- Mau link (dry-run) ---")
        for row in rows[: max(args.sample, 0)]:
            print(f"  {row['id']}")
            print(f"    -> {row['link']}")
        if len(rows) > args.sample:
            print(f"  ... va {len(rows) - args.sample} node khac")
        return

    updated = apply_links(rows)
    print(f"Da cap nhat link cho {updated} node.")


if __name__ == "__main__":
    try:
        main()
    finally:
        driver.close()
