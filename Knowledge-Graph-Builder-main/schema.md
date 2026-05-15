Chào bạn, việc xây dựng một **Knowledge Graph (KG - Đồ thị tri thức)** từ văn bản Luật Hôn nhân và Gia đình (HN&GĐ) để phục vụ hệ thống Hỏi đáp (Q&A) là một hướng đi rất thực tế và hiệu quả. So với các văn bản luật khác, Luật HN&GĐ mang tính "đời sống" cao, xoay quanh các mối quan hệ con người và tài sản.

Dựa trên toàn văn bạn cung cấp, tôi xin phân tích cấu trúc logic của Luật này và đề xuất lược đồ (Schema) bao gồm các **Entity (Thực thể)** và **Relationship (Mối quan hệ)** phù hợp nhất cho bài toán tư vấn pháp luật.

---

### PHẦN 1: PHÂN TÍCH CẤU TRÚC LOGIC CỦA LUẬT HN&GĐ

Luật HN&GĐ 2014 được xây dựng dựa trên một cấu trúc logic mang tính nguyên nhân - kết quả và phân nhánh theo vòng đời của một gia đình. Logic này xoay quanh 4 trục chính:

1.  **Trục Chủ thể (Ai?):** Cá nhân (Vợ, Chồng, Cha, Mẹ, Con, Người thứ ba...), Cơ quan nhà nước (Tòa án, UBND, Cơ quan quản lý hộ tịch).
2.  **Trục Sự kiện/Hành vi pháp lý (Việc gì xảy ra?):** Kết hôn, Chung sống như vợ chồng, Ly hôn, Nhận cha mẹ con, Mang thai hộ, Mang tài sản vào kinh doanh...
3.  **Trục Quyền & Nghĩa vụ (Được làm gì, Phải làm gì, Bị cấm gì?):** Cấp dưỡng, Đại diện, Thăm nom con, Tôn trọng tín ngưỡng...
4.  **Trục Tài sản (Cái gì?):** Tài sản chung, Tài sản riêng, Di sản thừa kế, Quyền sử dụng đất...

**Mô hình suy luận của Luật (Rules) thường có dạng:**
`[Chủ thể A] + [Thực hiện Hành vi B] + [Thỏa mãn Điều kiện C] => [Phát sinh Quyền/Nghĩa vụ/Hệ quả D]`

---

### PHẦN 2: ĐỀ XUẤT CÁC ENTITY (NHÃN NÚT - NODES)

Dưới đây là các Node cần thiết lập, mỗi Node sẽ đi kèm với các Property (Thuộc tính) để lưu trữ thông tin chi tiết phục vụ việc tra cứu.

#### 1. Nút `LegalProvision` (Điều khoản Luật)
*Đóng vai trò làm căn cứ trích dẫn (Grounding) để hệ thống Q&A trả về cho người dùng nhằm tăng tính thuyết phục.*
*   **Properties:**
    *   `id`: (VD: Dieu_8_Khoan_1_Diem_a)
    *   `chuong` (Chương): (VD: Chương II)
    *   `dieu` (Điều): (VD: 8)
    *   `khoan` (Khoản): (VD: 1)
    *   `noidung` (Nội dung text): "Nam từ đủ 20 tuổi trở lên..."

#### 2. Nút `LegalConcept` (Khái niệm pháp lý)
*Lưu trữ các định nghĩa tại Điều 3 hoặc các khái niệm bao trùm.*
*   **Properties:**
    *   `ten_khai_niem`: (VD: "Tảo hôn", "Kết hôn giả tạo", "Tài sản chung", "Thời kỳ hôn nhân")
    *   `dinh_nghia`: Text giải thích chi tiết.

#### 3. Nút `Subject` (Chủ thể / Vai trò)
*Ai là người đang đặt câu hỏi hoặc đối tượng được nhắc đến.*
*   **Properties:**
    *   `ten_vai_tro`: (VD: "Vợ", "Chồng", "Người đang có vợ/chồng", "Con chưa thành niên", "Người thứ ba ngay tình", "Tòa án", "Cơ quan đăng ký hộ tịch")
    *   `loai_chu_the`: Cá nhân / Tổ chức / Cơ quan Nhà nước.

#### 4. Nút `LegalAction` (Hành vi / Sự kiện)
*Các hành động mà người dùng muốn hỏi (VD: "Tôi muốn ly hôn thì làm sao?").*
*   **Properties:**
    *   `ten_hanh_vi`: (VD: "Kết hôn", "Ly hôn đơn phương", "Mang thai hộ", "Nhập tài sản riêng vào tài sản chung", "Cấp dưỡng")
    *   `tinh_trang`: Hợp pháp / Trái pháp luật / Bị cấm.

#### 5. Nút `Asset` (Tài sản)
*Trục rất quan trọng trong tranh chấp ly hôn.*
*   **Properties:**
    *   `loai_tai_san`: (VD: "Bất động sản", "Tài khoản ngân hàng", "Hoa lợi, lợi tức", "Thu nhập do lao động")
    *   `thoi_diem_tao_lap`: Trước kết hôn / Trong thời kỳ hôn nhân / Sau khi chia tài sản.

#### 6. Nút `Condition` (Điều kiện)
*Điều kiện để một hành vi được công nhận hoặc một quyền được thực thi.*
*   **Properties:**
    *   `noi_dung_dieu_kien`: (VD: "Nam từ đủ 20 tuổi trở lên", "Không bị mất năng lực hành vi dân sự", "Vợ đang có thai hoặc nuôi con dưới 12 tháng tuổi")

#### 7. Nút `Right_Obligation` (Quyền và Nghĩa vụ)
*   **Properties:**
    *   `loai`: Quyền (Right) / Nghĩa vụ (Duty) / Cấm (Prohibition).
    *   `noi_dung`: (VD: "Yêu cầu Tòa án giải quyết ly hôn", "Bồi thường thiệt hại", "Đóng góp tài sản riêng")

---

### PHẦN 3: ĐỀ XUẤT RELATIONS (MỐI QUAN HỆ - EDGES)

Để nối các Node lại thành một Graph có khả năng suy luận, ta cần các quan hệ có hướng (Directed Edges):

| Tên Quan hệ (Relationship) | Nút nguồn (Source) | Nút đích (Target) | Ý nghĩa / Ví dụ thực tế từ Luật |
| :--- | :--- | :--- | :--- |
| **BASED_ON** (Căn cứ theo) | *Tất cả các Nút* | `LegalProvision` | Nối mọi thực thể về Điều khoản cụ thể để trích dẫn nguồn luật. |
| **IS_A** (Là một loại) | `Subject` / `Asset` | `LegalConcept` | Phân loại. *VD: Đất được thừa kế riêng [IS_A] Tài sản riêng.* |
| **HAS_RIGHT** (Có quyền) | `Subject` | `LegalAction` / `Right_Obligation` | *VD: Vợ/Chồng [HAS_RIGHT] Yêu cầu ly hôn (Điều 51).* |
| **HAS_DUTY** (Có nghĩa vụ) | `Subject` | `Right_Obligation` | *VD: Cha mẹ [HAS_DUTY] Cấp dưỡng cho con (Điều 110).* |
| **IS_PROHIBITED** (Bị cấm làm) | `Subject` | `LegalAction` | *VD: Người đang có vợ/chồng [IS_PROHIBITED] Kết hôn với người khác.* |
| **REQUIRES_CONDITION** (Yêu cầu ĐK) | `LegalAction` | `Condition` | Để thực hiện hành vi cần ĐK gì. *VD: Kết hôn [REQUIRES_CONDITION] Tự nguyện.* |
| **BLOCKED_BY** (Bị chặn bởi) | `LegalAction` | `Condition` | Ngoại lệ. *VD: Chồng yêu cầu ly hôn [BLOCKED_BY] Vợ nuôi con dưới 12 tháng (Điều 51).* |
| **RESULTS_IN** (Dẫn đến hệ quả) | `LegalAction` | `LegalAction` / `Right_Obligation` | *VD: Ly hôn [RESULTS_IN] Chia tài sản chung.* |
| **RESOLVED_BY** (Giải quyết bởi) | `LegalAction` / `Dispute` | `Subject` (Cơ quan) | *VD: Hủy kết hôn trái PL [RESOLVED_BY] Tòa án.* |
| **OWNS** (Sở hữu) | `Subject` | `Asset` | Ai sở hữu cái gì. *VD: Vợ, Chồng [OWNS] Tài sản chung.* |

---

### PHẦN 4: VÍ DỤ MINH HỌA (USE-CASE GRAPH)

Hãy thử vẽ (tưởng tượng) một Graph cho câu hỏi phổ biến: **"Vợ đang mang thai thì chồng có được ly hôn không, và tài sản chung chia như thế nào?"**

1.  **Truy vấn Tình trạng Ly hôn:**
    *   `Subject (Chồng)` --[HAS_RIGHT]--> `LegalAction (Yêu cầu ly hôn)`
    *   `LegalAction (Yêu cầu ly hôn)` --[BLOCKED_BY]--> `Condition (Vợ đang có thai)` --[BASED_ON]--> `LegalProvision (Khoản 3 Điều 51)`.
    *   *=> Hệ thống suy luận:* Chồng không được quyền ly hôn lúc này.

2.  **Truy vấn Tài sản chung:**
    *   `LegalConcept (Tài sản chung)` --[IS_A]--> `Asset`
    *   `Subject (Vợ/Chồng)` --[HAS_RIGHT]--> `LegalAction (Chia tài sản chung)` --[REQUIRES_CONDITION]--> `Condition (Thỏa thuận hoặc Tòa án giải quyết)`.
    *   `LegalAction (Chia tài sản chung)` --[BASED_ON]--> `LegalProvision (Điều 59)`
    *   `LegalProvision (Điều 59)` --[HAS_PRINCIPLE]--> `Condition (Chia đôi nhưng xét hoàn cảnh, công sức)`

---

### LỜI KHUYÊN KHI XÂY DỰNG ỨNG DỤNG RAG/Q&A TRÊN DỮ LIỆU NÀY

1.  **Xử lý Ngoại lệ (Exceptions):** Pháp luật VN luôn có cụm từ *"trừ trường hợp luật có quy định khác"* hoặc *"trừ khi có thỏa thuận khác"*. Bạn nên thêm một property boolean `has_exception = True` vào các relationship hoặc tạo hẳn node `Exception` để LLM (Large Language Model) biết đường sinh câu trả lời cẩn thận ("Theo nguyên tắc thì..., trừ trường hợp...").
2.  **Thời điểm (Temporal Logic):** Luật HN&GĐ cực kỳ quan tâm đến "thời điểm" (VD: Tài sản có *trước* khi kết hôn vs *trong* thời kỳ hôn nhân). Nút `Condition` cần được thiết kế cẩn thận để bắt các keyword thời gian này.
3.  **Tích hợp Cypher Query:** Khi người dùng hỏi "Con dưới 36 tháng tuổi thì ai nuôi?", hệ thống AI sẽ dịch sang graph query tìm: `Subject(Con)` -> `Condition(Dưới 36 tháng)` -> `HAS_DUTY (Trực tiếp nuôi)` -> Trả về `Subject(Mẹ)`. Khớp với Điều 81.