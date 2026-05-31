# Gói triển khai bản đầu — Agentic GraphRAG Chatbot Luật

> **Deploy lên GCP Cloud Run:** xem hướng dẫn chi tiết từng bước tại [deploy-gcp.md](deploy-gcp.md) (Dockerfile + script `scripts/deploy-gcp.ps1` có sẵn trong repo).

Tài liệu mô tả cấu hình triển khai phiên bản đầu tiên của hệ thống chatbot vấn đáp pháp luật Việt Nam. Gói này gồm **ứng dụng Chainlit** (Python), **PostgreSQL** (Docker), **Neo4j** (cloud hoặc local) và **Vercel AI Gateway** (LLM).

---

## 1. Tổng quan kiến trúc triển khai

```text
┌─────────────────────────────────────────────────────────────┐
│  Người dùng  →  Chainlit UI (port 8000)                     │
│                    presentation/main.py                      │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
     PostgreSQL (Docker)              Neo4j (Aura / local)
     port 5432 — lưu hội thoại         bolt / neo4j+ssc
               │
               ▼
     pgAdmin (Docker, tùy chọn)
     port 5050
               │
               ▼
     Vercel AI Gateway — LLM (Router / Retriever / Response)
```

| Thành phần | Cách triển khai | Vai trò |
|------------|-----------------|---------|
| **Chainlit app** | Chạy trực tiếp trên host (`chainlit run`) | Giao diện chat, agent router, retriever |
| **PostgreSQL** | Docker Compose (`docker-compose.yml`) | Chainlit Data Layer — thread, step, lịch sử chat |
| **pgAdmin** | Docker Compose (tùy chọn) | Quản trị PostgreSQL qua web |
| **Neo4j** | Neo4j Aura (cloud) hoặc instance local | Đồ thị pháp luật — truy vấn Cypher |
| **LLM** | Vercel AI Gateway (OpenAI-compatible) | Router, retriever, tổng hợp câu trả lời |

> **Lưu ý:** Bản đầu **chưa** container hóa ứng dụng Chainlit. Chỉ PostgreSQL và pgAdmin được đóng gói trong Docker. Ứng dụng Python chạy trên máy host.

---

## 2. Yêu cầu hệ thống

| Hạng mục | Phiên bản / yêu cầu |
|----------|---------------------|
| Python | 3.9+ (khuyến nghị 3.11+) |
| Docker | Docker Engine + Docker Compose v2 |
| Neo4j | Instance đã import dữ liệu pháp luật |
| API Key | `VERCEL_AI_GATEWAY_API_KEY` (bắt buộc) |
| Hệ điều hành | Windows / Linux / macOS |

---

## 3. Cấu hình Docker

File: `docker-compose.yml`

### 3.1. Dịch vụ PostgreSQL

| Thuộc tính | Giá trị |
|------------|---------|
| Image | `postgres:15` |
| Container name | `chainlit_pg` |
| Restart policy | `always` |
| Port | `5432:5432` |
| Database | `chainlit_db` |
| User | `postgres` |
| Password | `123456` |
| Volume | `pgdata` → `/var/lib/postgresql/data` |

### 3.2. Dịch vụ pgAdmin (tùy chọn)

| Thuộc tính | Giá trị |
|------------|---------|
| Image | `dpage/pgadmin4` |
| Container name | `pgadmin` |
| Restart policy | `always` |
| Port | `5050:80` |
| Email đăng nhập | `admin@admin.com` |
| Password | `admin` |
| Phụ thuộc | Service `db` |

### 3.3. Lệnh Docker

```bash
# Khởi động PostgreSQL + pgAdmin
docker compose up -d

# Kiểm tra trạng thái
docker compose ps

# Xem log
docker compose logs -f

# Dừng dịch vụ
docker compose down

# Dừng và xóa volume (mất dữ liệu DB)
docker compose down -v
```

---

## 4. Môi trường triển khai

### 4.1. File cấu hình

| File | Mục đích |
|------|----------|
| `.env` | Biến môi trường thực tế ( **không commit** — đã có trong `.gitignore`) |
| `.env.example` | Mẫu biến môi trường để copy khi triển khai mới |
| `.chainlit/config.toml` | Cấu hình Chainlit (auth, UI, session) |
| `adapter/config.py` | Đọc biến môi trường, khởi tạo Neo4j driver và LLM |

### 4.2. Biến môi trường bắt buộc

```ini
# Vercel AI Gateway
VERCEL_AI_GATEWAY_API_KEY=<api-key>
AI_GATEWAY_BASE_URL=https://ai-gateway.vercel.sh/v1

# Neo4j
NEO4J_URI=<bolt://localhost:7687 hoặc neo4j+ssc://*.databases.neo4j.io>
NEO4J_USERNAME=<username>
NEO4J_PASSWORD=<password>
NEO4J_DATABASE=<database-name>

# PostgreSQL — Chainlit Data Layer
DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5432/chainlit_db

# Chainlit
CHAINLIT_AUTH_SECRET=<chuỗi-ngẫu-nhiên-dài>
```

### 4.3. Biến môi trường tùy chọn

```ini
# Model LLM (mặc định trong adapter/config.py)
RESPONSE_LLM=openai/gpt-4.1
ROUTER_LLM=openai/gpt-4o
RETRIEVER_LLM=openai/o3

# OAuth — cần bật auth trong .chainlit/config.toml
OAUTH_GOOGLE_CLIENT_ID=
OAUTH_GOOGLE_CLIENT_SECRET=
OAUTH_GITHUB_CLIENT_ID=
OAUTH_GITHUB_CLIENT_SECRET=
```

### 4.4. Model LLM mặc định

| Vai trò | Biến môi trường | Model mặc định |
|---------|-----------------|----------------|
| Tổng hợp câu trả lời | `RESPONSE_LLM` | `openai/gpt-4.1` |
| Định tuyến câu hỏi | `ROUTER_LLM` | `openai/gpt-4o` |
| Trích xuất Điều luật | `RETRIEVER_LLM` | `openai/o3` |

### 4.5. Cấu hình Chainlit

File `.chainlit/config.toml`:

| Cấu hình | Giá trị | Ghi chú |
|----------|---------|---------|
| `auth.enabled` | `false` | Không bắt đăng nhập password mặc định |
| OAuth providers | Google, GitHub | Khai báo sẵn; cần điền client ID/secret trong `.env` |
| `session_timeout` | 3600 giây | Lưu session khi mất kết nối |
| `user_session_timeout` | 1296000 giây (15 ngày) | Hết hạn phiên người dùng |
| `allow_origins` | `["*"]` | CORS mở (cân nhắc thu hẹp khi production) |

---

## 5. Quy trình triển khai

### Bước 1 — Clone và cài dependency Python

```bash
cd "Agentic GraphRAG Chatbot luật"
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt
```

### Bước 2 — Khởi động PostgreSQL

```bash
docker compose up -d
```

### Bước 3 — Cấu hình biến môi trường

```bash
copy .env.example .env    # Windows
# cp .env.example .env    # Linux / macOS
```

Điền đầy đủ giá trị trong `.env`, đặc biệt:

- `VERCEL_AI_GATEWAY_API_KEY`
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
- `CHAINLIT_AUTH_SECRET`

### Bước 4 — Kiểm tra Neo4j

Đảm bảo instance Neo4j đang chạy và đồ thị pháp luật đã được import. Bản triển khai hiện tại sử dụng **Neo4j Aura** (URI dạng `neo4j+ssc://*.databases.neo4j.io`).

### Bước 5 — Khởi chạy ứng dụng

```bash
chainlit run presentation/main.py -w
```

- `-w`: bật auto-reload khi sửa code (phù hợp môi trường dev)
- Lần chạy đầu, Chainlit tự tạo schema PostgreSQL nếu `DATABASE_URL` hợp lệ

---

## 6. Thông tin truy cập

### 6.1. Bảng endpoint và thông tin đăng nhập

| Dịch vụ | URL / Host | Port | Tài khoản | Mật khẩu | Ghi chú |
|---------|------------|------|-----------|----------|---------|
| **Chainlit UI** | http://localhost:8000 | 8000 | — | — | Không yêu cầu đăng nhập (`auth.enabled = false`) |
| **PostgreSQL** | localhost | 5432 | `postgres` | `123456` | Theo `docker-compose.yml` |
| **pgAdmin** | http://localhost:5050 | 5050 | `admin@admin.com` | `admin` | Quản trị DB qua giao diện web |
| **Neo4j** | Xem `NEO4J_URI` trong `.env` | — | Xem `NEO4J_USERNAME` | Xem `NEO4J_PASSWORD` | Neo4j Aura (cloud) hoặc local |
| **Vercel AI Gateway** | https://ai-gateway.vercel.sh/v1 | 443 | API Key | Xem `VERCEL_AI_GATEWAY_API_KEY` | Endpoint OpenAI-compatible |

### 6.2. Kết nối pgAdmin → PostgreSQL

Khi thêm server mới trong pgAdmin:

| Trường | Giá trị |
|--------|---------|
| Host name / address | `db` (trong Docker network) hoặc `host.docker.internal` / `localhost` (từ host) |
| Port | `5432` |
| Maintenance database | `chainlit_db` |
| Username | `postgres` |
| Password | `123456` |

### 6.3. Connection string PostgreSQL (Chainlit)

```
postgresql+asyncpg://postgres:123456@localhost:5432/chainlit_db
```

### 6.4. OAuth (tùy chọn, chưa bật mặc định)

OAuth Google và GitHub đã được khai báo trong `.chainlit/config.toml`. Để bật:

1. Điền `OAUTH_GOOGLE_*` hoặc `OAUTH_GITHUB_*` trong `.env`
2. Đặt `auth.enabled = true` trong `.chainlit/config.toml`
3. Cấu hình redirect URI tương ứng trên Google Cloud Console / GitHub OAuth App

---

## 7. Kiểm tra sau triển khai

| Kiểm tra | Lệnh / hành động | Kết quả mong đợi |
|----------|------------------|------------------|
| PostgreSQL | `docker compose ps` | Container `chainlit_pg` trạng thái `running` |
| pgAdmin | Mở http://localhost:5050 | Đăng nhập thành công |
| Chainlit | Mở http://localhost:8000 | Giao diện chat hiển thị |
| Neo4j | Gửi câu hỏi pháp luật trên UI | Retriever trả về context, có câu trả lời trích dẫn |
| Lưu hội thoại | Refresh trang, mở lại thread cũ | Thread được persist trong PostgreSQL |

---

## 8. Lưu ý vận hành và bảo mật

- **Secret:** Toàn bộ API key, mật khẩu Neo4j và OAuth nằm trong file `.env`. Không commit `.env` lên git.
- **Mật khẩu mặc định Docker:** `postgres/123456` và `admin/admin` chỉ phù hợp môi trường dev/local. Đổi mật khẩu trước khi triển khai production.
- **Thiếu `VERCEL_AI_GATEWAY_API_KEY`:** Ứng dụng lỗi khi khởi tạo LLM.
- **Thiếu `DATABASE_URL`:** Chat vẫn chạy nhưng **không** lưu thread lâu dài.
- **Neo4j:** Dữ liệu đồ thị cần import riêng; mã nguồn thô nằm tại thư mục `data/`.
- **Production:** Cân nhắc reverse proxy (nginx/Caddy), HTTPS, thu hẹp `allow_origins`, bật xác thực OAuth, và container hóa ứng dụng Chainlit trong giai đoạn triển khai tiếp theo.

---

## 9. Phụ lục — Cấu trúc file liên quan triển khai

```text
├── docker-compose.yml       # PostgreSQL + pgAdmin
├── .env.example             # Mẫu biến môi trường
├── .env                     # Biến môi trường thực (local, không commit)
├── .chainlit/config.toml    # Cấu hình Chainlit
├── adapter/config.py        # Neo4j driver, LLM, DATABASE_URL
├── adapter/data_layer.py    # Chainlit ↔ PostgreSQL
├── presentation/main.py     # Entry point ứng dụng
└── requirements.txt         # Python dependencies
```
