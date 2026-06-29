"""RouterAgent — tác tử định tuyến không trạng thái.

Mỗi lần được gọi, RouterAgent đọc câu hỏi hiện tại cùng tóm tắt bộ nhớ
retrieval, dùng LLM tool calling để chọn zero hoặc nhiều retriever phù
hợp. Các retriever được gọi song song bằng `asyncio.gather`, kết quả
được trả về dưới dạng danh sách `RetrieverResult` đã chuẩn hoá. Khi
Router quyết định tái sử dụng ngữ cảnh đã lưu (`context_action="reuse"`),
RouterAgent sẽ chạy qua bước kiểm tra deterministic trước khi trả ngữ
cảnh cũ thay vì gọi retriever thật.
"""
