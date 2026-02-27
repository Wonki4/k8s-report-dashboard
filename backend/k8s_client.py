from typing import List, Dict, Optional, Tuple
from kubernetes import client, config
from models import (
    ContainerStatus,
    PodDetail,
    NodeDetail,
    ClusterSummary,
    ResourceStat,
    GpuTypeStat,
    parse_k8s_quantity,
    parse_cpu_quantity,
    bytes_to_human_readable,
    millicores_to_cores,
    ClusterInfo,
)

GPU_RESOURCE = "nvidia.com/gpu"

GPU_TYPE_LABELS = [
    "nvidia.com/gpu.product",
    "nvidia.com/gpu.machine",
    "accelerator",
    "gpu-type",
    "node.kubernetes.io/instance-type",
]


class K8sClient:
    def __init__(self, context: Optional[str] = None):
        self._in_cluster = False
        try:
            config.load_incluster_config()
            self._in_cluster = True
            self.core = client.CoreV1Api()
        except config.ConfigException:
            if context:
                api_client = config.new_client_from_config(context=context)
                self.core = client.CoreV1Api(api_client=api_client)
            else:
                config.load_kube_config()
                self.core = client.CoreV1Api()

    def _extract_gpu_type(self, labels: Dict[str, str]) -> str:
        for key in GPU_TYPE_LABELS:
            if key in labels:
                return labels[key]
        return "N/A"

    def _build_container_status(self, cs) -> ContainerStatus:
        state = cs.state or {}
        if state.running:
            state_name = "running"
            reason = None
            started = (
                state.running.started_at.isoformat()
                if state.running.started_at
                else None
            )
        elif state.waiting:
            state_name = "waiting"
            reason = state.waiting.reason
            started = None
        elif state.terminated:
            state_name = "terminated"
            reason = state.terminated.reason
            started = None
        else:
            state_name = "unknown"
            reason = None
            started = None

        return ContainerStatus(
            name=cs.name,
            state=state_name,
            ready=cs.ready or False,
            restart_count=cs.restart_count or 0,
            image=cs.image or "",
            reason=reason,
            started_at=started,
        )

    def _build_pod_detail(self, pod) -> PodDetail:
        gpu_request = 0
        gpu_limit = 0
        cpu_request_millicores = 0
        cpu_limit_millicores = 0
        memory_request_bytes = 0
        memory_limit_bytes = 0

        for c in pod.spec.containers:
            res = c.resources or client.V1ResourceRequirements()
            req = res.requests or {}
            lim = res.limits or {}

            # GPU
            gpu_request += int(req.get(GPU_RESOURCE, 0))
            gpu_limit += int(lim.get(GPU_RESOURCE, 0))

            # CPU (in millicores)
            cpu_req_str = req.get("cpu", "0")
            cpu_lim_str = lim.get("cpu", "0")
            cpu_request_millicores += parse_cpu_quantity(cpu_req_str)
            cpu_limit_millicores += parse_cpu_quantity(cpu_lim_str)

            # Memory (in bytes)
            mem_req_str = req.get("memory", "0")
            mem_lim_str = lim.get("memory", "0")
            memory_request_bytes += parse_k8s_quantity(mem_req_str)
            memory_limit_bytes += parse_k8s_quantity(mem_lim_str)

        owners = pod.metadata.owner_references or []
        owner_kind = owners[0].kind if owners else "None"
        owner_name = owners[0].name if owners else pod.metadata.name

        container_statuses = []
        for cs in pod.status.container_statuses or []:
            container_statuses.append(self._build_container_status(cs))

        pod_labels = pod.metadata.labels or {}

        return PodDetail(
            name=pod.metadata.name,
            namespace=pod.metadata.namespace,
            owner_kind=owner_kind,
            owner_name=owner_name,
            phase=pod.status.phase or "Unknown",
            gpu_request=gpu_request,
            gpu_limit=gpu_limit,
            cpu_request_millicores=cpu_request_millicores,
            cpu_limit_millicores=cpu_limit_millicores,
            memory_request_bytes=memory_request_bytes,
            memory_limit_bytes=memory_limit_bytes,
            containers=container_statuses,
            created_at=pod.metadata.creation_timestamp.isoformat()
            if pod.metadata.creation_timestamp
            else None,
            ip=pod.status.pod_ip,
            qos_class=pod.status.qos_class,
            labels=pod_labels,
        )

    def get_nodes_with_pods(self) -> List[NodeDetail]:
        all_nodes = self.core.list_node().items
        all_pods = self.core.list_pod_for_all_namespaces().items

        pods_by_node: Dict[str, List[PodDetail]] = {}
        for pod in all_pods:
            node_name = pod.spec.node_name or "unscheduled"
            detail = self._build_pod_detail(pod)
            pods_by_node.setdefault(node_name, []).append(detail)

        result = []
        for node in all_nodes:
            labels = node.metadata.labels or {}
            cap = node.status.capacity or {}
            alloc = node.status.allocatable or {}

            # GPU
            gpu_total = int(cap.get(GPU_RESOURCE, 0))
            gpu_allocatable = int(alloc.get(GPU_RESOURCE, 0))

            # CPU (in millicores)
            cpu_total = parse_cpu_quantity(cap.get("cpu", "0"))
            cpu_allocatable = parse_cpu_quantity(alloc.get("cpu", "0"))

            # Memory (in bytes)
            memory_total = parse_k8s_quantity(cap.get("memory", "0"))
            memory_allocatable = parse_k8s_quantity(alloc.get("memory", "0"))

            node_pods = pods_by_node.get(node.metadata.name, [])

            # Calculate used resources based on pod requests
            gpu_used = sum(p.gpu_request for p in node_pods)
            cpu_used = sum(p.cpu_request_millicores for p in node_pods)
            memory_used = sum(p.memory_request_bytes for p in node_pods)

            conditions = node.status.conditions or []
            is_ready = any(c.type == "Ready" and c.status == "True" for c in conditions)

            node_info = node.status.node_info
            result.append(
                NodeDetail(
                    name=node.metadata.name,
                    gpu_type=self._extract_gpu_type(labels),
                    gpu_total=gpu_total,
                    gpu_allocatable=gpu_allocatable,
                    gpu_used=gpu_used,
                    cpu_total_millicores=cpu_total,
                    cpu_allocatable_millicores=cpu_allocatable,
                    cpu_used_millicores=cpu_used,
                    memory_total_bytes=memory_total,
                    memory_allocatable_bytes=memory_allocatable,
                    memory_used_bytes=memory_used,
                    labels=labels,
                    pods=node_pods,
                    conditions_ready=is_ready,
                    os=node_info.os_image if node_info else "",
                    arch=labels.get("kubernetes.io/arch", ""),
                    kubelet_version=node_info.kubelet_version if node_info else "",
                )
            )

        return result

    def get_cluster_summary(self) -> ClusterSummary:
        """Get aggregated cluster-wide resource statistics."""
        nodes = self.get_nodes_with_pods()

        # Aggregate CPU
        cpu_total = sum(n.cpu_total_millicores for n in nodes)
        cpu_allocatable = sum(n.cpu_allocatable_millicores for n in nodes)
        cpu_used = sum(n.cpu_used_millicores for n in nodes)
        cpu_available = cpu_allocatable - cpu_used
        cpu_util = (cpu_used / cpu_allocatable * 100) if cpu_allocatable > 0 else 0.0

        # Aggregate Memory
        memory_total = sum(n.memory_total_bytes for n in nodes)
        memory_allocatable = sum(n.memory_allocatable_bytes for n in nodes)
        memory_used = sum(n.memory_used_bytes for n in nodes)
        memory_available = memory_allocatable - memory_used
        memory_util = (
            (memory_used / memory_allocatable * 100) if memory_allocatable > 0 else 0.0
        )

        # Aggregate GPU
        gpu_total = sum(n.gpu_total for n in nodes)
        gpu_allocatable = sum(n.gpu_allocatable for n in nodes)
        gpu_used = sum(n.gpu_used for n in nodes)
        gpu_available = gpu_allocatable - gpu_used
        gpu_util = (gpu_used / gpu_allocatable * 100) if gpu_allocatable > 0 else 0.0

        # Aggregate Pods
        pods_total = sum(len(n.pods) for n in nodes)

        # Count ready nodes
        ready_nodes = sum(1 for n in nodes if n.conditions_ready)

        # GPU by type
        gpu_type_map: Dict[str, Dict] = {}
        for n in nodes:
            if n.gpu_total > 0:
                t = n.gpu_type
                if t not in gpu_type_map:
                    gpu_type_map[t] = {"total": 0, "allocatable": 0, "used": 0, "node_count": 0}
                gpu_type_map[t]["total"] += n.gpu_total
                gpu_type_map[t]["allocatable"] += n.gpu_allocatable
                gpu_type_map[t]["used"] += n.gpu_used
                gpu_type_map[t]["node_count"] += 1

        gpu_by_type = []
        for gtype, stats in sorted(gpu_type_map.items()):
            avail = stats["allocatable"] - stats["used"]
            util = (stats["used"] / stats["allocatable"] * 100) if stats["allocatable"] > 0 else 0.0
            gpu_by_type.append(GpuTypeStat(
                gpu_type=gtype,
                total=stats["total"],
                allocatable=stats["allocatable"],
                used=stats["used"],
                available=avail,
                utilization_percent=round(util, 1),
                node_count=stats["node_count"],
            ))

        return ClusterSummary(
            cpu=ResourceStat(
                total=cpu_total,
                allocatable=cpu_allocatable,
                used=cpu_used,
                available=cpu_available,
                utilization_percent=round(cpu_util, 1),
                unit="millicores",
                total_display=f"{millicores_to_cores(cpu_total):.1f} cores",
                used_display=f"{millicores_to_cores(cpu_used):.1f} cores",
                available_display=f"{millicores_to_cores(cpu_available):.1f} cores",
            ),
            memory=ResourceStat(
                total=memory_total,
                allocatable=memory_allocatable,
                used=memory_used,
                available=memory_available,
                utilization_percent=round(memory_util, 1),
                unit="bytes",
                total_display=bytes_to_human_readable(memory_total),
                used_display=bytes_to_human_readable(memory_used),
                available_display=bytes_to_human_readable(memory_available),
            ),
            gpu=ResourceStat(
                total=gpu_total,
                allocatable=gpu_allocatable,
                used=gpu_used,
                available=gpu_available,
                utilization_percent=round(gpu_util, 1),
                unit="GPUs",
                total_display=str(gpu_total),
                used_display=str(gpu_used),
                available_display=str(gpu_available),
            ),
            pods=ResourceStat(
                total=pods_total,
                allocatable=pods_total,  # Pods don't have allocatable in same sense
                used=pods_total,
                available=0,
                utilization_percent=0.0,
                unit="pods",
                total_display=str(pods_total),
                used_display=str(pods_total),
                available_display="0",
            ),
            node_count=len(nodes),
            ready_node_count=ready_nodes,
            gpu_by_type=gpu_by_type,
        )

_clients: Dict[str, K8sClient] = {}


def get_k8s_client(context: Optional[str] = None) -> K8sClient:
    """Get or create a cached K8sClient for the given context."""
    cache_key = context or "__default__"
    if cache_key not in _clients:
        _clients[cache_key] = K8sClient(context=context)
    return _clients[cache_key]


def list_clusters() -> Tuple[List[ClusterInfo], Optional[str]]:
    """List available kubeconfig contexts.
    Returns (clusters, active_context_name).
    For in-cluster mode, returns a single 'in-cluster' entry.
    """
    try:
        contexts, active = config.list_kube_config_contexts()
        active_name = active["name"] if active else None
        clusters = [
            ClusterInfo(name=ctx["name"], is_active=(ctx["name"] == active_name))
            for ctx in contexts
        ]
        return clusters, active_name
    except config.ConfigException:
        # In-cluster mode: no kubeconfig available
        return [ClusterInfo(name="in-cluster", is_active=True)], "in-cluster"
