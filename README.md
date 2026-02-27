# K8s GPU Dashboard

Multi-cluster Kubernetes GPU resource monitoring dashboard. Provides real-time visibility into GPU, CPU, and memory utilization across multiple clusters with workload-level filtering.

## Features

- **Multi-Cluster Support** -- Monitor multiple K8s clusters from a single view, or drill into individual clusters
- **GPU-Focused** -- GPU utilization by type (A100, H100, L40S, T4, etc.) with per-node breakdown
- **Resource Overview** -- Aggregated CPU / Memory / GPU / Pod counts with progress bars
- **Workload View** -- Filter by owner (Deployment, ReplicaSet, etc.) or by label, with searchable multi-select
- **Node & Owner Grouping** -- Toggle between node-centric and owner-centric pod views
- **Auto-Refresh** -- 15-second polling interval
- **Dark Theme** -- Monospace-based UI designed for ops/SRE workflows

## Architecture

```
frontend/          React 18 + Vite + Axios (JSX)
backend/           Python FastAPI + kubernetes client
  main.py          API server (serves static files in production)
  k8s_client.py    Multi-context K8s client with caching
  models.py        Pydantic models + resource parsers
  mock_server.py   Mock server with 3 clusters for UI testing
helm/              Helm chart for K8s deployment
k8s/               Raw K8s manifests (reference)
```

### API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/clusters` | List available clusters |
| `GET /api/cluster-summary` | Default cluster summary |
| `GET /api/nodes` | Default cluster nodes + pods |
| `GET /api/clusters/{name}/summary` | Specific cluster summary |
| `GET /api/clusters/{name}/nodes` | Specific cluster nodes + pods |

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.10+
- Node.js 18+
- Access to a kubeconfig with one or more cluster contexts

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Backend runs at `http://localhost:8000`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server runs at `http://localhost:3000` with API proxy to backend.

### 3. Mock Server (no K8s cluster needed)

```bash
cd backend
python mock_server.py
```

Runs a mock API on port 8000 with 3 fake clusters containing GPU nodes (A100, H100, L40S, T4).

---

## Docker Build

A single multi-stage Dockerfile builds both frontend and backend into one container:

```bash
# Build
docker build -t k8s-gpu-dashboard:latest .

# Run (with local kubeconfig)
docker run -p 8080:8000 \
  -v ~/.kube/config:/root/.kube/config:ro \
  k8s-gpu-dashboard:latest
```

Open `http://localhost:8080`.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DASHBOARD_HOST` | `0.0.0.0` | Bind address |
| `DASHBOARD_PORT` | `8000` | Listen port |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
| `KUBECONFIG` | `~/.kube/config` | Path to kubeconfig (ignored when running in-cluster) |

See `.env.example` for a full template.

---

## Kubernetes Deployment (Helm)

### Prerequisites

- Helm 3.x
- `kubectl` configured for the target cluster
- Container image pushed to an accessible registry

### 1. Build and Push Image

```bash
docker build -t your-registry.io/k8s-gpu-dashboard:latest .
docker push your-registry.io/k8s-gpu-dashboard:latest
```

### 2. Install with Helm

```bash
helm install gpu-dashboard ./helm/k8s-gpu-dashboard \
  --namespace monitoring --create-namespace \
  --set image.repository=your-registry.io/k8s-gpu-dashboard \
  --set image.tag=latest
```

### 3. Enable Ingress (optional)

```bash
helm install gpu-dashboard ./helm/k8s-gpu-dashboard \
  --namespace monitoring --create-namespace \
  --set image.repository=your-registry.io/k8s-gpu-dashboard \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=gpu-dashboard.example.com \
  --set ingress.hosts[0].paths[0].path=/ \
  --set ingress.hosts[0].paths[0].pathType=Prefix
```

### 4. Port-Forward (without Ingress)

```bash
kubectl -n monitoring port-forward svc/gpu-dashboard-k8s-gpu-dashboard 8080:80
```

Open `http://localhost:8080`.

### Helm Values Reference

| Key | Default | Description |
|---|---|---|
| `replicaCount` | `1` | Number of replicas |
| `image.repository` | `k8s-gpu-dashboard` | Container image |
| `image.tag` | `latest` | Image tag |
| `service.type` | `ClusterIP` | Service type |
| `service.port` | `80` | Service port |
| `ingress.enabled` | `false` | Enable Ingress |
| `ingress.className` | `nginx` | Ingress class |
| `rbac.create` | `true` | Create ClusterRole + binding for pod/node read access |
| `serviceAccount.create` | `true` | Create ServiceAccount |
| `env.CORS_ORIGINS` | `*` | CORS allowed origins |
| `resources.requests.cpu` | `100m` | CPU request |
| `resources.requests.memory` | `128Mi` | Memory request |
| `resources.limits.cpu` | `500m` | CPU limit |
| `resources.limits.memory` | `256Mi` | Memory limit |
| `kubeconfig.enabled` | `false` | Enable kubeconfig Secret mount for multi-cluster |
| `kubeconfig.existingSecret` | `""` | Use existing Secret name (skip inline data) |
| `kubeconfig.data` | `""` | Base64-encoded kubeconfig content |
| `kubeconfig.mountPath` | `/etc/kubeconfig` | Mount path inside container |

See `helm/k8s-gpu-dashboard/values.yaml` for all options.

---

## RBAC

The dashboard requires **read-only** access to the Kubernetes API:

| Resource | Verbs |
|---|---|
| `pods`, `nodes`, `namespaces` | `get`, `list`, `watch` |
| `pods/log` | `get`, `list` |

The Helm chart creates a `ClusterRole` and `ClusterRoleBinding` automatically when `rbac.create=true`.

---

## Multi-Cluster Setup

The dashboard reads all contexts from the kubeconfig file. Each context appears as a selectable cluster in the UI, plus an "All Clusters" aggregate view.

**Single cluster (in-cluster)**: No kubeconfig needed. The Helm chart creates ServiceAccount + RBAC automatically. The kubernetes client auto-detects in-cluster credentials.

**Multi-cluster**: Mount a kubeconfig with multiple contexts via the Helm chart.

### Option A: Existing Secret (recommended)

```bash
# 1. Create a Secret from your kubeconfig
kubectl create secret generic gpu-dashboard-kubeconfig \
  --from-file=config=$HOME/.kube/config \
  -n monitoring

# 2. Install with the existing Secret
helm install gpu-dashboard ./helm/k8s-gpu-dashboard \
  --namespace monitoring \
  --set image.repository=your-registry.io/k8s-gpu-dashboard \
  --set kubeconfig.enabled=true \
  --set kubeconfig.existingSecret=gpu-dashboard-kubeconfig
```

### Option B: Inline kubeconfig data

```bash
# Pass base64-encoded kubeconfig directly
helm install gpu-dashboard ./helm/k8s-gpu-dashboard \
  --namespace monitoring \
  --set image.repository=your-registry.io/k8s-gpu-dashboard \
  --set kubeconfig.enabled=true \
  --set kubeconfig.data=$(cat ~/.kube/config | base64 | tr -d '\n')
```

### Docker (local multi-cluster)

```bash
docker run -p 8080:8000 \
  -v ~/.kube/config:/root/.kube/config:ro \
  k8s-gpu-dashboard:latest
```

---

## Project Structure

```
.
├── backend/
│   ├── main.py              # FastAPI app + static file serving
│   ├── k8s_client.py        # Multi-context K8s client
│   ├── models.py            # Pydantic models
│   ├── mock_server.py       # Mock data server
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Backend-only container (alternative)
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React application
│   │   ├── index.css        # All styles (dark theme)
│   │   └── main.jsx         # Entry point
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile           # Frontend-only container (alternative)
├── helm/
│   └── k8s-gpu-dashboard/   # Helm chart
├── k8s/                     # Raw K8s manifests (reference)
├── Dockerfile               # Unified multi-stage build (recommended)
├── .dockerignore
├── .env.example
└── README.md
```
