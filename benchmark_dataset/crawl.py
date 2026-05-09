import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# Base URL của trang web
BASE_URL = "https://thuvienphapluat.vn"

def get_article_links(category_url):
    """
    Bước 1: Lấy danh sách các đường link bài viết từ trang chủ đề.
    """
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
    # Tìm tất cả các thẻ article chứa danh sách bài viết
    articles = soup.find_all('article', class_='tvpl-field-row')
    
    for article in articles:
        # Tìm thẻ a chứa link và tiêu đề
        a_tag = article.find('a', class_='tvpl-field-row-title')
        if a_tag and 'href' in a_tag.attrs:
            full_link = BASE_URL + a_tag['href']
            links.append(full_link)
            
    print(f"-> Đã tìm thấy {len(links)} bài viết.")
    return links

def extract_qa_from_article(article_url):
    """
    Bước 2: Truy cập vào từng bài viết và bóc tách Câu hỏi / Câu trả lời.
    """
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
    
    # Giả định toàn bộ nội dung nằm trong thẻ section hoặc div chính
    # Ta sẽ tìm tất cả các thẻ h2 (chứa câu hỏi)
    h2_tags = soup.find_all('h2')
    
    for h2 in h2_tags:
        # Lấy text câu hỏi, loại bỏ khoảng trắng thừa
        question = h2.get_text(separator=' ', strip=True)
        if not question:
            continue
            
        answer_parts = []
        
        # Duyệt qua các thẻ anh em (siblings) nằm sau thẻ h2 này
        for sibling in h2.find_next_siblings():
            # Nếu gặp thẻ h2 tiếp theo -> Đã hết câu trả lời cho câu hỏi hiện tại
            if sibling.name == 'h2':
                break
                
            # Lấy nội dung text của các thẻ p, blockquote...
            # Dùng separator=' ' để các từ trong các thẻ con (như strong, a) không bị dính vào nhau
            text = sibling.get_text(separator=' ', strip=True)
            if text:
                answer_parts.append(text)
                
        # Gộp các đoạn text lại thành 1 câu trả lời hoàn chỉnh
        answer = '\n\n'.join(answer_parts)
        
        # Chỉ lưu nếu trích xuất được cả câu hỏi và câu trả lời
        if answer:
            qa_pairs.append({
                'question': question,
                'ground_truth': answer, # Đặt tên ground_truth để tiện dùng cho RAGAs sau này
                'source_url': article_url
            })
            
    return qa_pairs

def main():
    # URL danh sách chủ đề bạn muốn crawl
    category_url = "https://thuvienphapluat.vn/hoi-dap-phap-luat/chu-de/dieu-kien-ket-hon"
    
    # Bước 1
    article_links = get_article_links(category_url)
    
    all_qa_data = []
    
    # Bước 2
    for idx, link in enumerate(article_links):
        print(f"Đang crawl bài {idx + 1}/{len(article_links)}: {link}")
        qa_pairs = extract_qa_from_article(link)
        all_qa_data.extend(qa_pairs)
        
        # Nghỉ 1-2 giây giữa các request để tránh bị chặn (Rate Limit)
        time.sleep(2)
        
    # Bước 3: Lưu thành DataFrame và xuất ra file
    if all_qa_data:
        df = pd.DataFrame(all_qa_data)
        
        # Lưu ra CSV (dùng utf-8-sig để Excel đọc tiếng Việt không bị lỗi font)
        csv_filename = "qa_hon_nhan_gia_dinh.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        
        # Lưu ra JSON (format phổ biến khi feed vào LLMs/RAG)
        json_filename = "qa_hon_nhan_gia_dinh.json"
        df.to_json(json_filename, orient='records', force_ascii=False, indent=4)
        
        print(f"\nThành công! Đã crawl được tổng cộng {len(all_qa_data)} cặp Q&A.")
        print(f"Dữ liệu đã được lưu vào '{csv_filename}' và '{json_filename}'.")
    else:
        print("\nKhông tìm thấy dữ liệu Q&A nào.")

if __name__ == "__main__":
    main()