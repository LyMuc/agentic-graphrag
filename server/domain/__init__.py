"""Tầng miền — kiểu dữ liệu pháp lý thuần, không có I/O hay LLM.

Tầng này chứa khai báo cấu trúc `LegalContextBundle` cùng các thao tác
mã hoá / giải mã / hợp nhất / khử trùng lặp và quy tắc render văn bản
pháp luật. Tầng miền không phụ thuộc Neo4j, OpenAI hay Chainlit, có thể
unit test độc lập.
"""
