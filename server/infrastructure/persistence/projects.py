from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import text


PROJECTS_MIGRATION_SQL = (
    """
    CREATE TABLE IF NOT EXISTS projects (
        "id" UUID PRIMARY KEY,
        "name" TEXT NOT NULL,
        "userId" UUID NOT NULL REFERENCES users("id") ON DELETE CASCADE,
        "createdAt" TEXT NOT NULL,
        "updatedAt" TEXT NOT NULL,
        "metadata" JSONB DEFAULT '{}'::jsonb
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_threads (
        "threadId" UUID PRIMARY KEY REFERENCES threads("id") ON DELETE CASCADE,
        "projectId" UUID NOT NULL REFERENCES projects("id") ON DELETE CASCADE,
        "createdAt" TEXT NOT NULL
    )
    """,
    'CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects ("userId")',
    'CREATE INDEX IF NOT EXISTS idx_project_threads_project_id ON project_threads ("projectId")',
    'CREATE INDEX IF NOT EXISTS idx_steps_thread_created_at ON steps ("threadId", "createdAt" DESC)',
)


class ProjectNotFoundError(ValueError):
    pass


class ThreadNotFoundError(ValueError):
    pass


@dataclass(frozen=True)
class ThreadPage:
    data: list[dict[str, Any]]
    has_next_page: bool
    start_cursor: Optional[str]
    end_cursor: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pageInfo": {
                "hasNextPage": self.has_next_page,
                "startCursor": self.start_cursor,
                "endCursor": self.end_cursor,
            },
            "data": self.data,
        }


class ProjectStore:
    def __init__(self, data_layer: Any):
        if not hasattr(data_layer, "engine") or not hasattr(
            data_layer, "async_session"
        ):
            raise TypeError("Projects require Chainlit's SQLAlchemyDataLayer")
        self.data_layer = data_layer

    async def migrate(self) -> None:
        async with self.data_layer.engine.begin() as connection:
            for statement in PROJECTS_MIGRATION_SQL:
                await connection.execute(text(statement))

    async def list_projects(self, user_id: str) -> list[dict[str, Any]]:
        query = text(
            """
            SELECT
                p."id",
                p."name",
                p."createdAt",
                GREATEST(
                    p."updatedAt",
                    COALESCE(MAX(s."createdAt"), p."updatedAt")
                ) AS "updatedAt",
                COUNT(DISTINCT pt."threadId") AS "threadCount"
            FROM projects p
            LEFT JOIN project_threads pt ON pt."projectId" = p."id"
            LEFT JOIN steps s ON s."threadId" = pt."threadId"
            WHERE p."userId" = CAST(:user_id AS uuid)
            GROUP BY p."id", p."name", p."createdAt", p."updatedAt"
            ORDER BY "updatedAt" DESC, p."id" DESC
            """
        )
        async with self.data_layer.async_session() as session:
            rows = (await session.execute(query, {"user_id": user_id})).mappings()
            return [self._project_dict(row) for row in rows]

    async def create_project(
        self, user_id: str, name: str, now: str
    ) -> dict[str, Any]:
        project_id = str(uuid4())
        query = text(
            """
            INSERT INTO projects (
                "id", "name", "userId", "createdAt", "updatedAt", "metadata"
            )
            VALUES (
                CAST(:id AS uuid),
                :name,
                CAST(:user_id AS uuid),
                :created_at,
                :updated_at,
                '{}'::jsonb
            )
            RETURNING "id", "name", "createdAt", "updatedAt"
            """
        )
        async with self.data_layer.async_session() as session:
            async with session.begin():
                row = (
                    await session.execute(
                        query,
                        {
                            "id": project_id,
                            "name": name,
                            "user_id": user_id,
                            "created_at": now,
                            "updated_at": now,
                        },
                    )
                ).mappings().one()
        project = self._project_dict(row)
        project["threadCount"] = 0
        return project

    async def rename_project(
        self, project_id: UUID, user_id: str, name: str, now: str
    ) -> dict[str, Any]:
        query = text(
            """
            UPDATE projects
            SET "name" = :name, "updatedAt" = :updated_at
            WHERE "id" = CAST(:project_id AS uuid)
              AND "userId" = CAST(:user_id AS uuid)
            RETURNING "id", "name", "createdAt", "updatedAt"
            """
        )
        async with self.data_layer.async_session() as session:
            async with session.begin():
                row = (
                    await session.execute(
                        query,
                        {
                            "project_id": str(project_id),
                            "user_id": user_id,
                            "name": name,
                            "updated_at": now,
                        },
                    )
                ).mappings().one_or_none()
        if row is None:
            raise ProjectNotFoundError("Project not found")
        project = self._project_dict(row)
        project["threadCount"] = await self._thread_count(project_id, user_id)
        return project

    async def delete_project(self, project_id: UUID, user_id: str) -> list[str]:
        async with self.data_layer.async_session() as session:
            async with session.begin():
                owned_project = (
                    await session.execute(
                        text(
                            """
                            SELECT "id"
                            FROM projects
                            WHERE "id" = CAST(:project_id AS uuid)
                              AND "userId" = CAST(:user_id AS uuid)
                            FOR UPDATE
                            """
                        ),
                        {
                            "project_id": str(project_id),
                            "user_id": user_id,
                        },
                    )
                ).scalar_one_or_none()
                if owned_project is None:
                    raise ProjectNotFoundError("Project not found")

                thread_ids = (
                    await session.execute(
                        text(
                            """
                            SELECT pt."threadId"
                            FROM project_threads pt
                            JOIN threads t ON t."id" = pt."threadId"
                            WHERE pt."projectId" = CAST(:project_id AS uuid)
                              AND t."userId" = CAST(:user_id AS uuid)
                            """
                        ),
                        {
                            "project_id": str(project_id),
                            "user_id": user_id,
                        },
                    )
                ).scalars().all()

                if thread_ids:
                    storage_provider = getattr(
                        self.data_layer, "storage_provider", None
                    )
                    if storage_provider is not None:
                        object_keys = (
                            await session.execute(
                                text(
                                    """
                                    SELECT "objectKey"
                                    FROM elements
                                    WHERE "threadId" = ANY(
                                        CAST(:thread_ids AS uuid[])
                                    )
                                      AND "objectKey" IS NOT NULL
                                    """
                                ),
                                {
                                    "thread_ids": [
                                        str(thread_id) for thread_id in thread_ids
                                    ]
                                },
                            )
                        ).scalars().all()
                        for object_key in object_keys:
                            await storage_provider.delete_file(
                                object_key=object_key
                            )

                    await session.execute(
                        text(
                            """
                            DELETE FROM threads
                            WHERE "id" = ANY(CAST(:thread_ids AS uuid[]))
                              AND "userId" = CAST(:user_id AS uuid)
                            """
                        ),
                        {
                            "thread_ids": [str(thread_id) for thread_id in thread_ids],
                            "user_id": user_id,
                        },
                    )

                await session.execute(
                    text(
                        """
                        DELETE FROM projects
                        WHERE "id" = CAST(:project_id AS uuid)
                          AND "userId" = CAST(:user_id AS uuid)
                        """
                    ),
                    {
                        "project_id": str(project_id),
                        "user_id": user_id,
                    },
                )
        return [str(thread_id) for thread_id in thread_ids]

    async def list_project_threads(
        self,
        project_id: UUID,
        user_id: str,
        first: int,
        cursor: Optional[UUID],
    ) -> ThreadPage:
        await self._require_project(project_id, user_id)
        return await self._list_threads(
            user_id=user_id,
            first=first,
            cursor=cursor,
            project_id=project_id,
        )

    async def list_unassigned_threads(
        self, user_id: str, first: int, cursor: Optional[UUID]
    ) -> ThreadPage:
        return await self._list_threads(
            user_id=user_id,
            first=first,
            cursor=cursor,
            project_id=None,
        )

    async def assign_thread(
        self,
        thread_id: UUID,
        user_id: str,
        project_id: Optional[UUID],
        now: str,
    ) -> None:
        async with self.data_layer.async_session() as session:
            async with session.begin():
                owned_thread = (
                    await session.execute(
                        text(
                            """
                            SELECT "id"
                            FROM threads
                            WHERE "id" = CAST(:thread_id AS uuid)
                              AND "userId" = CAST(:user_id AS uuid)
                            FOR UPDATE
                            """
                        ),
                        {
                            "thread_id": str(thread_id),
                            "user_id": user_id,
                        },
                    )
                ).scalar_one_or_none()
                if owned_thread is None:
                    raise ThreadNotFoundError("Thread not found")

                if project_id is None:
                    await session.execute(
                        text(
                            """
                            DELETE FROM project_threads
                            WHERE "threadId" = CAST(:thread_id AS uuid)
                            """
                        ),
                        {"thread_id": str(thread_id)},
                    )
                    return

                owned_project = (
                    await session.execute(
                        text(
                            """
                            SELECT "id"
                            FROM projects
                            WHERE "id" = CAST(:project_id AS uuid)
                              AND "userId" = CAST(:user_id AS uuid)
                            FOR UPDATE
                            """
                        ),
                        {
                            "project_id": str(project_id),
                            "user_id": user_id,
                        },
                    )
                ).scalar_one_or_none()
                if owned_project is None:
                    raise ProjectNotFoundError("Project not found")

                await session.execute(
                    text(
                        """
                        INSERT INTO project_threads ("threadId", "projectId", "createdAt")
                        VALUES (
                            CAST(:thread_id AS uuid),
                            CAST(:project_id AS uuid),
                            :created_at
                        )
                        ON CONFLICT ("threadId") DO UPDATE
                        SET "projectId" = EXCLUDED."projectId",
                            "createdAt" = EXCLUDED."createdAt"
                        """
                    ),
                    {
                        "thread_id": str(thread_id),
                        "project_id": str(project_id),
                        "created_at": now,
                    },
                )
                await session.execute(
                    text(
                        """
                        UPDATE projects
                        SET "updatedAt" = :updated_at
                        WHERE "id" = CAST(:project_id AS uuid)
                        """
                    ),
                    {
                        "project_id": str(project_id),
                        "updated_at": now,
                    },
                )

    async def _require_project(self, project_id: UUID, user_id: str) -> None:
        query = text(
            """
            SELECT "id"
            FROM projects
            WHERE "id" = CAST(:project_id AS uuid)
              AND "userId" = CAST(:user_id AS uuid)
            """
        )
        async with self.data_layer.async_session() as session:
            found = (
                await session.execute(
                    query,
                    {"project_id": str(project_id), "user_id": user_id},
                )
            ).scalar_one_or_none()
        if found is None:
            raise ProjectNotFoundError("Project not found")

    async def _thread_count(self, project_id: UUID, user_id: str) -> int:
        query = text(
            """
            SELECT COUNT(*)
            FROM project_threads pt
            JOIN projects p ON p."id" = pt."projectId"
            WHERE pt."projectId" = CAST(:project_id AS uuid)
              AND p."userId" = CAST(:user_id AS uuid)
            """
        )
        async with self.data_layer.async_session() as session:
            return int(
                (
                    await session.execute(
                        query,
                        {"project_id": str(project_id), "user_id": user_id},
                    )
                ).scalar_one()
            )

    async def _list_threads(
        self,
        user_id: str,
        first: int,
        cursor: Optional[UUID],
        project_id: Optional[UUID],
    ) -> ThreadPage:
        project_filter = (
            'pt."projectId" = CAST(:project_id AS uuid)'
            if project_id is not None
            else 'pt."threadId" IS NULL'
        )
        query = text(
            f"""
            WITH activity AS (
                SELECT
                    t."id",
                    t."name",
                    t."createdAt",
                    COALESCE(MAX(s."createdAt"), t."createdAt", '') AS updated_at,
                    pt."projectId" AS project_id
                FROM threads t
                LEFT JOIN project_threads pt ON pt."threadId" = t."id"
                LEFT JOIN steps s ON s."threadId" = t."id"
                WHERE t."userId" = CAST(:user_id AS uuid)
                  AND {project_filter}
                GROUP BY
                    t."id",
                    t."name",
                    t."createdAt",
                    pt."projectId"
            ),
            cursor_row AS (
                SELECT updated_at, "id"
                FROM activity
                WHERE "id" = CAST(:cursor AS uuid)
            )
            SELECT "id", "name", "createdAt", updated_at, project_id
            FROM activity
            WHERE CAST(:cursor AS uuid) IS NULL
               OR (updated_at, "id") < (
                    (SELECT updated_at FROM cursor_row),
                    CAST(:cursor AS uuid)
               )
            ORDER BY updated_at DESC, "id" DESC
            LIMIT :limit
            """
        )
        parameters = {
            "user_id": user_id,
            "project_id": str(project_id) if project_id else None,
            "cursor": str(cursor) if cursor else None,
            "limit": first + 1,
        }
        async with self.data_layer.async_session() as session:
            rows = list((await session.execute(query, parameters)).mappings())

        has_next_page = len(rows) > first
        page_rows = rows[:first]
        data = [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "createdAt": row["createdAt"],
                "updatedAt": row["updated_at"],
                "projectId": (
                    str(row["project_id"]) if row["project_id"] is not None else None
                ),
            }
            for row in page_rows
        ]
        return ThreadPage(
            data=data,
            has_next_page=has_next_page,
            start_cursor=data[0]["id"] if data else None,
            end_cursor=data[-1]["id"] if data else None,
        )

    @staticmethod
    def _project_dict(row: Any) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "name": row["name"],
            "createdAt": row["createdAt"],
            "updatedAt": row["updatedAt"],
            "threadCount": int(row.get("threadCount", 0)),
        }
