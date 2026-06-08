import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from adapter.data_layer import data_layer
from adapter.projects import (
    ProjectNotFoundError,
    ProjectStore,
    ThreadNotFoundError,
)


pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is required for project integration tests",
)


@pytest.mark.asyncio
async def test_project_crud_assignment_ownership_and_cascade_delete():
    store = ProjectStore(data_layer)
    await store.migrate()
    await store.migrate()

    user_a = str(uuid4())
    user_b = str(uuid4())
    thread_a_unassigned = str(uuid4())
    thread_a_to_delete = str(uuid4())
    thread_b = str(uuid4())
    step_to_delete = str(uuid4())
    now = "2026-06-07T00:00:00Z"

    async with data_layer.async_session() as session:
        async with session.begin():
            await session.execute(
                text(
                    """
                    INSERT INTO users ("id", "identifier", "metadata", "createdAt")
                    VALUES
                        (CAST(:user_a AS uuid), :identifier_a, '{}'::jsonb, :now),
                        (CAST(:user_b AS uuid), :identifier_b, '{}'::jsonb, :now)
                    """
                ),
                {
                    "user_a": user_a,
                    "identifier_a": f"projects-a-{user_a}@example.test",
                    "user_b": user_b,
                    "identifier_b": f"projects-b-{user_b}@example.test",
                    "now": now,
                },
            )
            await session.execute(
                text(
                    """
                    INSERT INTO threads (
                        "id", "createdAt", "name", "userId", "userIdentifier",
                        "tags", "metadata"
                    )
                    VALUES
                        (
                            CAST(:thread_a_unassigned AS uuid), :now, 'A unassigned',
                            CAST(:user_a AS uuid), :identifier_a, NULL, '{}'::jsonb
                        ),
                        (
                            CAST(:thread_a_to_delete AS uuid), :now, 'A delete',
                            CAST(:user_a AS uuid), :identifier_a, NULL, '{}'::jsonb
                        ),
                        (
                            CAST(:thread_b AS uuid), :now, 'B thread',
                            CAST(:user_b AS uuid), :identifier_b, NULL, '{}'::jsonb
                        )
                    """
                ),
                {
                    "thread_a_unassigned": thread_a_unassigned,
                    "thread_a_to_delete": thread_a_to_delete,
                    "thread_b": thread_b,
                    "user_a": user_a,
                    "user_b": user_b,
                    "identifier_a": f"projects-a-{user_a}@example.test",
                    "identifier_b": f"projects-b-{user_b}@example.test",
                    "now": now,
                },
            )
            await session.execute(
                text(
                    """
                    INSERT INTO steps (
                        "id", "name", "type", "threadId", "streaming",
                        "metadata", "input", "output", "createdAt"
                    )
                    VALUES (
                        CAST(:step_id AS uuid), 'assistant', 'assistant_message',
                        CAST(:thread_id AS uuid), false, '{}'::jsonb, '', 'answer', :now
                    )
                    """
                ),
                {
                    "step_id": step_to_delete,
                    "thread_id": thread_a_to_delete,
                    "now": now,
                },
            )

    try:
        project_a = await store.create_project(user_a, "Project A", now)
        project_b = await store.create_project(user_b, "Project B", now)
        project_a_id = UUID(project_a["id"])
        project_b_id = UUID(project_b["id"])
        thread_a_unassigned_id = UUID(thread_a_unassigned)
        thread_a_to_delete_id = UUID(thread_a_to_delete)
        thread_b_id = UUID(thread_b)

        assert [project["id"] for project in await store.list_projects(user_a)] == [
            project_a["id"]
        ]

        await store.assign_thread(
            thread_a_to_delete_id, user_a, project_a_id, now
        )
        project_page = await store.list_project_threads(
            project_a_id, user_a, 35, None
        )
        assert [thread["id"] for thread in project_page.data] == [
            thread_a_to_delete
        ]

        unassigned_page = await store.list_unassigned_threads(user_a, 35, None)
        assert thread_a_unassigned in {
            thread["id"] for thread in unassigned_page.data
        }
        assert thread_a_to_delete not in {
            thread["id"] for thread in unassigned_page.data
        }

        with pytest.raises(ThreadNotFoundError):
            await store.assign_thread(thread_b_id, user_a, project_a_id, now)
        with pytest.raises(ProjectNotFoundError):
            await store.rename_project(project_a_id, user_b, "Forbidden", now)
        with pytest.raises(ProjectNotFoundError):
            await store.assign_thread(
                thread_a_unassigned_id, user_a, project_b_id, now
            )

        await store.assign_thread(
            thread_a_unassigned_id, user_a, project_a_id, now
        )
        await store.assign_thread(thread_a_unassigned_id, user_a, None, now)
        await store.assign_thread(thread_a_to_delete_id, user_a, None, now)
        unassigned_page = await store.list_unassigned_threads(user_a, 1, None)
        assert unassigned_page.has_next_page is True
        next_page = await store.list_unassigned_threads(
            user_a, 1, UUID(unassigned_page.end_cursor)
        )
        assert len(next_page.data) == 1
        await store.assign_thread(
            thread_a_to_delete_id, user_a, project_a_id, now
        )

        await store.delete_project(project_a_id, user_a)

        async with data_layer.async_session() as session:
            deleted_thread = (
                await session.execute(
                    text(
                        'SELECT "id" FROM threads WHERE "id" = CAST(:id AS uuid)'
                    ),
                    {"id": thread_a_to_delete},
                )
            ).scalar_one_or_none()
            deleted_step = (
                await session.execute(
                    text('SELECT "id" FROM steps WHERE "id" = CAST(:id AS uuid)'),
                    {"id": step_to_delete},
                )
            ).scalar_one_or_none()
            other_user_thread = (
                await session.execute(
                    text(
                        'SELECT "id" FROM threads WHERE "id" = CAST(:id AS uuid)'
                    ),
                    {"id": thread_b},
                )
            ).scalar_one_or_none()

        assert deleted_thread is None
        assert deleted_step is None
        assert str(other_user_thread) == thread_b
        assert [project["id"] for project in await store.list_projects(user_b)] == [
            project_b["id"]
        ]
    finally:
        async with data_layer.async_session() as session:
            async with session.begin():
                await session.execute(
                    text(
                        'DELETE FROM users WHERE "id" IN '
                        '(CAST(:user_a AS uuid), CAST(:user_b AS uuid))'
                    ),
                    {"user_a": user_a, "user_b": user_b},
                )
