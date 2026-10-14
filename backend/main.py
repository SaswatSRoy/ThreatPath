"""
ThreatPath Backend Main Application
FastAPI Modular Monolith Entrypoint
"""
import logging
from fastapi import FastAPI
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

# Enable CORS for local frontend development (Vite default is 5173)
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

app.include_router(router)


@app.get("/")
def root():
    return {
        "project": "ThreatPath",
        "description": "Graph-Native Defensive Security Investigation Agent",
        "track": "Track 01 — Agents That Act on Connected Data",
        "hackathon": "Graph Hacks 2026",
        "graph_database": "FalkorDB",
        "active_graph": settings.FALKORDB_GRAPH,
        "docs_url": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False
    )
