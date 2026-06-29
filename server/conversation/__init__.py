"""ConversationOrchestrator — lớp điều phối có trạng thái phiên, điểm vào mỗi lượt chat.

Khác với các tác tử LLM-driven trong ``server.agents``, ConversationOrchestrator
không có model riêng và không tự suy luận. Lớp này giữ ba khối trạng thái:
``session_history``, ``retrieval_memory`` và ``conversation_anchors``. Mỗi lượt
người dùng, orchestrator dựng lịch sử rút gọn, gọi RouterAgent, cập nhật bộ nhớ
và uỷ thác sinh câu trả lời cho SynthesizerAgent — tương ứng cách LangChain mô
tả *external state management* bọc quanh Router stateless.
"""
