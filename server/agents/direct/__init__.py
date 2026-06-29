"""Hai tác tử phản hồi trực tiếp — `RespondAgent` và `ClarifyAgent`.

Khi Router quyết định câu hỏi có thể trả lời ngay từ lịch sử (`respond`)
hoặc cần làm rõ ý người dùng (`clarify`), một trong hai tác tử này sẽ
chạy độc quyền: không retriever nào được gọi và pipeline tổng hợp đáp
án bị bỏ qua. Đây là cơ chế lối tắt giúp các câu hỏi tầm thường không
phải đi qua bước truy xuất Neo4j tốn kém.
"""
