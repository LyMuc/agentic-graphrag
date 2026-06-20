from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, uuid5

from chainlit.context import context_var
from chainlit.user import PersistedUser, User
from chainlit.utils import utc_now

GUEST_IDENTIFIER_PREFIX = "guest:"
GUEST_AUTH_MODE = "guest"


def is_guest_identifier(identifier: str | None) -> bool:
    return bool(identifier and identifier.startswith(GUEST_IDENTIFIER_PREFIX))


def is_guest_user(user: User | PersistedUser | None) -> bool:
    if user is None:
        return False
    metadata = user.metadata or {}
    return (
        metadata.get("auth_mode") == GUEST_AUTH_MODE
        or is_guest_identifier(user.identifier)
    )


def current_session_user() -> User | PersistedUser | None:
    context = context_var.get(None)
    if context is None:
        return None
    return getattr(context.session, "user", None)


def is_guest_context() -> bool:
    return is_guest_user(current_session_user())


def create_guest_user(identifier: str) -> User:
    if not is_guest_identifier(identifier):
        raise ValueError("Guest identifiers must start with 'guest:'")
    return User(
        identifier=identifier,
        display_name="Guest",
        metadata={"auth_mode": GUEST_AUTH_MODE, "name": "Guest"},
    )


def create_persisted_guest(identifier: str, metadata: dict[str, Any]) -> PersistedUser:
    return PersistedUser(
        id=str(uuid5(NAMESPACE_URL, identifier)),
        identifier=identifier,
        display_name="Guest",
        metadata=metadata,
        createdAt=utc_now(),
    )
