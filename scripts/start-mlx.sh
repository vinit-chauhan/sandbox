#!/usr/bin/env bash
#
# Start mlx_lm.server for fast Apple Silicon inference.
# Usage: ./scripts/start-mlx.sh [model]
#
# Prerequisites: pipx install mlx-lm  (or pip install mlx-lm in a venv)
#
set -euo pipefail

# Load .env if it exists (from repo root, relative to this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    set -a; source "$ENV_FILE"; set +a
fi

MODEL="${1:-${MLX_MODEL:-mlx-community/Qwen3.5-9B-MLX-4bit}}"
PORT="${MLX_PORT:-8081}"

if ! command -v mlx_lm.server &> /dev/null; then
    echo "mlx-lm not found. Installing via pipx..."
    if command -v pipx &> /dev/null; then
        pipx install mlx-lm
    else
        echo "pipx not found either. Install mlx-lm manually:"
        echo "  pipx install mlx-lm"
        echo "  # or: python3 -m venv .venv && source .venv/bin/activate && pip install mlx-lm"
        exit 1
    fi
fi

echo "=== MLX Server Startup ==="
echo "  Model:  $MODEL"
echo "  Port:   $PORT"
echo "=========================="

exec mlx_lm.server --model "$MODEL" --host "${MLX_HOST:-0.0.0.0}" --port "$PORT"
