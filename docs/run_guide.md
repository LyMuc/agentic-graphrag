# Hướng dẫn Khởi chạy Hệ thống Agentic GraphRAG + Chainlit (+ PostgreSQL)

Hệ thống đã được cấu trúc thành 1 Data Layer chuẩn chỉnh bằng Chainlit để có thể log message và steps qua PostgreSQL. 
Hãy làm theo các bước dưới đây để chạy hệ thống:

## 1. Cân nhắc và chuẩn bị Môi trường

**A. Khởi chạy CSDL Đồ thị Neo4j**
Hãy chắc chắn rằng Instance Neo4j của bạn đang chạy ở locahost (port 7687) hoặc link máy chủ chỉ định. (Dữ liệu import thông qua script APOC - nếu chưa có hãy setup theo script gốc).

**B. Khởi chạy CSDL PostgreSQL (Cho Chainlit Tracing/Datalayer)**
Nên sử dụng Docker để khởi chạy nhanh 1 instance postgresql:
```bash
docker run --name chainlit_pg -e POSTGRES_PASSWORD=123456 -e POSTGRES_DB=chainlit_db -p 5432:5432 -d postgres
```

## 2. Thiết lập dự án

1. **Cài đặt thư viện:**
Mở terminal tại thư mục gốc của project (có chứa requirements.txt):
```bash
pip install -r requirements.txt
```

2. **Cấu hình file biến môi trường:**
Đổi tên `.env.example` thành `.env`, sau đó cấp phát các giá trị:
- `GROQ_API_KEY`: API Key để gọi ChatGroq Llama.
- Các thông số liên quan tới NEO4J (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`).
- `DATABASE_URL`: URI của postgresql, dùng asyncpg ví dụ: `postgresql+asyncpg://postgres:123456@localhost:5432/chainlit_db` (Nếu bạn dùng docker CSDL).
- `CHAINLIT_AUTH_SECRET`: Một chuỗi hash bất kỳ (BẮT BUỘC ĐỂ BẬT AUTH).
- `OAUTH_GOOGLE_CLIENT_ID` / `OAUTH_GOOGLE_CLIENT_SECRET`: App Key lấy từ Google Cloud Console (APIs & Services -> Credentials) để bật chế độ đăng nhập Google (OAuth). Bỏ trống nếu muốn tắt.

3. **Khởi tạo Database Schema của Chainlit:**
Khi dùng SQLAlchemy Data Layer, Chainlit yêu cầu việc khởi tạo các tables (users, threads, steps). Bạn cần thiết lập thủ công lệnh alembic migration từ Chainlit nhưng phiên bản mới nhất đôi khi tự động auto-create. Tốt nhất là cứ chạy chainlit, nếu báo schema missing, hãy vào container postgres và chạy script của Chainlit.

## 3. Khởi chạy Chatbot

Chạy lệnh sau tại thư mục chứa file `main.py`:
```bash
chainlit run main.py -w
```
> Option `-w` chỉ ra bật auto-reload (watch) khi dev.

Khi khởi động thành công, Chainlit sẽ báo:
```bash
2026-05-04 00:00:00 - Chainlit is running on http://localhost:8000 
```

**Mở trình duyệt ở `http://localhost:8000`** -> Bạn sẽ thấy giao diện nhắn tin mới tinh tế, nhập thử *"Điều kiện kết hôn là gì?"* và quan sát luồng Agent chạy ngay trên màn hình. Mọi logs/steps đều sẽ insert vào PostgreSQL background.