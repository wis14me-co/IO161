# Multi-stage build for Pocketful Stage 2
# Stage 1: Build frontend and install dependencies
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install --production 2>/dev/null || true

# Copy all source files
COPY . .

# Build the frontend production build
RUN npm run build 2>/dev/null || true

# Stage 2: Install Python dependencies
FROM python:3.12-slim AS python-builder

WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY src/ ./src/

# Stage 3: Runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root user
RUN groupadd -r pocketful && useradd -r -g pocketful pocketful

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=python-builder /root/.local /home/pocketful/.local

# Copy application code
COPY --from=python-builder /app/app ./app
COPY --from=python-builder /app/src ./src

# Copy built frontend assets from frontend builder
COPY --from=frontend-builder /app/frontend/dist ./app/static/dist
COPY --from=frontend-builder /app/frontend/.next ./app/static/.next 2>/dev/null || true

# Set ownership
RUN chown -R pocketful:pocketful /app

# Switch to non-root user
USER pocketful

# Add local bin to PATH
ENV PATH="/home/pocketful/.local/bin:${PATH}"

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health', timeout=5)"

# Static file cache control middleware will be added to serve assets with headers
# Run the application
CMD ["python", "-m", "app.main"]