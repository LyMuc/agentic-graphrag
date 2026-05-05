from agents.text2cypher import Text2Cypher
from config import driver

chung_song_nhu_vo_chong_description = {
    "type": "function",
    "function": {
        "name": "chung_song_nhu_vo_chong",
        "description": "Lấy thông tin quy định về Giải quyết hậu quả; Xác định quyền, nghĩa vụ của cha mẹ và con và Giải quyết quan hệ tài sản, nghĩa vụ và hợp đồng trong trường hợp nam, nữ chung sống với nhau như vợ chồng mà không đăng ký kết hôn.",
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

async def chung_song_nhu_vo_chong(query: str):
    """
    Tool xử lý các vấn đề về nam nữ chung sống như vợ chồng mà không đăng ký kết hôn.
    """
    print(f"[Agent chung_song_nhu_vo_chong] Đang xử lý: '{query}'...")

    schema_cohabitation = """
    Thuộc tính của node (properties):
    DieuKhoanLuat {id: STRING, chuong: STRING, dieu: STRING, khoan: STRING, noidung: STRING}
    DieuLuat {id: STRING, chuong: STRING, dieu: STRING, noidung: STRING}
    DieuKhoanDiemLuat {id: STRING, chuong: STRING, dieu: STRING, khoan: STRING, noidung: STRING, diem: STRING}

    Các mối quan hệ (The relationships):
    (:DieuKhoanLuat)-[:CO_DIEM]->(:DieuKhoanDiemLuat)
    (:DieuLuat)-[:CO_KHOAN]->(:DieuKhoanLuat)

    Các node căn cứ pháp luật cần truy vấn: [\"Dieu_14\", \"Dieu_15\", \"Dieu_16\"]
    Thông tin về các node căn cứ pháp luật:
    Dieu_14: Giải quyết hậu quả của việc nam, nữ chung sống với nhau như vợ chồng mà không đăng ký kết hôn
    Dieu_15: Quyền, nghĩa vụ của cha mẹ và con trong trường hợp nam, nữ chung sống với nhau như vợ chồng mà không đăng ký kết hôn
    Dieu_16: Giải quyết quan hệ tài sản, nghĩa vụ và hợp đồng của nam, nữ chung sống với nhau như vợ chồng mà không đăng ký kết hôn
    """

    examples_cohabitation = """
    Câu hỏi: Nam nữ chung sống như vợ chồng mà không đăng ký kết hôn thì có làm phát sinh quyền nghĩa vụ giữa vợ và chồng không?
    Cypher query:
    MATCH (luat_goc:DieuLuat {id: "Dieu_14"})
    OPTIONAL MATCH (luat_goc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_goc)
    OPTIONAL MATCH (chi_tiet_goc)-[:THAM_CHIEU_DEN]-(luat_tham_chieu)
    OPTIONAL MATCH (luat_tham_chieu)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_tham_chieu)
    WITH luat_goc,
         collect(DISTINCT {id: chi_tiet_goc.id, noi_dung: chi_tiet_goc.noidung}) AS NoiDungDieu14,
         collect(DISTINCT {id: chi_tiet_tham_chieu.id, noi_dung: chi_tiet_tham_chieu.noidung}) AS NoiDungThamChieu
    RETURN {
        dieu_luat_goc: luat_goc.id,
        noi_dung_chinh: NoiDungDieu14,
        cac_quy_dinh_tham_chieu: NoiDungThamChieu
    } AS Context_TraLoi
    """

    t2c = Text2Cypher(driver)
    t2c.set_prompt_section("schema", schema_cohabitation)
    t2c.set_prompt_section("examples", examples_cohabitation)
    t2c.set_prompt_section("question", query)

    cypher = await t2c.generate_cypher()
    print(f"[Agent chung_song_nhu_vo_chong] Cypher: {cypher}")

    try:
        records, _, _ = driver.execute_query(cypher)
        return [record.data() for record in records]
    except Exception as e:
        return [f"Lỗi: {e}"]
