# Kiến trúc hệ thống (tóm tắt)

Rút gọn từ [integration.md](../integration.md) và [README.md](../README.md).

## Luồng một câu hỏi

```text
Người dùng (Chainlit UI)
    → presentation/main.py
    → application/router.py (Router LLM chọn tool)
    → adapter/retrievers/* (Retriever LLM + Cypher → Neo4j)
    → utils/utils.py (chuan_hoa_Context_cho_LLM)
    → Response LLM stream câu trả lời
```

## Lớp phần mềm (server)

| Lớp | Thư mục | Vai trò |
|---|---|---|
| Presentation | `presentation/` | Chainlit hooks, registry tools, OAuth |
| Application | `application/` | Router, retriever catalog/policy |
| Adapter | `adapter/` | Neo4j/LLM config, retrievers, cypher templates |
| Utils | `utils/` | Text2cypher, chuẩn hóa context, tiện ích |

## Dữ liệu

- **Neo4j**: đồ thị pháp luật + KG ngữ nghĩa theo topic (semantic nodes + `CAN_CU_TAI`).
- **PostgreSQL**: Chainlit threads/steps (lịch sử hội thoại).
- **Vercel AI Gateway**: Router / Retriever / Response LLM.

## Agentic GraphRAG

- Router chọn **một hoặc nhiều** retriever, chạy **song song**.
- Mỗi retriever: structured output `TrichXuatLuat` (điều luật IDs + `thoi_diem_su_kien`) → Cypher → `Context_Tho`.
- Fallback: `text2cypher` khi không khớp domain.

## Liên hệ đồ án

- Chương 4: kiến trúc client–server, package diagram, Agentic workflow.
- Chương 5: legal reasoning, Cypher templates, benchmark.
