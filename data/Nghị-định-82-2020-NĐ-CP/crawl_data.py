import fitz  # PyMuPDF
import re
from neo4j import GraphDatabase
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

class NghiDinhGraphBuilder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

        # Tiền tố ID theo yêu cầu
        self.prefix = "NghiDinh_82_2020_ND_CP"

        # Các thuộc tính chung cho mọi node
        self.common_props = {
            "loai_van_ban": "Nghị định",
            "ngay_ban_hanh": "15/07/2020",
            "ngay_co_hieu_luc": "01/09/2020",
            "ngay_het_hieu_luc": "--",
            "tinh_trang_hieu_luc": "Hết hiệu lực một phần",
            "cap_bac_phap_ly": 5
        }

    def close(self):
        self.driver.close()

    def parse_pdf_and_insert(self, pdf_path):
        # 1. Trích xuất text từ PDF
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"

        lines = full_text.split('\n')

        articles = []
        clauses = []
        points = []

        # Regex nhận diện
        chuong_pattern = re.compile(r'^Chương\s+([IVXLCDM]+)', re.IGNORECASE)
        dieu_pattern = re.compile(r'^Điều\s+(\d+[a-zA-Z]?)\.\s*(.*)')
        khoan_pattern = re.compile(r'^(\d+)\.\s+(.*)')
        diem_pattern = re.compile(r'^([a-zđ])\)\s+(.*)')

        in_target_range = False
        current_chuong = "Chưa xác định"
        current_dieu_id = None
        current_khoan_id = None

        active_entity = None

        # 2. Phân tích từng dòng
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Theo dõi Chương
            if chuong_match := chuong_pattern.match(line):
                current_chuong = chuong_match.group(1)
                continue

            # Bật/tắt cờ khi quét đến khoảng Điều 58 - Điều 63
            if dieu_match := dieu_pattern.match(line):
                dieu_num = dieu_match.group(1)
                if int(dieu_num) == 58:
                    in_target_range = True
                elif int(dieu_num) == 64:
                    in_target_range = False
                    break # Đã qua Điều 63, dừng phân tích

            if not in_target_range:
                continue

            # Xử lý khi nằm trong vùng Điều 58 -> 63
            if dieu_match := dieu_pattern.match(line):
                dieu_num = dieu_match.group(1)

                # Cách đặt tên ID theo yêu cầu: NghiDinh_82_2020_ND_CP_Diem_X
                current_dieu_id = f"{self.prefix}_Dieu_{dieu_num}"
                current_khoan_id = None

                art_dict = {
                    "id": current_dieu_id,
                    "chuong": current_chuong,
                    "dieu": dieu_num,
                    "noidung": line
                }
                articles.append(art_dict)
                active_entity = art_dict
                continue

            if khoan_match := khoan_pattern.match(line):
                khoan_num = khoan_match.group(1)
                current_khoan_id = f"{current_dieu_id}_Khoan_{khoan_num}"

                khoan_dict = {
                    "id": current_khoan_id,
                    "chuong": current_chuong,
                    "dieu": dieu_num, # Lấy từ điều hiện tại
                    "khoan": khoan_num,
                    "noidung": line,
                    "dieu_id": current_dieu_id
                }
                clauses.append(khoan_dict)
                active_entity = khoan_dict
                continue

            if diem_match := diem_pattern.match(line):
                diem_char = diem_match.group(1)
                diem_id = f"{current_khoan_id}_Diem_{diem_char}" if current_khoan_id else f"{current_dieu_id}_Diem_{diem_char}"

                diem_dict = {
                    "id": diem_id,
                    "chuong": current_chuong,
                    "dieu": dieu_num,
                    "khoan": khoan_num if current_khoan_id else "",
                    "diem": diem_char,
                    "noidung": line,
                    "khoan_id": current_khoan_id
                }
                points.append(diem_dict)
                active_entity = diem_dict
                continue

            # Cộng dồn nội dung nếu đoạn văn bản bị ngắt dòng trong PDF
            if active_entity is not None:
                active_entity["noidung"] += " " + line

        print(f"Trích xuất: {len(articles)} Điều, {len(clauses)} Khoản, {len(points)} Điểm.")

        # 3. Đẩy vào Neo4j bằng UNWIND + MERGE
        with self.driver.session() as session:
            session.execute_write(self._upsert_articles, articles, self.common_props)
            session.execute_write(self._upsert_clauses, clauses, self.common_props)
            session.execute_write(self._upsert_points, points, self.common_props)

        print("Đã hoàn tất Insert/Upsert vào Neo4j!")

    @staticmethod
    def _upsert_articles(tx, data, props):
        query = """
        UNWIND $data AS row
        MERGE (d:DieuLuat {id: row.id})
        SET d.chuong = row.chuong,
            d.dieu = row.dieu,
            d.noidung = row.noidung,
            d.loai_van_ban = $props.loai_van_ban,
            d.ngay_ban_hanh = $props.ngay_ban_hanh,
            d.ngay_co_hieu_luc = $props.ngay_co_hieu_luc,
            d.ngay_het_hieu_luc = $props.ngay_het_hieu_luc,
            d.tinh_trang_hieu_luc = $props.tinh_trang_hieu_luc,
            d.cap_bac_phap_ly = $props.cap_bac_phap_ly
        """
        tx.run(query, data=data, props=props)

    @staticmethod
    def _upsert_clauses(tx, data, props):
        query = """
        UNWIND $data AS row
        MERGE (k:DieuKhoanLuat {id: row.id})
        SET k.chuong = row.chuong,
            k.dieu = row.dieu,
            k.khoan = row.khoan,
            k.noidung = row.noidung,
            k.loai_van_ban = $props.loai_van_ban,
            k.ngay_ban_hanh = $props.ngay_ban_hanh,
            k.ngay_co_hieu_luc = $props.ngay_co_hieu_luc,
            k.ngay_het_hieu_luc = $props.ngay_het_hieu_luc,
            k.tinh_trang_hieu_luc = $props.tinh_trang_hieu_luc,
            k.cap_bac_phap_ly = $props.cap_bac_phap_ly
        WITH k, row
        MATCH (d:DieuLuat {id: row.dieu_id})
        MERGE (d)-[:CO_KHOAN]->(k)
        """
        tx.run(query, data=data, props=props)

    @staticmethod
    def _upsert_points(tx, data, props):
        query = """
        UNWIND $data AS row
        MERGE (p:DieuKhoanDiemLuat {id: row.id})
        SET p.chuong = row.chuong,
            p.dieu = row.dieu,
            p.khoan = row.khoan,
            p.diem = row.diem,
            p.noidung = row.noidung,
            p.loai_van_ban = $props.loai_van_ban,
            p.ngay_ban_hanh = $props.ngay_ban_hanh,
            p.ngay_co_hieu_luc = $props.ngay_co_hieu_luc,
            p.ngay_het_hieu_luc = $props.ngay_het_hieu_luc,
            p.tinh_trang_hieu_luc = $props.tinh_trang_hieu_luc,
            p.cap_bac_phap_ly = $props.cap_bac_phap_ly
        WITH p, row
        MATCH (k:DieuKhoanLuat {id: row.khoan_id})
        MERGE (k)-[:CO_DIEM]->(p)
        """
        tx.run(query, data=data, props=props)

if __name__ == "__main__":
    URI = NEO4J_URI
    USER = NEO4J_USERNAME
    PASSWORD = NEO4J_PASSWORD
    
    # Bạn truyền đường dẫn file PDF Nghị định vào đây
    base_dir = os.path.dirname(os.path.abspath(__file__))
    PDF_FILE_PATH = os.path.join(base_dir, "Nghị-định-82-2020-NĐ-CP.pdf")

    builder = NghiDinhGraphBuilder(URI, USER, PASSWORD)
    try:
        if os.path.exists(PDF_FILE_PATH):
            builder.parse_pdf_and_insert(PDF_FILE_PATH)
        else:
            print("Vui lòng tải file Nghi-định-82-2020-NĐ-CP.pdf vào thư mục này để chạy.")
    finally:
        builder.close()