# Agentic GraphRAG Chatbot Luật 

Hệ thống Chatbot vấn đáp pháp luật Việt Nam thông minh, ứng dụng kiến trúc **Agentic GraphRAG** (Retrieval-Augmented Generation kết hợp Knowledge Graph và AI Agent). 

Hệ thống cho phép tra cứu, giải đáp các vấn đề pháp lý (chủ đề Hôn nhân & Gia đình, Xử phạt vi phạm hành chính,...) một cách chính xác dựa trên cơ sở dữ liệu đồ thị (Neo4j) thay vì chỉ tìm kiếm văn bản thuần túy.

---

## Tính Năng Nổi Bật

- **Agentic Router**: Sử dụng LLM để tự động phân tích ý định câu hỏi và điều hướng (route) đến các bộ truy xuất (retriever) chuyên biệt (ví dụ: điều kiện kết hôn, xử phạt vi phạm,...).
- **GraphRAG (Text2Cypher)**: Chuyển đổi ngôn ngữ tự nhiên thành câu lệnh Cypher để truy vấn trực tiếp vào Cơ sở dữ liệu đồ thị Neo4j, giúp trích xuất các điều luật, khoản, điểm và mối liên hệ tham chiếu mượt mà.
- **Lưu trữ ngữ cảnh hội thoại**: Giao diện và luồng hội thoại được quản lý qua **Chainlit**, tích hợp Data Layer bằng **PostgreSQL** để theo dõi (tracing), lưu lịch sử chat và các bước can thiệp của Agent.
- **Clean Architecture**: Tổ chức thư mục theo kiến trúc phân lớp (Application, Adapter, Presentation) giúp dễ dàng bảo trì và mở rộng thêm các domain luật mới.

## Yêu Cầu Hệ Thống (Prerequisites)

- **Python**: 3.9+
- **Docker & Docker Compose**: Để khởi chạy PostgreSQL (Chainlit Data Layer) dễ dàng.
- **Neo4j**: CSDL Đồ thị đang chạy ở `localhost:7687` (đã được import dữ liệu pháp luật).
- **Vercel AI Gateway API Key**: dùng để gọi LLM qua OpenAI-compatible endpoint.

---

## Hướng Dẫn Cài Đặt & Chạy Dự Án

### 1. Chuẩn bị Cơ sở dữ liệu
Hệ thống sử dụng **Neo4j** (chứa luật) và **PostgreSQL** (chứa lịch sử chat của Chainlit).
Sử dụng Docker để chạy nhanh PostgreSQL:
```bash
docker run --name chainlit_pg -e POSTGRES_PASSWORD=123456 -e POSTGRES_DB=chainlit_db -p 5432:5432 -d postgres
```
*(Đối với Neo4j, hãy chắc chắn instance đã chạy và import các Entity, Relationship của Luật học)*.

### 2. Cài đặt Môi trường Python
Tạo môi trường ảo (Virtualenv/Conda khuyến nghị) và cài đặt dependencies:
```bash
pip install -r requirements.txt
```

### 3. Cấu hình Biến môi trường
Tạo file `.env` ở thư mục gốc (có thể copy từ `.env.example` nếu có) và cấu hình các thông số:
```ini
VERCEL_AI_GATEWAY_API_KEY="your-vercel-ai-gateway-key"
AI_GATEWAY_BASE_URL="https://ai-gateway.vercel.sh/v1"

# (Optional) Model overrides
RESPONSE_LLM="openai/gpt-oss-120b"
ROUTER_LLM="meta-llama/llama-4-scout-17b-16e-instruct"
RETRIEVER_LLM="llama-3.3-70b-versatile"

# Neo4j Graph Database
NEO4J_URI="bolt://localhost:7687"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="your-neo4j-password"

# PostgreSQL (Chainlit Data Layer)
DATABASE_URL="postgresql+asyncpg://postgres:123456@localhost:5432/chainlit_db"
CHAINLIT_AUTH_SECRET="random_super_secret_hash"
```

### 4. Khởi chạy Ứng dụng
Khởi chạy UI Chainlit từ thư mục gốc (*Lưu ý file chính nằm trong presentation*):
```bash
chainlit run presentation/main.py -w
```
> *-w: Bật chế độ auto-reload khi chỉnh sửa code.*

Chainlit sẽ tự động tạo bảng (schema) trong PostgreSQL trong lần chạy đầu tiên. Mở trình duyệt tại địa chỉ: **http://localhost:8000** để thử nghiệm chatbot.

---

