"""Khai báo schema tool theo chuẩn OpenAI để Router LLM dùng cho tool calling.

Schema ở đây tách khỏi cài đặt thật của retriever nhằm hai mục đích: cho
phép Router LLM thấy đầy đủ mô tả mà không phải nạp module retriever, và
phục vụ benchmark Router độc lập với hạ tầng Neo4j.
"""
