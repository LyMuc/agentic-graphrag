import csv
import json
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://thuvienphapluat.vn"

# ---------------------------------------------------------------------------
# Schema (giữ cố định để mọi lần crawl đều sinh ra cùng bộ cột).
# Crawl chỉ điền `question` và `ground_truth`, các cột còn lại để trống
# (chuỗi rỗng) để người dùng tự điền sau khi annotate thủ công.
# ---------------------------------------------------------------------------
# Nhóm 1: Metadata pháp lý của mẫu Q&A (annotator điền tay).
ANNOTATION_COLUMNS = [
    "question",                                  # Câu hỏi của người dùng
    "ground_truth",                              # Câu trả lời tham chiếu
    "chatbot_answer",                            # Câu trả lời do chatbot sinh ra (để đối chiếu trực tiếp với ground_truth)
    "chu_de_phap_ly",                            # Chủ đề pháp lý (kết hôn, ly hôn, tài sản vợ chồng, ...)
    "loai_cau_hoi",                              # Loại câu hỏi: lý thuyết / tình huống thực tế
    "van_ban_phap_luat_lien_quan",               # Văn bản pháp luật liên quan
    "dieu_khoan_ap_dung",                        # Điều / khoản đúng cần áp dụng
    "tinh_trang_hieu_luc",                       # Tình trạng hiệu lực của văn bản pháp luật
    "can_cu_phap_ly_chinh",                      # Căn cứ pháp lý chính
    "can_cu_phap_ly_bo_tro",                     # Căn cứ pháp lý bổ trợ
    "van_ban_huong_dan_sua_doi_bo_sung_thay_the",# Văn bản hướng dẫn, sửa đổi, bổ sung hoặc thay thế (nếu có)
    "can_cu_khong_nen_ap_dung",                  # Căn cứ không nên áp dụng (nếu có)
    "quan_he_chong_cheo_mau_thuan",              # Quan hệ chồng chéo hoặc mâu thuẫn giữa các căn cứ (nếu có)
]

# Nhóm 2: Nhãn đánh giá hệ thống (do pipeline evaluation hoặc human điền).
# Mỗi cột chứa điểm/cờ cho từng mẫu Q&A; số tổng hợp toàn bộ dataset
# (mục tiêu > 85%, < 10%, ...) sẽ được tính khi aggregate.
EVALUATION_METRIC_COLUMNS = [
    "legal_citation_accuracy",          # Trích dẫn đúng điều luật hiện hành (mục tiêu > 85%)
    "legal_validity_accuracy",          # Căn cứ còn hiệu lực / phù hợp thời điểm (mục tiêu > 90%)
    "citation_prioritization_accuracy", # Xác định đúng căn cứ chính / bổ trợ / hướng dẫn / không nên áp dụng (mục tiêu > 85%)
    "invalid_citation_rate",            # Viện dẫn văn bản hết hiệu lực, bị thay thế, không liên quan (mục tiêu < 10%)
    "context_conflict_detection_rate",  # Phát hiện được context có căn cứ chồng chéo / mâu thuẫn (mục tiêu > 80%)
    "hallucination_rate",               # Tỷ lệ thông tin bịa / không có trong context
    "faithfulness",                     # Mức độ trung thành với context được truy xuất
    "context_recall",                   # Khả năng truy xuất đủ thông tin cần thiết để trả lời
    "answer_correctness",               # Mức độ đúng của câu trả lời so với ground_truth
]

BENCHMARK_COLUMNS = ANNOTATION_COLUMNS + EVALUATION_METRIC_COLUMNS


def make_empty_record(question: str = "", ground_truth: str = "") -> dict:
    """Tạo một mẫu dữ liệu benchmark với đủ tất cả các cột.

    Chỉ `question` và `ground_truth` được điền giá trị; các cột còn lại để
    chuỗi rỗng để annotator điền tay sau.
    """
    record = {col: "" for col in BENCHMARK_COLUMNS}
    record["question"] = question
    record["ground_truth"] = ground_truth
    return record


def get_article_links(category_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    print(f"Đang lấy danh sách bài viết từ: {category_url}")
    
    try:
        response = requests.get(category_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Lỗi khi truy cập trang danh sách: {e}")
        return []

    links = []
    articles = soup.find_all('article', class_='tvpl-field-row')
    
    for article in articles:
        a_tag = article.find('a', class_='tvpl-field-row-title')
        if a_tag and 'href' in a_tag.attrs:
            full_link = BASE_URL + a_tag['href']
            links.append(full_link)
            
    print(f"-> Đã tìm thấy {len(links)} bài viết.")
    return links

def extract_qa_from_article(article_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(article_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Lỗi khi truy cập bài viết {article_url}: {e}")
        return []

    qa_pairs = []
    h2_tags = soup.find_all('h2')
    
    ignore_identifiers = ["tvpl-latest-posts-heading", "tvpl-detail-rail-most"]
    
    for h2 in h2_tags:
        h2_id = h2.get('id', '')
        h2_class = h2.get('class', [])
        
        if h2_id in ignore_identifiers or any(c in ignore_identifiers for c in h2_class):
            continue
            
        question = h2.get_text(separator=' ', strip=True)
        if not question:
            continue
            
        answer_parts = []
        
        for sibling in h2.find_next_siblings():
            if sibling.name == 'h2':
                break
                
            text = sibling.get_text(separator=' ', strip=True)
            if not text:
                continue
                
            # Bỏ qua caption của ảnh: thẻ <p> in nghiêng/căn giữa nằm
            # ngay sau một <p> chứa <img>.
            if sibling.name == 'p':
                prev_tag = sibling.find_previous_sibling(['p', 'div', 'blockquote', 'h2', 'ul', 'ol'])
                
                if prev_tag and prev_tag.name == 'p' and prev_tag.find('img'):
                    if sibling.find('em') or 'center' in sibling.get('style', '') or '(Hình' in text:
                        continue
            
            answer_parts.append(text)
            
        answer = '\n\n'.join(answer_parts)
        
        if answer:
            qa_pairs.append(make_empty_record(question=question, ground_truth=answer))
            
    return qa_pairs


def _normalize_records(records):
    """Chuẩn hoá list[dict]: đảm bảo có đủ tất cả cột, đúng thứ tự, không None."""
    normalized = []
    for row in records:
        rec = {col: "" for col in BENCHMARK_COLUMNS}
        for col in BENCHMARK_COLUMNS:
            value = row.get(col, "") if isinstance(row, dict) else ""
            rec[col] = "" if value is None else value
        normalized.append(rec)
    return normalized


def save_dataset(records, csv_path: str, json_path: str):
    """Ghi dataset ra CSV + JSON, đảm bảo đúng thứ tự cột của schema."""
    normalized = _normalize_records(records)

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=BENCHMARK_COLUMNS)
        writer.writeheader()
        writer.writerows(normalized)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=4)


def main():
    category_url = "https://thuvienphapluat.vn/hoi-dap-phap-luat/chu-de/dieu-kien-ket-hon"
    article_links = get_article_links(category_url)
    all_qa_data = []
    
    for idx, link in enumerate(article_links):
        print(f"Đang crawl bài {idx + 1}/{len(article_links)}...")
        qa_pairs = extract_qa_from_article(link)
        all_qa_data.extend(qa_pairs)
        time.sleep(1.5)
        
    if all_qa_data:
        save_dataset(
            all_qa_data,
            csv_path="qa_dieu_kien_ket_hon.csv",
            json_path="qa_dieu_kien_ket_hon.json",
        )
        print(f"\nThành công! Đã crawl được tổng cộng {len(all_qa_data)} cặp Q&A.")
    else:
        print("\nKhông tìm thấy dữ liệu Q&A nào.")

if __name__ == "__main__":
    main()
