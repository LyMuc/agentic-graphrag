"""Định nghĩa nền móng cho mọi tác tử trong server.

Module này khai báo kiểu dữ liệu chung được Router LLM và các retriever sử dụng,
cùng lớp cơ sở trừu tượng `Agent`. Tất cả tác tử cụ thể (Conversation, Router,
Retriever, Synthesizer, các direct tool) đều phải kế thừa `Agent` để giữ một
giao diện ``async run`` thống nhất.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict


class ToolCall(TypedDict, total=False):
    """Tool call do Router LLM trả về.

    Schema khớp với khuôn dạng OpenAI/LangChain. Các trường điều khiển bổ
    sung (`confidence_score`, `context_action`, `context_refs`, `time_scope`,
    `target_date`) nằm bên trong ``args``.
    """

    name: str
    args: dict[str, Any]
    id: str
    type: str


class RetrieverResult(TypedDict, total=False):
    """Kết quả chuẩn của một `RetrieverAgent`.

    Trường ``contexts`` chứa danh sách ``LEGAL_CONTEXT_BUNDLE_V1`` đã mã hoá
    hoặc chuỗi ngữ cảnh legacy. Trường ``debug`` được hiển thị ở Chainlit step
    expert mode. Các trường ``retriever_name``, ``resolved_query``,
    ``cache_status`` và ``context_refs_used`` được Router gắn vào trước khi
    trả về cho ConversationOrchestrator.
    """

    contexts: list[str]
    debug: str
    retriever_name: str
    resolved_query: str
    cache_status: str
    cache_fallback_reason: str
    context_refs_used: list[str]
    graph_viz_id: str


class Agent(ABC):
    """Lớp cơ sở cho mọi tác tử.

    Mỗi tác tử nhận đầu vào không đồng nhất và trả kết quả có cấu trúc.
    Cài đặt cụ thể sẽ định nghĩa lại chữ ký ``run`` cho phù hợp với vai trò
    riêng (ví dụ: `RouterAgent.run` nhận câu hỏi + bộ nhớ + lịch sử và trả
    danh sách `RetrieverResult`, còn `RetrieverAgent.run` nhận một câu hỏi
    và trả về duy nhất một `RetrieverResult`).
    """

    name: str

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Hàm điểm vào duy nhất, bắt buộc cài đặt."""
        raise NotImplementedError
