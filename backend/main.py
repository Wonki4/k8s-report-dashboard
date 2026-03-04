import asyncio
import logging
import os
from pathlib import Path
from typing import List

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from k8s_client import get_k8s_client, list_clusters
from models import ClusterInfo, ClusterSummary, NodeDetail

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="K8s GPU Dashboard", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health check — lightweight, no K8s API dependency
# ---------------------------------------------------------------------------
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# API endpoints — all blocking K8s calls run in a thread pool via
# asyncio.to_thread() so the event loop stays responsive for health probes.
# ---------------------------------------------------------------------------
@app.get("/api/cluster-summary", response_model=ClusterSummary)
async def get_cluster_summary():
    k8s = get_k8s_client()
    return await asyncio.to_thread(k8s.get_cluster_summary)


@app.get("/api/nodes", response_model=List[NodeDetail])
async def get_nodes():
    k8s = get_k8s_client()
    return await asyncio.to_thread(k8s.get_nodes_with_pods)


@app.get("/api/clusters", response_model=List[ClusterInfo])
async def get_clusters():
    clusters, _ = await asyncio.to_thread(list_clusters)
    return clusters


@app.get("/api/clusters/{cluster_name}/nodes", response_model=List[NodeDetail])
async def get_cluster_nodes(cluster_name: str):
    k8s = get_k8s_client(context=cluster_name)
    return await asyncio.to_thread(k8s.get_nodes_with_pods)


@app.get("/api/clusters/{cluster_name}/summary", response_model=ClusterSummary)
async def get_cluster_summary_by_name(cluster_name: str):
    k8s = get_k8s_client(context=cluster_name)
    return await asyncio.to_thread(k8s.get_cluster_summary)


# ---------------------------------------------------------------------------
# Serve frontend static files in production (Docker build)
# ---------------------------------------------------------------------------
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")

if __name__ == "__main__":
    host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    port = int(os.getenv("DASHBOARD_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
