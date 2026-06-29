"""Back-compat shim — moved to ``server.infrastructure.persistence.data_layer`` (Phase 2).

Import side-effect (đăng ký ``cl_data._data_layer``) chạy đúng một lần khi module mới
được nạp lần đầu — giữ nguyên hành vi của ``from adapter import data_layer`` ở main.py.
"""
from server.infrastructure.persistence.data_layer import *  # noqa: F401,F403
