"""Lớp cơ sở trừu tượng cho mọi Subagent truy xuất (RetrieverAgent).

Mỗi RetrieverAgent là một mini-supervisor stateless theo pattern Subagents:
``classify`` (chọn template Cypher) → ``extract`` (trích tham số) → ``execute``
(chạy Cypher) → ``run`` (ghép pipeline, encode ``LegalContextBundle``). Các
retriever cụ thể trong gói này ủy quyền các bước cho hàm module đã kiểm chứng,
giữ contract thống nhất ``run(query) -> RetrieverResult``.
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any

from server.agents.base import Agent, RetrieverResult

__all__ = ["RetrieverAgent", "RetrieverResult"]


class RetrieverAgent(Agent):
    """Subagent truy xuất một miền pháp lý.

    Thuộc tính:
        name: Khóa định danh retriever (khớp tên tool ở Router).
        description: Tool schema kiểu OpenAI để Router quảng bá cho LLM.
    """

    name: str
    description: dict

    @abstractmethod
    async def classify(self, query: str) -> Any:
        """Chọn 1..n template Cypher phù hợp câu hỏi."""
        raise NotImplementedError

    @abstractmethod
    async def extract(self, query: str, template: Any) -> Any:
        """Trích tham số + mốc thời gian cho một template."""
        raise NotImplementedError

    @abstractmethod
    async def execute(self, template: Any, params: Any, target_date: str) -> Any:
        """Chạy Cypher của template với tham số đã trích."""
        raise NotImplementedError

    @abstractmethod
    async def run(self, query: str) -> RetrieverResult:
        """Ghép toàn bộ pipeline classify→extract→execute→encode."""
        raise NotImplementedError
