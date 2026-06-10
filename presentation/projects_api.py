from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

import chainlit as cl
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from adapter.projects import (
    ProjectNotFoundError,
    ProjectStore,
    ThreadNotFoundError,
)
from adapter.guest import is_guest_user
from chainlit.auth import get_current_user
from chainlit.data import get_data_layer
from chainlit.server import app
from chainlit.user import PersistedUser, User
from chainlit.utils import utc_now


class ProjectNamePayload(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Project name is required")
        if len(normalized) > 100:
            raise ValueError("Project name must be at most 100 characters")
        return normalized


class ThreadPaginationPayload(BaseModel):
    first: int = Field(default=35, ge=1, le=100)
    cursor: Optional[UUID] = None


class AssignThreadPayload(BaseModel):
    projectId: Optional[UUID] = None


CurrentUser = Annotated[Optional[User], Depends(get_current_user)]
router = APIRouter()


def _store() -> ProjectStore:
    data_layer = get_data_layer()
    if data_layer is None:
        raise HTTPException(status_code=503, detail="Data persistence is not enabled")
    try:
        return ProjectStore(data_layer)
    except TypeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _user_id(current_user: Optional[User]) -> str:
    if is_guest_user(current_user):
        raise HTTPException(
            status_code=403,
            detail="Login is required to manage conversations",
        )
    if not isinstance(current_user, PersistedUser):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return current_user.id


@cl.on_app_startup
async def migrate_projects() -> None:
    data_layer = get_data_layer()
    if data_layer is not None:
        await ProjectStore(data_layer).migrate()


@router.post("/project/projects/list")
async def list_projects(current_user: CurrentUser):
    return await _store().list_projects(_user_id(current_user))


@router.post("/project/projects")
async def create_project(payload: ProjectNamePayload, current_user: CurrentUser):
    return await _store().create_project(
        _user_id(current_user), payload.name, utc_now()
    )


@router.put("/project/projects/{project_id}")
async def rename_project(
    project_id: UUID,
    payload: ProjectNamePayload,
    current_user: CurrentUser,
):
    try:
        return await _store().rename_project(
            project_id, _user_id(current_user), payload.name, utc_now()
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/project/projects/{project_id}")
async def delete_project(project_id: UUID, current_user: CurrentUser):
    try:
        deleted_thread_ids = await _store().delete_project(
            project_id, _user_id(current_user)
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "deletedThreadIds": deleted_thread_ids}


@router.post("/project/projects/{project_id}/threads")
async def list_project_threads(
    project_id: UUID,
    payload: ThreadPaginationPayload,
    current_user: CurrentUser,
):
    try:
        page = await _store().list_project_threads(
            project_id,
            _user_id(current_user),
            payload.first,
            payload.cursor,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return page.to_dict()


@router.post("/project/threads/unassigned")
async def list_unassigned_threads(
    payload: ThreadPaginationPayload,
    current_user: CurrentUser,
):
    page = await _store().list_unassigned_threads(
        _user_id(current_user), payload.first, payload.cursor
    )
    return page.to_dict()


@router.put("/project/threads/{thread_id}/project")
async def assign_thread(
    thread_id: UUID,
    payload: AssignThreadPayload,
    current_user: CurrentUser,
):
    try:
        await _store().assign_thread(
            thread_id,
            _user_id(current_user),
            payload.projectId,
            utc_now(),
        )
    except (ProjectNotFoundError, ThreadNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True}


app.include_router(router)
