from adapter.text2cypher import Text2Cypher
from adapter.config import driver

dang_ky_ket_hon_description = {
    "type": "function",
    "function": {
        "name": "dang_ky_ket_hon",
        "description": "Lấy thông tin quy định về đăng ký kết hôn như kết hôn lại, thẩm quyền đăng ký kết hôn, thủ tục đăng ký kết hôn hay xử lý đăng ký kết hôn không đúng thẩm quyền.",
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

async def dang_ky_ket_hon(query: str):
    """
    Tool xử lý các vấn đề về đăng ký kết hôn và thẩm quyền thực hiện.
    """
    print(f"[Agent dang_ky_ket_hon] Đang xử lý: '{query}'...")

    registration_schema = """
    Thuộc tính của node (properties):
    DieuKhoanLuat {id: STRING, chuong: STRING, dieu: STRING, khoan: STRING, noidung: STRING}
    DieuLuat {id: STRING, chuong: STRING, dieu: STRING, noidung: STRING}
    DieuKhoanDiemLuat {id: STRING, chuong: STRING, dieu: STRING, khoan: STRING, noidung: STRING, diem: STRING}

    Các mối quan hệ (The relationships):
    (:DieuKhoanLuat)-[:CO_DIEM]->(:DieuKhoanDiemLuat)
    (:DieuLuat)-[:CO_KHOAN]->(:DieuKhoanLuat)
    (:DieuLuat)-[:KET_HON_CO_YEU_TO_NUOC_NGOAI]->(:DieuLuat)
    (:DieuLuat)-[:KET_HON_KHONG_CO_YEU_TO_NUOC_NGOAI]->(:DieuLuat)
    (:DieuLuat)-[:KET_HON_KHONG_CO_YEU_TO_NUOC_NGOAI]->(:DieuKhoanLuat)

    Các node căn cứ pháp luật cần truy vấn: ["Luat_HNGD_2014_Dieu_9", "Luat_HNGD_2014_Dieu_13"]
    Thông tin về các node căn cứ pháp luật:
    Luat_HNGD_2014_Dieu_9: Đăng ký kết hôn (Quy định chung, thẩm quyền đăng ký kết hôn, thủ tục đăng ký kết hôn)
    Luat_HNGD_2014_Dieu_13: Xử lý việc đăng ký kết hôn không đúng thẩm quyền
    """

    registration_examples = """
    Câu hỏi: Kết hôn chồng cũ có được không?
    Cypher Query:
    // 1. Chọn node quy định chung
    MATCH (luat_goc:DieuLuat {id: "Luat_HNGD_2014_Dieu_9"})

    // 2. Quét dọc (Top-Down) để lấy trọn vẹn nội dung của Điều 9 (bao gồm Khoản và Điểm)
    OPTIONAL MATCH (luat_goc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_goc)

    // 3. Gom nhóm và trả về JSON gọn gàng
    WITH luat_goc,
    collect(DISTINCT {id: chi_tiet_goc.id, noi_dung: chi_tiet_goc.noidung}) AS NoiDungDieuLuat

    RETURN {
      dieu_luat_ap_dung: luat_goc.id,
      noi_dung_chinh: NoiDungDieuLuat
    } AS Context_TraLoi

    Câu hỏi: Kết hôn chồng cũ có được không và thủ tục như thế nào?
    // 1. Lấy node gốc Điều 9 (Quy định về việc đăng ký kết hôn lại)
    MATCH (luat_goc:DieuLuat {id: "Luat_HNGD_2014_Dieu_9"})

    // 2. Vét cạn chi tiết nội dung Điều 9 (Khoản, Điểm)
    OPTIONAL MATCH (luat_goc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_goc)

    // 3. Lấy thủ tục: Dùng KET_HON_KHONG_CO_YEU_TO_NUOC_NGOAI (vì câu hỏi không nói rõ có yếu tố nước ngoài hay không nên mặc định là kết hôn trong nước)
    OPTIONAL MATCH (luat_goc)-[:KET_HON_KHONG_CO_YEU_TO_NUOC_NGOAI]->(luat_thu_tuc)

    // 4. Vét cạn chi tiết các điều luật về thủ tục vừa tìm được
    OPTIONAL MATCH (luat_thu_tuc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_thu_tuc)

    // 5. Gom nhóm tách bạch giữa luật gốc và luật thủ tục
    WITH luat_goc,
        collect(DISTINCT {id: chi_tiet_goc.id, noi_dung: chi_tiet_goc.noidung}) AS NoiDungDieu9,
        collect(DISTINCT {id: chi_tiet_thu_tuc.id, noi_dung: chi_tiet_thu_tuc.noidung}) AS NoiDungThuTucTrongNuoc

    // 6. Đóng gói gọn gàng thành 1 object JSON trả về cho Agent
    RETURN {
        dieu_luat_goc: luat_goc.id,
        noi_dung_chinh: NoiDungDieu9,
        cac_quy_dinh_thu_tuc: NoiDungThuTucTrongNuoc
    } AS Context_TraLoi

    Câu hỏi: Chồng tôi là người nước ngoài, vậy khi tôi muốn đăng ký kết hôn thì thủ tục như thế nào ạ?
    Cypher Query:
    MATCH (luat_goc:DieuLuat {id: "Luat_HNGD_2014_Dieu_9"})
    OPTIONAL MATCH (luat_goc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_goc)
    OPTIONAL MATCH (luat_goc)-[:KET_HON_CO_YEU_TO_NUOC_NGOAI]->(luat_lien_quan)
    OPTIONAL MATCH (luat_lien_quan)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_lien_quan)
    WITH luat_goc,
         collect(DISTINCT {id: chi_tiet_goc.id, noi_dung: chi_tiet_goc.noidung}) AS NoiDungDieu9,
         collect(DISTINCT {id: chi_tiet_lien_quan.id, noi_dung: chi_tiet_lien_quan.noidung}) AS NoiDungLienQuanNuocNgoai
    RETURN { dieu_luat_goc: luat_goc.id, noi_dung_chinh: NoiDungDieu9, cac_quy_dinh_yeu_to_nuoc_ngoai: NoiDungLienQuanNuocNgoai } AS Context_TraLoi

    Câu hỏi: Tôi kết hôn với người trong nước nhưng đăng ký kết hôn sai thẩm quyền thì sao
    Cypher Query:
    MATCH (luat_goc:DieuLuat {id: "Luat_HNGD_2014_Dieu_13"})
    OPTIONAL MATCH (luat_goc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_goc)
    OPTIONAL MATCH (luat_goc)-[:KET_HON_KHONG_CO_YEU_TO_NUOC_NGOAI]->(luat_lien_quan)
    OPTIONAL MATCH (luat_lien_quan)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_lien_quan)
    WITH luat_goc,
         collect(DISTINCT {id: chi_tiet_goc.id, noi_dung: chi_tiet_goc.noidung}) AS NoiDungDieu13,
         collect(DISTINCT {id: chi_tiet_lien_quan.id, noi_dung: chi_tiet_lien_quan.noidung}) AS NoiDungLienQuanTrongNuoc
    RETURN { dieu_luat_goc: luat_goc.id, noi_dung_chinh: NoiDungDieu13, cac_quy_dinh_trong_nuoc: NoiDungLienQuanTrongNuoc } AS Context_TraLoi
    """

    t2c = Text2Cypher(driver)
    t2c.set_prompt_section("schema", registration_schema)
    t2c.set_prompt_section("examples", registration_examples)
    t2c.set_prompt_section("question", query)

    cypher = await t2c.generate_cypher()
    print(f"[Agent dang_ky_ket_hon] Cypher: {cypher}")

    try:
        records, _, _ = driver.execute_query(cypher)
        return [record.data() for record in records]
    except Exception as e:
        return [f"Lỗi: {e}"]
