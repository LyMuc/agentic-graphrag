"""SynthesizerAgent — tổng hợp câu trả lời cuối từ ngữ cảnh đã hợp nhất.

Tác tử này nhận tập `LegalContextBundle` đã được dedupe và render thành
văn bản pháp lý chuẩn, ghép với prompt hệ thống dài chứa các quy tắc dẫn
chiếu pháp luật, rồi stream từng token tới giao diện. Khi gặp lỗi mạng,
SynthesizerAgent có cơ chế retry và fallback `ainvoke` trước khi báo lỗi
ra giao diện.
"""
