# =============================================================================
# Stage 1: Build React/Vite Frontend
# =============================================================================
FROM node:20-slim AS frontend-builder

WORKDIR /build/frontend

# Install dependencies reproducibly
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source files and configuration
COPY frontend/index.html frontend/vite.config.ts frontend/tsconfig*.json ./
COPY frontend/public ./public
COPY frontend/src ./src

# Build production assets to /build/frontend/dist
RUN npm run build

# =============================================================================
# Stage 2: Python 3.12 Runtime
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Set production environment flags
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    APP_ENV=production \
    APP_HOST=0.0.0.0

# Install system utilities for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python runtime dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source directories
COPY backend /app/backend
COPY cypher /app/cypher
COPY scripts /app/scripts

# Create data directory for durable simulation state
RUN mkdir -p /app/data

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# Expose default application port
EXPOSE 8000

# Healthcheck configuration
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8000}/api/health || exit 1

# Production startup command expanding $PORT dynamically
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
