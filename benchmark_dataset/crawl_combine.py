"""Crawler kết hợp 3 chiến lược parse trang chi tiết.

Trên thuvienphapluat.vn, layout trang Q&A có 3 dạng phổ biến, script thử
lần lượt từ specific tới generic:

- Strategy B: trong `<section class="tvpl-detail-prose" id="news-content">`,
  với mỗi `<h2>` chỉ đọc các `<p>` liên tiếp tới `<h2>` kế tiếp.
- Strategy A: tìm tất cả `<h2>` trên toàn document, đọc mọi sibling không
  rỗng (p/ul/ol/div/blockquote/...) giữa hai `<h2>` làm câu trả lời; bỏ
  qua các `<h2>` thuộc block phụ ("Bài viết mới nhất", ...); lọc bỏ caption
  ảnh nằm dưới <p><img></p>.
- Strategy C: trang dạng "1 bài = 1 Q&A". Câu hỏi lấy từ
  `<div class="tvpl-article-sapo ...">`, câu trả lời là toàn bộ `<p>` trong
  `<section class="tvpl-detail-prose" id="news-content">`.

Với mỗi article: thử B -> A -> C; chiến lược nào trả về >= 1 cặp Q&A
thì dùng kết quả đó.

Mode ghi dataset:
- Output dir + tên file tự derive theo slug cuối của `--category-url`
  (vd. `dang-ky-ket-hon` -> `dang_ky_ket_hon/qa_dang_ky_ket_hon.{csv,json}`).
- Merge/append, dedup theo `question` đã chuẩn hoá (whitespace + lowercase).
- **Save sau mỗi article có Q&A mới** (incremental), an toàn nếu bị Ctrl+C.

Cách dùng:
    # Crawl chuyên mục mặc định (điều kiện kết hôn) page 1..10
    python crawl_combine.py

    # Chuyên mục khác + khoảng trang tuỳ ý
    python crawl_combine.py \\
        --category-url https://thuvienphapluat.vn/hoi-dap-phap-luat/chu-de/dang-ky-ket-hon \\
        --start 1 --end 20 --sleep 2.0

    # Khi gặp CloudFlare challenge (trang phân trang trả 403 + "Just a
    # moment..."), copy cookie từ browser rồi truyền vào:
    python crawl_combine.py --start 2 --end 5 \\
        --cookies "cf_clearance=...; __cf_bm=..."

Lấy cookie khi gặp CloudFlare challenge:
    1) Mở browser truy cập URL `?page=2` của chuyên mục.
    2) F12 -> Network -> Reload -> click request đầu tiên ->
       Request Headers -> copy nguyên dòng `Cookie:`.
    3) Truyền vào `--cookies "..."`. Cookie thường sống ~30 phút.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from crawl import (
    BASE_URL,
    BENCHMARK_COLUMNS,
    make_empty_record,
    save_dataset,
)


def _ensure_ascii_cacert() -> None:
    """Workaround cho curl_cffi trên Windows khi đường dẫn project chứa
    ký tự non-ASCII (vd. "luật" -> chữ "ậ" không encode được bằng cp1252).

    curl_cffi gọi `certifi.where()` rồi encode path để truyền cho libcurl;
    nếu path có Unicode thì `value.encode("cp1252")` ném UnicodeEncodeError.
    Cách an toàn: copy cacert.pem sang %TEMP% (ASCII) và set
    CURL_CA_BUNDLE / SSL_CERT_FILE trước khi curl_cffi đụng tới.
    """
    try:
        import certifi  # type: ignore
    except ImportError:
        return

    src = certifi.where()
    try:
        src.encode("ascii")
        return  # path đã ASCII, không cần làm gì
    except UnicodeEncodeError:
        pass

    dst = Path(tempfile.gettempdir()) / "curl_cffi_cacert.pem"
    if not dst.exists() or dst.stat().st_size != Path(src).stat().st_size:
        shutil.copy2(src, dst)
    dst_str = str(dst)
    os.environ.setdefault("CURL_CA_BUNDLE", dst_str)
    os.environ.setdefault("SSL_CERT_FILE", dst_str)


_ensure_ascii_cacert()

# thuvienphapluat.vn dùng anti-bot dựa trên TLS fingerprint (JA3/JA4) cho
# các URL phân trang. requests dùng OpenSSL của Python -> bị 403; cần
# client mạo nhận handshake của Chrome thật.
try:
    from curl_cffi import requests as http_client  # type: ignore

    _IMPERSONATE = "chrome124"
    _USING_CURL_CFFI = True
except ImportError:  # pragma: no cover
    import requests as http_client  # type: ignore

    _IMPERSONATE = None
    _USING_CURL_CFFI = False

DEFAULT_CATEGORY_URL = (
    "https://thuvienphapluat.vn/hoi-dap-phap-luat/chu-de/dieu-kien-ket-hon"
)

SCRIPT_DIR = Path(__file__).parent

# Các id/class của <h2> không phải là câu hỏi (block phụ trong layout cũ).
IGNORE_H2_IDENTIFIERS = ["tvpl-latest-posts-heading", "tvpl-detail-rail-most"]


def derive_paths(category_url: str) -> tuple[str, Path, Path, Path]:
    """Từ URL chuyên mục, derive (slug, data_dir, csv_path, json_path).

    Vd: '.../chu-de/dang-ky-ket-hon' -> slug='dang-ky-ket-hon',
        folder='dang_ky_ket_hon',
        files='qa_dang_ky_ket_hon.{csv,json}'.
    """
    raw_slug = urlparse(category_url).path.rstrip("/").rsplit("/", 1)[-1]
    if not raw_slug:
        raise ValueError(f"Không lấy được slug từ URL: {category_url}")
    folder_name = raw_slug.replace("-", "_")
    data_dir = SCRIPT_DIR / folder_name
    csv_path = data_dir / f"qa_{folder_name}.csv"
    json_path = data_dir / f"qa_{folder_name}.json"
    return raw_slug, data_dir, csv_path, json_path


# ---------------------------------------------------------------------------
# HTTP session giả lập browser (Chrome 124 trên Windows).
# - Nếu có `curl_cffi`, session sẽ impersonate TLS handshake của Chrome
#   để qua được bộ lọc fingerprint của server (yêu cầu cho URL ?page=N).
# - Headers + Sec-Fetch-* gửi kèm để giống browser thật ở tầng HTTP.
# - warm_up_session() truy cập trang chủ + chuyên mục page 1 trước để
#   server set cookie session.
# ---------------------------------------------------------------------------
if _USING_CURL_CFFI:
    SESSION = http_client.Session(impersonate=_IMPERSONATE)  # type: ignore[call-arg]
else:
    SESSION = http_client.Session()

SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Ch-Ua": '"Chromium";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
    }
)


def fetch_html(url: str, referer: str | None = None, max_retries: int = 3) -> bytes | None:
    """GET `url` qua session, có retry với exponential backoff."""
    headers: dict[str, str] = {}
    if referer:
        headers["Referer"] = referer
        headers["Sec-Fetch-Site"] = "same-origin"

    for attempt in range(1, max_retries + 1):
        try:
            response = SESSION.get(url, headers=headers, timeout=25)
        except Exception as e:
            print(f"  Lỗi network (lần {attempt}/{max_retries}): {e}")
            time.sleep(2 * attempt)
            continue

        if response.status_code == 200:
            return response.content

        is_cf = (
            response.headers.get("cf-mitigated") == "challenge"
            or looks_like_cloudflare_challenge(response.content)
        )
        cf_note = " [CloudFlare challenge]" if is_cf else ""
        print(
            f"  HTTP {response.status_code} (lần {attempt}/{max_retries}){cf_note} -> {url}"
        )
        if is_cf and attempt == max_retries:
            print(
                "  -> CloudFlare yêu cầu JS challenge. Copy cookie `cf_clearance` "
                "từ browser và chạy lại với --cookies \"cf_clearance=...; __cf_bm=...\""
            )
        # 403/429 thường do anti-bot; chờ lâu hơn rồi thử lại.
        if response.status_code in (403, 429, 503):
            time.sleep(3 * attempt)
        else:
            time.sleep(1 * attempt)

    return None


def fetch_soup(url: str, referer: str | None = None) -> BeautifulSoup | None:
    content = fetch_html(url, referer=referer)
    if content is None:
        return None
    return BeautifulSoup(content, "html.parser")


def warm_up_session(category_url: str) -> None:
    """Truy cập trang chủ + chuyên mục page 1 để server set cookie session.

    Sau bước này, các request tới page 2+ sẽ được gửi kèm cookie và đi qua
    được vòng kiểm tra anti-bot của server.
    """
    print("Warm-up: truy cập trang chủ + chuyên mục page 1 để seed cookie...")
    fetch_html(BASE_URL + "/")
    fetch_html(category_url, referer=BASE_URL + "/")


# ---------------------------------------------------------------------------
# Strategy B: section.tvpl-detail-prose + h2/p only.
# ---------------------------------------------------------------------------
def extract_qa_strategy_b(soup: BeautifulSoup) -> list[dict]:
    section = soup.find("section", class_="tvpl-detail-prose")
    if section is None:
        section = soup.find(id="news-content")
    if section is None:
        return []

    qa_pairs: list[dict] = []
    for h2 in section.find_all("h2", recursive=True):
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
# Strategy A: whole-document h2 + complex siblings (giống crawl.py gốc).
# ---------------------------------------------------------------------------
def _is_image_caption(sibling) -> bool:
    """True nếu sibling là <p> đang đóng vai trò caption cho <img> phía trên."""
    if sibling.name != "p":
        return False
    prev_tag = sibling.find_previous_sibling(["p", "div", "blockquote", "h2", "ul", "ol"])
    if not (prev_tag and prev_tag.name == "p" and prev_tag.find("img")):
        return False
    text = sibling.get_text(separator=" ", strip=True)
    return bool(
        sibling.find("em")
        or "center" in sibling.get("style", "")
        or "(Hình" in text
    )


def extract_qa_strategy_a(soup: BeautifulSoup) -> list[dict]:
    qa_pairs: list[dict] = []
    for h2 in soup.find_all("h2"):
        h2_id = h2.get("id", "")
        h2_class = h2.get("class", []) or []
        if h2_id in IGNORE_H2_IDENTIFIERS or any(c in IGNORE_H2_IDENTIFIERS for c in h2_class):
            continue

        question = h2.get_text(separator=" ", strip=True)
        if not question:
            continue

        answer_parts: list[str] = []
        for sibling in h2.find_next_siblings():
            if sibling.name == "h2":
                break
            text = sibling.get_text(separator=" ", strip=True)
            if not text:
                continue
            if _is_image_caption(sibling):
                continue
            answer_parts.append(text)

        answer = "\n\n".join(answer_parts)
        if answer:
            qa_pairs.append(make_empty_record(question=question, ground_truth=answer))

    return qa_pairs


# ---------------------------------------------------------------------------
# Strategy C: 1 article = 1 Q&A.
#   - Question: text của <div class="tvpl-article-sapo ...">.
#   - Answer:   tất cả <p> trong <section class="tvpl-detail-prose">.
# Dùng cho các bài viết "tin pháp luật" (không có h2 chia mục), nội dung
# nằm trọn trong section.tvpl-detail-prose.
# ---------------------------------------------------------------------------
def extract_qa_strategy_c(soup: BeautifulSoup) -> list[dict]:
    sapo = soup.find("div", class_="tvpl-article-sapo")
    if sapo is None:
        return []

    question = sapo.get_text(separator=" ", strip=True)
    if not question:
        return []

    section = soup.find("section", class_="tvpl-detail-prose")
    if section is None:
        section = soup.find(id="news-content")
    if section is None:
        return []

    answer_parts: list[str] = []
    for p in section.find_all("p"):
        text = p.get_text(separator=" ", strip=True)
        if not text:
            continue
        answer_parts.append(text)

    answer = "\n\n".join(answer_parts)
    if not answer:
        return []

    return [make_empty_record(question=question, ground_truth=answer)]


# ---------------------------------------------------------------------------
# Orchestrator.
# ---------------------------------------------------------------------------
def extract_qa_from_article(article_url: str, referer: str | None = None) -> tuple[list[dict], str]:
    """Trả về (list Q&A, tên strategy đã dùng)."""
    soup = fetch_soup(article_url, referer=referer)
    if soup is None:
        return [], "fetch_failed"

    qa_b = extract_qa_strategy_b(soup)
    if qa_b:
        return qa_b, "B"

    qa_a = extract_qa_strategy_a(soup)
    if qa_a:
        return qa_a, "A"

    qa_c = extract_qa_strategy_c(soup)
    if qa_c:
        return qa_c, "C"

    return [], "empty"


# ---------------------------------------------------------------------------
# Pagination: bám theo link "trang kế tiếp" thật trong HTML.
# Tránh đoán URL template (?page=N, /trang-N, /page-N.html, ...) vì
# thuvienphapluat.vn trả 403 cho mọi URL pagination không đúng convention.
# ---------------------------------------------------------------------------
def find_next_page_link(
    soup: BeautifulSoup, current_url: str, current_page: int
) -> str | None:
    """Tìm URL của trang kế tiếp từ HTML trang hiện tại.

    Thử nhiều cách phổ biến để hoạt động bất kể site dùng convention gì:
    1) `<a rel="next">`
    2) `<a>` có class chứa "next" trong khối pagination
    3) `<a>` mà visible text bằng số trang kế tiếp
    """
    next_page_num = current_page + 1

    def _absolutize(href: str) -> str:
        return href if href.startswith("http") else urljoin(current_url, href)

    for a in soup.find_all("a", href=True):
        rels = a.get("rel") or []
        if "next" in rels:
            return _absolutize(a["href"])

    for a in soup.find_all("a", href=True):
        cls = " ".join(a.get("class") or []).lower()
        if "next" in cls:
            return _absolutize(a["href"])

    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True).strip()
        if text == str(next_page_num):
            return _absolutize(a["href"])

    return None


def _get_article_links_from_soup(soup: BeautifulSoup) -> list[str]:
    """Trích link bài viết từ HTML của một trang chuyên mục đã fetch."""
    links: list[str] = []
    for article in soup.find_all("article", class_="tvpl-field-row"):
        a_tag = article.find("a", class_="tvpl-field-row-title")
        if a_tag and "href" in a_tag.attrs:
            href = a_tag["href"]
            full_link = href if href.startswith("http") else BASE_URL + href
            links.append(full_link)
    return links


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
    seen = {_normalize_question(r.get("question", "")) for r in existing}
    merged = list(existing)
    added = 0
    for rec in new_records:
        key = _normalize_question(rec.get("question", ""))
        if not key or key in seen:
            continue
        seen.add(key)
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
    parser.add_argument(
        "--category-url",
        type=str,
        default=DEFAULT_CATEGORY_URL,
        help=(
            "URL chuyên mục cần crawl. Output dir + tên file sẽ được derive từ "
            "slug cuối của URL (vd. dang-ky-ket-hon -> dang_ky_ket_hon/qa_dang_ky_ket_hon.*)."
        ),
    )
    parser.add_argument("--start", type=int, default=1, help="Trang bắt đầu (mặc định 1)")
    parser.add_argument("--end", type=int, default=10, help="Trang kết thúc, đã tính cả (mặc định 10)")
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.5,
        help="Thời gian nghỉ giữa các request đến trang chi tiết (giây)",
    )
    parser.add_argument(
        "--cookies",
        type=str,
        default=None,
        help=(
            'Chuỗi cookie copy từ browser (vd: "cf_clearance=XXX; __cf_bm=YYY"). '
            "Cần khi CloudFlare bật JS challenge trên các URL phân trang."
        ),
    )
    return parser.parse_args()


def apply_cookie_string(session, cookie_string: str) -> int:
    """Parse chuỗi 'name1=val1; name2=val2' và set vào session.cookies."""
    n = 0
    for pair in cookie_string.split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        name, value = pair.split("=", 1)
        name, value = name.strip(), value.strip()
        if not name:
            continue
        try:
            session.cookies.set(name, value, domain=".thuvienphapluat.vn")
        except TypeError:
            # Một số phiên bản .cookies.set không nhận `domain=` kwarg.
            session.cookies.set(name, value)
        n += 1
    return n


def looks_like_cloudflare_challenge(content: bytes | None) -> bool:
    if not content:
        return False
    head = content[:2048]
    return b"Just a moment" in head or b"cf-mitigated" in head or b"challenges.cloudflare.com" in head


def main() -> None:
    args = parse_args()

    if _USING_CURL_CFFI:
        print(f"HTTP client: curl_cffi (impersonate={_IMPERSONATE})")
    else:
        print(
            "HTTP client: requests (KHÔNG có TLS impersonation).\n"
            "  -> Khuyến nghị: pip install curl_cffi để qua được anti-bot "
            "JA3/JA4 của thuvienphapluat.vn."
        )

    if args.cookies:
        n = apply_cookie_string(SESSION, args.cookies)
        print(f"Đã nạp {n} cookie từ flag --cookies vào session.")
    else:
        print(
            "Không có --cookies; nếu trang phân trang trả 403 với CloudFlare "
            "challenge, hãy copy cookie từ browser và chạy lại."
        )

    category_url = args.category_url
    slug, data_dir, csv_path, json_path = derive_paths(category_url)
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"Crawl chuyên mục: {category_url}")
    print(f"Output: {csv_path}")
    print(f"        {json_path}")

    existing = load_existing_records(json_path)
    print(f"Đã có sẵn {len(existing)} bản ghi trong dataset.")

    warm_up_session(category_url)

    # In-memory state. Sau mỗi article có Q&A mới sẽ flush save_dataset()
    # nên file luôn up-to-date, không bị mất nếu bị Ctrl+C giữa chừng.
    merged: list[dict] = list(existing)
    seen: set[str] = {_normalize_question(r.get("question", "")) for r in merged}
    initial_count = len(merged)

    strategy_counter = {"A": 0, "B": 0, "C": 0, "empty": 0, "fetch_failed": 0}
    raw_qa_seen = 0

    def _flush() -> None:
        save_dataset(merged, csv_path=str(csv_path), json_path=str(json_path))

    # Bám theo link "trang kế tiếp" trong HTML thay vì đoán URL template.
    current_url: str | None = category_url
    prev_page_url: str = BASE_URL + "/"
    current_page = 1

    try:
        while current_url is not None and current_page <= args.end:
            print(f"\n=== Trang {current_page}: {current_url} ===")
            page_soup = fetch_soup(current_url, referer=prev_page_url)
            if page_soup is None:
                print(f"-> Không tải được trang {current_page}, dừng.")
                break

            article_links = _get_article_links_from_soup(page_soup)
            print(f"  -> Tìm thấy {len(article_links)} bài viết.")

            if current_page >= args.start:
                for idx, link in enumerate(article_links):
                    qa_pairs, strategy = extract_qa_from_article(link, referer=current_url)
                    strategy_counter[strategy] = strategy_counter.get(strategy, 0) + 1
                    raw_qa_seen += len(qa_pairs)

                    added_this = 0
                    for rec in qa_pairs:
                        key = _normalize_question(rec.get("question", ""))
                        if not key or key in seen:
                            continue
                        seen.add(key)
                        full = {col: "" for col in BENCHMARK_COLUMNS}
                        full.update(rec)
                        merged.append(full)
                        added_this += 1

                    if added_this:
                        _flush()

                    print(
                        f"  [{idx + 1}/{len(article_links)}] strategy={strategy} "
                        f"qa={len(qa_pairs)} added={added_this} total={len(merged)}  {link}"
                    )
                    time.sleep(args.sleep)
            else:
                print(f"  (Bỏ qua trang {current_page}, chưa tới --start={args.start})")

            if current_page >= args.end:
                break

            next_url = find_next_page_link(page_soup, current_url, current_page)
            if not next_url:
                print(f"-> Không tìm thấy link trang kế tiếp ở page {current_page}, dừng.")
                break
            if next_url == current_url:
                print(f"-> Link trang kế tiếp trùng trang hiện tại ({next_url}), dừng.")
                break

            prev_page_url = current_url
            current_url = next_url
            current_page += 1
    except KeyboardInterrupt:
        print("\n[Ctrl+C] Đang lưu dataset trước khi thoát...")
    finally:
        _flush()

    print("\n--- Thống kê strategy ---")
    for k, v in strategy_counter.items():
        print(f"  {k}: {v} bài viết")

    print(
        f"\nKết thúc. Q&A thô: {raw_qa_seen}. "
        f"Bổ sung {len(merged) - initial_count} bản ghi mới "
        f"(dataset từ {initial_count} -> {len(merged)} bản ghi)."
    )


if __name__ == "__main__":
    main()
