FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install dependencies (includes google-cloud-storage for GCS article storage)
RUN pip install --no-cache-dir -e ".[dev]"

# Environment variables for GCS storage (override in Cloud Run)
ENV GCS_BUCKET_NAME="graphfolio-articles"
ENV GCS_ENABLED="true"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Default command (Example API Server)
CMD ["uvicorn", "apps.api.example:app", "--host", "0.0.0.0", "--port", "8000"]

