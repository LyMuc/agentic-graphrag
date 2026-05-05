# Hướng dẫn cài đặt và chạy PostgreSQL bằng Docker trên Windows

Nếu bạn chưa từng sử dụng Docker, đừng lo lắng. Docker là một công cụ giúp bạn chạy các phần mềm (như database PostgreSQL) trong một "hộp chứa" (container) bị cô lập, không làm rác máy tính của bạn và cấu hình rất dễ dàng.

Dưới đây là các bước chi tiết cho nền tảng Windows.

## Bước 1: Cài đặt Docker Desktop 
1. Truy cập trang web chính thức của Docker: [Download Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/).
2. Nhấn nút **Download for Windows** để tải file chạy (`.exe`).
3. Nhấp đúp vào file vừa tải về và cài đặt theo các cấu hình mặc định (Nhớ đánh dấu tích vào ô "Use WSL 2 instead of Hyper-V" nếu nó hỏi).
4. Khởi động lại máy tính (nếu cài đặt yêu cầu).
5. Mở ứng dụng **Docker Desktop** (tìm trong Start Menu). Ở lần mở đầu tiên, bạn cứ nhấn "Accept" (Đồng ý) điều khoản và "Skip" các bước khảo sát.
> **Lưu ý:** Đảm bảo Docker Desktop luôn đang mở và biểu tượng hình chú cá voi (hoặc biểu tượng Docker) ở góc dưới cùng bên phải màn hình (Taskbar) màu xanh lá hoặc không có cảnh báo đỏ báo hiệu Docker đang chạy.

## Bước 2: Chạy PostgreSQL và pgAdmin bằng Docker Compose (An toàn & Bền vững)

Để dữ liệu không bao giờ bị mất (kể cả khi xóa container) và có giao diện pgAdmin để xem CSDL, tôi đã chuẩn bị sẵn file `docker-compose.yml` cực kỳ tiện lợi ở thư mục gốc của project.

1. Mở **PowerShell** hoặc **Terminal** ngay tại thư mục chứa code của bạn (nơi có file `docker-compose.yml`).
2. Gõ câu lệnh sau và nhấn `Enter`:

```bash
docker compose up -d
```

### Điều gì vừa xảy ra?
Lệnh trên đã tự động làm 3 việc:
1. Tạo một ổ đĩa ảo (Volume có tên `pgdata`) nằm an toàn trong máy tính của bạn để lưu dữ liệu cứng của PostgreSQL.
2. Khởi chạy CSDL PostgreSQL (ở cổng 5432).
3. Khởi chạy công cụ quản trị giao diện web pgAdmin4 (ở cổng 5050).
- `-d` giúp cả hai chạy ngầm.

## Bước 3: Xem và quản lý dữ liệu bằng pgAdmin
1. Mở trình duyệt web và truy cập: [http://localhost:5050](http://localhost:5050)
2. Đăng nhập bằng tài khoản hiển thị trong file compose:
   - Email: `admin@admin.com`
   - Password: `admin`
3. **Kết nối pgAdmin với PostgreSQL:**
   - Khi vào trong, ở góc trái màn hình, nhấp chuột phải vào ký hiệu **Servers** -> Chọn **Register** -> **Server...**
   - Tab **General**: Đặt tên gợi nhớ (VD: `Chainlit-DB`).
   - Tab **Connection**:
     - Host name/address: Gõ `db` (Đây là tên dịch vụ chứa Postgres trong mạng nội bộ docker, hệ thống tự hiểu).
     - Port: `5432`
     - Maintenance database: `chainlit_db`
     - Username: `postgres`
     - Password: `123456`
   - Nhấn **Save**. 
Giờ đây bạn đã có thể nhấp vào `Chainlit-DB` ở góc trái để xem trực quan các bảng `users`, `threads`, `steps` mà Chainlit sinh ra.

## Bước 4: Liên kết với cấu hình Project của bạn
Cấu hình trong file `.env.example` của tôi hoàn toàn khớp với Database vừa tạo:
```text
DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5432/chainlit_db
```
Đổi tên `.env.example` thành `.env`, ứng dụng Python và Chainlit của bạn sẽ tự động biết cách kết nối với database này.

## Một số lệnh quản lý Docker hữu ích khác (Dành cho PowerShell)
- **Tạm dừng hệ thống DB:** `docker compose stop`
- **Chạy lại hệ thống DB khi bạn mở lại máy tính:** `docker compose start`
- **Tắt và dọn dẹp hệ thống (dữ liệu ổ đĩa vẫn còn do dùng Volume!):** `docker compose down`