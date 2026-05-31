from adapter.config import driver, build_llm, RETRIEVER_LLM
# Cấu hình Gemini (tạm comment): from adapter.config import driver, ainvoke_structured_retriever
from utils.utils import TrichXuatLuat, chuan_hoa_ket_qua_retriever, lay_target_date_tu_extraction

from datetime import date
today = date.today()
formatted_date = today.strftime("%Y-%m-%d")

quyen_nghia_vu_cha_me_con_description = {
    "type": "function",
    "function": {
        "name": "quyen_nghia_vu_cha_me_con",
        "description": (
            "Tra cứu quyền và nghĩa vụ giữa cha mẹ và con trong quan hệ gia đình bình thường "
            "(không phải sau ly hôn): chăm sóc, nuôi dưỡng, giáo dục, đại diện pháp luật, "
            "bồi thường thiệt hại do con gây ra; quyền nghĩa vụ của cha nuôi/mẹ nuôi/con nuôi, "
            "cha dượng/mẹ kế/con riêng, con dâu/con rể với cha mẹ vợ/chồng. "
            "Không dùng cho tài sản riêng của con, cấp dưỡng sau ly hôn, hay quyền nuôi con sau ly hôn."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Câu hỏi cụ thể về quyền, nghĩa vụ giữa cha mẹ và con trong gia đình, "
                        "bao gồm quan hệ cha dượng/mẹ kế, con nuôi, con dâu/con rể."
                    )
                }
            },
            "required": ["query"],
        },
    },
}

async def quyen_nghia_vu_cha_me_con(query: str):
    """
    Tool xử lý các quy định về quyền và nghĩa vụ của cha mẹ và con (Điều 68 - Điều 74, Điều 78 - Điều 80).
    """
    print(f"[Agent quyen_nghia_vu_cha_me_con] Đang xử lý: '{query}'...")

    # 1. Trích xuất ID và thời gian
    prompt_extract = """
    Bạn là chuyên gia xác định căn cứ pháp lý. Đọc câu hỏi và chọn đúng các Điều luật phù hợp. Có thể cần phải chọn nhiều hơn 1 Điều luật nếu cần thiết.
    Chỉ được phép chọn từ danh sách:
    - 'Luat_HNGD_2014_Dieu_68': Bảo vệ quyền và nghĩa vụ của cha mẹ và con (tôn trọng, bảo vệ quyền nghĩa vụ; con sinh ra không phụ thuộc tình trạng hôn nhân cha mẹ; quyền nghĩa vụ con nuôi–cha/mẹ nuôi; thỏa thuận nhân thân, tài sản không được ảnh hưởng người yếu thế).
    - 'Luat_HNGD_2014_Dieu_69': Nghĩa vụ và quyền của cha mẹ.
    - 'Luat_HNGD_2014_Dieu_70': Quyền và nghĩa vụ của con.
    - 'Luat_HNGD_2014_Dieu_71': Nghĩa vụ và quyền chăm sóc, nuôi dưỡng (cha mẹ đối với con, con đối với cha mẹ).
    - 'Luat_HNGD_2014_Dieu_72': Nghĩa vụ và quyền giáo dục con.
    - 'Luat_HNGD_2014_Dieu_73': Đại diện cho con.
    - 'Luat_HNGD_2014_Dieu_74': Bồi thường thiệt hại do con gây ra.
    - 'Luat_HNGD_2014_Dieu_78': Quyền, nghĩa vụ của cha nuôi, mẹ nuôi và con nuôi.
    - 'Luat_HNGD_2014_Dieu_79': Quyền, nghĩa vụ của cha dượng, mẹ kế và con riêng của vợ hoặc của chồng.
    - 'Luat_HNGD_2014_Dieu_80': Quyền, nghĩa vụ của con dâu, con rể, cha mẹ vợ, cha mẹ chồng.
    
    Trích xuất mốc thời gian sự kiện (nếu có) định dạng 'YYYY-MM-DD'. Nếu người dùng chỉ nêu năm (vd: 2023), trả về 'YYYY' hoặc 'YYYY-01-01'. Nếu không có, trả về null.
    """
    # Cấu hình Gemini (tạm comment):
    # extraction = await structured_llm.ainvoke(...)
    llm = build_llm(model=RETRIEVER_LLM, temperature=0)
    structured_llm = llm.with_structured_output(TrichXuatLuat)

    try:
        extraction = await structured_llm.ainvoke([{"role": "system", "content": prompt_extract}, {"role": "user", "content": query}])
        target_ids = extraction.dieu_luat_ids
        target_date, is_user_provide_date = lay_target_date_tu_extraction(extraction.thoi_diem_su_kien, formatted_date)
    except:
        target_ids, target_date, is_user_provide_date = [
            "Luat_HNGD_2014_Dieu_68",
            "Luat_HNGD_2014_Dieu_69",
            "Luat_HNGD_2014_Dieu_70",
            "Luat_HNGD_2014_Dieu_71",
            "Luat_HNGD_2014_Dieu_72",
            "Luat_HNGD_2014_Dieu_73",
            "Luat_HNGD_2014_Dieu_74",
            "Luat_HNGD_2014_Dieu_78",
            "Luat_HNGD_2014_Dieu_79",
            "Luat_HNGD_2014_Dieu_80",
        ], formatted_date, False

    # 2. Truy vấn Neo4j
    cypher = """
    MATCH (n_goc:DieuLuat) WHERE n_goc.id IN $danh_sach_id

    // 1. MỞ RỘNG THÀNH CÁC KHOẢN/ĐIỂM GỐC (Chưa lọc thời gian vội)
    OPTIONAL MATCH (n_goc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_goc)

    // 2. LẤY TOÀN BỘ GIA PHẢ THEO DÒNG THỜI GIAN (QÚA KHỨ + TƯƠNG LAI)
    OPTIONAL MATCH (chi_tiet_goc)-[:THAY_THE_BOI*0..]-(chi_tiet_gia_toc)

    // 2b. MỞ RỘNG CHI TIẾT (KHOẢN/ĐIỂM) CỦA VĂN BẢN THAY THẾ
    OPTIONAL MATCH (chi_tiet_gia_toc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_thay_the)

    // Gom tất cả các phiên bản (Bản gốc + Bản quá khứ + Bản tương lai) vào 1 rổ
    WITH n_goc, collect(chi_tiet_goc) + collect(chi_tiet_gia_toc) + collect(chi_tiet_thay_the) AS tat_ca_phien_ban
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
    OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAY_THE_BOI*1..]->(hien_hanh)
    WHERE hien_hanh.ngay_het_hieu_luc IS NULL

    // 7. TÌM CÁC QUY ĐỊNH THAM CHIẾU (THAM_CHIEU_DEN)
    OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAM_CHIEU_DEN]->(luat_tham_chieu)
    WHERE luat_tham_chieu.ngay_co_hieu_luc <= $target_date
    AND (luat_tham_chieu.ngay_het_hieu_luc IS NULL OR luat_tham_chieu.ngay_het_hieu_luc > $target_date)

    OPTIONAL MATCH (luat_tham_chieu)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_tham_chieu)
    WHERE chi_tiet_tham_chieu.ngay_co_hieu_luc <= $target_date
    AND (chi_tiet_tham_chieu.ngay_het_hieu_luc IS NULL OR chi_tiet_tham_chieu.ngay_het_hieu_luc > $target_date)

    // 8. TÌM QUY ĐỊNH THAM CHIẾU TỪ VĂN BẢN HƯỚNG DẪN (Nghị định -> Luật khác)
    OPTIONAL MATCH (chi_tiet_huong_dan)-[:THAM_CHIEU_DEN]->(luat_tham_chieu_tu_hd)
    WHERE luat_tham_chieu_tu_hd.ngay_co_hieu_luc <= $target_date
    AND (luat_tham_chieu_tu_hd.ngay_het_hieu_luc IS NULL OR luat_tham_chieu_tu_hd.ngay_het_hieu_luc > $target_date)

    OPTIONAL MATCH (luat_tham_chieu_tu_hd)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_tc_tu_hd)
    WHERE chi_tiet_tc_tu_hd.ngay_co_hieu_luc <= $target_date
    AND (chi_tiet_tc_tu_hd.ngay_het_hieu_luc IS NULL OR chi_tiet_tc_tu_hd.ngay_het_hieu_luc > $target_date)

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
        })
        + collect(DISTINCT {
            id: luat_tham_chieu_tu_hd.id,
            noidung: luat_tham_chieu_tu_hd.noidung,
            cap_bac: luat_tham_chieu_tu_hd.cap_bac_phap_ly,
            ngay_hieu_luc: luat_tham_chieu_tu_hd.ngay_co_hieu_luc,
            ngay_het_hieu_luc: luat_tham_chieu_tu_hd.ngay_het_hieu_luc
        }) + collect(DISTINCT {
            id: chi_tiet_tc_tu_hd.id,
            noidung: chi_tiet_tc_tu_hd.noidung,
            cap_bac: chi_tiet_tc_tu_hd.cap_bac_phap_ly,
            ngay_hieu_luc: chi_tiet_tc_tu_hd.ngay_co_hieu_luc,
            ngay_het_hieu_luc: chi_tiet_tc_tu_hd.ngay_het_hieu_luc
        }),
        lien_ket_huong_dan: [pair IN collect(DISTINCT {
            id_huong_dan: coalesce(chi_tiet_huong_dan.id, huong_dan.id),
            id_duoc_huong_dan: chi_tiet_ap_dung.id
        }) WHERE pair.id_huong_dan IS NOT NULL AND pair.id_duoc_huong_dan IS NOT NULL],

        quy_dinh_hien_hanh_doi_chieu: collect(DISTINCT hien_hanh.id)
    } AS Context_Tho
    """
    records, _, _ = driver.execute_query(cypher, danh_sach_id=target_ids, target_date=target_date)

    return chuan_hoa_ket_qua_retriever(records, target_date, is_user_provide_date)
