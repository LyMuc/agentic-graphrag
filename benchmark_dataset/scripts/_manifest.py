"""
Read/write helpers for _state/mapped_manifest.json.

Schema:
{
  "schema_version": 1,
  "updated_at": "2026-05-17T11:39:00+07:00",
  "topics": {
    "<chu_de>": {
      "mapped_question_ids": ["abc123...", ...],
      "versions": [
        {
          "version": 1,
          "date": "1705",
          "files": ["test_versions/<chu_de>/test_v1_1705_<chu_de>.json", ".csv"],
          "added_question_ids": [...]
        }
      ]
    }
  }
}
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta

from scripts._common import MANIFEST_PATH, STATE_DIR, ensure_dir, backup_paths

SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")


def empty_manifest() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": _now_iso(),
        "topics": {},
    }


def load() -> dict:
    if not os.path.exists(MANIFEST_PATH):
        return empty_manifest()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("topics", {})
    return data


def save(manifest: dict, *, with_backup: bool = True) -> None:
    ensure_dir(STATE_DIR)
    if with_backup and os.path.exists(MANIFEST_PATH):
        backup_paths([MANIFEST_PATH], "manifest")
    manifest["updated_at"] = _now_iso()
    tmp = MANIFEST_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    os.replace(tmp, MANIFEST_PATH)


def topic_entry(manifest: dict, topic: str) -> dict:
    return manifest["topics"].setdefault(
        topic,
        {"mapped_question_ids": [], "versions": []},
    )


def next_version_number(topic_obj: dict) -> int:
    if not topic_obj["versions"]:
        return 1
    return max(v["version"] for v in topic_obj["versions"]) + 1
