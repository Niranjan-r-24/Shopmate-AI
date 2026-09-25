# Dockerfile for ShopMate AI - Production Deployment on Google Cloud Run
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr and writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0

WORKDIR /app

# Install build dependencies if needed (e.g. gcc, build-essential for C-extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose port (Cloud Run defaults to 8080)
EXPOSE 8080

# Start server using the exact requested Cloud Run startup command
# exec ensures SIGTERM signals from Cloud Run are delivered directly to uvicorn
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
