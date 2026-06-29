"""Direct tool ``clarify`` — hỏi lại khi câu follow-up mơ hồ.

Tách từ ``adapter/direct_tools.py`` trong Phase 3 refactor (không gọi LLM/retriever).
"""
from __future__ import annotations

from server.agents.base import Agent

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


class ClarifyAgent(Agent):
    """Direct tool ``clarify`` dạng Agent — ủy quyền cho ``clarify_question``."""

    name = "clarify"
    description = clarify_description

    async def run(self, question: str, **kwargs):
        return await clarify_question(question, **kwargs)
