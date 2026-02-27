from pydantic import BaseModel
from typing import Optional, List, Dict


def parse_k8s_quantity(quantity_str: str) -> int:
    """Parse Kubernetes resource quantity string to integer.

    Handles:
    - CPU: "500m" -> 500 (millicores), "2" -> 2000
    - Memory: "128Gi" -> bytes, "128Mi" -> bytes
    - Storage: "10Gi", "1000Mi" -> bytes
    """
    if not quantity_str:
        return 0

    quantity_str = str(quantity_str).strip()

    # CPU millicores: "500m", "1000m"
    if quantity_str.endswith("m"):
        return int(quantity_str[:-1])

    # Memory/Storage: Ki, Mi, Gi, Ti, Pi, Ei
    suffixes = {
        "Ki": 1024,
        "Mi": 1024**2,
        "Gi": 1024**3,
        "Ti": 1024**4,
        "Pi": 1024**5,
        "Ei": 1024**6,
        "K": 1000,
        "M": 1000**2,
        "G": 1000**3,
        "T": 1000**4,
        "P": 1000**5,
        "E": 1000**6,
    }

    for suffix, multiplier in suffixes.items():
        if quantity_str.endswith(suffix):
            value = float(quantity_str[: -len(suffix)])
            return int(value * multiplier)

    # Plain integer
    return int(quantity_str)

def parse_cpu_quantity(quantity_str: str) -> int:
    """Parse Kubernetes CPU quantity string to millicores.
    
    Handles: "500m" -> 500, "2" -> 2000, "0.5" -> 500
    Plain integers/floats mean cores, NOT millicores.
    """
    if not quantity_str:
        return 0
    quantity_str = str(quantity_str).strip()
    if quantity_str.endswith("m"):
        return int(quantity_str[:-1])
    return int(float(quantity_str) * 1000)


def bytes_to_human_readable(bytes_val: int) -> str:
    """Convert bytes to human readable format."""
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f}PiB"


def millicores_to_cores(millicores: int) -> float:
    """Convert millicores to cores (with 1 decimal)."""
    return millicores / 1000


class ContainerStatus(BaseModel):
    name: str
    state: str  # running, waiting, terminated
    ready: bool = False
    restart_count: int = 0
    image: str = ""
    reason: Optional[str] = None  # e.g., CrashLoopBackOff, OOMKilled
    message: Optional[str] = None
    started_at: Optional[str] = None


class PodDetail(BaseModel):
    name: str
    namespace: str
    owner_kind: str  # ReplicaSet, DaemonSet, Job, StatefulSet, Node, etc.
    owner_name: str
    phase: str  # Running, Pending, Succeeded, Failed, Unknown
    gpu_request: int = 0
    gpu_limit: int = 0
    cpu_request_millicores: int = 0
    cpu_limit_millicores: int = 0
    memory_request_bytes: int = 0
    memory_limit_bytes: int = 0
    containers: List[ContainerStatus] = []
    created_at: Optional[str] = None
    ip: Optional[str] = None
    qos_class: Optional[str] = None  # Guaranteed, Burstable, BestEffort
    labels: Dict[str, str] = {}


class ResourceStat(BaseModel):
    """Aggregated resource statistics for the cluster."""

    total: int = 0
    allocatable: int = 0
    used: int = 0
    available: int = 0
    utilization_percent: float = 0.0
    unit: str = ""
    total_display: str = ""
    used_display: str = ""
    available_display: str = ""


class GpuTypeStat(BaseModel):
    """GPU usage statistics per GPU type."""
    gpu_type: str
    total: int = 0
    allocatable: int = 0
    used: int = 0
    available: int = 0
    utilization_percent: float = 0.0
    node_count: int = 0


class ClusterSummary(BaseModel):
    """Cluster-wide resource summary."""

    cpu: ResourceStat = ResourceStat()
    memory: ResourceStat = ResourceStat()
    gpu: ResourceStat = ResourceStat()
    pods: ResourceStat = ResourceStat()
    ephemeral_storage: ResourceStat = ResourceStat()
    node_count: int = 0
    ready_node_count: int = 0
    gpu_by_type: List[GpuTypeStat] = []


class NodeDetail(BaseModel):
    name: str
    gpu_type: str = "N/A"  # from label: nvidia.com/gpu.product, accelerator, etc.
    gpu_total: int = 0
    gpu_allocatable: int = 0
    gpu_used: int = 0
    cpu_total_millicores: int = 0
    cpu_allocatable_millicores: int = 0
    cpu_used_millicores: int = 0
    memory_total_bytes: int = 0
    memory_allocatable_bytes: int = 0
    memory_used_bytes: int = 0
    labels: Dict[str, str] = {}
    pods: List[PodDetail] = []
    conditions_ready: bool = True
    os: str = ""
    arch: str = ""
    kubelet_version: str = ""


class ClusterInfo(BaseModel):
    """Info about an available Kubernetes cluster context."""
    name: str
    is_active: bool = False
