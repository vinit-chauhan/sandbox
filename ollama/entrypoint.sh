#!/bin/sh
ollama serve &
PID=$!

sleep 8

ollama pull "${MODEL_NAME:-qwen3.5:4b}"

wait $PID
