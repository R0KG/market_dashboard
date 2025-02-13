FROM python:3.9.18-slim-bullseye

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create start script
RUN echo '#!/bin/bash\nuvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}' > start.sh && \
    chmod +x start.sh

# Start the application
CMD uvicorn main:app --host 0.0.0.0 --port $PORT 