import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# The DATABASE_URL is in format: postgresql+asyncpg://postgres:123456@localhost:5432/chainlit_db
# For psycopg2, we need it without +asyncpg
db_url = os.environ.get("DATABASE_URL")
if db_url and "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "")

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    "id" UUID PRIMARY KEY,
    "identifier" TEXT NOT NULL UNIQUE,
    "metadata" JSONB NOT NULL,
    "createdAt" TEXT
);

CREATE TABLE IF NOT EXISTS threads (
    "id" UUID PRIMARY KEY,
    "createdAt" TEXT,
    "name" TEXT,
    "userId" UUID,
    "userIdentifier" TEXT,
    "tags" TEXT[],
    "metadata" JSONB,
    FOREIGN KEY ("userId") REFERENCES users("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS steps (
    "id" UUID PRIMARY KEY,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "threadId" UUID NOT NULL,
    "parentId" UUID,
    "disableFeedback" BOOLEAN,
    "streaming" BOOLEAN NOT NULL,
    "waitForAnswer" BOOLEAN,
    "isError" BOOLEAN,
    "metadata" JSONB,
    "tags" TEXT[],
    "input" TEXT,
    "output" TEXT,
    "createdAt" TEXT,
    "command" TEXT,
    "start" TEXT,
    "end" TEXT,
    "generation" JSONB,
    "showInput" TEXT,
    "language" TEXT,
    "indent" INT,
    "defaultOpen" BOOLEAN,
    "autoCollapse" BOOLEAN,
    "modes" JSONB,
    "icon" TEXT,
    FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS elements (
    "id" UUID PRIMARY KEY,
    "threadId" UUID,
    "type" TEXT,
    "url" TEXT,
    "chainlitKey" TEXT,
    "name" TEXT NOT NULL,
    "display" TEXT,
    "objectKey" TEXT,
    "size" TEXT,
    "page" INT,
    "language" TEXT,
    "forId" UUID,
    "mime" TEXT,
    "props" JSONB,
    FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedbacks (
    "id" UUID PRIMARY KEY,
    "forId" UUID NOT NULL,
    "threadId" UUID NOT NULL,
    "value" INT NOT NULL,
    "comment" TEXT,
    FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
);
"""

def init_db():
    print(f"Connecting to {db_url}...")
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Drop các bảng cũ bị lệch schema
        print("Xóa các bảng cũ (để update schema mới)...")
        cur.execute("DROP TABLE IF EXISTS feedbacks CASCADE;")
        cur.execute("DROP TABLE IF EXISTS elements CASCADE;")
        cur.execute("DROP TABLE IF EXISTS steps CASCADE;")
        cur.execute("DROP TABLE IF EXISTS threads CASCADE;")
        cur.execute("DROP TABLE IF EXISTS users CASCADE;")
        
        print("Tạo lại schema chuẩn...")
        cur.execute(CREATE_TABLES_SQL)
        conn.commit()
        cur.close()
        conn.close()
        print("Cơ sở dữ liệu (Schema) của Chainlit đã được tạo MỚI thành công!")
    except Exception as e:
        print("Lỗi khi khởi tạo CSDL:", e)

if __name__ == "__main__":
    init_db()
