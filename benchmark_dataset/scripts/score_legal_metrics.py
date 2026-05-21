"""
Score legal citation metrics for benchmark test-version JSON files.

Metrics (per user rules):
- tong_so_can_cu_duoc_neu_ra / so_can_cu_con_hieu_luc: count distinct legal
  citations mentioned in chatbot_answer.
- legal_citation_accuracy: (# required citations matched in answer) / (total required).
- citation_prioritization_accuracy: 1 if context unions contain required sets, else 0.
- co_loi_hieu_luc: always 0.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

LAW_HINTS: dict[str, list[str]] = {
    "Luat_HNGD_2014": [
        r"luật\s+hôn\s+nhân",
        r"luật\s+hngd",
        r"luật\s+hôn\s+nhân\s+và\s+gia\s+đình",
    ],
    "BoLuat_DanSu_2015": [
        r"bộ\s+luật\s+dân\s+sự",
        r"blđs",
        r"bl\s*đs",
    ],
    "NghiDinh_126_2014_ND_CP": [
        r"nghị\s+định\s+126",
        r"nđ\s*126",
        r"126/2014",
    ],
    "NghiQuyet_01_2024_NQ_HDTP": [
        r"nghị\s+quyết\s+01/2024",
        r"nq-hđtp",
        r"nq\s*hđtp",
        r"01/2024/nq",
    ],
    "NghiDinh_282_2025_ND_CP": [
        r"nghị\s+định\s+282",
        r"282/2025",
    ],
    "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP": [
        r"thông\s+tư\s+liên\s+tịch",
        r"01/2016/tt",
    ],
}


def parse_legal_id(legal_id: str) -> dict:
    """Parse benchmark legal id into components."""
    parts = legal_id.split("_")
    out: dict = {"raw": legal_id, "law_key": "", "dieu": None, "khoan": None, "diem": None}

    if parts[0] == "Luat" and len(parts) >= 3:
        out["law_key"] = "_".join(parts[:3])  # Luat_HNGD_2014
        rest = parts[3:]
    elif parts[0] == "BoLuat" and len(parts) >= 3:
        out["law_key"] = "_".join(parts[:3])
        rest = parts[3:]
    elif parts[0] == "NghiDinh" and len(parts) >= 4:
        out["law_key"] = "_".join(parts[:4])
        rest = parts[4:]
    elif parts[0] == "NghiQuyet" and len(parts) >= 4:
        out["law_key"] = "_".join(parts[:4])
        rest = parts[4:]
    elif parts[0] == "ThongTuLienTich" and len(parts) >= 2:
        out["law_key"] = legal_id.split("_Dieu_")[0] if "_Dieu_" in legal_id else legal_id
        rest = legal_id.split("_Dieu_")[1].split("_") if "_Dieu_" in legal_id else []
        if "_Dieu_" in legal_id:
            rest = ["Dieu"] + rest
    else:
        out["law_key"] = parts[0]
        rest = parts[1:]

    i = 0
    while i < len(rest):
        if rest[i] == "Dieu" and i + 1 < len(rest):
            out["dieu"] = int(rest[i + 1])
            i += 2
        elif rest[i] == "Khoan" and i + 1 < len(rest):
            out["khoan"] = int(rest[i + 1])
            i += 2
        elif rest[i] == "Diem" and i + 1 < len(rest):
            out["diem"] = rest[i + 1].lower()
            i += 2
        else:
            i += 1
    return out


def _law_mentioned(answer: str, law_key: str) -> bool:
    hints = LAW_HINTS.get(law_key, [])
    if not hints:
        return True  # unknown law: rely on dieu only
    return any(re.search(p, answer, re.I) for p in hints)


def _dieu_mentioned(answer: str, dieu: int) -> bool:
    patterns = [
        rf"điều\s*{dieu}\b",
        rf"điều\s*{dieu}\s*[\.\,]",
    ]
    return any(re.search(p, answer, re.I) for p in patterns)


def _khoan_mentioned(answer: str, khoan: int, dieu: int | None) -> bool:
    patterns = [
        rf"khoản\s*{khoan}\b",
        rf"khoản\s*{khoan}\s*điều\s*{dieu}\b" if dieu else None,
        rf"^\s*{khoan}\.\s",  # line starts with "1. "
    ]
    for p in patterns:
        if p and re.search(p, answer, re.I | re.M):
            return True
    return False


def _diem_mentioned(answer: str, diem: str) -> bool:
    return bool(re.search(rf"\b{re.escape(diem)}\)", answer, re.I))


def id_matches_answer(legal_id: str, answer: str) -> bool:
    if not answer or not legal_id:
        return False
    answer_l = answer.lower()
    p = parse_legal_id(legal_id)
    if p["dieu"] is None:
        return False
    if not _dieu_mentioned(answer_l, p["dieu"]):
        return False
    if p["law_key"] and not _law_mentioned(answer_l, p["law_key"]):
        return False
    if p["khoan"] is not None:
        if not _khoan_mentioned(answer_l, p["khoan"], p["dieu"]):
            # "Khoản 1, 2, 3 Điều N" lists multiple khoans in one cite
            if not re.search(
                rf"khoản\s+[\d\s,dàvà\-]+điều\s*{p['dieu']}\b",
                answer_l,
                re.I,
            ):
                return False
    if p["diem"] is not None and not _diem_mentioned(answer_l, p["diem"]):
        return False
    return True


def _infer_law_near(text: str, start: int, end: int) -> str:
    """Prefer the legal instrument closest to the Điều mention."""
    near = (
        text[max(0, start - 100) : start] + text[end : min(len(text), end + 100)]
    ).lower()
    ordered = [
        ("NghiDinh_126_2014_ND_CP", LAW_HINTS["NghiDinh_126_2014_ND_CP"]),
        ("NghiDinh_282_2025_ND_CP", LAW_HINTS["NghiDinh_282_2025_ND_CP"]),
        ("NghiQuyet_01_2024_NQ_HDTP", LAW_HINTS["NghiQuyet_01_2024_NQ_HDTP"]),
        ("BoLuat_DanSu_2015", LAW_HINTS["BoLuat_DanSu_2015"]),
        ("ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP", LAW_HINTS["ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP"]),
        ("Luat_HNGD_2014", LAW_HINTS["Luat_HNGD_2014"]),
    ]
    for law_key, patterns in ordered:
        if any(re.search(p, near, re.I) for p in patterns):
            return law_key
    if re.search(r"luật\s+này", near, re.I):
        return "Luat_HNGD_2014"
    return "unknown"


LAW_PRIORITY: dict[str, int] = {
    "NghiDinh_126_2014_ND_CP": 5,
    "NghiDinh_282_2025_ND_CP": 5,
    "NghiQuyet_01_2024_NQ_HDTP": 5,
    "BoLuat_DanSu_2015": 4,
    "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP": 4,
    "Luat_HNGD_2014": 3,
    "unknown": 0,
}


def _is_cross_reference(text: str, start: int, end: int) -> bool:
    """Skip in-text cross-refs inside quoted clauses, not primary Căn cứ blocks."""
    prefix = text[max(0, start - 80) : start].lower()
    after = text[end : min(len(text), end + 60)].lower()
    if re.search(r"căn cứ|đồng thời,\s*dẫn chiếu", prefix, re.I):
        return False
    if re.search(r"trừ trường hợp|vi phạm quy định tại", prefix, re.I):
        return True
    if re.search(r"hướng dẫn\s+điều\s+\d+", prefix, re.I):
        return True
    if re.search(r"của luật này\b", after, re.I):
        return True
    return False


def count_citations_in_answer(answer: str) -> int:
    """
    Count distinct (law, điều) citations explicitly named in chatbot_answer.
    Matches manual scoring: each điều/khoản/văn bản đếm 1 lần (deduped by law+dieu).
    """
    if not answer:
        return 0
    text = answer
    lower = answer.lower()
    by_dieu: dict[int, str] = {}

    def add(dieu: int, start: int, end: int) -> None:
        if _is_cross_reference(text, start, end):
            return
        law = _infer_law_near(text, start, end)
        prev = by_dieu.get(dieu)
        if prev is None or LAW_PRIORITY.get(law, 0) > LAW_PRIORITY.get(prev, 0):
            by_dieu[dieu] = law

    for m in re.finditer(
        r"khoản\s+[\d\s,dàvà\-]+điều\s*(\d+)\b",
        lower,
        re.I,
    ):
        add(int(m.group(1)), m.start(), m.end())

    for m in re.finditer(r"khoản\s+(\d+)\s+điều\s*(\d+)\b", lower, re.I):
        add(int(m.group(2)), m.start(), m.end())

    for m in re.finditer(r"điều\s*(\d+)\b", lower, re.I):
        add(int(m.group(1)), m.start(), m.end())

    return len(by_dieu)


def union_context_ids(context_raw: str, field: str) -> set[str]:
    if not context_raw or not str(context_raw).strip():
        return set()
    try:
        chunks = json.loads(context_raw)
    except json.JSONDecodeError:
        return set()
    out: set[str] = set()
    for ch in chunks:
        raw = ch.get("raw_ids") or {}
        for x in raw.get(field) or []:
            out.add(x)
    return out


def required_ids(row: dict) -> list[str]:
    ids: list[str] = []
    for key in (
        "can_cu_phap_ly_chinh",
        "can_cu_phap_ly_bo_tro",
        "van_ban_huong_dan_sua_doi_bo_sung_thay_the",
    ):
        ids.extend(row.get(key) or [])
    return ids


def _category_prioritization_ratio(required: set[str], ctx_ids: set[str]) -> float:
    """Share of required IDs that appear in the matching context bucket."""
    if not required:
        return 1.0
    correct = len(required & ctx_ids)
    return correct / len(required)


def citation_prioritization_score(row: dict, context_raw: str) -> float:
    """
    CPA = average of three ratios (always /3):
    - can_cu_chinh coverage of can_cu_phap_ly_chinh
    - can_cu_bo_tro coverage of can_cu_phap_ly_bo_tro
    - can_cu_huong_dan coverage of van_ban_huong_dan_sua_doi_bo_sung_thay_the
    """
    chinh = set(row.get("can_cu_phap_ly_chinh") or [])
    bo_tro = set(row.get("can_cu_phap_ly_bo_tro") or [])
    huong_dan = set(row.get("van_ban_huong_dan_sua_doi_bo_sung_thay_the") or [])

    ctx_chinh = union_context_ids(context_raw, "can_cu_chinh")
    ctx_bo_tro = union_context_ids(context_raw, "can_cu_bo_tro")
    ctx_huong_dan = union_context_ids(context_raw, "can_cu_huong_dan")

    r_chinh = _category_prioritization_ratio(chinh, ctx_chinh)
    r_bo_tro = _category_prioritization_ratio(bo_tro, ctx_bo_tro)
    r_huong_dan = _category_prioritization_ratio(huong_dan, ctx_huong_dan)

    return round((r_chinh + r_bo_tro + r_huong_dan) / 3, 2)


def score_row(row: dict) -> dict:
    answer = str(row.get("chatbot_answer") or "")
    context_raw = str(row.get("context") or "")
    req = required_ids(row)

    tong = count_citations_in_answer(answer)

    correct = sum(1 for rid in req if id_matches_answer(rid, answer))
    total_req = len(req)
    lca = (correct / total_req) if total_req else 1.0
    lca = round(lca, 2)

    cpa = citation_prioritization_score(row, context_raw)

    return {
        "legal_citation_accuracy": lca,
        "so_can_cu_con_hieu_luc": tong,
        "tong_so_can_cu_duoc_neu_ra": tong,
        "citation_prioritization_accuracy": cpa,
        "co_loi_hieu_luc": 0.0,
    }


def score_file(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    summary = []
    for i, row in enumerate(data, 1):
        metrics = score_row(row)
        row.update(metrics)
        q = str(row.get("question", ""))[:60]
        summary.append((i, metrics, q))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python score_legal_metrics.py <json_path>")
        sys.exit(1)
    path = Path(sys.argv[1])
    summary = score_file(path)
    print(f"Scored {len(summary)} rows in {path}")
    for i, m, q in summary:
        print(
            f"  [{i:>2}] LCA={m['legal_citation_accuracy']:.2f} "
            f"tong={m['tong_so_can_cu_duoc_neu_ra']} "
            f"CPA={m['citation_prioritization_accuracy']:.2f} | {q}..."
        )


if __name__ == "__main__":
    main()
