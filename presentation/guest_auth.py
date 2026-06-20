from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from adapter.guest import (
    GUEST_IDENTIFIER_PREFIX,
    create_guest_user,
    is_guest_user,
)
from chainlit.auth import get_token_from_cookies, set_auth_cookie
from chainlit.auth.jwt import create_jwt, decode_jwt

router = APIRouter()

GUEST_FORBIDDEN_MESSAGE = "Login is required to manage conversations"


def get_request_user(request: Request):
    token = get_token_from_cookies(request.cookies)
    if not token:
        return None
    try:
        return decode_jwt(token)
    except Exception:
        return None


def is_guest_management_request(method: str, path: str) -> bool:
    if method in {"PUT", "DELETE"} and path == "/feedback":
        return True
    if path == "/project/threads" and method == "POST":
        return True
    if path.startswith("/project/thread/") and method in {"GET", "PUT", "DELETE"}:
        return True
    if path == "/project/thread" and method in {"PUT", "DELETE"}:
        return True
    if path.startswith("/project/projects"):
        return True
    if path.startswith("/project/threads/"):
        return True
    return False


async def guest_management_guard(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    path = request.scope.get("path", request.url.path)
    if is_guest_management_request(request.method, path):
        user = get_request_user(request)
        if is_guest_user(user):
            return JSONResponse(
                status_code=403,
                content={"detail": GUEST_FORBIDDEN_MESSAGE},
            )
    return await call_next(request)


@router.post("/auth/guest")
async def guest_auth(request: Request) -> JSONResponse:
    response = JSONResponse(content={"success": True})
    current_user = get_request_user(request)

    if current_user is not None:
        return response

    guest = create_guest_user(f"{GUEST_IDENTIFIER_PREFIX}{uuid4()}")
    set_auth_cookie(request, response, create_jwt(guest))
    return response
