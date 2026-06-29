"""Direct tool ``respond`` — trả thẳng câu trả lời Router lấy từ lịch sử.

Tách từ ``adapter/direct_tools.py`` trong Phase 3 refactor (không gọi LLM/retriever).
"""
from __future__ import annotations

from server.agents.base import Agent

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


class RespondAgent(Agent):
    """Direct tool ``respond`` dạng Agent — ủy quyền cho ``answer_given``."""

    name = "respond"
    description = answer_given_description

    async def run(self, answer: str, **kwargs):
        return await answer_given(answer, **kwargs)
