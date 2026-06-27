# Kiến trúc Gói (Architecture Packages) - Agentic GraphRAG

Tài liệu này mô tả chi tiết cấu trúc phân rã theo gói (packages) của dự án Chatbot tư vấn luật. Hệ thống chia thành 4 lớp chính với quy tắc "gói vòng ngoài gọi vào gói vòng trong", nhằm cô lập thư viện và logic nghiệp vụ.

## Sơ đồ phụ thuộc (Dependency)
`presentation`, `adapter` --> `application`
(Gói `utils` cung cấp tiện ích cho tất cả các gói).

---

## Chi tiết các Package

### 1. `application` (Lớp Ứng dụng / Use Case)
- **Mục đích:** Đóng vai trò điều phối luồng làm việc của Chatbot.
- **Nhiệm vụ:** 
  - Chứa bộ não Agentic Workflow: Router chọn tool (`router.py`), catalog retriever (`retriever_catalog.py`), hợp nhất context pháp lý (`legal_context.py`).
- **Phụ thuộc:** Phụ thuộc `utils`; không gọi trực tiếp Neo4j driver.

### 2. `adapter` (Lớp Hạ tầng / Adapter)
- **Mục đích:** Tương tác trực tiếp với Database, AI Model API và framework bên ngoài.
- **Nhiệm vụ:**
  - Kết nối Neo4j GraphDB (`config.py`).
  - Direct tools Chainlit: `clarify`, `respond` (`direct_tools.py`).
  - Kết nối PostgreSQL để tracking lịch sử (`data_layer.py`, `init_db.py`).
  - Cài đặt chi tiết cho các `retrievers` và `cypher_templates` theo chủ đề pháp lý.
- **Phụ thuộc:** Được `presentation` inject vào registry tool; không được các gói application gọi ngược trực tiếp ngoài luồng tool execution.

### 3. `presentation` (Lớp Trình diễn / Giao diện & Controllers)
- **Mục đích:** Giao tiếp với Client / Người dùng.
- **Nhiệm vụ:**
  - Cung cấp User Interface (Chainlit UI qua `main.py`).
  - Chứa các Hooks bắt sự kiện hội thoại (on_chat_start, on_message).
  - Đăng ký 22 tool (20 retriever + `clarify` + `respond`) qua `build_presentation_tools()`.
- **Phụ thuộc:** Gọi `application` để chạy Router/workflow và `adapter` qua registry tool.

### 4. `utils` (Lớp Dùng Chung / Utilities)
- **Mục đích:** Module tái sử dụng mã thuần tiện ích.
- **Nhiệm vụ:** Chuẩn hóa context pháp lý, helper string/regex, codec bundle (`legal_context_codec.py`).
- **Phụ thuộc:** Không phụ thuộc logic gói nghiệp vụ; được mọi lớp khác import khi cần.
