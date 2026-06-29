# Tài liệu lựa chọn và mô tả kiến trúc phần mềm

## 1) Kiến trúc phần mềm được lựa chọn

Ứng dụng chọn **kiến trúc phân lớp (Layered Architecture)** theo hướng **Modular Monolith**, trong đó lớp nghiệp vụ trung tâm là **Agentic GraphRAG**.

Giải thích ngắn gọn:
- **Layered**: hệ thống được tách thành các lớp có vai trò rõ ràng (giao diện, điều phối nghiệp vụ, truy xuất tri thức, dữ liệu).
- **Modular Monolith**: toàn bộ thành phần chạy trong một dịch vụ Python duy nhất, nhưng chia module độc lập theo chức năng.
- **Agentic GraphRAG**: thay vì truy vấn văn bản thuần túy, hệ thống dùng agent/router để chọn tool phù hợp và truy xuất dữ liệu pháp luật từ đồ thị Neo4j.

Lý do chọn kiến trúc này cho bài toán:
- Bài toán pháp lý cần truy xuất căn cứ có cấu trúc (Điều/Khoản/Điểm, tham chiếu, hiệu lực theo thời gian), phù hợp với GraphRAG.
- Dễ phát triển và vận hành cho quy mô đồ án (không cần tách microservice ngay từ đầu).
- Dễ mở rộng theo module retriever chuyên đề pháp luật.

---

## 2) Mô tả kiến trúc cụ thể của ứng dụng

### 2.1. Ánh xạ kiến trúc lý thuyết vào hệ thống

Thay vì mô hình MVC thuần, hệ thống áp dụng Layered theo các lớp cụ thể sau:

1. **App / Presentation Layer (Giao diện)**
   - Thành phần: Chainlit Web Chat UI, hooks vòng đời chat.
   - File chính: `server/app/main.py`
   - Nhiệm vụ: nhận câu hỏi người dùng, hiển thị tiến trình xử lý (`cl.Step`), gửi trả câu trả lời.

2. **Conversation/Orchestration Layer (Điều phối)**
   - Thành phần: `ConversationOrchestrator` (deterministic, KHÔNG có LLM riêng).
   - File chính: `server/conversation/orchestrator.py`
   - Nhiệm vụ: điều phối chuỗi xử lý `router -> tools/retrievers -> tổng hợp đáp án`.

3. **Agent/Domain Service Layer (Nghiệp vụ pháp lý)**
   - Thành phần:
     - Router Agent: `server/agents/router/agent.py`
     - Retriever catalog: `server/agents/router/catalog.py`
     - Domain Retrievers: `server/agents/retrievers/` + `server/infrastructure/neo4j/cypher_templates/`
     - Synthesizer Agent: `server/agents/synthesizer/agent.py`
     - Direct tools: `server/agents/direct/` (`clarify`, `respond`)
   - Nhiệm vụ: hiểu ý định pháp lý, chọn công cụ phù hợp, thực thi Cypher template và lấy đúng ngữ cảnh pháp lý.

4. **Data Access & Infrastructure Layer (Dữ liệu - hạ tầng)**
   - Thành phần:
     - Kết nối LLM: `server/infrastructure/llm/factory.py`; Neo4j driver: `server/infrastructure/neo4j/client.py`
     - Chainlit SQLAlchemy Data Layer (PostgreSQL): `server/infrastructure/persistence/data_layer.py`
   - Nhiệm vụ: truy cập CSDL đồ thị pháp luật, lưu thread/steps lịch sử chat.

### 2.2. Luồng xử lý nghiệp vụ chính

1. Người dùng nhập câu hỏi từ UI.
2. Router (`server/agents/router/agent.py`) dùng LLM tool-calling để chọn một hoặc nhiều retriever, hoặc direct tool `clarify`/`respond`.
3. Retriever thực thi Cypher template trên Neo4j và trả `Context_Tho` / `LEGAL_CONTEXT_BUNDLE_V1`.
4. Hệ thống hợp nhất context qua `server/domain/legal/bundle.py` và gọi LLM sinh câu trả lời cuối cùng.
5. Dữ liệu hội thoại và các bước xử lý được lưu qua PostgreSQL data layer (user đăng nhập; guest không persist).

---

## 3) Thành phần cụ thể trong kiến trúc của sinh viên

### 3.1. Thành phần tương ứng lớp giao diện
- `server/app/main.py`
  - `@cl.on_chat_start`, `@cl.on_chat_resume`, `@cl.on_message` — mỗi hook delegate sang `ConversationOrchestrator`.
  - Vai trò: entrypoint, quản lý session, tiếp nhận yêu cầu và hiển thị phản hồi.

### 3.2. Thành phần tương ứng lớp điều phối ứng dụng
- `server/conversation/orchestrator.py` (lớp `ConversationOrchestrator`)
  - `route_question_with_audit(...)` từ `server/agents/router/agent.py`
  - Vai trò: workflow orchestration của toàn bộ phiên hỏi đáp (deterministic, không có LLM riêng).

### 3.3. Thành phần tương ứng lớp nghiệp vụ/miền pháp lý
- **Interface mức công cụ (tool contract)**: các biến `*_description` theo chuẩn function-calling JSON schema.
  - Ví dụ: `dieu_kien_ket_hon_description`, `xu_phat_vi_pham_description`, `clarify_description`, `answer_given_description`.
- **Các lớp/hàm triển khai nghiệp vụ cụ thể**:
  - Retriever theo chủ đề trong `server/agents/retrievers/` (mỗi lớp kế thừa `RetrieverAgent`)
  - Direct tools `clarify_question`, `answer_given` trong `server/agents/direct/`

=> Có thể xem tương đương tư duy “I + C1 + C2...” như sau:
- **I (hợp đồng tool)**: `*_description` (mô tả tên, tham số, mục đích tool).
- **C1..Cn (triển khai cụ thể)**: các hàm retriever và direct tool.

### 3.4. Thành phần tương ứng lớp dữ liệu
- `server/infrastructure/neo4j/client.py`: tạo `driver` Neo4j; `server/infrastructure/llm/factory.py`: hàm `chat(...)` kết nối LLM.
- `server/infrastructure/persistence/data_layer.py`: khởi tạo `SQLAlchemyDataLayer` cho PostgreSQL.
- Neo4j giữ tri thức pháp luật dạng đồ thị; PostgreSQL giữ metadata hội thoại và tracing.

---

## 4) Điều chỉnh/cải tiến so với lý thuyết chung

So với Layered truyền thống, hệ thống có các cải tiến:
- **Bổ sung lớp Router Agent** để quyết định động tool cần gọi thay vì if-else cứng.
- **Tách retriever theo miền nghiệp vụ pháp lý** (kết hôn, vi phạm...) để dễ bảo trì và mở rộng.
- **Kết hợp GraphRAG + kiểm soát căn cứ pháp lý theo thời gian hiệu lực** (đặc biệt ở module xử phạt vi phạm).
- **Tăng tính minh bạch xử lý** bằng `cl.Step`, giúp theo dõi từng bước suy luận/truy xuất.

---

## 5) Kết luận ngắn

Ứng dụng phù hợp với kiến trúc **Layered Modular Monolith tích hợp Agentic GraphRAG**.  
Kiến trúc này cân bằng giữa tính rõ ràng học thuật, khả năng mở rộng theo module pháp lý và độ phù hợp với phạm vi triển khai của một đồ án chatbot tư vấn luật.
