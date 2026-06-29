"""Tập hợp các tác tử con (Subagents) — mỗi tác tử phụ trách một miền pháp lý.

Mỗi `RetrieverAgent` cụ thể đại diện cho một chủ đề (cấp dưỡng, đăng ký
kết hôn, chia tài sản sau ly hôn, ...) và bên trong là một quy trình ba
bước: phân loại Cypher template, trích xuất tham số có kiểm chứng schema,
rồi thực thi Cypher trên Neo4j và mã hoá thành `LEGAL_CONTEXT_BUNDLE_V1`.
Toàn bộ retriever không có trạng thái giữa các lượt, đảm bảo tính cô lập
ngữ cảnh đúng theo định nghĩa Subagents pattern.
"""
