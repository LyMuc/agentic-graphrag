"""Lưu / đọc snapshot JSON cho trang visualize đồ thị."""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

_DEFAULT_DIR = Path(__file__).resolve().parent.parent / "data" / "viz_snapshots"
_TTL_SECONDS = 7 * 24 * 3600


def _snapshot_dir() -> Path:
    custom = os.environ.get("VIZ_SNAPSHOT_DIR")
    if custom:
        return Path(custom)
    return _DEFAULT_DIR


def _cleanup_expired(directory: Path) -> None:
    now = time.time()
    for path in directory.glob("*.json"):
        try:
            if now - path.stat().st_mtime > _TTL_SECONDS:
                path.unlink(missing_ok=True)
        except OSError:
            pass


def save_snapshot(payload: dict[str, Any]) -> str:
    """Lưu payload, trả về viz_id (UUID)."""
    directory = _snapshot_dir()
    directory.mkdir(parents=True, exist_ok=True)
    _cleanup_expired(directory)

    viz_id = uuid.uuid4().hex
    path = directory / f"{viz_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
    return viz_id


def update_snapshot(viz_id: str, payload: dict[str, Any]) -> None:
    """Ghi đè snapshot (cache sau materialize lazy viz)."""
    if not viz_id or "/" in viz_id or "\\" in viz_id:
        raise ValueError("Invalid viz_id")
    directory = _snapshot_dir()
    path = directory / f"{viz_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")


def load_snapshot(viz_id: str) -> dict[str, Any] | None:
    if not viz_id or "/" in viz_id or "\\" in viz_id:
        return None
    path = _snapshot_dir() / f"{viz_id}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
