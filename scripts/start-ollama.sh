#!/usr/bin/env bash
#
# Start Ollama with optimal settings for Apple Silicon / local GPU inference.
# Usage: ./scripts/start-ollama.sh [model]
#
set -euo pipefail

MODEL="${1:-${MODEL_NAME:-qwen3.5:4b}}"

# ── Performance tuning ────────────────────────────────────────────────
# Listen on all interfaces so Docker containers can reach it
export OLLAMA_HOST="${OLLAMA_HOST:-0.0.0.0}"

# Keep model loaded in memory indefinitely (avoids cold-start reload)
export OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:--1}"

# Offload all layers to GPU (Apple Metal / CUDA)
export OLLAMA_NUM_GPU="${OLLAMA_NUM_GPU:-999}"

# Enable flash attention for faster inference and lower memory usage
export OLLAMA_FLASH_ATTENTION="${OLLAMA_FLASH_ATTENTION:-1}"

# Number of parallel request slots (increase if you process many chunks)
export OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-2}"

# Max loaded models (keep at 1 to maximize memory for a single model)
export OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS:-1}"

echo "=== Ollama Optimized Startup ==="
echo "  Model:              $MODEL"
echo "  Host:               $OLLAMA_HOST"
echo "  Keep alive:         $OLLAMA_KEEP_ALIVE"
echo "  GPU layers:         $OLLAMA_NUM_GPU"
echo "  Flash attention:    $OLLAMA_FLASH_ATTENTION"
echo "  Parallel requests:  $OLLAMA_NUM_PARALLEL"
echo "  Max loaded models:  $OLLAMA_MAX_LOADED_MODELS"
echo "================================="

# Start Ollama server in background
ollama serve &
OLLAMA_PID=$!

# Wait for server to be ready
echo "Waiting for Ollama to start..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama is ready."
        break
    fi
    sleep 1
done

# Pull model if not already available
if ! ollama list | grep -q "^${MODEL}"; then
    echo "Pulling model: $MODEL ..."
    ollama pull "$MODEL"
else
    echo "Model $MODEL already available."
fi

# Warm up: load model into memory
echo "Warming up model..."
curl -sf http://localhost:11434/api/chat -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"hi\"}], \"stream\": false}" > /dev/null 2>&1 || true
echo "Model loaded and ready."

wait $OLLAMA_PID
