import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from neo4j import GraphDatabase

# Khởi tạo LLM
os.environ["OPENAI_API_KEY"] = "your_openai_api_key_here"
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

app = FastAPI(title="Luồng Template Cypher - Kết hôn trái pháp luật")

# =====================================================================
# BƯỚC 1: ĐỊNH NGHĨA PYDANTIC ĐỂ ÉP LLM TRÍCH XUẤT THAM SỐ (ROUTING)
# =====================================================================

class ThamSoYeuCauHuy(BaseModel):
    vai_tro_chu_the: Literal["Người bị cưỡng ép", "Người bị lừa dối", "Vợ", "Chồng", "Cha", "Mẹ", "Con", "Cơ quan quản lý", "Không xác định"] = Field(description="Ai đang muốn yêu cầu hủy?")
    nguyen_nhan_vi_pham: Literal["Bị cưỡng ép, lừa dối", "Vi phạm tuổi", "Mất năng lực hành vi dân sự", "Vi phạm điều cấm", "Không xác định"] = Field(description="Lý do trái pháp luật là gì?")

class ThamSoCongNhanHoiTo(BaseModel):
    du_tuoi_chua: bool = Field(description="Hiện tại đã đủ tuổi kết hôn chưa?")
    ca_hai_dong_thuan: bool = Field(description="Cả hai có cùng xin tòa công nhận không?")
    da_thong_cam_bo_qua: Optional[bool] = Field(description="Người bị lừa dối có bỏ qua và tiếp tục sống chung không? (Theo Thông tư 01)")

class RouterKetHonTraiPL(BaseModel):
    phan_tich_logic: str = Field(description="Suy nghĩ và tóm tắt lại tình huống của người dùng.")
    dang_cau_hoi: Literal["HOI_QUYEN_YEU_CAU", "HOI_DIEU_KIEN_CONG_NHAN", "HOI_HAU_QUA_PHAP_LY"] = Field(description="Phân loại câu hỏi vào 1 trong 3 dạng.")
    
    tham_so_yeu_cau: Optional[ThamSoYeuCauHuy] = None
    tham_so_cong_nhan: Optional[ThamSoCongNhanHoiTo] = None

# =====================================================================
# BƯỚC 2: KHO LƯU TRỮ CÁC CYPHER TEMPLATES (MẪU TRIPLE)
# =====================================================================
# Thay vì để LLM tự viết Cypher, ta định nghĩa sẵn các khuôn mẫu logic (Triple Patterns)
# LLM chỉ việc truyền tham số ($vai_tro, $nguyen_nhan...) vào đây.

CYPHER_TEMPLATES = {
    "HOI_QUYEN_YEU_CAU": """
        // Pattern: (ChuThe) -[CO_QUYEN]-> (HanhViPhapLy)
        MATCH (s:ChuThe {ten_thuc_the: $vai_tro_chu_the})-[r:CO_QUYEN]->(a:HanhViPhapLy {ten_thuc_the: 'Yêu cầu hủy kết hôn trái pháp luật'})
        
        // Pattern: Dò điều kiện vi phạm
        MATCH (a)-[:YEU_CAU_DIEU_KIEN]->(c:DieuKien {noi_dung_chi_tiet: $nguyen_nhan_vi_pham})
        
        // Pattern Grounding: Dò ngược về node Điều Khoản gốc
        MATCH (s)-[:CAN_CU_THEO]->(node_cau_truc:DieuKhoanDiemLuat)
        
        RETURN r.loai_quyen_nghia_vu AS Quyen, node_cau_truc.noidung AS NguyenVan, node_cau_truc.id AS ID_DieuLuat
    """,
    
    "HOI_DIEU_KIEN_CONG_NHAN": """
        // Pattern: (HanhViPhapLy) -[YEU_CAU_DIEU_KIEN]-> (DieuKien)
        MATCH (a:HanhViPhapLy {ten_thuc_the: 'Công nhận quan hệ hôn nhân'})-[r:YEU_CAU_DIEU_KIEN]->(c:DieuKien)
        
        // Pattern Grounding: Lấy cả hướng dẫn từ Thông tư (nếu có lưu trong properties)
        MATCH (c)-[:CAN_CU_THEO]->(node_cau_truc:DieuKhoanDiemLuat)
        
        RETURN c.noi_dung_chi_tiet AS DieuKien, c.huong_dan_chi_tiet AS HuongDanThongTu, node_cau_truc.id AS ID_DieuLuat
    """,
    
    "HOI_HAU_QUA_PHAP_LY": """
        // Pattern: (HanhVi) -[DAN_DEN_HE_QUA]-> (TaiSan / QuyenNghiaVu)
        MATCH (a:HanhViPhapLy {ten_thuc_the: 'Hủy kết hôn trái pháp luật'})-[r:DAN_DEN_HE_QUA]->(he_qua)
        MATCH (he_qua)-[:CAN_CU_THEO]->(node_cau_truc:DieuKhoanDiemLuat)
        RETURN he_qua.ten_thuc_the AS HeQua, node_cau_truc.id AS ID_DieuLuat, node_cau_truc.noidung AS NguyenVan
    """
}

# =====================================================================
# BƯỚC 3: HÀM TRUY VẤN GRAPH DỰA TRÊN TEMPLATE (EXECUTION)
# =====================================================================

def query_graph_with_template(dang_cau_hoi: str, tham_so: dict) -> dict:
    """Chọn đúng Template Cypher và nhồi tham số vào để chạy trên Neo4j"""
    
    # Lấy template tương ứng
    cypher_query = CYPHER_TEMPLATES.get(dang_cau_hoi)
    if not cypher_query:
        return {"error": "Không tìm thấy mẫu Cypher phù hợp."}
    
    # Thực thi truy vấn trên Neo4j
    # driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    # with driver.session() as session:
    #     result = session.run(cypher_query, **tham_so)
    #     records = [record.data() for record in result]
    
    # -------- MOCK DATA ĐỂ TEST LUỒNG --------
    print(f"\n[Neo4j] Đang chạy Cypher Template cho dạng: {dang_cau_hoi}")
    print(f"[Neo4j] Tham số truyền vào: {tham_so}")
    
    mock_db_result = {
        "Ket_Qua_Logic": "Có quyền yêu cầu Tòa án hủy việc kết hôn.",
        "Huong_Dan_TT01": "Nếu đã biết bị lừa dối nhưng thông cảm sống chung thì tính từ thời điểm sống chung.",
        "Trang_Thai_Hop_Le": True,
        "ID_DieuLuat": "Luat_HNGD_2014_Dieu_10_Khoan_1",
        "Nguyen_Van": "Người bị lừa dối kết hôn... có quyền tự mình yêu cầu Tòa án hủy..."
    }
    return mock_db_result

# =====================================================================
# BƯỚC 4: LLM TỔNG HỢP VÀ SINH CÂU TRẢ LỜI (GENERATION)
# =====================================================================

def generate_final_answer(user_query: str, phan_tich: str, db_data: dict) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Bạn là trợ lý pháp lý ảo.
        Nhiệm vụ: Trả lời câu hỏi người dùng DỰA TRÊN KẾT QUẢ TỪ DATABASE ĐỒ THỊ.
        
        Bắt buộc:
        1. Phải kết luận thẳng vào vấn đề (Được / Không được / Ai có quyền).
        2. Nếu Database có 'Huong_Dan_TT01', phải lồng ghép giải thích cho người dùng hiểu.
        3. Cuối câu trả lời, LUÔN LUÔN trích dẫn 'Căn cứ pháp lý: [ID_DieuLuat]'.
        """),
        ("user", """
        - Câu hỏi: {query}
        - Phân tích ban đầu: {phan_tich}
        
        [KẾT QUẢ TRẢ VỀ TỪ ĐỒ THỊ TRI THỨC]
        {db_data}
        """)
    ])
    
    chain = prompt | llm
    return chain.invoke({
        "query": user_query,
        "phan_tich": phan_tich,
        "db_data": db_data
    }).content

# =====================================================================
# LUỒNG CHẠY CHÍNH (ORCHESTRATOR)
# =====================================================================

class ChatRequest(BaseModel):
    query: str

@app.post("/api/chat")
async def process_chat(request: ChatRequest):
    # Bước 1: LLM đóng vai trò Router để trích xuất tham số
    structured_llm = llm.with_structured_output(RouterKetHonTraiPL)
    extracted_info = structured_llm.invoke(request.query)
    
    # Lọc lấy dictionary tham số tương ứng để truyền vào Cypher
    params = {}
    if extracted_info.dang_cau_hoi == "HOI_QUYEN_YEU_CAU" and extracted_info.tham_so_yeu_cau:
        params = extracted_info.tham_so_yeu_cau.model_dump()
    elif extracted_info.dang_cau_hoi == "HOI_DIEU_KIEN_CONG_NHAN" and extracted_info.tham_so_cong_nhan:
        params = extracted_info.tham_so_cong_nhan.model_dump()
        
    # Bước 2 & 3: Lắp tham số vào Template và truy vấn Neo4j
    db_result = query_graph_with_template(extracted_info.dang_cau_hoi, params)
    
    # Bước 4: LLM sinh câu trả lời tự nhiên
    final_answer = generate_final_answer(request.query, extracted_info.phan_tich_logic, db_result)
    
    return {
        "intent": extracted_info.dang_cau_hoi,
        "extracted_params": params,
        "answer": final_answer
    }

# Để test thử luồng:
if __name__ == "__main__":
    test_query = "Lúc cưới tôi bị lừa, giờ tôi muốn kiện ra tòa để hủy hôn có được không?"
    
    print("--- 1. ROUTING & EXTRACTION ---")
    structured_llm = llm.with_structured_output(RouterKetHonTraiPL)
    info = structured_llm.invoke(test_query)
    print(f"Dạng câu hỏi: {info.dang_cau_hoi}")
    print(f"Tham số: {info.tham_so_yeu_cau}")
    
    print("\n--- 2 & 3. CYPHER TEMPLATE EXECUTION ---")
    db_data = query_graph_with_template(info.dang_cau_hoi, info.tham_so_yeu_cau.model_dump() if info.tham_so_yeu_cau else {})
    
    print("\n--- 4. FINAL GENERATION ---")
    ans = generate_final_answer(test_query, info.phan_tich_logic, db_data)
    print(f"Trả lời:\n{ans}")