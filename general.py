from agents.text2cypher import Text2Cypher
from config import driver

answer_given_description = {
    "type": "function",
    "function": {
        "name": "respond",
        "description": "Nếu cuộc hội thoại đã chứa một câu trả lời hoàn chỉnh cho câu hỏi, hãy sử dụng công cụ này để trích xuất nó. Ngoài ra, nếu người dùng trò chuyện phiếm, hãy dùng công cụ này để nhắc họ rằng bạn chỉ có thể trả lời các câu hỏi liên quan đến luật hôn nhân gia đình.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "Phản hồi trực tiếp bằng câu trả lời",
                }
            },
            "required": ["answer"],
        },
    },
}

async def answer_given(answer: str, **kwargs):
    """Trích xuất câu trả lời từ đoạn văn bản đã cho."""
    return answer

text2cypher_description = {
    "type": "function",
    "function": {
        "name": "text2cypher",
        "description": "Truy vấn cơ sở dữ liệu đồ thị bằng câu hỏi của người dùng. Khi các công cụ khác không phù hợp, hãy sử dụng công cụ này làm phương án dự phòng (fallback).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi của người dùng cần tìm câu trả lời",
                }
            },
            "required": ["query"],
        },
    },
}

async def text2cypher(query: str, **kwargs):
    """Truy vấn cơ sở dữ liệu bằng câu hỏi của người dùng."""
    t2c = Text2Cypher(driver)
    t2c.set_prompt_section("question", query)
    cypher = await t2c.generate_cypher()
    try:
        records, _, _ = await driver.execute_query(cypher)
        print('neo4j data:', [record.data() for record in records])
        return [record.data() for record in records]
    except Exception as e:
        return [f"Câu lệnh {cypher} gây ra lỗi: {e}"]