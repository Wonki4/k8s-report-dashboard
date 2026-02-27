from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List
import uvicorn
import os
from pathlib import Path

from models import NodeDetail, ClusterSummary, ClusterInfo
from k8s_client import get_k8s_client, list_clusters

app = FastAPI(title="K8s GPU Dashboard", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/cluster-summary", response_model=ClusterSummary)
async def get_cluster_summary():
    return get_k8s_client().get_cluster_summary()



@app.get("/api/nodes", response_model=List[NodeDetail])
async def get_nodes():
    return get_k8s_client().get_nodes_with_pods()


@app.get("/api/clusters", response_model=List[ClusterInfo])
async def get_clusters():
    clusters, _ = list_clusters()
    return clusters


@app.get("/api/clusters/{cluster_name}/nodes", response_model=List[NodeDetail])
async def get_cluster_nodes(cluster_name: str):
    return get_k8s_client(context=cluster_name).get_nodes_with_pods()


@app.get("/api/clusters/{cluster_name}/summary", response_model=ClusterSummary)
async def get_cluster_summary_by_name(cluster_name: str):
    return get_k8s_client(context=cluster_name).get_cluster_summary()

# Serve frontend static files in production (Docker build)
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
