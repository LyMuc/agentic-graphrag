import re
from docx import Document
from neo4j import GraphDatabase

class LawGraphBuilder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        # Thông tin chung cho văn bản Luật Hộ tịch 2014
        self.base_id = "Luat_HoTich_2014"
        self.common_props = {
            "loai_van_ban": "Luật",
            "ngay_ban_hanh": "20/11/2014",
            "ngay_co_hieu_luc": "01/01/2016",
            "ngay_het_hieu_luc": "",
            "tinh_trang_hieu_luc": "Còn hiệu lực",
            "cap_bac_phap_ly": 2
        }

    def close(self):
        self.driver.close()

    def parse_and_insert(self, file_path):
        doc = Document(file_path)
        # Lấy danh sách các dòng văn bản không rỗng
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip() != ""]

        # Data containers
        law_info = {
            "id": self.base_id,
            "so_hieu": "60/2014/QH13",
            "ten_luat": "Luật Hộ tịch",
            "co_quan_ban_hanh": "Quốc hội"
        }
        articles = []
        clauses = []
        points = []

        # State tracking
        current_chuong = "Chưa xác định"
        current_dieu_num = ""
        current_dieu_id = ""
        current_khoan_num = ""
        current_khoan_id = ""
        active_entity = None

        # Regex Patterns
        chuong_pattern = re.compile(r'^CHƯƠNG\s+([IVXLCDM]+)', re.IGNORECASE)
        dieu_pattern = re.compile(r'^Điều\s+(\d+)\.\s*(.*)')
        khoan_pattern = re.compile(r'^(\d+)\.\s+(.*)')
        diem_pattern = re.compile(r'^([a-zđ])\)\s+(.*)')

        for line in lines:
            # 1. Nhận diện Chương
            if chuong_match := chuong_pattern.match(line):
                current_chuong = chuong_match.group(1)
                active_entity = None
                continue

            # 2. Nhận diện Điều
            if dieu_match := dieu_pattern.match(line):
                current_dieu_num = dieu_match.group(1)
                current_dieu_id = f"{self.base_id}_Dieu_{current_dieu_num}"
                
                # Reset Khoản khi sang Điều mới
                current_khoan_num = ""
                current_khoan_id = ""

                art_dict = {
                    "id": current_dieu_id,
                    "chuong": current_chuong,
                    "dieu": current_dieu_num,
                    "noidung": line,
                    "luat_id": self.base_id
                }
                articles.append(art_dict)
                active_entity = art_dict
                continue

            # 3. Nhận diện Khoản
            if khoan_match := khoan_pattern.match(line):
                current_khoan_num = khoan_match.group(1)
                current_khoan_id = f"{current_dieu_id}_Khoan_{current_khoan_num}"

                khoan_dict = {
                    "id": current_khoan_id,
                    "chuong": current_chuong,
                    "dieu": current_dieu_num,
                    "khoan": current_khoan_num,
                    "noidung": line,
                    "dieu_id": current_dieu_id
                }
                clauses.append(khoan_dict)
                active_entity = khoan_dict
                continue

            # 4. Nhận diện Điểm
            if diem_match := diem_pattern.match(line):
                diem_char = diem_match.group(1)
                # ID: ..._DIEU_X_KHOAN_Y_DIEM_Z
                diem_id = f"{current_khoan_id}_Diem_{diem_char}" if current_khoan_id else f"{current_dieu_id}_Diem_{diem_char}"

                diem_dict = {
                    "id": diem_id,
                    "chuong": current_chuong,
                    "dieu": current_dieu_num,
                    "khoan": current_khoan_num,
                    "diem": diem_char,
                    "noidung": line,
                    "khoan_id": current_khoan_id
                }
                points.append(diem_dict)
                active_entity = diem_dict
                continue

            # Nối dòng văn bản nếu là đoạn tiếp theo của Điều/Khoản/Điểm
            if active_entity is not None:
                active_entity["noidung"] += " " + line

        # Thực hiện chèn dữ liệu
        with self.driver.session() as session:
            session.execute_write(self._upsert_law_root, law_info, self.common_props)
            session.execute_write(self._upsert_articles, articles, self.common_props)
            session.execute_write(self._upsert_clauses, clauses, self.common_props)
            session.execute_write(self._upsert_points, points, self.common_props)

        print(f"Đã xử lý xong {len(articles)} Điều của Luật Hộ tịch.")

    @staticmethod
    def _upsert_law_root(tx, info, common):
        query = """
        MERGE (l:Luat {id: $info.id})
        SET l.so_hieu = $info.so_hieu,
            l.ten_luat = $info.ten_luat,
            l.co_quan_ban_hanh = $info.co_quan_ban_hanh,
            l.ngay_ban_hanh = $common.ngay_ban_hanh,
            l.loai_van_ban = $common.loai_van_ban,
            l.ngay_co_hieu_luc = $common.ngay_co_hieu_luc,
            l.tinh_trang_hieu_luc = $common.tinh_trang_hieu_luc,
            l.cap_bac_phap_ly = $common.cap_bac_phap_ly
        """
        tx.run(query, info=info, common=common)

    @staticmethod
    def _upsert_articles(tx, data, common):
        query = """
        UNWIND $data AS row
        MERGE (d:DieuLuat {id: row.id})
        SET d.chuong = row.chuong, d.dieu = row.dieu, d.noidung = row.noidung,
            d.ngay_ban_hanh = $common.ngay_ban_hanh, d.loai_van_ban = $common.loai_van_ban,
            d.ngay_co_hieu_luc = $common.ngay_co_hieu_luc, d.ngay_het_hieu_luc = $common.ngay_het_hieu_luc,
            d.tinh_trang_hieu_luc = $common.tinh_trang_hieu_luc, d.cap_bac_phap_ly = $common.cap_bac_phap_ly
        WITH d, row
        MATCH (l:Luat {id: row.luat_id})
        MERGE (l)-[:CO_DIEU]->(d)
        """
        tx.run(query, data=data, common=common)

    @staticmethod
    def _upsert_clauses(tx, data, common):
        query = """
        UNWIND $data AS row
        MERGE (k:DieuKhoanLuat {id: row.id})
        SET k.chuong = row.chuong, k.dieu = row.dieu, k.khoan = row.khoan, k.noidung = row.noidung,
            k.loai_van_ban = $common.loai_van_ban, k.ngay_co_hieu_luc = $common.ngay_co_hieu_luc,
            k.tinh_trang_hieu_luc = $common.tinh_trang_hieu_luc, k.cap_bac_phap_ly = $common.cap_bac_phap_ly,
            k.ngay_ban_hanh = $common.ngay_ban_hanh, k.ngay_het_hieu_luc = $common.ngay_het_hieu_luc
        WITH k, row
        MATCH (d:DieuLuat {id: row.dieu_id})
        MERGE (d)-[:CO_KHOAN]->(k)
        """
        tx.run(query, data=data, common=common)

    @staticmethod
    def _upsert_points(tx, data, common):
        query = """
        UNWIND $data AS row
        MERGE (p:DieuKhoanDiemLuat {id: row.id})
        SET p.chuong = row.chuong, p.dieu = row.dieu, p.khoan = row.khoan, p.diem = row.diem, p.noidung = row.noidung,
            p.ngay_ban_hanh = $common.ngay_ban_hanh, p.loai_van_ban = $common.loai_van_ban,
            p.ngay_co_hieu_luc = $common.ngay_co_hieu_luc, p.ngay_het_hieu_luc = $common.ngay_het_hieu_luc,
            p.tinh_trang_hieu_luc = $common.tinh_trang_hieu_luc, p.cap_bac_phap_ly = $common.cap_bac_phap_ly
        WITH p, row
        MATCH (k:DieuKhoanLuat {id: row.khoan_id})
        MERGE (k)-[:CO_DIEM]->(p)
        """
        tx.run(query, data=data, common=common)

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Tập hợp các biến từ file .env
    load_dotenv()

    URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    USER = os.getenv("NEO4J_USERNAME", "neo4j")
    PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")
    
    # Lấy đường dẫn tuyệt đối đến thư mục chứa file crawl.py
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Tên file lấy từ document bạn cung cấp.
    # LƯU Ý: Thư viện python-docx CHỈ ĐỌC ĐƯỢC file .docx.
    # Bạn HÃY MỞ FILE .doc BẰNG WORD VÀ LƯU LẠI DƯỚI DẠNG .docx TRƯỚC KHI CHẠY.
    FILE_PATH = os.path.join(BASE_DIR, "Luật-60-2014-QH13.docx") 

    builder = LawGraphBuilder(URI, USER, PASSWORD)
    try:
        builder.parse_and_insert(FILE_PATH)
    finally:
        builder.close()