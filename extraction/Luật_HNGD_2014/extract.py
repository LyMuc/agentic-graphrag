import re
import os
from docx import Document

def split_law_articles(file_path, output_dir="output_articles"):
    # Tạo thư mục đầu ra nếu chưa tồn tại
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Mở tài liệu Word (.docx)
    try:
        doc = Document(file_path)
    except Exception as e:
        print(f"Lỗi khi mở file: {e}")
        return

    articles = {}
    current_dieu = None
    
    # Regex để nhận diện dòng bắt đầu bằng "Điều X."
    # Ví dụ: "Điều 1.", "Điều 123.", "Điều 1a."
    dieu_pattern = re.compile(r'^Điều\s+(\d+[a-z]?)\.')

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
            
        # Kiểm tra xem dòng này có phải là tiêu đề Điều mới không
        match = dieu_pattern.match(text)
        if match:
            current_dieu = match.group(1) # Lấy số thứ tự X
            articles[current_dieu] = text
        else:
            # Nếu đã xác định được Điều hiện tại, cộng dồn nội dung vào
            if current_dieu:
                articles[current_dieu] += "\n" + text

    # Ghi từng điều ra file .txt
    for dieu_num, content in articles.items():
        file_name = f"Luat_HNGD_2014_Dieu_{dieu_num}.txt"
        file_path_out = os.path.join(output_dir, file_name)
        
        with open(file_path_out, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Đã tạo file: {file_name}")

    print(f"\nHoàn tất! Tất cả các điều luật đã được lưu tại thư mục: {output_dir}")

# --- Thực thi ---
if __name__ == "__main__":
    # Thay đổi đường dẫn này tới file .docx của bạn
    import os
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

    base_dir = os.path.dirname(os.path.abspath(__file__))
    FILE_PATH = os.path.join(base_dir, "52_2014_QH13_238640.docx")
    split_law_articles(FILE_PATH)