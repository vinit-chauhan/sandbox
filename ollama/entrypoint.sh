#!/bin/sh
ollama serve &
PID=$!

sleep 8

ollama pull "${MODEL_NAME:-qwen2.5:3b}"

wait $PID
