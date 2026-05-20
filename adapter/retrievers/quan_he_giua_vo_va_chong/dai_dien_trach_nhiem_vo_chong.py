from adapter.config import driver, build_llm, RETRIEVER_LLM
from utils.utils import TrichXuatLuat, chuan_hoa_Context_cho_LLM, lay_target_date_tu_extraction

from datetime import date
today = date.today()
formatted_date = today.strftime("%Y-%m-%d")

dai_dien_trach_nhiem_vo_chong_description = {
    "type": "function",
    "function": {
        "name": "dai_dien_trach_nhiem_vo_chong",
        "description": "Tra cứu các quy định về đại diện giữa vợ và chồng (căn cứ xác lập đại diện, đại diện trong kinh doanh, đại diện khi giấy tờ tài sản chỉ ghi tên một người) và trách nhiệm liên đới của vợ chồng.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi cụ thể của người dùng về đại diện hoặc trách nhiệm liên đới giữa vợ và chồng."
                }
            },
            "required": ["query"],
        },
    },
}

async def dai_dien_trach_nhiem_vo_chong(query: str):
    """
    Tool xử lý các quy định về Đại diện và Trách nhiệm liên đới (Điều 24 - Điều 27).
    """
    print(f"[Agent dai_dien_trach_nhiem_vo_chong] Đang xử lý: '{query}'...")

    # 1. Trích xuất ID và thời gian
    prompt_extract = """
    Bạn là chuyên gia xác định căn cứ pháp lý. Đọc câu hỏi và chọn đúng các Điều luật phù hợp.
    Chỉ được phép chọn từ danh sách:
    - 'Luat_HNGD_2014_Dieu_24': Căn cứ xác lập đại diện giữa vợ và chồng.
    - 'Luat_HNGD_2014_Dieu_25': Đại diện giữa vợ và chồng trong quan hệ kinh doanh.
    - 'Luat_HNGD_2014_Dieu_26': Đại diện trong trường hợp Giấy chứng nhận tài sản chung chỉ ghi tên vợ hoặc chồng.
    - 'Luat_HNGD_2014_Dieu_27': Trách nhiệm liên đới của vợ, chồng trong giao dịch dân sự, tài sản.
    Trích xuất mốc thời gian sự kiện (nếu có) định dạng 'YYYY-MM-DD'. Nếu người dùng chỉ nêu năm (vd: 2023), trả về 'YYYY' hoặc 'YYYY-01-01'. Nếu không có, trả về null.
    """
    llm = build_llm(model=RETRIEVER_LLM, temperature=0)
    structured_llm = llm.with_structured_output(TrichXuatLuat)

    try:
        extraction = structured_llm.invoke([{"role": "system", "content": prompt_extract}, {"role": "user", "content": query}])
        target_ids = extraction.dieu_luat_ids
        target_date, is_user_provide_date = lay_target_date_tu_extraction(extraction.thoi_diem_su_kien, formatted_date)
    except:
        target_ids, target_date, is_user_provide_date = ["Luat_HNGD_2014_Dieu_24", "Luat_HNGD_2014_Dieu_27"], formatted_date, False

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
    records, _, _ = driver.execute_query(cypher, danh_sach_id=target_ids, target_date=target_date)

    results = []
    for r in records:
        results.append(chuan_hoa_Context_cho_LLM(r, target_date, is_user_provide_date))
    return results