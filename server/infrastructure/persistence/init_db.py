import asyncio
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[3]))

from server.infrastructure.persistence.data_layer import data_layer
from server.infrastructure.persistence.projects import ProjectStore


async def migrate_db() -> None:
    """Apply non-destructive application migrations."""
    await ProjectStore(data_layer).migrate()


if __name__ == "__main__":
    asyncio.run(migrate_db())
    print("Database migrations completed successfully.")
