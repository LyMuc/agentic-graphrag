"""Route visualize đồ thị tri thức — mount vào Chainlit FastAPI app."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from server.infrastructure.viz.graph_viz import resolve_viz_snapshot
from server.infrastructure.viz.store import load_snapshot

VIZ_DIR = Path(__file__).resolve().parents[3] / "viz"
VIZ_ASSETS_MOUNT = "/viz-assets"
INDEX_HTML = (VIZ_DIR / "index.html").read_text(encoding="utf-8")

router = APIRouter(tags=["kg-viz"])


@router.get("/api/viz/{viz_id}")
def get_viz_data(viz_id: str):
    payload = resolve_viz_snapshot(viz_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Snapshot không tồn tại hoặc đã hết hạn.")
    return payload


@router.get("/viz/{viz_id}", response_class=HTMLResponse)
def viz_page(viz_id: str):
    if load_snapshot(viz_id) is None:
        return HTMLResponse(
            "<h2>Không tìm thấy snapshot đồ thị.</h2>"
            "<p>Link có thể đã hết hạn (TTL 7 ngày) hoặc server đã restart.</p>",
            status_code=404,
        )
    return HTMLResponse(INDEX_HTML.replace("{{VIZ_ID}}", viz_id))


def _chainlit_spa_catch_all_index(fastapi_app: FastAPI) -> int | None:
    """Vị trí route SPA catch-all của Chainlit — viz phải đăng ký trước đó."""
    for index, route in enumerate(fastapi_app.routes):
        if getattr(route, "path", None) == "/{full_path:path}":
            return index
    return None


def register_viz_routes(fastapi_app: FastAPI) -> None:
    """Gắn route viz và static assets lên một FastAPI app."""
    if getattr(fastapi_app.state, "kg_viz_registered", False):
        return
    fastapi_app.state.kg_viz_registered = True

    route_count_before = len(fastapi_app.routes)

    fastapi_app.mount(
        VIZ_ASSETS_MOUNT,
        StaticFiles(directory=str(VIZ_DIR)),
        name=f"viz-assets-{id(fastapi_app)}",
    )
    fastapi_app.include_router(router)

    # Chainlit có GET /{full_path:path} trả SPA index.html. Route append sau
    # catch-all sẽ không bao giờ khớp khi mở tab mới /viz/{id}.
    new_routes = fastapi_app.routes[route_count_before:]
    del fastapi_app.routes[route_count_before:]

    insert_at = _chainlit_spa_catch_all_index(fastapi_app)
    if insert_at is None:
        insert_at = len(fastapi_app.routes)

    for offset, route in enumerate(new_routes):
        fastapi_app.routes.insert(insert_at + offset, route)
