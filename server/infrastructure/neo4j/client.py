"""Driver Neo4j + cấu hình kết nối.

Tách từ ``adapter/config.py`` trong Phase 2 refactor (infrastructure layer).
Đây là nơi duy nhất khởi tạo ``GraphDatabase.driver`` cho toàn hệ thống.
"""
import os
import ssl

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')
NEO4J_DATABASE = os.environ.get('NEO4J_DATABASE')

ssl_context = ssl._create_unverified_context()

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
    notifications_min_severity="OFF",
)
