"""
ThreatPath Backend Main Application
FastAPI Modular Monolith Entrypoint with Static Frontend Serving
"""
import os
import logging
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.api.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("threatpath")

app = FastAPI(
    title="ThreatPath — Graph-Native Defensive Investigation Agent",
    description="FalkorDB-powered defensive security investigation agent for Graph Hacks 2026 (Track 01)",
    version="1.0.0"
)

# Enable CORS for local frontend development (Vite default is 5173) and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes under /api
app.include_router(router)

# Resolve frontend production distribution directory
DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
ASSETS_DIR = DIST_DIR / "assets"

if ASSETS_DIR.exists() and ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/")
def root(request: Request):
    """
    Root route:
    - Returns frontend index.html for browser navigation requests when dist is present.
    - Returns structured project metadata JSON for API clients and tests.
    """
    accept = request.headers.get("accept", "")
    index_file = DIST_DIR / "index.html"
    if "text/html" in accept and index_file.exists():
        return FileResponse(str(index_file))

    return {
        "project": "ThreatPath",
        "description": "Graph-Native Defensive Security Investigation Agent",
        "track": "Track 01 — Agents That Act on Connected Data",
        "hackathon": "Graph Hacks 2026",
        "graph_database": "FalkorDB",
        "active_graph": settings.FALKORDB_GRAPH,
        "docs_url": "/docs"
    }


@app.get("/{full_path:path}")
def catch_all_spa_fallback(full_path: str):
    """
    Single Page Application fallback:
    - Never serves index.html for missing /api routes (preserves strict 404).
    - Serves static files if they exist in dist/.
    - Falls back to index.html for client-side routing.
    """
    if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
        raise HTTPException(status_code=404, detail="Endpoint not found")

    target_file = DIST_DIR / full_path
    if target_file.exists() and target_file.is_file():
        return FileResponse(str(target_file))

    index_file = DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))

    raise HTTPException(status_code=404, detail=f"File not found: /{full_path}")


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", settings.APP_HOST)
    port = int(os.environ.get("PORT", settings.effective_port))
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=False
    )
