import re
import json
from docx import Document
import os

def read_docx(file_path):
    doc = Document(file_path)
    lines = []
    for para in doc.paragraphs:
        lines.append(para.text)
    return lines

def convert_law_to_jsonl(input_file_path, output_file_path):
    lines = read_docx(input_file_path)
    
    results = []
    
    # Biến lưu trạng thái hiện tại
    dieu_num = None
    dieu_title = ""
    khoan_num = None
    diem_num = None
    
    # Buffer lưu trữ nội dung text thuộc về ID hiện tại
    buffer = []
    
    # Các pattern Regex để bắt cấu trúc luật
    # VD: "Điều 1. Phạm vi điều chỉnh"
    re_dieu = re.compile(r'^Điều\s+(\d+)\.\s+(.*)', re.IGNORECASE)
    # VD: "1. Hôn nhân tự nguyện..."
    re_khoan = re.compile(r'^(\d+)\.\s+(.*)')
    # VD: "a) Kết hôn giả tạo..." (Lưu ý bao gồm cả ký tự 'đ' trong tiếng Việt)
    re_diem = re.compile(r'^([a-zđ])\)\s+(.*)', re.IGNORECASE)
    
    # Pattern để dọn dẹp các thẻ nếu bạn copy trực tiếp từ màn hình chat
    re_source = re.compile(r'^\\s*') 
    # Bỏ qua các dòng tiêu đề Chương, Mục
    re_ignore = re.compile(r'^(Chương|Mục)\s+', re.IGNORECASE)

    def flush():
        """Hàm này dùng để đóng gói buffer hiện tại thành 1 block JSON và đẩy vào kết quả"""
        if not dieu_num or not buffer:
            return

        # Tạo ID theo format: Luat_HNGD_2014_Dieu_X_Khoan_Y_Diem_Z
        doc_id = f"Luat_HNGD_2014_Dieu_{dieu_num}"
        if khoan_num:
            doc_id += f"_Khoan_{khoan_num}"
        if diem_num:
            doc_id += f"_Diem_{diem_num}"

        # Gom text lại và dọn dẹp các khoảng trắng thừa
        text_content = " ".join(buffer).strip()
        text_content = re.sub(r'\s+', ' ', text_content)

        # Gắn tên của Điều lên đầu để giữ context (nếu câu đó chưa bắt đầu bằng tên Điều)
        if dieu_title and not text_content.startswith(dieu_title):
            text_content = f"{dieu_title}: {text_content}"

        results.append({
            "id": doc_id,
            "text": text_content
        })
        buffer.clear()

    for line in lines:
        # Xóa tag nếu có và strip khoảng trắng
        clean_line = re_source.sub('', line).strip()
        
        if not clean_line:
            continue
            
        if re_ignore.match(clean_line):
            continue

        # 1. Kiểm tra xem có phải là thẻ Điều không
        match_dieu = re_dieu.match(clean_line)
        if match_dieu:
            flush() # Lưu lại block cũ trước khi sang Điều mới
            dieu_num = match_dieu.group(1)
            dieu_title = match_dieu.group(2).strip()
            khoan_num = None
            diem_num = None
            continue

        # 2. Kiểm tra xem có phải là thẻ Khoản không
        match_khoan = re_khoan.match(clean_line)
        if match_khoan:
            flush() # Lưu lại block cũ
            khoan_num = match_khoan.group(1)
            diem_num = None
            buffer.append(match_khoan.group(2).strip())
            continue

        # 3. Kiểm tra xem có phải là thẻ Điểm không
        match_diem = re_diem.match(clean_line)
        if match_diem:
            flush() # Lưu lại block cũ
            diem_num = match_diem.group(1).lower()
            buffer.append(match_diem.group(2).strip())
            continue

        # 4. Nếu không phải Điều/Khoản/Điểm, nó là phần chữ nối tiếp của mục hiện tại
        if dieu_num: # Chỉ bắt đầu hứng text khi đã đi qua "Điều 1" (loại bỏ header tự động)
            buffer.append(clean_line)

    # Lưu lại block cuối cùng sau khi hết file
    flush()

    # Ghi ra file JSONL
    with open(output_file_path, 'w', encoding='utf-8') as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    print(f"Xử lý thành công! Đã lưu {len(results)} chunks vào file {output_file_path}")

# Hướng dẫn chạy
# input.txt là file chứa text bạn đã cung cấp ở trên
input_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '52_2014_QH13_238640.docx')
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output.jsonl')

convert_law_to_jsonl(input_path, output_path)