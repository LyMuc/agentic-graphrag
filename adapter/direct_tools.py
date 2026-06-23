from adapter.text2cypher import Text2Cypher
from adapter.config import driver

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
    """Trả trực tiếp câu trả lời Router đã lấy được từ lịch sử.

    Args:
        answer: Nội dung phản hồi hoàn chỉnh do Router cung cấp.
        **kwargs: Tham số điều khiển tùy chọn từ Router; bị bỏ qua để giữ tương
            thích với tool schema mở rộng.

    Returns:
        Chính chuỗi ``answer`` mà không gọi thêm LLM hoặc retriever.
    """
    return answer


clarify_description = {
    "type": "function",
    "function": {
        "name": "clarify",
        "description": (
            "Hỏi lại người dùng khi câu follow-up có từ hai cách hiểu hợp lý trở lên "
            "và lịch sử gần cùng chỉ mục lượt cũ không đủ để xác định chắc chắn. "
            "Không dùng nếu câu hỏi tự nó đã đầy đủ hoặc có thể trả lời theo các trường hợp."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Một câu hỏi làm rõ ngắn, nêu cụ thể các cách hiểu cần chọn.",
                }
            },
            "required": ["question"],
        },
    },
}


async def clarify_question(question: str, **kwargs):
    """Trả trực tiếp câu hỏi làm rõ mà không gọi retriever hay Response LLM.

    Args:
        question: Câu hỏi ngắn yêu cầu người dùng xác định đối tượng, mốc thời
            gian hoặc ý hỏi đang mơ hồ.
        **kwargs: Tham số điều khiển tùy chọn từ Router; bị bỏ qua.

    Returns:
        Chính chuỗi ``question`` để Chainlit gửi trực tiếp cho người dùng.
    """

    return question

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
    """Sinh và thực thi Cypher fallback cho câu hỏi ngoài retriever chuyên biệt.

    Args:
        query: Câu hỏi độc lập đã được Router giải nghĩa.
        **kwargs: Tham số điều khiển tùy chọn từ Router; bị bỏ qua.

    Returns:
        Danh sách record Neo4j dưới dạng dictionary, hoặc một phần tử chuỗi mô
        tả lỗi Cypher khi truy vấn thất bại.
    """
    t2c = Text2Cypher(driver)
    t2c.set_prompt_section("question", query)
    cypher = await t2c.generate_cypher()
    try:
        records, _, _ = await driver.execute_query(cypher)
        print('neo4j data:', [record.data() for record in records])
        return [record.data() for record in records]
    except Exception as e:
        return [f"Câu lệnh {cypher} gây ra lỗi: {e}"]
