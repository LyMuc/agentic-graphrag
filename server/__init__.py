"""Server package — gốc của backend sau refactor theo Router + Subagents pattern.

Cây thư mục mục tiêu:

```
server/
    app/             Lớp ứng dụng Chainlit + FastAPI route
    conversation/    ConversationOrchestrator — điều phối phiên (deterministic, không LLM)
    agents/          Router / Synthesizer / Retriever (Subagents) / Direct tools
    domain/          Kiểu dữ liệu pháp lý thuần (legal bundle, render, warning)
    infrastructure/  Adapter ra ngoài: LLM, Neo4j, Postgres, viz store
    interface/       OpenAI tool schema dùng cho Router LLM
    shared/          Tiện ích chéo lớp (phrase match, datetime VN)
```

Mỗi sub-package nhập ý niệm đúng một tầng kiến trúc và chỉ phụ thuộc tầng dưới.
"""
