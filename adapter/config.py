import os
import ssl
from neo4j import GraphDatabase
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')
NEO4J_DATABASE = os.environ.get('NEO4J_DATABASE')

# PostgreSQL (Chainlit Data Layer)
DATABASE_URL = os.environ.get("DATABASE_URL") # format: postgresql+asyncpg://user:pass@host:port/dbname

ssl_context = ssl._create_unverified_context()

driver = GraphDatabase.driver(NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
    notifications_min_severity="OFF", 
)

# KHỞI TẠO LLM GROQ CHUNG
async def chat(messages, **config):
    llm = ChatGroq(api_key=GROQ_API_KEY, model="openai/gpt-oss-120b", temperature=0, max_tokens=2048)
    res = await llm.ainvoke(messages, **config)
    return res.content
