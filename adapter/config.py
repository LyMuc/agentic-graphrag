import os
import ssl
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

AI_GATEWAY_API_KEY = os.environ.get("VERCEL_AI_GATEWAY_API_KEY")
AI_GATEWAY_BASE_URL = os.environ.get("AI_GATEWAY_BASE_URL", "https://ai-gateway.vercel.sh/v1")

RESPONSE_LLM = os.environ.get("RESPONSE_LLM", "openai/gpt-4o")
ROUTER_LLM = os.environ.get("ROUTER_LLM", "openai/gpt-4o-mini")
RETRIEVER_LLM = os.environ.get("RETRIEVER_LLM", "openai/gpt-4o-mini")
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

def build_llm(model: str, temperature: float = 0, max_tokens: int = 2048, **kwargs) -> ChatOpenAI:
    if not AI_GATEWAY_API_KEY:
        raise ValueError("Missing VERCEL_AI_GATEWAY_API_KEY in environment.")
    return ChatOpenAI(
        api_key=AI_GATEWAY_API_KEY,
        base_url=AI_GATEWAY_BASE_URL,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )

# KHỞI TẠO LLM CHUNG (qua Vercel AI Gateway - OpenAI compatible)
async def chat(messages, **config):
    llm = build_llm(model=RESPONSE_LLM, temperature=0, max_tokens=2048)
    res = await llm.ainvoke(messages, **config)
    return res.content
