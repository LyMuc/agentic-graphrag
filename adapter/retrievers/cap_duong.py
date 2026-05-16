from adapter.config import driver, build_llm, RETRIEVER_LLM
from utils.utils import TrichXuatLuat, chuan_hoa_Context_cho_LLM

from datetime import date
today = date.today()
formatted_date = today.strftime("%Y-%m-%d")

cap_duong_description = {
    "type": "function",
    "function": {
        "name": "cap_duong",
        "description": "Tool xử lý các quy định về cấp dưỡng.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi cụ thể của người dùng."
                }
            },
            "required": ["query"],
        },
    },
}

async def cap_duong(query: str):
    """
    Tool xử lý các quy định về cấp dưỡng.
    """
    print(f"[Agent cap_duong] Đang xử lý: '{query}'...")

    # 1. Trích xuất ID và thời gian
    prompt_extract = """
    Bạn là chuyên gia xác định căn cứ pháp lý. Đọc câu hỏi và chọn đúng các Điều luật để trả lời cho câu hỏi của người dùng. Có thể cần phải chọn nhiều hơn 1 Điều luật nếu cần thiết.
    Chỉ được phép chọn từ danh sách:
    - 'Luat_HNGD_2014_Dieu_107': Nghĩa vụ cấp dưỡng (nghĩa vụ cấp dưỡng được thực hiện giữa ai, nếu trốn nghĩa vụ thì sao)
    - 'Luat_HNGD_2014_Dieu_108': Một người cấp dưỡng cho nhiều người.
    - 'Luat_HNGD_2014_Dieu_109': Nhiều người cùng cấp dưỡng cho một người hoặc cho nhiều người.
    - 'Luat_HNGD_2014_Dieu_110': Nghĩa vụ cấp dưỡng của cha, mẹ đối với con.
    - 'Luat_HNGD_2014_Dieu_111': Nghĩa vụ cấp dưỡng của con đối với cha, mẹ.
    - 'Luat_HNGD_2014_Dieu_112': Nghĩa vụ cấp dưỡng giữa anh, chị, em.
    - 'Luat_HNGD_2014_Dieu_113': Nghĩa vụ cấp dưỡng giữa ông bà nội, ông bà ngoại và cháu.
    - 'Luat_HNGD_2014_Dieu_114': Nghĩa vụ cấp dưỡng giữa cô, dì, chú, cậu, bác ruột và cháu ruột.
    - 'Luat_HNGD_2014_Dieu_115': Nghĩa vụ cấp dưỡng giữa vợ và chồng khi ly hôn.
    - 'Luat_HNGD_2014_Dieu_116': Mức cấp dưỡng.
    - 'Luat_HNGD_2014_Dieu_117': Phương thức cấp dưỡng.
    - 'Luat_HNGD_2014_Dieu_118': Chấm dứt nghĩa vụ cấp dưỡng.
    - 'Luat_HNGD_2014_Dieu_119': Người có quyền yêu cầu thực hiện nghĩa vụ cấp dưỡng.
    - 'Luat_HNGD_2014_Dieu_120': Khuyến khích việc trợ giúp của tổ chức, cá nhân. 
    Trích xuất mốc thời gian sự kiện (nếu có) định dạng 'YYYY-MM-DD'. Nếu không có, trả về null.
    """
    llm = build_llm(model=RETRIEVER_LLM, temperature=0)
    structured_llm = llm.with_structured_output(TrichXuatLuat)

    try:
        extraction = structured_llm.invoke([{"role": "system", "content": prompt_extract}, {"role": "user", "content": query}])
        target_ids, target_date = extraction.dieu_luat_ids, extraction.thoi_diem_su_kien
        is_user_provide_date = True if target_date else False
        if not target_date: target_date = formatted_date
    except:
        target_ids, target_date, is_user_provide_date = ["Luat_HNGD_2014_Dieu_107"], formatted_date, False

    # 2. Truy vấn Neo4j
    cypher = """
    MATCH (n_goc:DieuLuat) WHERE n_goc.id IN $danh_sach_id

    // 1. MỞ RỘNG THÀNH CÁC KHOẢN/ĐIỂM GỐC (Chưa lọc thời gian vội)
    OPTIONAL MATCH (n_goc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_goc)

    // 2. LẤY TOÀN BỘ GIA PHẢ THEO DÒNG THỜI GIAN (QÚA KHỨ + TƯƠNG LAI)
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

    OPTIONAL MATCH (huong_dan)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_huong_dan)
    WHERE chi_tiet_huong_dan.ngay_co_hieu_luc <= $target_date
    AND (chi_tiet_huong_dan.ngay_het_hieu_luc IS NULL OR chi_tiet_huong_dan.ngay_het_hieu_luc > $target_date)

    // 6. TÌM LUẬT HIỆN HÀNH (Nếu bản áp dụng đã chết, phóng mũi tên tới tương lai để lấy bản mới nhất đối chiếu)
    OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAY_THE_BOI*0..]->(hien_hanh)
    WHERE hien_hanh.ngay_het_hieu_luc IS NULL

    // 7. TÌM CÁC QUY ĐỊNH THAM CHIẾU (THAM_CHIEU_DEN)
    OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAM_CHIEU_DEN]->(luat_tham_chieu)
    WHERE luat_tham_chieu.ngay_co_hieu_luc <= $target_date
    AND (luat_tham_chieu.ngay_het_hieu_luc IS NULL OR luat_tham_chieu.ngay_het_hieu_luc > $target_date)

    OPTIONAL MATCH (luat_tham_chieu)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_tham_chieu)
    WHERE chi_tiet_tham_chieu.ngay_co_hieu_luc <= $target_date
    AND (chi_tiet_tham_chieu.ngay_het_hieu_luc IS NULL OR chi_tiet_tham_chieu.ngay_het_hieu_luc > $target_date)

    RETURN {
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
        }) + collect(DISTINCT {
            id: chi_tiet_huong_dan.id,
            noidung: chi_tiet_huong_dan.noidung,
            cap_bac: chi_tiet_huong_dan.cap_bac_phap_ly
        }),
        can_cu_bo_tro: collect(DISTINCT {
            id: luat_tham_chieu.id,
            noidung: luat_tham_chieu.noidung,
            cap_bac: luat_tham_chieu.cap_bac_phap_ly
        }) + collect(DISTINCT {
            id: chi_tiet_tham_chieu.id,
            noidung: chi_tiet_tham_chieu.noidung,
            cap_bac: chi_tiet_tham_chieu.cap_bac_phap_ly
        }),
        quy_dinh_hien_hanh_doi_chieu: collect(DISTINCT hien_hanh.id)
    } AS Context_Tho
    """
    records, _, _ = driver.execute_query(cypher, danh_sach_id=target_ids, target_date=target_date)
    
    results = []
    for r in records:
        results.append(chuan_hoa_Context_cho_LLM(r, target_date, is_user_provide_date))
    return results