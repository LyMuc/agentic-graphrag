#!/usr/bin/env python3
"""Chuẩn hóa ID điều khoản trong extracted JSON sang Luat_HNGD_2014_Dieu_X[_Khoan_Y[_Diem_Z]].

Ví dụ:
    Luat_HNGD_Dieu_33_Khoan_1          -> Luat_HNGD_2014_Dieu_33_Khoan_1
    Luat_HNGD_Dieu_42_Khoan_2_Diem_dd  -> Luat_HNGD_2014_Dieu_42_Khoan_2_Diem_đ

Usage:
    python scripts/fix_provision_ids.py --input outputs/hngd_run/extracted_json --in-place
    python scripts/fix_provision_ids.py --input outputs/hngd_run/extracted_json --output outputs/hngd_run/extracted_json_fixed
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

PROVISION_ID_PATTERN = re.compile(r"^Luat_HNGD(?:_2014)?_Dieu_\d+")
CANONICAL_PREFIX = "Luat_HNGD_2014_Dieu_"

# Sửa lỗi trích xuất đã biết (source_id sai / typo)
RELATIONSHIP_SOURCE_FIXES: dict[str, dict[str, str]] = {
    "Luat_HNGD_2014_Dieu_32.json": {
        "Xác lập, thực hiện giao dịch liên quan đến tài sản ngân hàng, tài khoản chứng khoán chung": (
            "Xác lập, thực hiện giao dịch liên quan đến tài khoản ngân hàng, tài khoản chứng khoán chung"
        ),
    },
}

RELATIONSHIP_REPAIRS: dict[str, list[dict[str, str]]] = {
    "Luat_HNGD_2014_Dieu_39.json": [
        {
            "relationship": "DAN_DEN",
            "source_id": "DieuKien",
            "target_id": "Quyền, nghĩa vụ tài sản đó vẫn có giá trị pháp lý",
            "new_source_id": (
                "Quyền, nghĩa vụ tài sản với người thứ ba phát sinh trước thời điểm việc chia tài sản chung có hiệu lực"
            ),
        }
    ],
}


def normalize_provision_id(value: str) -> str:
    """Đưa ID điều khoản về đúng format Luat_HNGD_2014_Dieu_..."""
    if not isinstance(value, str) or not value.startswith("Luat_HNGD"):
        return value

    normalized = value
    if normalized.startswith("Luat_HNGD_Dieu_"):
        normalized = normalized.replace("Luat_HNGD_Dieu_", CANONICAL_PREFIX, 1)
    elif normalized.startswith("Luat_HNGD_2014_Dieu_"):
        pass
    else:
        return value

    # Điểm đ (nghĩa vụ nộp thuế) trong Đ42 k2: graph cũ dùng Diem_dd
    normalized = normalized.replace("_Diem_dd", "_Diem_đ")
    return normalized


def _walk_and_fix(obj: Any, changes: list[tuple[str, str]]) -> Any:
    if isinstance(obj, dict):
        fixed: dict[str, Any] = {}
        for key, value in obj.items():
            if key in {"id", "source_id", "target_id"} and isinstance(value, str) and PROVISION_ID_PATTERN.match(value):
                new_value = normalize_provision_id(value)
                if new_value != value:
                    changes.append((value, new_value))
                fixed[key] = new_value
            else:
                fixed[key] = _walk_and_fix(value, changes)
        return fixed

    if isinstance(obj, list):
        return [_walk_and_fix(item, changes) for item in obj]

    if isinstance(obj, str) and PROVISION_ID_PATTERN.match(obj):
        new_value = normalize_provision_id(obj)
        if new_value != obj:
            changes.append((obj, new_value))
        return new_value

    return obj


def _repair_relationships(path: Path, block: dict[str, Any], repairs: list[str]) -> None:
    file_fixes = RELATIONSHIP_SOURCE_FIXES.get(path.name, {})
    for rel in block.get("relationships", []):
        old_source = rel.get("source_id")
        if old_source in file_fixes:
            rel["source_id"] = file_fixes[old_source]
            repairs.append(f"{path.name}: source_id '{old_source}' -> '{rel['source_id']}'")

    for repair in RELATIONSHIP_REPAIRS.get(path.name, []):
        for rel in block.get("relationships", []):
            if (
                rel.get("relationship") == repair["relationship"]
                and rel.get("source_id") == repair["source_id"]
                and rel.get("target_id") == repair["target_id"]
            ):
                rel["source_id"] = repair["new_source_id"]
                repairs.append(
                    f"{path.name}: repair {repair['relationship']} source "
                    f"'{repair['source_id']}' -> '{repair['new_source_id']}'"
                )


def fix_file(path: Path) -> tuple[Any, list[tuple[str, str]], list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    changes: list[tuple[str, str]] = []
    repairs: list[str] = []
    fixed_data = _walk_and_fix(data, changes)

    if fixed_data and isinstance(fixed_data, list):
        block = fixed_data[0]
        if isinstance(block, dict):
            _repair_relationships(path, block, repairs)

    return fixed_data, changes, repairs


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Chuẩn hóa ID điều khoản trong extracted JSON.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("outputs/hngd_run/extracted_json"),
        help="Thư mục chứa các file JSON đã trích xuất.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Thư mục output. Nếu bỏ trống và dùng --in-place thì ghi đè file gốc.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Ghi đè trực tiếp lên file trong thư mục --input.",
    )
    args = parser.parse_args()

    input_dir = args.input.resolve()
    if not input_dir.is_dir():
        raise SystemExit(f"Không tìm thấy thư mục input: {input_dir}")

    if args.in_place and args.output:
        raise SystemExit("Chỉ dùng một trong hai: --in-place hoặc --output.")

    if args.output:
        output_dir = args.output.resolve()
        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(input_dir, output_dir)
        target_dir = output_dir
    elif args.in_place:
        target_dir = input_dir
    else:
        raise SystemExit("Cần chỉ định --in-place hoặc --output.")

    total_files = 0
    total_changes = 0
    total_repairs = 0
    all_unique_changes: dict[str, str] = {}

    for path in sorted(target_dir.glob("*.json")):
        fixed_data, changes, repairs = fix_file(path)
        total_files += 1
        total_changes += len(changes)
        total_repairs += len(repairs)
        for old, new in changes:
            all_unique_changes[old] = new

        path.write_text(
            json.dumps(fixed_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if changes or repairs:
            print(f"[FIXED] {path.name}: {len(changes)} ID, {len(repairs)} repair")
            for msg in repairs:
                print(f"         {msg}")

    print(
        f"\nHoàn tất: {total_files} file, {total_changes} ID, {total_repairs} repair "
        f"({len(all_unique_changes)} ID duy nhất)."
    )
    if all_unique_changes:
        print("\nMột số ví dụ mapping:")
        for old, new in list(sorted(all_unique_changes.items()))[:10]:
            print(f"  {old} -> {new}")


if __name__ == "__main__":
    main()
