from adapter.text2cypher import Text2Cypher
from adapter.config import driver, ChatGroq, GROQ_API_KEY
from utils.utils import TrichXuatLuat, chuan_hoa_Context_cho_LLM

from datetime import date
today = date.today()
formatted_date = today.strftime("%Y-%m-%d")

xu_phat_vi_pham_description = {
    "type": "function",
    "function": {
        "name": "xu_phat_vi_pham",
        "description": "Tra cứu các quy định về xử phạt vi phạm hành chính trong lĩnh vực hôn nhân gia đình (tảo hôn, vi phạm chế độ một vợ một chồng, kết hôn, ly hôn, sinh con, giám hộ, nuôi con nuôi, văn phòng con nuôi nước ngoài tại Việt Nam).",
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

async def xu_phat_vi_pham(query: str):
    print(f"[Agent xu_phat_vi_pham] Đang xử lý: '{query}'...")

    prompt_extract = """
    Bạn là chuyên gia xác định căn cứ pháp lý. Đọc câu hỏi và chọn đúng các Điều luật về XỬ PHẠT HÀNH CHÍNH.
    Chỉ được phép chọn từ danh sách:
    - 'NghiDinh_82_2020_ND_CP_Dieu_58': Tảo hôn
    - 'NghiDinh_82_2020_ND_CP_Dieu_59': Vi phạm chế độ một vợ một chồng, vi phạm quy định về kết hôn, ly hôn
    - 'NghiDinh_82_2020_ND_CP_Dieu_60': Vi phạm quy định về sinh con
    - 'NghiDinh_82_2020_ND_CP_Dieu_61': Vi phạm quy định về giám hộ
    - 'NghiDinh_82_2020_ND_CP_Dieu_62': Vi phạm quy định về nuôi con nuôi
    - 'NghiDinh_82_2020_ND_CP_Dieu_63': Vi phạm quy định về văn phòng con nuôi nước ngoài tại Việt Nam
    Trích xuất mốc thời gian sự kiện (nếu có) định dạng 'YYYY-MM-DD'. Nếu không có, trả về null.
    """
    llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.3-70b-versatile", temperature=0)
    structured_llm = llm.with_structured_output(TrichXuatLuat)

    try:
        extraction = structured_llm.invoke([{"role": "system", "content": prompt_extract}, {"role": "user", "content": query}])
        target_ids, target_date = extraction.dieu_luat_ids, extraction.thoi_diem_su_kien
        is_user_provide_date = True if target_date else False
        if not target_date: target_date = formatted_date
    except:
        target_ids, target_date, is_user_provide_date = ["NghiDinh_82_2020_ND_CP_Dieu_58", "NghiDinh_82_2020_ND_CP_Dieu_59"], formatted_date, False

    cypher = """
    MATCH (n_goc:DieuLuat) WHERE n_goc.id IN $danh_sach_id

    // 1. MỞ RỘNG THÀNH CÁC KHOẢN/ĐIỂM GỐC (Chưa lọc thời gian vội)
    OPTIONAL MATCH (n_goc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_goc)

    // 2. LẤY TOÀN BỘ GIA PHẢ THEO DÒNG THỜI GIAN (QÚA KHỨ + TƯƠNG LAI)
    // Lưu ý mũi tên -[...]-(...) không có hướng, Neo4j sẽ chạy cả tiến và lùi theo dây THAY_THE_BOI
    OPTIONAL MATCH (chi_tiet_goc)-[:THAY_THE_BOI*0..]-(chi_tiet_gia_toc)

    // Gom tất cả các phiên bản (Bản gốc + Bản quá khứ + Bản tương lai) vào 1 rổ
    WITH n_goc, collect(chi_tiet_goc) + collect(chi_tiet_gia_toc) AS tat_ca_phien_ban
    UNWIND tat_ca_phien_ban AS node_xet_duyet

    // 3. TÌM CHÍNH XÁC PHIÊN BẢN CÓ HIỆU LỰC TẠI $target_date
    WITH DISTINCT n_goc, node_xet_duyet AS chi_tiet_ap_dung
    WHERE chi_tiet_ap_dung.ngay_co_hieu_luc <= $target_date
    AND (chi_tiet_ap_dung.ngay_het_hieu_luc IS NULL OR chi_tiet_ap_dung.ngay_het_hieu_luc > $target_date)

    // 4. KIỂM TRA SỬA ĐỔI BỔ SUNG ĐỐI VỚI BẢN ÁP DỤNG NÀY
    OPTIONAL MATCH (chi_tiet_ap_dung)-[:DUOC_SUA_DOI_BOI]->(van_ban_sua_doi)
    WHERE van_ban_sua_doi.ngay_co_hieu_luc <= $target_date
    AND (van_ban_sua_doi.ngay_het_hieu_luc IS NULL OR van_ban_sua_doi.ngay_het_hieu_luc > $target_date)

    // 5. TÌM HƯỚNG DẪN CHI TIẾT ĐỐI VỚI BẢN ÁP DỤNG
    OPTIONAL MATCH (chi_tiet_ap_dung)-[:HUONG_DAN_BOI]->(huong_dan)
    WHERE huong_dan.ngay_co_hieu_luc <= $target_date
    AND (huong_dan.ngay_het_hieu_luc IS NULL OR huong_dan.ngay_het_hieu_luc > $target_date)

    // 6. TÌM LUẬT HIỆN HÀNH (Nếu bản áp dụng đã chết, phóng mũi tên tới tương lai để lấy bản mới nhất đối chiếu)
    OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAY_THE_BOI*0..]->(hien_hanh)
    WHERE hien_hanh.ngay_het_hieu_luc IS NULL

    RETURN {
        // Tập hợp căn cứ chính
        can_cu_chinh: collect(DISTINCT {
            id_goc_tu_router: n_goc.id,
            id_thuc_te_ap_dung: chi_tiet_ap_dung.id,
            noidung: chi_tiet_ap_dung.noidung,
            cap_bac: chi_tiet_ap_dung.cap_bac_phap_ly,
            het_hieu_luc: chi_tiet_ap_dung.ngay_het_hieu_luc IS NOT NULL,
            id_sua_doi: van_ban_sua_doi.id,
            noidung_sua_doi: van_ban_sua_doi.noidung
        }),

        can_cu_huong_dan: collect(DISTINCT {
            id: huong_dan.id,
            noidung: huong_dan.noidung,
            cap_bac: huong_dan.cap_bac_phap_ly
        }),

        quy_dinh_hien_hanh_doi_chieu: collect(DISTINCT hien_hanh.id)
    } AS Context_Tho
        """

    print(f"Cypher Query với IDs: {target_ids} và Thời điểm: {target_date}")
    records, _, _ = driver.execute_query(cypher, danh_sach_id=target_ids, target_date=target_date)

    results = []
    for r in records:
        final_string = chuan_hoa_Context_cho_LLM(r, target_date, is_user_provide_date)
        results.append(final_string)

    return "\n\n***\n\n".join(results) if results else "Không tìm thấy kết quả phù hợp."
