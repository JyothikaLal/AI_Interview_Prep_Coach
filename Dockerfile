FROM python:3.12-slim

# ffmpeg is required by faster-whisper for audio decoding
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/kb/ ./data/kb/
COPY index.html ./index.html
COPY .env ./.env

# Pre-build the FAISS index (optional, but helps on startup)
RUN mkdir -p ./data/faiss_index && python3 src/rag.py || true

WORKDIR /app/src
EXPOSE 5000
CMD ["python3", "app.py"]
