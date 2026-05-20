from pydantic import BaseModel, Field
from typing import List, Optional
from adapter.config import driver, build_llm, RETRIEVER_LLM
from utils.utils import TrichXuatLuat, chuan_hoa_Context_cho_LLM, lay_target_date_tu_extraction

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
    - "Luat_HNGD_2014_Dieu_11": Xử lý việc kết hôn trái pháp luật (Căn cứ hủy kết hôn, Thẩm quyền giải quyết, Thủ tục giải quyết).
    - "Luat_HNGD_2014_Dieu_12": Hậu quả pháp lý của việc hủy kết hôn trái pháp luật
    Bạn cũng cần trích xuất mốc thời gian (nếu có) để hệ thống áp dụng đúng luật thời kỳ đó.
    """

    llm = build_llm(model=RETRIEVER_LLM, temperature=0)
    structured_llm = llm.with_structured_output(TrichXuatLuat)

    messages = [
        {"role": "system", "content": prompt_extract},
        {"role": "user", "content": f"Câu hỏi: {query}"}
    ]

    from datetime import date
    today = date.today()
    formatted_date = today.strftime("%Y-%m-%d")

    try:
        extraction = structured_llm.invoke(messages)
        target_ids = extraction.dieu_luat_ids
        target_date, is_user_provide_date = lay_target_date_tu_extraction(extraction.thoi_diem_su_kien, formatted_date)
        print(f"[LLM Filter] Chọn IDs: {target_ids} | Thời điểm: {target_date}")

        if not target_ids:
            target_ids = ["Luat_HNGD_2014_Dieu_10", "Luat_HNGD_2014_Dieu_11", "Luat_HNGD_2014_Dieu_12"]

    except Exception as e:
        print(f"[Lỗi LLM Filter] {e}. Sử dụng mặc định toàn bộ Điều.")
        target_ids = ["Luat_HNGD_2014_Dieu_10", "Luat_HNGD_2014_Dieu_11", "Luat_HNGD_2014_Dieu_12"]
        target_date = formatted_date
        is_user_provide_date = False

    cypher_query = """
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

    // [THEM MOI]: KIEM TRA XEM CAI KHOAN/DIEM CUA HUONG DAN CO BI SUA DOI KHONG?
    OPTIONAL MATCH (chi_tiet_huong_dan)-[:DUOC_SUA_DOI_BOI]->(sua_doi_cua_hd)
    WHERE sua_doi_cua_hd.ngay_co_hieu_luc <= $target_date
    AND (sua_doi_cua_hd.ngay_het_hieu_luc IS NULL OR sua_doi_cua_hd.ngay_het_hieu_luc > $target_date)

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
            ngay_hieu_luc: chi_tiet_ap_dung.ngay_co_hieu_luc,
            ngay_het_hieu_luc: chi_tiet_ap_dung.ngay_het_hieu_luc,
            id_sua_doi: van_ban_sua_doi.id,
            noidung_sua_doi: van_ban_sua_doi.noidung,
            ngay_hieu_luc_sua_doi: van_ban_sua_doi.ngay_co_hieu_luc,
            ngay_het_hieu_luc_sua_doi: van_ban_sua_doi.ngay_het_hieu_luc
        }),
        can_cu_huong_dan: collect(DISTINCT {
            id: huong_dan.id,
            noidung: huong_dan.noidung,
            cap_bac: huong_dan.cap_bac_phap_ly,
            ngay_hieu_luc: huong_dan.ngay_co_hieu_luc,
            ngay_het_hieu_luc: huong_dan.ngay_het_hieu_luc,
            id_sua_doi: null,
            noidung_sua_doi: null,
            ngay_hieu_luc_sua_doi: null,
            ngay_het_hieu_luc_sua_doi: null
        }) + collect(DISTINCT {
            id: chi_tiet_huong_dan.id,
            noidung: chi_tiet_huong_dan.noidung,
            cap_bac: chi_tiet_huong_dan.cap_bac_phap_ly,
            ngay_hieu_luc: chi_tiet_huong_dan.ngay_co_hieu_luc,
            ngay_het_hieu_luc: chi_tiet_huong_dan.ngay_het_hieu_luc,
            id_sua_doi: sua_doi_cua_hd.id,
            noidung_sua_doi: sua_doi_cua_hd.noidung,
            ngay_hieu_luc_sua_doi: sua_doi_cua_hd.ngay_co_hieu_luc,
            ngay_het_hieu_luc_sua_doi: sua_doi_cua_hd.ngay_het_hieu_luc
        }),
        can_cu_bo_tro: collect(DISTINCT {
            id: luat_tham_chieu.id,
            noidung: luat_tham_chieu.noidung,
            cap_bac: luat_tham_chieu.cap_bac_phap_ly,
            ngay_hieu_luc: luat_tham_chieu.ngay_co_hieu_luc,
            ngay_het_hieu_luc: luat_tham_chieu.ngay_het_hieu_luc
        }) + collect(DISTINCT {
            id: chi_tiet_tham_chieu.id,
            noidung: chi_tiet_tham_chieu.noidung,
            cap_bac: chi_tiet_tham_chieu.cap_bac_phap_ly,
            ngay_hieu_luc: chi_tiet_tham_chieu.ngay_co_hieu_luc,
            ngay_het_hieu_luc: chi_tiet_tham_chieu.ngay_het_hieu_luc
        }),
        quy_dinh_hien_hanh_doi_chieu: collect(DISTINCT hien_hanh.id)
    } AS Context_Tho
    """

    print(f"Cypher Query:\n{cypher_query}\nVới IDs: {target_ids} và Thời điểm: {target_date}")
    print("[Cypher] Đang truy vấn Database...")

    try:
        records, _, _ = driver.execute_query(
            cypher_query,
            danh_sach_id=target_ids,
            target_date=target_date
        )
        results = []
        for r in records:
            results.append(chuan_hoa_Context_cho_LLM(r, target_date, is_user_provide_date))
        return results

    except Exception as e:
        return [{"Lỗi Database": str(e)}]
