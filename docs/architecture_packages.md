# Kiến trúc Gói (Architecture Packages) - Agentic GraphRAG

Tài liệu này mô tả chi tiết cấu trúc phân rã theo gói (packages) của dự án Chatbot tư vấn luật áp dụng **Clean Architecture** và **Domain-Driven Design (DDD)**. Hệ thống chia thành 5 lớp với quy tắc "Gói vòng ngoài gọi vào gói vòng trong", nhằm cô lập thư viện và logic nghiệp vụ.

## Sơ đồ phụ thuộc (Dependency)
`presentation`, `adapter` --> `application` -> `domain`
(Gói `utils` cung cấp tiện ích cho tất cả các gói).

---

## Chi tiết các Package

### 1. `domain` (Lớp Lõi / Thực Thể)
- **Mục đích:** Là linh hồn của hệ thống, chứa các định nghĩa lõi nhất. Không chứa logic gọi thư viện hay bất kì Database nào.
- **Nhiệm vụ:**
  - Định nghĩa cấu trúc Schema, Pydantic BaseModels (`db_schema.py` - chứa lược đồ CSDL).
  - Đóng vai trò là Interface/Port cho các hệ thống vòng ngoài đăng ký theo dạng Contract (Hợp đồng).
- **Phụ thuộc:** Đứng độc lập ở mức thấp nhất, không phụ thuộc vào bất cứ package nào.

### 2. `application` (Lớp Ứng dụng / Use Case)
- **Mục đích:** Đóng vai trò điều phối luồng làm việc của Chatbot.
- **Nhiệm vụ:** 
  - Chứa bộ não Agentic Workflow: gồm việc phân tích câu hỏi (`query_updater.py`), chọn và định tuyến chức năng truy cập dữ liệu cần thiết dựa vào description của tools (`router.py`).
  - Giao tiếp dữ liệu thông qua cấu trúc của `domain` do mình triệu gọi.
- **Phụ thuộc:** Chỉ phụ thuộc vào `domain` và `utils`. Hoàn toàn không gọi chéo qua `presentation` hay gọi trực tiếp thư viện trong `adapter`.

### 3. `adapter` (Lớp Hạ tầng / Adapter)
- **Mục đích:** Tương tác trực tiếp với các yếu tố thay đổi (Database, AI Model API, external framework). 
- **Nhiệm vụ:**
  - Kết nối Neo4j GrapDB (`config.py`), chuyển đổi Text sang Cypher GraphQL (`text2cypher.py`).
  - Kết nối PostgreSQL để tracking lịch sử (`data_layer.py`, `init_db.py`).
  - Nơi cài đặt chi tiết cho các `retrievers` (vd: `retrievers/ket_hon`, `retrievers/vi_pham`). Do các file này trực tiếp gọi API và câu lệnh Cypher nên nó nằm tại lớp hạ tầng.
- **Phụ thuộc:** Bắt buộc tuân thủ giao thức Interface từ `domain` đã cắm. Chịu phụ thuộc ở nhánh phụ để khởi tạo các service nếu cần chuyển giao tool. Không cho phép package khác gọi vào (trừ lúc khởi chạy App).

### 4. `presentation` (Lớp Trình diễn / Giao diện & Controllers)
- **Mục đích:** Giao tiếp với Client / Người dùng.
- **Nhiệm vụ:**
  - Cung cấp User Interface (Sử dụng Chainlit UI qua file `main.py`).
  - Chứa các Hooks bắt sự kiện hội thoại (on_chat_start, on_message).
  - Đây cũng là khu vực Setup, tiến hành _Dependency Injection_ bằng cách load các adapter từ `adapter` và truyền (inject) vào logic luồng ở `application`. Do đó tránh cho hệ thống trực tiếp vướng gọi CSDL sau này.
- **Phụ thuộc:** Gói này phụ thuộc vào `application` (để gọi run Use Case/Workflow) và `domain` (thao tác đối tượng DTOs/Data Types).

### 5. `utils` (Lớp Dùng Chung / Utilities)
- **Mục đích:** Module độc quyền tái sử dụng mã (Reusability).
- **Nhiệm vụ:** Khai thác các function và constant phổ quát (xử lý RegExp String như `utils.py`, hay các class cấu hình cơ sở `general.py`).
- **Phụ thuộc:** Là thư viện trung gian thuần túy tiện ích, độc lập tuyệt tác không phụ thuộc logic gói nào, nhưng có quyền hỗ trợ tất cả các gói còn lại.