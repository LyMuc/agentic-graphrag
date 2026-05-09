import re
import os
import sys
from docx import Document
from neo4j import GraphDatabase

class NghiQuyetGraphBuilder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # ID gốc
        self.base_id = "NghiQuyet_01_2024_NQ_HDTP"
        self.common_props = {
            "loai_van_ban": "Nghị quyết",
            "ngay_ban_hanh": "2024-05-16", 
            "ngay_co_hieu_luc": "2024-07-01",
            "ngay_het_hieu_luc": "",
            "tinh_trang_hieu_luc": "Còn hiệu lực",
            "cap_bac_phap_ly": 7
        }

    def close(self):
        self.driver.close()

    def parse_and_insert(self, file_path):
        doc = Document(file_path)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip() != ""]

        # Thông tin node gốc
        nghi_quyet_info = {
            "id": self.base_id,
            "so_hieu": "01/2024/NQ-HĐTP",
            "ten_van_ban": "Nghị quyết hướng dẫn áp dụng một số quy định của pháp luật trong giải quyết vụ việc về hôn nhân và gia đình",
            "co_quan_ban_hanh": "Hội đồng Thẩm phán Tòa án nhân dân tối cao",
            "noidung": "Nghị quyết hướng dẫn áp dụng một số quy định của pháp luật trong giải quyết vụ việc về hôn nhân và gia đình"
        }

        articles = []
        clauses = []
        points = []

        current_chuong = "Chưa xác định"
        current_dieu_num = ""
        current_dieu_id = ""
        current_khoan_num = ""
        current_khoan_id = ""
        active_entity = None

        chuong_pattern = re.compile(r'^Chương\s+([IVXLCDM]+)', re.IGNORECASE)
        dieu_pattern = re.compile(r'^Điều\s+(\d+[a-zA-Z]?)\.\s*(.*)')
        khoan_pattern = re.compile(r'^(\d+)\.\s+(.*)')
        diem_pattern = re.compile(r'^([a-zđ])\)\s+(.*)')

        for line in lines:
            if chuong_match := chuong_pattern.match(line):
                current_chuong = chuong_match.group(1)
                active_entity = None
                continue

            # 1. CẬP NHẬT: Nhận diện Điều -> In hoa chữ cái đầu (Dieu)
            if dieu_match := dieu_pattern.match(line):
                current_dieu_num = dieu_match.group(1)
                current_dieu_id = f"{self.base_id}_Dieu_{current_dieu_num}"
                current_khoan_num = ""
                current_khoan_id = ""
                
                art_dict = {
                    "id": current_dieu_id, "chuong": current_chuong, "dieu": current_dieu_num,
                    "noidung": line, "nghi_quyet_id": self.base_id
                }
                articles.append(art_dict)
                active_entity = art_dict
                continue

            # 2. CẬP NHẬT: Nhận diện Khoản -> In hoa chữ cái đầu (Khoan)
            if khoan_match := khoan_pattern.match(line):
                current_khoan_num = khoan_match.group(1)
                current_khoan_id = f"{current_dieu_id}_Khoan_{current_khoan_num}"
                
                khoan_dict = {
                    "id": current_khoan_id, "chuong": current_chuong, "dieu": current_dieu_num,
                    "khoan": current_khoan_num, "noidung": line, "dieu_id": current_dieu_id
                }
                clauses.append(khoan_dict)
                active_entity = khoan_dict
                continue

            # 3. CẬP NHẬT: Nhận diện Điểm -> In hoa chữ cái đầu (Diem)
            if diem_match := diem_pattern.match(line):
                diem_char = diem_match.group(1)
                diem_id = f"{current_khoan_id}_Diem_{diem_char}" if current_khoan_id else f"{current_dieu_id}_Diem_{diem_char}"
                
                diem_dict = {
                    "id": diem_id, "chuong": current_chuong, "dieu": current_dieu_num,
                    "khoan": current_khoan_num, "diem": diem_char, "noidung": line, "khoan_id": current_khoan_id
                }
                points.append(diem_dict)
                active_entity = diem_dict
                continue

            if active_entity:
                active_entity["noidung"] += " " + line

        # Thực thi Insert
        with self.driver.session() as session:
            session.execute_write(self._upsert_nghi_quyet, nghi_quyet_info, self.common_props)
            session.execute_write(self._upsert_articles, articles, self.common_props)
            session.execute_write(self._upsert_clauses, clauses, self.common_props)
            session.execute_write(self._upsert_points, points, self.common_props)
            
        print(f"Đã hoàn tất bóc tách Nghị quyết {self.base_id}. Tổng cộng: {len(articles)} Điều.")

    @staticmethod
    def _upsert_nghi_quyet(tx, info, common):
        query = """
        MERGE (nq:NghiQuyet {id: $info.id})
        SET nq.so_hieu = $info.so_hieu, nq.ten_van_ban = $info.ten_van_ban, nq.co_quan_ban_hanh = $info.co_quan_ban_hanh,
            nq.noidung = $info.noidung, nq.ngay_ban_hanh = $common.ngay_ban_hanh, nq.loai_van_ban = $common.loai_van_ban,
            nq.ngay_co_hieu_luc = $common.ngay_co_hieu_luc, nq.ngay_het_hieu_luc = $common.ngay_het_hieu_luc,
            nq.tinh_trang_hieu_luc = $common.tinh_trang_hieu_luc, nq.cap_bac_phap_ly = $common.cap_bac_phap_ly
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
        MATCH (nq:NghiQuyet {id: row.nghi_quyet_id})
        MERGE (nq)-[:CO_DIEU]->(d)
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
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from adapter.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

    URI = NEO4J_URI
    USER = NEO4J_USERNAME
    PASSWORD = NEO4J_PASSWORD
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    FILE_PATH = os.path.join(base_dir, "01_2024_NQ-HDTP_515531.docx")

    builder = NghiQuyetGraphBuilder(URI, USER, PASSWORD)
    try:
        if os.path.exists(FILE_PATH):
            builder.parse_and_insert(FILE_PATH)
        else:
            print(f"Không tìm thấy file: {FILE_PATH}. Vui lòng kiểm tra lại đường dẫn!")
    finally:
        builder.close()