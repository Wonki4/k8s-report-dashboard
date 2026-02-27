"""Mock server for multi-cluster GPU dashboard testing."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="K8s GPU Dashboard (Mock)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLUSTERS = [
    {"name": "prod-us-east-1", "is_active": True},
    {"name": "prod-eu-west-1", "is_active": False},
    {"name": "staging-apne-1", "is_active": False},
]


def _make_container(
    name, state="running", ready=True, restarts=0, image="nvidia/cuda:12.4-runtime"
):
    return {
        "name": name,
        "state": state,
        "ready": ready,
        "restart_count": restarts,
        "image": image,
        "reason": None,
        "message": None,
        "started_at": "2026-02-26T01:00:00+00:00",
    }


def _make_pod(
    name,
    ns,
    owner_kind,
    owner_name,
    gpu_req=0,
    gpu_lim=0,
    cpu_req=500,
    cpu_lim=1000,
    mem_req=1073741824,
    mem_lim=2147483648,
    phase="Running",
    labels=None,
    containers=None,
):
    return {
        "name": name,
        "namespace": ns,
        "owner_kind": owner_kind,
        "owner_name": owner_name,
        "phase": phase,
        "gpu_request": gpu_req,
        "gpu_limit": gpu_lim,
        "cpu_request_millicores": cpu_req,
        "cpu_limit_millicores": cpu_lim,
        "memory_request_bytes": mem_req,
        "memory_limit_bytes": mem_lim,
        "containers": containers or [_make_container("main")],
        "created_at": "2026-02-25T10:00:00+00:00",
        "ip": "10.244.1.10",
        "qos_class": "Burstable",
        "labels": labels or {},
    }


# ── prod-us-east-1: 4 GPU nodes (A100, H100) ──

PROD_US_NODES = [
    {
        "name": "gpu-node-a100-01",
        "gpu_type": "NVIDIA-A100-SXM4-80GB",
        "gpu_total": 8,
        "gpu_allocatable": 8,
        "gpu_used": 6,
        "cpu_total_millicores": 128000,
        "cpu_allocatable_millicores": 126000,
        "cpu_used_millicores": 78000,
        "memory_total_bytes": 1099511627776,
        "memory_allocatable_bytes": 1082331758592,
        "memory_used_bytes": 687194767360,
        "labels": {
            "nvidia.com/gpu.product": "NVIDIA-A100-SXM4-80GB",
            "kubernetes.io/arch": "amd64",
            "topology.kubernetes.io/zone": "us-east-1a",
        },
        "pods": [
            _make_pod(
                "llm-train-a100-0",
                "ml-training",
                "StatefulSet",
                "llm-train-a100",
                gpu_req=2,
                gpu_lim=2,
                cpu_req=16000,
                cpu_lim=32000,
                mem_req=137438953472,
                mem_lim=274877906944,
                labels={
                    "app": "llm-training",
                    "gpu-type": "a100",
                    "team": "ml-platform",
                },
            ),
            _make_pod(
                "llm-train-a100-1",
                "ml-training",
                "StatefulSet",
                "llm-train-a100",
                gpu_req=2,
                gpu_lim=2,
                cpu_req=16000,
                cpu_lim=32000,
                mem_req=137438953472,
                mem_lim=274877906944,
                labels={
                    "app": "llm-training",
                    "gpu-type": "a100",
                    "team": "ml-platform",
                },
            ),
            _make_pod(
                "embedding-svc-7f8b9-xk2p1",
                "ml-serving",
                "ReplicaSet",
                "embedding-svc-7f8b9",
                gpu_req=1,
                gpu_lim=1,
                cpu_req=8000,
                cpu_lim=16000,
                mem_req=68719476736,
                mem_lim=137438953472,
                labels={"app": "embedding-svc", "team": "search"},
            ),
            _make_pod(
                "embedding-svc-7f8b9-m3n9z",
                "ml-serving",
                "ReplicaSet",
                "embedding-svc-7f8b9",
                gpu_req=1,
                gpu_lim=1,
                cpu_req=8000,
                cpu_lim=16000,
                mem_req=68719476736,
                mem_lim=137438953472,
                labels={"app": "embedding-svc", "team": "search"},
            ),
            _make_pod(
                "monitoring-agent-gpu-01",
                "monitoring",
                "DaemonSet",
                "monitoring-agent",
                cpu_req=200,
                cpu_lim=500,
                mem_req=268435456,
                mem_lim=536870912,
                labels={"app": "monitoring-agent"},
            ),
        ],
        "conditions_ready": True,
        "os": "Ubuntu 22.04.4 LTS",
        "arch": "amd64",
        "kubelet_version": "v1.29.3",
    },
    {
        "name": "gpu-node-a100-02",
        "gpu_type": "NVIDIA-A100-SXM4-80GB",
        "gpu_total": 8,
        "gpu_allocatable": 8,
        "gpu_used": 8,
        "cpu_total_millicores": 128000,
        "cpu_allocatable_millicores": 126000,
        "cpu_used_millicores": 98000,
        "memory_total_bytes": 1099511627776,
        "memory_allocatable_bytes": 1082331758592,
        "memory_used_bytes": 824633720832,
        "labels": {
            "nvidia.com/gpu.product": "NVIDIA-A100-SXM4-80GB",
            "kubernetes.io/arch": "amd64",
            "topology.kubernetes.io/zone": "us-east-1b",
        },
        "pods": [
            _make_pod(
                "diffusion-train-0",
                "ml-training",
                "StatefulSet",
                "diffusion-train",
                gpu_req=4,
                gpu_lim=4,
                cpu_req=32000,
                cpu_lim=64000,
                mem_req=274877906944,
                mem_lim=549755813888,
                labels={
                    "app": "diffusion-training",
                    "gpu-type": "a100",
                    "team": "cv-research",
                },
            ),
            _make_pod(
                "diffusion-train-1",
                "ml-training",
                "StatefulSet",
                "diffusion-train",
                gpu_req=4,
                gpu_lim=4,
                cpu_req=32000,
                cpu_lim=64000,
                mem_req=274877906944,
                mem_lim=549755813888,
                labels={
                    "app": "diffusion-training",
                    "gpu-type": "a100",
                    "team": "cv-research",
                },
            ),
            _make_pod(
                "monitoring-agent-gpu-02",
                "monitoring",
                "DaemonSet",
                "monitoring-agent",
                cpu_req=200,
                cpu_lim=500,
                mem_req=268435456,
                mem_lim=536870912,
                labels={"app": "monitoring-agent"},
            ),
        ],
        "conditions_ready": True,
        "os": "Ubuntu 22.04.4 LTS",
        "arch": "amd64",
        "kubelet_version": "v1.29.3",
    },
    {
        "name": "gpu-node-h100-01",
        "gpu_type": "NVIDIA-H100-SXM5-80GB",
        "gpu_total": 8,
        "gpu_allocatable": 8,
        "gpu_used": 4,
        "cpu_total_millicores": 192000,
        "cpu_allocatable_millicores": 190000,
        "cpu_used_millicores": 72000,
        "memory_total_bytes": 2199023255552,
        "memory_allocatable_bytes": 2164663517184,
        "memory_used_bytes": 824633720832,
        "labels": {
            "nvidia.com/gpu.product": "NVIDIA-H100-SXM5-80GB",
            "kubernetes.io/arch": "amd64",
            "topology.kubernetes.io/zone": "us-east-1a",
        },
        "pods": [
            _make_pod(
                "llm-finetune-h100-0",
                "ml-training",
                "Job",
                "llm-finetune-h100",
                gpu_req=4,
                gpu_lim=4,
                cpu_req=32000,
                cpu_lim=64000,
                mem_req=274877906944,
                mem_lim=549755813888,
                labels={
                    "app": "llm-finetune",
                    "gpu-type": "h100",
                    "team": "ml-platform",
                },
            ),
            _make_pod(
                "monitoring-agent-gpu-03",
                "monitoring",
                "DaemonSet",
                "monitoring-agent",
                cpu_req=200,
                cpu_lim=500,
                mem_req=268435456,
                mem_lim=536870912,
                labels={"app": "monitoring-agent"},
            ),
        ],
        "conditions_ready": True,
        "os": "Ubuntu 22.04.4 LTS",
        "arch": "amd64",
        "kubelet_version": "v1.29.3",
    },
    {
        "name": "gpu-node-h100-02",
        "gpu_type": "NVIDIA-H100-SXM5-80GB",
        "gpu_total": 8,
        "gpu_allocatable": 8,
        "gpu_used": 7,
        "cpu_total_millicores": 192000,
        "cpu_allocatable_millicores": 190000,
        "cpu_used_millicores": 142000,
        "memory_total_bytes": 2199023255552,
        "memory_allocatable_bytes": 2164663517184,
        "memory_used_bytes": 1649267441664,
        "labels": {
            "nvidia.com/gpu.product": "NVIDIA-H100-SXM5-80GB",
            "kubernetes.io/arch": "amd64",
            "topology.kubernetes.io/zone": "us-east-1b",
        },
        "pods": [
            _make_pod(
                "gpt-serve-h100-0",
                "ml-serving",
                "StatefulSet",
                "gpt-serve-h100",
                gpu_req=4,
                gpu_lim=4,
                cpu_req=64000,
                cpu_lim=96000,
                mem_req=549755813888,
                mem_lim=1099511627776,
                labels={
                    "app": "gpt-serving",
                    "gpu-type": "h100",
                    "team": "ml-platform",
                },
            ),
            _make_pod(
                "rlhf-train-h100-0",
                "ml-training",
                "Job",
                "rlhf-train-h100",
                gpu_req=2,
                gpu_lim=2,
                cpu_req=16000,
                cpu_lim=32000,
                mem_req=274877906944,
                mem_lim=549755813888,
                labels={
                    "app": "rlhf-training",
                    "gpu-type": "h100",
                    "team": "alignment",
                },
            ),
            _make_pod(
                "vllm-inference-0",
                "ml-serving",
                "ReplicaSet",
                "vllm-inference",
                gpu_req=1,
                gpu_lim=1,
                cpu_req=8000,
                cpu_lim=16000,
                mem_req=137438953472,
                mem_lim=274877906944,
                labels={
                    "app": "vllm-inference",
                    "gpu-type": "h100",
                    "team": "ml-platform",
                },
            ),
            _make_pod(
                "monitoring-agent-gpu-04",
                "monitoring",
                "DaemonSet",
                "monitoring-agent",
                cpu_req=200,
                cpu_lim=500,
                mem_req=268435456,
                mem_lim=536870912,
                labels={"app": "monitoring-agent"},
            ),
        ],
        "conditions_ready": True,
        "os": "Ubuntu 22.04.4 LTS",
        "arch": "amd64",
        "kubelet_version": "v1.29.3",
    },
]


def _make_summary(nodes):
    cpu_total = sum(n["cpu_total_millicores"] for n in nodes)
    cpu_alloc = sum(n["cpu_allocatable_millicores"] for n in nodes)
    cpu_used = sum(n["cpu_used_millicores"] for n in nodes)
    cpu_avail = cpu_alloc - cpu_used
    cpu_pct = round(cpu_used / cpu_alloc * 100, 1) if cpu_alloc > 0 else 0

    mem_total = sum(n["memory_total_bytes"] for n in nodes)
    mem_alloc = sum(n["memory_allocatable_bytes"] for n in nodes)
    mem_used = sum(n["memory_used_bytes"] for n in nodes)
    mem_avail = mem_alloc - mem_used
    mem_pct = round(mem_used / mem_alloc * 100, 1) if mem_alloc > 0 else 0

    gpu_total = sum(n["gpu_total"] for n in nodes)
    gpu_alloc = sum(n["gpu_allocatable"] for n in nodes)
    gpu_used = sum(n["gpu_used"] for n in nodes)
    gpu_avail = gpu_alloc - gpu_used
    gpu_pct = round(gpu_used / gpu_alloc * 100, 1) if gpu_alloc > 0 else 0

    pods_total = sum(len(n["pods"]) for n in nodes)
    ready = sum(1 for n in nodes if n["conditions_ready"])

    def fmt_bytes(b):
        for u in ["B", "KiB", "MiB", "GiB", "TiB"]:
            if b < 1024:
                return f"{b:.1f}{u}"
            b /= 1024
        return f"{b:.1f}PiB"

    def fmt_cores(m):
        return f"{m / 1000:.1f} cores"

    # GPU by type
    gpu_type_map = {}
    for n in nodes:
        if n["gpu_total"] > 0:
            t = n.get("gpu_type", "N/A")
            if t not in gpu_type_map:
                gpu_type_map[t] = {
                    "total": 0,
                    "allocatable": 0,
                    "used": 0,
                    "node_count": 0,
                }
            gpu_type_map[t]["total"] += n["gpu_total"]
            gpu_type_map[t]["allocatable"] += n["gpu_allocatable"]
            gpu_type_map[t]["used"] += n["gpu_used"]
            gpu_type_map[t]["node_count"] += 1

    gpu_by_type = []
    for gtype, s in sorted(gpu_type_map.items()):
        avail = s["allocatable"] - s["used"]
        util = (
            round(s["used"] / s["allocatable"] * 100, 1) if s["allocatable"] > 0 else 0
        )
        gpu_by_type.append(
            {
                "gpu_type": gtype,
                "total": s["total"],
                "allocatable": s["allocatable"],
                "used": s["used"],
                "available": avail,
                "utilization_percent": util,
                "node_count": s["node_count"],
            }
        )

    return {
        "cpu": {
            "total": cpu_total,
            "allocatable": cpu_alloc,
            "used": cpu_used,
            "available": cpu_avail,
            "utilization_percent": cpu_pct,
            "unit": "millicores",
            "total_display": fmt_cores(cpu_total),
            "used_display": fmt_cores(cpu_used),
            "available_display": fmt_cores(cpu_avail),
        },
        "memory": {
            "total": mem_total,
            "allocatable": mem_alloc,
            "used": mem_used,
            "available": mem_avail,
            "utilization_percent": mem_pct,
            "unit": "bytes",
            "total_display": fmt_bytes(mem_total),
            "used_display": fmt_bytes(mem_used),
            "available_display": fmt_bytes(mem_avail),
        },
        "gpu": {
            "total": gpu_total,
            "allocatable": gpu_alloc,
            "used": gpu_used,
            "available": gpu_avail,
            "utilization_percent": gpu_pct,
            "unit": "GPUs",
            "total_display": str(gpu_total),
            "used_display": str(gpu_used),
            "available_display": str(gpu_avail),
        },
        "pods": {
            "total": pods_total,
            "allocatable": pods_total,
            "used": pods_total,
            "available": 0,
            "utilization_percent": 0,
            "unit": "pods",
            "total_display": str(pods_total),
            "used_display": str(pods_total),
            "available_display": "0",
        },
        "ephemeral_storage": {
            "total": 0,
            "allocatable": 0,
            "used": 0,
            "available": 0,
            "utilization_percent": 0,
            "unit": "",
            "total_display": "",
            "used_display": "",
            "available_display": "",
        },
        "node_count": len(nodes),
        "ready_node_count": ready,
        "gpu_by_type": gpu_by_type,
    }


# ── prod-eu-west-1: 2 GPU nodes (L40S), 1 CPU node ──

PROD_EU_NODES = [
    {
        "name": "gpu-node-l40s-01",
        "gpu_type": "NVIDIA-L40S",
        "gpu_total": 4,
        "gpu_allocatable": 4,
        "gpu_used": 3,
        "cpu_total_millicores": 64000,
        "cpu_allocatable_millicores": 62000,
        "cpu_used_millicores": 34000,
        "memory_total_bytes": 549755813888,
        "memory_allocatable_bytes": 536870912000,
        "memory_used_bytes": 322122547200,
        "labels": {
            "nvidia.com/gpu.product": "NVIDIA-L40S",
            "kubernetes.io/arch": "amd64",
            "topology.kubernetes.io/zone": "eu-west-1a",
        },
        "pods": [
            _make_pod(
                "tts-serve-l40s-0",
                "ml-serving",
                "ReplicaSet",
                "tts-serve-l40s",
                gpu_req=1,
                gpu_lim=1,
                cpu_req=4000,
                cpu_lim=8000,
                mem_req=34359738368,
                mem_lim=68719476736,
                labels={"app": "tts-serving", "gpu-type": "l40s", "team": "speech"},
            ),
            _make_pod(
                "whisper-serve-l40s-0",
                "ml-serving",
                "ReplicaSet",
                "whisper-serve-l40s",
                gpu_req=1,
                gpu_lim=1,
                cpu_req=4000,
                cpu_lim=8000,
                mem_req=34359738368,
                mem_lim=68719476736,
                labels={"app": "whisper-serving", "gpu-type": "l40s", "team": "speech"},
            ),
            _make_pod(
                "sd-inpaint-l40s-0",
                "ml-serving",
                "ReplicaSet",
                "sd-inpaint-l40s",
                gpu_req=1,
                gpu_lim=1,
                cpu_req=4000,
                cpu_lim=8000,
                mem_req=34359738368,
                mem_lim=68719476736,
                labels={
                    "app": "sd-inpainting",
                    "gpu-type": "l40s",
                    "team": "cv-research",
                },
            ),
        ],
        "conditions_ready": True,
        "os": "Ubuntu 22.04.4 LTS",
        "arch": "amd64",
        "kubelet_version": "v1.29.3",
    },
    {
        "name": "gpu-node-l40s-02",
        "gpu_type": "NVIDIA-L40S",
        "gpu_total": 4,
        "gpu_allocatable": 4,
        "gpu_used": 2,
        "cpu_total_millicores": 64000,
        "cpu_allocatable_millicores": 62000,
        "cpu_used_millicores": 18000,
        "memory_total_bytes": 549755813888,
        "memory_allocatable_bytes": 536870912000,
        "memory_used_bytes": 171798691840,
        "labels": {
            "nvidia.com/gpu.product": "NVIDIA-L40S",
            "kubernetes.io/arch": "amd64",
            "topology.kubernetes.io/zone": "eu-west-1b",
        },
        "pods": [
            _make_pod(
                "ocr-serve-l40s-0",
                "ml-serving",
                "ReplicaSet",
                "ocr-serve-l40s",
                gpu_req=1,
                gpu_lim=1,
                cpu_req=4000,
                cpu_lim=8000,
                mem_req=17179869184,
                mem_lim=34359738368,
                labels={
                    "app": "ocr-serving",
                    "gpu-type": "l40s",
                    "team": "document-ai",
                },
            ),
            _make_pod(
                "clip-index-l40s-0",
                "ml-serving",
                "Job",
                "clip-index-l40s",
                gpu_req=1,
                gpu_lim=1,
                cpu_req=4000,
                cpu_lim=8000,
                mem_req=34359738368,
                mem_lim=68719476736,
                labels={"app": "clip-indexing", "gpu-type": "l40s", "team": "search"},
            ),
        ],
        "conditions_ready": True,
        "os": "Ubuntu 22.04.4 LTS",
        "arch": "amd64",
        "kubelet_version": "v1.29.3",
    },
    {
        "name": "cpu-node-01",
        "gpu_type": "N/A",
        "gpu_total": 0,
        "gpu_allocatable": 0,
        "gpu_used": 0,
        "cpu_total_millicores": 32000,
        "cpu_allocatable_millicores": 31000,
        "cpu_used_millicores": 12000,
        "memory_total_bytes": 137438953472,
        "memory_allocatable_bytes": 133143986176,
        "memory_used_bytes": 53687091200,
        "labels": {
            "kubernetes.io/arch": "amd64",
            "topology.kubernetes.io/zone": "eu-west-1a",
        },
        "pods": [
            _make_pod(
                "api-gateway-7f2c9-abc12",
                "platform",
                "ReplicaSet",
                "api-gateway-7f2c9",
                labels={"app": "api-gateway", "team": "platform"},
            ),
            _make_pod(
                "redis-cluster-0",
                "platform",
                "StatefulSet",
                "redis-cluster",
                cpu_req=2000,
                cpu_lim=4000,
                mem_req=8589934592,
                mem_lim=17179869184,
                labels={"app": "redis", "team": "platform"},
            ),
            _make_pod(
                "prometheus-0",
                "monitoring",
                "StatefulSet",
                "prometheus",
                cpu_req=1000,
                cpu_lim=2000,
                mem_req=4294967296,
                mem_lim=8589934592,
                labels={"app": "prometheus", "team": "sre"},
            ),
        ],
        "conditions_ready": True,
        "os": "Ubuntu 22.04.4 LTS",
        "arch": "amd64",
        "kubelet_version": "v1.29.3",
    },
]


# ── staging-apne-1: 1 GPU node (T4), 1 node NotReady ──

STAGING_NODES = [
    {
        "name": "gpu-node-t4-01",
        "gpu_type": "NVIDIA-Tesla-T4",
        "gpu_total": 2,
        "gpu_allocatable": 2,
        "gpu_used": 1,
        "cpu_total_millicores": 16000,
        "cpu_allocatable_millicores": 15000,
        "cpu_used_millicores": 6000,
        "memory_total_bytes": 68719476736,
        "memory_allocatable_bytes": 66571993088,
        "memory_used_bytes": 21474836480,
        "labels": {
            "nvidia.com/gpu.product": "NVIDIA-Tesla-T4",
            "kubernetes.io/arch": "amd64",
            "topology.kubernetes.io/zone": "ap-northeast-1a",
        },
        "pods": [
            _make_pod(
                "test-inference-t4-0",
                "staging",
                "ReplicaSet",
                "test-inference-t4",
                gpu_req=1,
                gpu_lim=1,
                cpu_req=2000,
                cpu_lim=4000,
                mem_req=8589934592,
                mem_lim=17179869184,
                labels={"app": "test-inference", "env": "staging"},
            ),
            _make_pod(
                "load-test-runner-xyz",
                "staging",
                "Job",
                "load-test-runner",
                cpu_req=1000,
                cpu_lim=2000,
                mem_req=2147483648,
                mem_lim=4294967296,
                phase="Running",
                labels={"app": "load-test", "env": "staging"},
            ),
        ],
        "conditions_ready": True,
        "os": "Ubuntu 22.04.4 LTS",
        "arch": "amd64",
        "kubelet_version": "v1.29.3",
    },
    {
        "name": "cpu-node-staging-01",
        "gpu_type": "N/A",
        "gpu_total": 0,
        "gpu_allocatable": 0,
        "gpu_used": 0,
        "cpu_total_millicores": 8000,
        "cpu_allocatable_millicores": 7500,
        "cpu_used_millicores": 0,
        "memory_total_bytes": 34359738368,
        "memory_allocatable_bytes": 33285996544,
        "memory_used_bytes": 0,
        "labels": {
            "kubernetes.io/arch": "amd64",
            "topology.kubernetes.io/zone": "ap-northeast-1a",
        },
        "pods": [],
        "conditions_ready": False,
        "os": "Ubuntu 22.04.4 LTS",
        "arch": "amd64",
        "kubelet_version": "v1.29.3",
    },
]

CLUSTER_DATA = {
    "prod-us-east-1": PROD_US_NODES,
    "prod-eu-west-1": PROD_EU_NODES,
    "staging-apne-1": STAGING_NODES,
}


@app.get("/api/clusters")
async def get_clusters():
    return CLUSTERS


@app.get("/api/clusters/{cluster_name}/nodes")
async def get_cluster_nodes(cluster_name: str):
    return CLUSTER_DATA.get(cluster_name, [])


@app.get("/api/clusters/{cluster_name}/summary")
async def get_cluster_summary(cluster_name: str):
    nodes = CLUSTER_DATA.get(cluster_name, [])
    return _make_summary(nodes)


# Default endpoints (backward compat - use active cluster)
@app.get("/api/nodes")
async def get_nodes():
    return PROD_US_NODES


@app.get("/api/cluster-summary")
async def get_summary():
    return _make_summary(PROD_US_NODES)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
