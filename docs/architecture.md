# Tài liệu Thiết kế Kiến trúc Hệ thống

## 1. Tổng quan
Hệ thống là một Agentic GraphRAG Chatbot hỗ trợ tra cứu và tư vấn Luật Hôn nhân và Gia đình Việt Nam. 
Hệ thống được chuyển đổi từ giao diện CLI (Command Line Interface) sang giao diện Web sử dụng **Chainlit**, đồng thời tích hợp **PostgreSQL** để theo dõi trạng thái, lưu vết (tracing) và quản lý lịch sử hội thoại.

## 2. Các thành phần chính

### 2.1. Frontend (Web Chatbot UI)
Sử dụng **Chainlit** - một open-source Python framework để xây dựng Chatbot UI nhanh chóng.
- **Tính năng:**
    - Giao diện chat trực quan với người dùng.
    - Hiển thị tường minh luồng xử lý (Thought Process) thông qua `cl.Step`: Người dùng thấy hệ thống đang phân tích câu hỏi, chọn tool nào, và đang truy vấn dữ liệu gì.
    - Quản lý phiên hỏi đáp (Session/Threats).
    - Hỗ trợ đánh giá (Feedback) câu trả lời hoặc các thao tác trung gian.
    - **Tích hợp Đăng nhập (OAuth):** Nút tắt/đăng xuất/đăng nhập Google, tự động xác định danh tính User.
    - **Lịch sử Sidebar:** Hiển thị lịch sử các đoạn chat cũ qua cơ chế `on_chat_resume`.

### 2.2. Backend (Agentic Workflow)
- **Orchestrator:** Hàm xử lý sự kiện `on_message` của Chainlit đóng vai trò điều phối pipeline.
- **Pipeline:** Xử lý tuần tự và linh hoạt:
    1. **Query Update:** Làm rõ câu hỏi hiện tại dựa trên ngữ cảnh lịch sử.
    2. **Router:** Dùng LLM quyết định các tools/retrievers nào được gọi.
    3. **Tools/Retrievers execution:** Gọi Neo4j / search để lấy context pháp lý.
    4. **Generate Answer:** Tổng hợp context và sinh câu trả lời bằng tiếng Việt.
- **LLM/LangChain Engine:** Giao tiếp với các mô hình ngôn ngữ lớn (ChatGroq, GPT...) để thực hiện suy luận.

### 2.3. Storage (Database Layer)
- **Knowledge Graph (Neo4j):** CSDL đồ thị chứa các Điều luật, Khoản luật, Văn bản pháp quy và mối quan hệ pháp lý.
- **Persistence & Tracing (PostgreSQL):** PostgreSQL kết hợp với SQL Alchemy (thông qua Custom Data Layer của Chainlit) để quản lý:
    - User Authentication / Profiles
    - Lịch sử Thread / Sessions
    - Data Tracing: input/output của router, query updater, retrievals...
