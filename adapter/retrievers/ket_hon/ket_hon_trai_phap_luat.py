from pydantic import BaseModel, Field
from typing import List, Optional
from adapter.config import driver, build_llm, RETRIEVER_LLM
from utils.utils import TrichXuatLuat, chuan_hoa_Context_cho_LLM

ket_hon_trai_phap_luat_description = {
    "type": "function",
    "function": {
        "name": "ket_hon_trai_phap_luat",
        "description": "Truy vấn các quy định về xử lý kết hôn trái pháp luật, quyền yêu cầu hủy kết hôn trái pháp luật và giải quyết hậu quả về tài sản, con cái.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi cụ thể của người dùng"
                }
            },
            "required": ["query"],
        },
    },
}

async def ket_hon_trai_phap_luat(query: str):
    """
    Tool xử lý các vấn đề về kết hôn trái pháp luật và hậu quả pháp lý.
    """
    print(f"[Agent ket_hon_trai_phap_luat] Đang xử lý: '{query}'...")

    prompt_extract = """
    Bạn là chuyên gia xác định căn cứ pháp lý. Đọc câu hỏi của người dùng và chọn ĐÚNG các Điều luật cần thiết.
    Chỉ được phép chọn từ danh sách sau:
    - "Luat_HNGD_2014_Dieu_10": Người có quyền yêu cầu hủy kết hôn trái pháp luật.
    - "Luat_HNGD_2014_Dieu_11": Xử lý việc kết hôn trái pháp luật
    - "Luat_HNGD_2014_Dieu_12": Hậu quả pháp lý của việc hủy kết hôn trái pháp luật
    Bạn cũng cần trích xuất mốc thời gian (nếu có) để hệ thống áp dụng đúng luật thời kỳ đó.
    """

    llm = build_llm(model=RETRIEVER_LLM, temperature=0)
    structured_llm = llm.with_structured_output(TrichXuatLuat)

    messages = [
        {"role": "system", "content": prompt_extract},
        {"role": "user", "content": f"Câu hỏi: {query}"}
    ]

    try:
        extraction = structured_llm.invoke(messages)
        target_ids = extraction.dieu_luat_ids
        target_date = extraction.thoi_diem_su_kien
        print(f"[LLM Filter] Chọn IDs: {target_ids} | Thời điểm: {target_date}")

        if not target_ids:
            target_ids = ["Luat_HNGD_2014_Dieu_10", "Luat_HNGD_2014_Dieu_11", "Luat_HNGD_2014_Dieu_12"]

    except Exception as e:
        print(f"[Lỗi LLM Filter] {e}. Sử dụng mặc định toàn bộ Điều.")
        target_ids = ["Luat_HNGD_2014_Dieu_10", "Luat_HNGD_2014_Dieu_11", "Luat_HNGD_2014_Dieu_12"]
        target_date = None

    cypher_query = """
    MATCH (n_goc:DieuLuat) WHERE n_goc.id IN $danh_sach_id

    // 1. TÌM LUẬT GỐC & CÁC KHOẢN/ĐIỂM CÓ HIỆU LỰC TẠI THỜI ĐIỂM $target_date
    OPTIONAL MATCH (n_goc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet)
    WHERE chi_tiet.ngay_co_hieu_luc <= $target_date 
    AND (chi_tiet.ngay_het_hieu_luc IS NULL OR chi_tiet.ngay_het_hieu_luc > $target_date)

    // 2. KIỂM TRA SỬA ĐỔI BỔ SUNG (Tại thời điểm $target_date)
    OPTIONAL MATCH (chi_tiet)<-[:DUOC_SUA_DOI_BOI]-(goc_bi_sua_doi)

    // 3. TÌM HƯỚNG DẪN CHI TIẾT (Có hiệu lực tại $target_date)
    OPTIONAL MATCH (chi_tiet)-[:HUONG_DAN_BOI]->(huong_dan)
    WHERE huong_dan.ngay_co_hieu_luc <= $target_date 
    AND (huong_dan.ngay_het_hieu_luc IS NULL OR huong_dan.ngay_het_hieu_luc > $target_date)

    // 4. NẾU QUY ĐỊNH Ở MỤC 1 ĐÃ HẾT HIỆU LỰC Ở HIỆN TẠI, LẤY LUẬT HIỆN HÀNH ĐỂ ĐỐI CHIẾU
    OPTIONAL MATCH (chi_tiet)-[:THAY_THE_BOI*1..]->(hien_hanh)
    WHERE chi_tiet.ngay_het_hieu_luc IS NOT NULL 
    AND hien_hanh.ngay_het_hieu_luc IS NULL

    RETURN {
        // Tập hợp căn cứ chính (Có check xem có phải là bản sửa đổi không)
        can_cu_chinh: collect(DISTINCT {
            id: chi_tiet.id, 
            noidung: chi_tiet.noidung, 
            cap_bac: chi_tiet.cap_bac_phap_ly,
            het_hieu_luc: chi_tiet.ngay_het_hieu_luc IS NOT NULL,
            la_sua_doi_cua: goc_bi_sua_doi.id 
        }),
        
        // Tập hợp căn cứ hướng dẫn
        can_cu_huong_dan: collect(DISTINCT {
            id: huong_dan.id, 
            noidung: huong_dan.noidung, 
            cap_bac: huong_dan.cap_bac_phap_ly
        }),
        
        // Tập hợp luật hiện hành (chỉ có data nếu luật mục 1 đã chết)
        quy_dinh_hien_hanh_doi_chieu: collect(DISTINCT hien_hanh.id)
    } AS Context_TraLoi
    """

    print(f"Cypher Query:\n{cypher_query}\nVới IDs: {target_ids} và Thời điểm: {target_date}")
    print("[Cypher] Đang truy vấn Database...")

    try:
        records, _, _ = driver.execute_query(
            cypher_query,
            danh_sach_id=target_ids,
            target_date=target_date
        )
        return [record["Context_TraLoi"] for record in records]

    except Exception as e:
        return [{"Lỗi Database": str(e)}]
