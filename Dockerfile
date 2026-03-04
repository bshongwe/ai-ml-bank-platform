# Multi-stage build for Hybrid AI/ML Banking Platform
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Development image
FROM base AS dev
ENV ENVIRONMENT=dev
EXPOSE 8000 8501
CMD ["python", "main.py", "dashboard"]

# API server image
FROM base AS api
ENV ENVIRONMENT=production
EXPOSE 8000
CMD ["python", "main.py", "api", "--host", "0.0.0.0"]

# Worker image (for pipelines/training)
FROM base AS worker
ENV ENVIRONMENT=production
CMD ["python", "main.py"]
