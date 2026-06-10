FROM python:3.10-slim-bookworm

WORKDIR /app

# ── Critical: make every sub-package importable as `security`, `retriever`, etc.
ENV PYTHONPATH=/app

# Install system dependencies:
#   djvulibre  – djvu parsing
#   poppler    – pdf2image
#   libgl/libglib2 – OpenCV headless
#   libmagic1  – python-magic MIME detection
#   curl       – healthcheck in app container
RUN apt-get update && apt-get install -y --no-install-recommends \
    djvulibre-bin \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 georag \
    && useradd --uid 1000 --gid georag --shell /bin/bash --create-home georag

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create runtime directories and set ownership
RUN mkdir -p /app/cache /app/index /app/documents /app/logs /app/reports /app/secrets \
    && chown -R georag:georag /app

# Switch to non-root user
USER georag

EXPOSE 8501

# Run streamlit from WORKDIR=/app so all relative imports resolve correctly
CMD ["streamlit", "run", "ui/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
