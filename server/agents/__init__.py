"""Tầng tác tử LLM-driven — hiện thực Router + Subagents pattern.

Điều phối phiên (session state, lifecycle) nằm ở ``server.conversation.ConversationOrchestrator``,
không thuộc gói này vì orchestrator không có model LLM riêng.

- `router.RouterAgent` không có trạng thái, nhận câu hỏi cùng bộ nhớ, chọn  zero hoặc nhiều `RetrieverAgent` chạy song song qua tool calling.
- `retrievers.RetrieverAgent` là tác tử con (Subagent) đại diện cho một
  miền pháp lý; bên trong mỗi retriever có quy trình ba bước phân loại
  template → trích xuất tham số → thực thi Cypher.
- `synthesizer.SynthesizerAgent` tổng hợp câu trả lời cuối từ ngữ cảnh
  hợp nhất.
- `direct.RespondAgent` / `direct.ClarifyAgent` là hai tác tử phản hồi
  trực tiếp (exclusive) khi Router chọn `respond` hoặc `clarify`.
"""

from server.agents.base import Agent, RetrieverResult, ToolCall

__all__ = ["Agent", "RetrieverResult", "ToolCall"]
