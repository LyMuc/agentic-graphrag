import os
import chainlit.data as cl_data
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from config import DATABASE_URL

# Cấu hình Custom Data Layer sử dụng SQLAlchemy (hỗ trợ PostgreSQL qua asyncpg)
if DATABASE_URL:
    # Khởi tạo data layer
    data_layer = SQLAlchemyDataLayer(conninfo=DATABASE_URL)
    # Gán data layer cho Chainlit
    cl_data._data_layer = data_layer
else:
    print("WARNING: Không tìm thấy DATABASE_URL trong môi trường. Chainlit sẽ không lưu dữ liệu vào PostgreSQL.")
