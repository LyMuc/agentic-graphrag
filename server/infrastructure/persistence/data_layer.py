import os

import chainlit.data as cl_data
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

from server.infrastructure.persistence.guest import (
    create_persisted_guest,
    is_guest_context,
    is_guest_identifier,
    is_guest_user,
)

# PostgreSQL (Chainlit Data Layer) — format: postgresql+asyncpg://user:pass@host:port/dbname
DATABASE_URL = os.environ.get("DATABASE_URL")


class GuestAwareSQLAlchemyDataLayer(SQLAlchemyDataLayer):
    async def get_user(self, identifier: str):
        if is_guest_identifier(identifier):
            return create_persisted_guest(
                identifier,
                {"auth_mode": "guest", "name": "Guest"},
            )
        return await super().get_user(identifier)

    async def create_user(self, user):
        if is_guest_user(user):
            return create_persisted_guest(user.identifier, user.metadata or {})
        return await super().create_user(user)

    async def update_thread(self, *args, **kwargs):
        if is_guest_context():
            return None
        return await super().update_thread(*args, **kwargs)

    async def delete_thread(self, *args, **kwargs):
        if is_guest_context():
            return None
        return await super().delete_thread(*args, **kwargs)

    async def create_step(self, *args, **kwargs):
        if is_guest_context():
            return None
        return await super().create_step(*args, **kwargs)

    async def update_step(self, *args, **kwargs):
        if is_guest_context():
            return None
        return await super().update_step(*args, **kwargs)

    async def delete_step(self, *args, **kwargs):
        if is_guest_context():
            return None
        return await super().delete_step(*args, **kwargs)

    async def create_element(self, *args, **kwargs):
        if is_guest_context():
            return None
        return await super().create_element(*args, **kwargs)

    async def delete_element(self, *args, **kwargs):
        if is_guest_context():
            return None
        return await super().delete_element(*args, **kwargs)

    async def upsert_feedback(self, *args, **kwargs):
        if is_guest_context():
            raise PermissionError("Login is required to save feedback")
        return await super().upsert_feedback(*args, **kwargs)

    async def delete_feedback(self, *args, **kwargs):
        if is_guest_context():
            raise PermissionError("Login is required to delete feedback")
        return await super().delete_feedback(*args, **kwargs)


if DATABASE_URL:
    data_layer = GuestAwareSQLAlchemyDataLayer(conninfo=DATABASE_URL)
    cl_data._data_layer = data_layer
else:
    print(
        "WARNING: DATABASE_URL is not configured. "
        "Chainlit conversations will not be persisted."
    )
