FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download ML models during build (reduces first-run delay)
# These downloads are ~500MB total but save 2-3 min on first video upload
RUN python -c "import whisper; whisper.load_model('base')" || echo "Whisper model download deferred"
RUN python -c "from deepface import DeepFace; DeepFace.build_model('Emotion')" || echo "DeepFace model download deferred"

# Copy application
COPY . .

# Create storage directories
RUN mkdir -p storage/videos storage/audio storage/archives storage/thumbnails

EXPOSE 8000

# Development command (override in compose for production)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
