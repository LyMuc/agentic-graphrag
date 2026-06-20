from http.cookies import SimpleCookie
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request

from adapter.data_layer import GuestAwareSQLAlchemyDataLayer
from adapter.guest import (
    create_guest_user,
    create_persisted_guest,
    is_guest_user,
)
from chainlit.auth.jwt import create_jwt, decode_jwt
from chainlit.context import context_var
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.user import User
from presentation.guest_auth import (
    guest_auth,
    guest_management_guard,
    is_guest_management_request,
)


def _request(cookie: str | None = None) -> Request:
    headers = []
    if cookie:
        headers.append((b"cookie", cookie.encode("ascii")))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/auth/guest",
            "headers": headers,
        }
    )


def _route_request(method: str, path: str, cookie: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [(b"cookie", cookie.encode("ascii"))],
        }
    )


def _access_token(response) -> str:
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    return cookie["access_token"].value


@pytest.mark.asyncio
async def test_guest_auth_sets_guest_jwt_without_persisting_user(monkeypatch):
    monkeypatch.setenv(
        "CHAINLIT_AUTH_SECRET",
        "guest-auth-test-secret-that-is-at-least-32-bytes",
    )

    response = await guest_auth(_request())
    user = decode_jwt(_access_token(response))

    assert response.status_code == 200
    assert user.identifier.startswith("guest:")
    assert user.metadata == {"auth_mode": "guest", "name": "Guest"}
    assert is_guest_user(user)


@pytest.mark.asyncio
async def test_guest_auth_does_not_replace_real_user_cookie(monkeypatch):
    monkeypatch.setenv(
        "CHAINLIT_AUTH_SECRET",
        "guest-auth-test-secret-that-is-at-least-32-bytes",
    )
    real_token = create_jwt(
        User(identifier="real@example.test", metadata={"provider": "google"})
    )

    response = await guest_auth(_request(f"access_token={real_token}"))

    assert response.status_code == 200
    assert "set-cookie" not in response.headers


@pytest.mark.asyncio
async def test_guest_management_middleware_returns_403(monkeypatch):
    monkeypatch.setenv(
        "CHAINLIT_AUTH_SECRET",
        "guest-auth-test-secret-that-is-at-least-32-bytes",
    )
    guest_token = create_jwt(create_guest_user("guest:middleware-test"))
    call_next = AsyncMock()

    response = await guest_management_guard(
        _route_request(
            "POST",
            "/project/threads",
            f"access_token={guest_token}",
        ),
        call_next,
    )

    assert response.status_code == 403
    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_guest_data_layer_returns_synthetic_user_and_skips_writes():
    layer = GuestAwareSQLAlchemyDataLayer(
        conninfo="postgresql+asyncpg://postgres:postgres@localhost/test"
    )
    identifier = "guest:data-layer-test"
    guest = await layer.get_user(identifier)

    assert guest is not None
    assert guest.identifier == identifier
    assert guest.metadata["auth_mode"] == "guest"
    assert guest.id == create_persisted_guest(identifier, guest.metadata).id

    token = context_var.set(SimpleNamespace(session=SimpleNamespace(user=guest)))
    try:
        await layer.update_thread("thread-id", name="ignored")
        await layer.delete_thread("thread-id")
        await layer.create_step({"id": "step-id"})
        await layer.update_step({"id": "step-id"})
        await layer.delete_step("step-id")
        await layer.create_element(SimpleNamespace(id="element-id"))
        await layer.delete_element("element-id")
    finally:
        context_var.reset(token)


@pytest.mark.asyncio
async def test_real_user_data_layer_write_delegates_to_sqlalchemy():
    layer = GuestAwareSQLAlchemyDataLayer(
        conninfo="postgresql+asyncpg://postgres:postgres@localhost/test"
    )
    user = User(identifier="real@example.test", metadata={})
    token = context_var.set(SimpleNamespace(session=SimpleNamespace(user=user)))
    update_thread = AsyncMock(return_value=None)
    try:
        with patch.object(SQLAlchemyDataLayer, "update_thread", update_thread):
            await layer.update_thread("thread-id", name="saved")
    finally:
        context_var.reset(token)

    update_thread.assert_awaited_once_with("thread-id", name="saved")


@pytest.mark.parametrize(
    ("method", "path", "expected"),
    [
        ("POST", "/project/threads", True),
        ("GET", "/project/thread/thread-id", True),
        ("PUT", "/project/thread", True),
        ("PUT", "/project/thread/share", True),
        ("DELETE", "/project/projects/project-id", True),
        ("PUT", "/project/threads/thread-id/project", True),
        ("PUT", "/feedback", True),
        ("POST", "/project/file", False),
        ("POST", "/project/action", False),
        ("GET", "/project/share/thread-id", False),
    ],
)
def test_guest_management_route_classification(method, path, expected):
    assert is_guest_management_request(method, path) is expected
