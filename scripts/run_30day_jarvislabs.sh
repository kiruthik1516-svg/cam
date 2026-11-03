#!/usr/bin/env bash
# ==============================================================================
# JarvisLabs 30-Day Master Runner Script (Engine 1 & Engine 2)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo "Loading environment from .env..."
    export $(grep -v '^#' .env | xargs)
fi

# Forward all arguments to the Python orchestrator
python3 scripts/run_30day_jarvislabs.py "$@"

