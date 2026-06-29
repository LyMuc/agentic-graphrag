"""Tầng hạ tầng — bộ adapter ra các dịch vụ ngoài.

Mỗi sub-package giấu kín một công nghệ cụ thể (LLM OpenAI, driver Neo4j,
SQLAlchemy Postgres, lớp lưu snapshot visualize) sau một API tối giản
cho các tầng trên. Đây là chỗ duy nhất được phép import driver bên thứ
ba; các tầng `agents`, `domain` chỉ thấy interface đã được trừu tượng
hoá.
"""
