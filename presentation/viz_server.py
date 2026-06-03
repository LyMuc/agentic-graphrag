"""FastAPI server cho trang visualize đồ thị tri thức."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from adapter.graph_viz import resolve_viz_snapshot
from adapter.viz_store import load_snapshot

VIZ_DIR = Path(__file__).resolve().parent.parent / "viz"
INDEX_HTML = (VIZ_DIR / "index.html").read_text(encoding="utf-8")

app = FastAPI(title="KG Graph Visualize", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory=str(VIZ_DIR)), name="static")


@app.on_event("startup")
def _log_local_url() -> None:
    print(
        "\n[KG Viz] Mo trinh duyet tai: http://localhost:8501/viz/{viz_id}\n"
        "         (Khong dung http://0.0.0.0:8501 — trinh duyet khong truy cap duoc.)\n"
    )


@app.get("/api/viz/{viz_id}")
def get_viz_data(viz_id: str):
    payload = resolve_viz_snapshot(viz_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Snapshot không tồn tại hoặc đã hết hạn.")
    return payload


@app.get("/viz/{viz_id}", response_class=HTMLResponse)
def viz_page(viz_id: str):
    if load_snapshot(viz_id) is None:
        return HTMLResponse(
            "<h2>Không tìm thấy snapshot đồ thị.</h2>"
            "<p>Link có thể đã hết hạn (TTL 7 ngày) hoặc viz server đã restart.</p>",
            status_code=404,
        )
    return HTMLResponse(INDEX_HTML.replace("{{VIZ_ID}}", viz_id))


@app.get("/")
def root():
    return HTMLResponse(
        "<h2>KG Graph Visualize</h2>"
        "<p>Truy cập: <code>http://localhost:8501/viz/{viz_id}</code></p>"
        "<p><em>Không dùng <code>0.0.0.0</code> trên trình duyệt — chỉ dùng "
        "<code>localhost</code>.</em></p>"
        "<p>Link visualize xuất hiện ở cuối câu trả lời chatbot (retriever V3).</p>"
    )
