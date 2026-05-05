from agents.text2cypher import Text2Cypher
from config import driver

dieu_kien_ket_hon_description = {
    "type": "function",
    "function": {
        "name": "dieu_kien_ket_hon",
        "description": "Lấy thông tin quy định pháp luật về điều kiện kết hôn, các trường hợp cấm kết hôn.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi cụ thể của người dùng",
                }
            },
            "required": ["query"],
        },
    },
}

async def dieu_kien_ket_hon(query: str):
    """
    Tool đóng vai trò agent: sinh Cypher dựa trên schema đặc thù cho kết hôn và thực thi.
    """
    print(f"[Agent dieu_kien_ket_hon] Đang xử lý truy vấn: '{query}'...")

    marriage_schema = """
    Thuộc tính của node (properties):
    DieuKhoanLuat {id: STRING, chuong: STRING, dieu: STRING, khoan: STRING, noidung: STRING}
    DieuLuat {id: STRING, chuong: STRING, dieu: STRING, noidung: STRING}
    DieuKhoanDiemLuat {id: STRING, chuong: STRING, dieu: STRING, khoan: STRING, noidung: STRING, diem: STRING}

    Các mối quan hệ (The relationships):
    (:DieuKhoanLuat)-[:CO_DIEM]->(:DieuKhoanDiemLuat)
    (:DieuLuat)-[:CO_KHOAN]->(:DieuKhoanLuat)
    (:DieuKhoanLuat)-[:THAM_CHIEU_DEN]->(:DieuKhoanDiemLuat)
    (:DieuKhoanLuat)-[:THAM_CHIEU_DEN]->(:DieuLuat)

    Các node căn cứ pháp luật cần truy vấn: ["Dieu_8"]
    Thông tin về các node căn cứ pháp luật:
    Dieu_8: Điều kiện kết hôn (Độ tuổi, tự nguyện, năng lực hành vi, không thuộc trường hợp cấm).
    """

    example_marriage = """
    Câu hỏi: Điều kiện kết hôn theo quy định pháp luật là gì?
    Suy luận: Câu hỏi hỏi về điều kiện kết hôn cơ bản, tương ứng với "Dieu_8". Tôi sẽ chọn id "Dieu_8" làm gốc.
    Query Cypher:
    // 1. Chọn node gốc dựa trên ID đã xác định
    MATCH (luat_goc:DieuLuat {id: "Dieu_8"})

    // 2. Lấy toàn bộ nội dung của Điều luật gốc (bao gồm chính nó, Khoản và Điểm)
    OPTIONAL MATCH (luat_goc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_goc)

    // 3. Tìm các điều luật tham chiếu chéo (THAM_CHIEU_DEN) - Ví dụ Điều 8 dẫn chiếu sang Điều 5.
    OPTIONAL MATCH (chi_tiet_goc)-[:THAM_CHIEU_DEN]->(luat_THAM_CHIEU_DEN)

    // 4. Nếu có luật liên quan, vét sạch Khoản/Điểm của luật liên quan đó
    OPTIONAL MATCH (luat_THAM_CHIEU_DEN)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_THAM_CHIEU_DEN)

    // 5. Gom nhóm trả về JSON
    WITH luat_goc,
         collect(DISTINCT {id: chi_tiet_goc.id, noi_dung: chi_tiet_goc.noidung}) AS NoiDungDieuLuatChinh,
         collect(DISTINCT {id: chi_tiet_THAM_CHIEU_DEN.id, noi_dung: chi_tiet_THAM_CHIEU_DEN.noidung}) AS NoiDungThamChieu

    RETURN {
        dieu_luat_ap_dung: luat_goc.id,
        noi_dung_chinh: NoiDungDieuLuatChinh,
        cac_quy_dinh_tham_chieu: NoiDungThamChieu
    } AS Context_TraLoi
    """

    t2c = Text2Cypher(driver)
    t2c.set_prompt_section("schema", marriage_schema)
    t2c.set_prompt_section("examples", example_marriage)
    t2c.set_prompt_section("question", query)

    cypher = await t2c.generate_cypher()
    print(f"[Agent dieu_kien_ket_hon] Cypher generated: {cypher}")

    try:
        records, _, _ = driver.execute_query(cypher)
        result = [record.data() for record in records]
        print(f"[Agent dieu_kien_ket_hon] Tìm thấy {len(result)} kết quả.")
        return result
    except Exception as e:
        return [f"Lỗi khi truy vấn dữ liệu kết hôn: {e}"]
