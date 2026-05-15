import re
import os
import sys
from docx import Document
from neo4j import GraphDatabase

class LuatSuaDoiGraphBuilder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # ID gốc và các thông tin chung
        self.base_id = "Luat_suadoi_BoLuat_HinhSu_2017"
        self.common_props = {
            "loai_van_ban": "Bộ luật",
            "ngay_ban_hanh": "2017-06-20",
            "ngay_co_hieu_luc": "2018-01-01",
            "tinh_trang_hieu_luc": "Còn hiệu lực",
            "cap_bac_phap_ly": 2
        }

    def close(self):
        self.driver.close()

    def parse_and_insert(self, file_path):
        doc = Document(file_path)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip() != ""]

        # Thông tin của node gốc Luat
        luat_info = {
            "id": self.base_id,
            "so_hieu": "12/2017/QH14",
            "ten_luat": "Luật sửa đổi, bổ sung một số điều của Bộ luật Hình sự số 100/2015/QH13",
            "co_quan_ban_hanh": "Quốc hội"
        }

        articles = []
        clauses = []
        points = []

        # Tracking trạng thái cấu trúc
        current_phan = ""
        current_chuong = "Chưa xác định"
        current_dieu_num = ""
        current_dieu_id = ""
        current_khoan_num = ""
        current_khoan_id = ""
        active_entity = None
        
        is_quoting = False  # Trạng thái đang trong trích đoạn sửa đổi

        # Regex nhận diện tiêu chuẩn
        phan_pattern = re.compile(r'^Phần\s+(thứ\s+)?\w+', re.IGNORECASE)
        chuong_pattern = re.compile(r'^Chương\s+([IVXLCDM]+)', re.IGNORECASE)
        dieu_pattern = re.compile(r'^Điều\s+(\d+[a-zA-Z]?)\.\s*(.*)')
        khoan_pattern = re.compile(r'^(\d+)\.\s+(.*)')
        diem_pattern = re.compile(r'^([a-zđ])\)\s+(.*)')

        # Danh sách các biến thể kết thúc trích đoạn trong văn bản sửa đổi bổ sung
        quote_endings = ['.".', ';".', '”.', ';”.', '.”.', ';”.', '."', ';"', '.”', ';”']

        for line in lines:
            # 1. XỬ LÝ TRONG TRÍCH ĐOẠN
            if is_quoting:
                if active_entity:
                    active_entity["noidung"] += "\n" + line
                # Kiểm tra kết thúc trích đoạn
                if any(line.endswith(ending) for ending in quote_endings):
                    is_quoting = False
                continue

            # 2. NHẬN DIỆN MỞ ĐẦU TRÍCH ĐOẠN
            if line.startswith('“') or line.startswith('"'):
                is_quoting = True
                if active_entity:
                    active_entity["noidung"] += "\n" + line
                if any(line.endswith(ending) for ending in quote_endings):
                    is_quoting = False
                continue

            # 3. NHẬN DIỆN CẤU TRÚC VĂN BẢN CHÍNH
            if phan_match := phan_pattern.match(line):
                current_phan = line
                active_entity = None
                continue

            if chuong_match := chuong_pattern.match(line):
                current_chuong = f"{current_phan} - {line}" if current_phan else line
                active_entity = None
                continue

            # Nhận diện Điều (PascalCase ID)
            if dieu_match := dieu_pattern.match(line):
                current_dieu_num = dieu_match.group(1)
                current_dieu_id = f"{self.base_id}_Dieu_{current_dieu_num}"
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

            # Nhận diện Khoản
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

            # Nhận diện Điểm
            if diem_match := diem_pattern.match(line):
                diem_char = diem_match.group(1)
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

            # Gộp nội dung văn bản liên tục
            if active_entity is not None:
                active_entity["noidung"] += " " + line

        # Thực thi Insert vào Neo4j bằng execute_write
        with self.driver.session() as session:
            session.execute_write(self._upsert_luat_root, luat_info, self.common_props)
            session.execute_write(self._upsert_articles, articles, self.common_props)
            session.execute_write(self._upsert_clauses, clauses, self.common_props)
            session.execute_write(self._upsert_points, points, self.common_props)
            
        print(f"Đã hoàn tất bóc tách {len(articles)} Điều của Luật sửa đổi, bổ sung Bộ luật Hình sự 2017.")

    @staticmethod
    def _upsert_luat_root(tx, info, common):
        query = """
        MERGE (l:Luat {id: $info.id})
        SET l.so_hieu = $info.so_hieu,
            l.ten_luat = $info.ten_luat,
            l.co_quan_ban_hanh = $info.co_quan_ban_hanh,
            l.ngay_ban_hanh = $common.ngay_ban_hanh,
            l.loai_van_ban = $common.loai_van_ban,
            l.ngay_co_hieu_luc = $common.ngay_co_hieu_luc,
            l.ngay_het_hieu_luc = $common.ngay_het_hieu_luc,
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
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from adapter.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

    URI = NEO4J_URI
    USER = NEO4J_USERNAME
    PASSWORD = NEO4J_PASSWORD
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    FILE_PATH = os.path.join(base_dir, "12_2017_QH14_354053.docx")

    builder = LuatSuaDoiGraphBuilder(URI, USER, PASSWORD)
    try:
        if os.path.exists(FILE_PATH):
            builder.parse_and_insert(FILE_PATH)
        else:
            print(f"Không tìm thấy file: {FILE_PATH}. Vui lòng kiểm tra lại đường dẫn!")
    finally:
        builder.close()