# Tài liệu Thiết kế Cơ sở dữ liệu (Database Schema)

Hệ thống sử dụng Data Layer mô hình hóa qua SQLAlchemy của Chainlit để tương tác với **PostgreSQL**. Điều này đảm bảo toàn bộ tin nhắn, session và context trung gian (steps) được lưu tự động cho quá trình truy vết/kiểm thử.

Dưới đây là các bảng (tables) chính trong PostgreSQL do Chainlit quản lý:

### 1. Bảng `users`
Lưu trữ thông tin người dùng hệ thống.
- `id` (UUID): Khóa chính.
- `identifier` (String): ID định danh hoặc username (vd: email lấy từ OAuth Google/Github).
- `metadata` (JSONB): Thông tin bổ sung của người dùng (như avatar_url, provider).
- `createdAt` (String): Thời gian tạo.

### 2. Bảng `threads` (Sessions)
Đại diện cho một phiên hỏi đáp/hội thoại của người dùng.
- `id` (UUID): Khóa chính (Thread ID).
- `createdAt` (String): Thời gian tạo.
- `name` (String): Tên của thread (có thể tự sinh từ câu hỏi đầu tiên).
- `user_id` (UUID): Foreign Key tới bảng `users`.
- `user_id_identifier` (String): Alias cho User Identifier.
- `tags` (Array): Các tag phân loại.
- `metadata` (JSONB): Metadata bổ sung của session.

### 3. Bảng `steps` (Messages & Tracing)
Đây là bảng **QUAN TRỌNG NHẤT** phục vụ mục đích Debug/Evaluation. Lưu trữ tin nhắn của User, Assistant, cũng như các hành động (Tool call, Router logic, LLM Prompt).
- `id` (UUID): Khóa chính.
- `name` (String): Tên bước (vd: `user`, `assistant`, `Query Updater`, `Khởi chạy Router`, `Truy vấn Điều kiện kết hôn`).
- `type` (String): user_message, assistant_message, tool, llm, run.
- `thread_id` (UUID): Foreign Key tới `threads`.
- `parent_id` (UUID): ID của bước cha (giúp tạo dạng cây chain/suy nghĩ).
- `input` (Text): Dữ liệu truyền vào (vd: Prompt truyền cho Router).
- `output` (Text): Dữ liệu trả ra (vd: Danh sách công cụ Router quyết định).
- `createdAt` (String): Thời điểm bắt đầu.
- `start` (String): Thời gian chạy.
- `end` (String): Thời gian kết thúc (để đo tốc độ tool).
- `isError` (Boolean): Đánh dấu lỗi nếu có.
- `language` (String): Ngôn ngữ.

### 4. Bảng `feedbacks`
Lưu trữ đánh giá của người dùng (nếu bạn bật tính năng đánh giá trên UI).
- `id` (UUID): Khóa chính.
- `forId` (UUID): Foreign key tới bảng `steps` (vd: ID của câu trả lời).
- `value` (Integer): Thường là 1 (Upvote) hoặc 0 (Downvote).
- `comment` (Text): Feedback chi tiết từ người dùng.

---
**Quy trình Mapping với Source Code:**
1. Khi Agent **Query Updater** chạy: Ta tạo một `cl.Step(name="Query Updater", type="tool")`. Chainlit sẽ tự động INSERT 1 row vào bảng `steps` lưu lại câu hỏi ban đầu -> câu hỏi đã chuẩn hóa (output).
2. Khi Tool **Router** chạy: Ta tạo `cl.Step(name="Router")`. Bảng `steps` ghi nhận Input (câu hỏi chuẩn hóa) -> Output (danh sách Retrievers được gọi).
3. Các context pháp lý sinh từ Retriever sẽ chạy dưới danh nghĩa Step con của Router, lưu kết quả text vào `output`. 
Việc này hoàn toàn tự động nhờ Chainlit Data Layer.
