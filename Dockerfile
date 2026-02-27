# ============================================================
# K8s GPU Dashboard - Multi-stage Docker Build
# ============================================================
# Stage 1: Build frontend static assets
# Stage 2: Python runtime serving API + static files
# ============================================================

# --- Stage 1: Build Frontend ---
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python Runtime ---
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/*.py ./

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./static

# Environment defaults
ENV DASHBOARD_HOST=0.0.0.0
ENV DASHBOARD_PORT=8000
ENV CORS_ORIGINS=*
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
