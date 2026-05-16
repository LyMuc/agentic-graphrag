"""Crawler cho các trang phân trang (page 2 trở đi) của cùng chuyên mục.

Khác biệt so với `crawl.py`:
- Vẫn lấy link bài viết qua `<a class="tvpl-field-row-title">` ở trang danh
  sách (tái sử dụng `get_article_links` của crawl.py).
- Trong trang chi tiết, toàn bộ Q&A nằm trong
  `<section class="tvpl-detail-prose" id="news-content">`:
    * Mỗi câu hỏi là text của một thẻ `<h2>`.
    * Câu trả lời là tất cả các thẻ `<p>` liên tiếp nằm giữa thẻ `<h2>`
      đó và thẻ `<h2>` kế tiếp (hoặc đến hết `<section>` nếu là h2 cuối).
- Kết quả được merge (theo `question`, đã chuẩn hoá whitespace) vào hai
  file CSV/JSON dataset hiện có – không ghi đè bản ghi cũ.

Cách dùng:
    python crawl2.py                 # crawl page 2..10 (mặc định)
    python crawl2.py --start 2 --end 5
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from crawl import (
    BASE_URL,
    BENCHMARK_COLUMNS,
    get_article_links,
    make_empty_record,
    save_dataset,
)

CATEGORY_URL = "https://thuvienphapluat.vn/hoi-dap-phap-luat/chu-de/dieu-kien-ket-hon"

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "dieu_kien_ket_hon"
CSV_PATH = DATA_DIR / "qa_dieu_kien_ket_hon.csv"
JSON_PATH = DATA_DIR / "qa_dieu_kien_ket_hon.json"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}


# ---------------------------------------------------------------------------
# Parser cho format trang chi tiết mới.
# ---------------------------------------------------------------------------
def extract_qa_from_article(article_url: str) -> list[dict]:
    try:
        response = requests.get(article_url, headers=REQUEST_HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        print(f"  Lỗi khi truy cập bài viết {article_url}: {e}")
        return []

    section = soup.find("section", class_="tvpl-detail-prose")
    if section is None:
        section = soup.find(id="news-content")
    if section is None:
        return []

    qa_pairs: list[dict] = []
    h2_tags = section.find_all("h2", recursive=True)

    for h2 in h2_tags:
        question = h2.get_text(separator=" ", strip=True)
        if not question:
            continue

        answer_parts: list[str] = []
        for sibling in h2.find_next_siblings():
            if sibling.name == "h2":
                break
            if sibling.name != "p":
                continue
            text = sibling.get_text(separator=" ", strip=True)
            if not text:
                continue
            answer_parts.append(text)

        answer = "\n\n".join(answer_parts)
        if answer:
            qa_pairs.append(make_empty_record(question=question, ground_truth=answer))

    return qa_pairs


# ---------------------------------------------------------------------------
# Pagination.
# ---------------------------------------------------------------------------
def get_paginated_url(base_url: str, page: int) -> str:
    if page <= 1:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}page={page}"


# ---------------------------------------------------------------------------
# Merge với dataset hiện có.
# ---------------------------------------------------------------------------
def _normalize_question(q: str) -> str:
    return " ".join((q or "").split()).lower()


def load_existing_records(json_path: Path) -> list[dict]:
    if not json_path.exists():
        return []
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def merge_records(existing: list[dict], new_records: list[dict]) -> tuple[list[dict], int]:
    """Append `new_records` vào `existing`, bỏ qua trùng theo question."""
    seen = {_normalize_question(r.get("question", "")) for r in existing}
    merged = list(existing)
    added = 0
    for rec in new_records:
        key = _normalize_question(rec.get("question", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        # Đảm bảo đúng schema (có thể thiếu cột mới).
        full = {col: "" for col in BENCHMARK_COLUMNS}
        full.update(rec)
        merged.append(full)
        added += 1
    return merged, added


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=2, help="Trang bắt đầu (mặc định 2)")
    parser.add_argument("--end", type=int, default=10, help="Trang kết thúc, đã tính cả (mặc định 10)")
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.5,
        help="Thời gian nghỉ giữa các request đến trang chi tiết (giây)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    existing = load_existing_records(JSON_PATH)
    print(f"Đã có sẵn {len(existing)} bản ghi trong dataset.")

    all_new: list[dict] = []
    for page in range(args.start, args.end + 1):
        page_url = get_paginated_url(CATEGORY_URL, page)
        print(f"\n=== Trang {page}: {page_url} ===")
        article_links = get_article_links(page_url)
        if not article_links:
            print(f"-> Không còn bài viết, dừng phân trang ở page {page}.")
            break

        for idx, link in enumerate(article_links):
            print(f"  [{idx + 1}/{len(article_links)}] {link}")
            qa_pairs = extract_qa_from_article(link)
            print(f"     -> Trích xuất được {len(qa_pairs)} cặp Q&A")
            all_new.extend(qa_pairs)
            time.sleep(args.sleep)

    if not all_new:
        print("\nKhông tìm thấy dữ liệu Q&A mới nào.")
        return

    merged, added = merge_records(existing, all_new)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    save_dataset(merged, csv_path=str(CSV_PATH), json_path=str(JSON_PATH))

    print(
        f"\nThành công! Crawl được {len(all_new)} cặp Q&A thô, "
        f"bổ sung {added} bản ghi mới (sau khi loại trùng). "
        f"Tổng dataset hiện tại: {len(merged)} bản ghi."
    )


if __name__ == "__main__":
    main()
