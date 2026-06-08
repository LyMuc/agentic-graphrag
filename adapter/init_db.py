import asyncio
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from adapter.data_layer import data_layer
from adapter.projects import ProjectStore


async def migrate_db() -> None:
    """Apply non-destructive application migrations."""
    await ProjectStore(data_layer).migrate()


if __name__ == "__main__":
    asyncio.run(migrate_db())
    print("Database migrations completed successfully.")
