FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies including ffmpeg for video composition
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy engine package and configuration
COPY fme_engine /app/fme_engine

# Expose internal API daemon and WebSocket ports
EXPOSE 8120
EXPOSE 9222

CMD ["uvicorn", "fme_engine.main:app", "--host", "0.0.0.0", "--port", "8120"]
