import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

BASE_URL = "https://thuvienphapluat.vn"

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
    
    # Danh sách các id hoặc class cần loại bỏ
    ignore_identifiers = ["tvpl-latest-posts-heading", "tvpl-detail-rail-most"]
    
    for h2 in h2_tags:
        # Lấy id và class của thẻ h2 để kiểm tra
        h2_id = h2.get('id', '')
        h2_class = h2.get('class', [])
        
        # Bỏ qua nếu h2 thuộc các khối "Bài viết mới nhất", "Đọc nhiều nhất"...
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
                
            # XỬ LÝ BỎ QUA CAPTION HÌNH ẢNH
            if sibling.name == 'p':
                # Tìm thẻ có nội dung (p, blockquote, div...) nằm ngay phía trước
                prev_tag = sibling.find_previous_sibling(['p', 'div', 'blockquote', 'h2', 'ul', 'ol'])
                
                # Nếu thẻ ngay trước đó là <p> và có chứa <img>
                if prev_tag and prev_tag.name == 'p' and prev_tag.find('img'):
                    # Caption thường có thẻ <em> (in nghiêng), có style="text-align: center;" 
                    # hoặc chứa chữ "(Hình..." đặc trưng.
                    if sibling.find('em') or 'center' in sibling.get('style', '') or '(Hình' in text:
                        continue # Bỏ qua không thêm dòng này vào answer_parts
            
            answer_parts.append(text)
            
        answer = '\n\n'.join(answer_parts)
        
        # Chỉ lưu dictionary gồm 2 key, không có source_url
        if answer:
            qa_pairs.append({
                'question': question,
                'ground_truth': answer
            })
            
    return qa_pairs

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
        df = pd.DataFrame(all_qa_data)
        
        csv_filename = "qa_hon_nhan_gia_dinh.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        
        json_filename = "qa_hon_nhan_gia_dinh.json"
        df.to_json(json_filename, orient='records', force_ascii=False, indent=4)
        
        print(f"\nThành công! Đã crawl được tổng cộng {len(all_qa_data)} cặp Q&A.")
    else:
        print("\nKhông tìm thấy dữ liệu Q&A nào.")

if __name__ == "__main__":
    main()