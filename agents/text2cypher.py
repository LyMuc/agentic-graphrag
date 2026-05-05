from typing import Literal
import neo4j
from config import driver, chat
from db_schema import get_schema
from utils import strip_code_cypher

prompt_template = {
    "static": {
        "instructions": """
    Bạn là một chuyên gia truy xuất Cơ sở dữ liệu Đồ thị pháp luật (Legal Graph Database) sử dụng ngôn ngữ Neo4j Cypher.
    Nhiệm vụ của bạn là đọc câu hỏi của người dùng, phân tích thông tin các node được cung cấp, và viết một câu lệnh Cypher để lấy về toàn bộ ngữ cảnh pháp lý cần thiết.

    QUY TẮC SINH LỆNH CYPHER (CRITICAL RULES):
    1. LỰA CHỌN ID CHÍNH XÁC (ID Selection): Đọc phần "Thông tin về các node căn cứ pháp luật". Xác định Điều luật nào phù hợp để trả lời câu hỏi và sử dụng chính xác ID đó trong lệnh `MATCH (n {id: "..."})`, có thể có nhiều hơn 1 Điều luật cần để trả lời cho câu hỏi. KHÔNG tự bịa ID ngoài danh sách.
    2. VÉT CẠN CẤU TRÚC LUẬT (Top-Down Traversal): Một Điều luật luôn chứa các Khoản và Điểm. BẮT BUỘC sử dụng cú pháp `OPTIONAL MATCH (n)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet)` để lấy trọn vẹn nội dung của Điều luật đó.
    3. XỬ LÝ THAM CHIẾU CHÉO (Cross-References): Pháp luật thường tham chiếu đến nhau. TỪ các node `chi_tiet` vừa tìm được, BẮT BUỘC phải dùng `OPTIONAL MATCH (chi_tiet)-[:THAM_CHIEU_DEN]->(luat_lien_quan)` để tìm các luật liên đới, sau đó vét cạn cấu trúc của luật liên đới đó (nếu có).
    4. ĐỊNH DẠNG ĐẦU RA JSON (JSON Context Packaging): KHÔNG trả về kết quả dạng bảng nhiều dòng. Bắt buộc dùng `WITH` và `collect(DISTINCT {...})` để gom nhóm toàn bộ nội dung luật chính và luật tham chiếu vào chung một Object (Dictionary) duy nhất trả về bằng `RETURN`.

    HƯỚNG DẪN ĐẦU RA (OUTPUT FORMATTING):
    - KHÔNG giải thích, phân tích hay xin lỗi.
    - CHỈ TRẢ LỜI BẰNG LỆNH CYPHER THUẦN TÚY.
    - KHÔNG SỬ DỤNG CODEBLOCKS (ví dụ: không dùng ```cypher ... ```).
    """
    },
    "dynamic": {
        "schema": """
    Lược đồ Cơ sở dữ liệu Đồ thị (Schema) và Danh sách ID hợp lệ:
    Chỉ sử dụng các loại quan hệ và thuộc tính được cung cấp trong lược đồ dưới đây.
    {}
    """,
        "terminology": """
    Ánh xạ thuật ngữ (Terminology mapping):
    {}
    """,
        "examples": """
    Ví dụ (Examples):
    {}
    """,
        "question": """
    Câu hỏi của người dùng: {}
    """,
    },
}

class Text2Cypher:
    def __init__(self, driver: neo4j.Driver):
        self.driver = driver
        self.dynamic_sections = {}
        self.required_sections = ["question"]
        self.prompt_template = prompt_template

        schema_string = get_schema(driver)
        self.set_prompt_section("schema", schema_string)

    def set_prompt_section(
        self,
        section: Literal["terminology", "examples", "schema", "question"],
        value: str,
    ):
        self.dynamic_sections[section] = value

    def get_full_prompt(self):
        prompt = self.prompt_template["static"]["instructions"]
        for section in self.prompt_template["dynamic"]:
            if section in self.dynamic_sections:
                prompt += self.prompt_template["dynamic"][section].format(
                    self.dynamic_sections[section]
                )
        return prompt

    async def generate_cypher(self):
        for section in self.required_sections:
            if section not in self.dynamic_sections:
                raise ValueError(
                    f"Phần {section} là bắt buộc để tạo prompt. Sử dụng set_prompt_section để thiết lập nó."
                )
        prompt = self.get_full_prompt()
        cypher = await chat(messages=[{"role": "user", "content": prompt}])
        return strip_code_cypher(cypher)
