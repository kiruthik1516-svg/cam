#!/usr/bin/env bash
# ==============================================================================
# Autonomous Cloud GPU Setup & Runner for Stage 2 (JarvisLabs RTX 4090)
# ==============================================================================
set -e

echo "======================================================================"
echo " Starting JarvisLabs RTX 4090 Stage 2 Vectorization Pipeline"
echo "======================================================================"

# 1. System tool dependencies (unrar / p7zip for archive extraction)
echo "[1/5] Checking extraction tools..."
if ! command -v unrar &> /dev/null && ! command -v 7z &> /dev/null; then
    echo "Installing p7zip-full unrar..."
    apt-get update -y > /dev/null 2>&1 || true
    apt-get install -y p7zip-full unrar > /dev/null 2>&1 || true
fi

# 2. Python environment & GPU package setup
echo "[2/5] Installing GPU dependencies (CUDA ONNXRuntime & InsightFace)..."
pip install --upgrade pip > /dev/null 2>&1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install onnxruntime-gpu insightface opencv-python-headless psycopg2-binary sqlalchemy numpy scipy tqdm

# 3. Locate & Extract candidate archive
echo "[3/5] Locating candidate archive..."
ARCHIVE_PATH=""
for f in stage1_candidates.rar stage1_candidates.zip stage1_candidates.tar.gz stage1_candidates.tar; do
    if [ -f "$f" ]; then
        ARCHIVE_PATH="$f"
        break
    fi
done

if [ -n "$ARCHIVE_PATH" ]; then
    echo "Found archive: $ARCHIVE_PATH. Extracting to ./stage1_candidates..."
    mkdir -p stage1_candidates
    if [[ "$ARCHIVE_PATH" == *.rar ]]; then
        if command -v unrar &> /dev/null; then
            unrar x -o+ "$ARCHIVE_PATH" ./
        else
            7z x -y "$ARCHIVE_PATH"
        fi
    elif [[ "$ARCHIVE_PATH" == *.zip ]]; then
        unzip -q -o "$ARCHIVE_PATH" -d ./
    elif [[ "$ARCHIVE_PATH" == *.tar.gz ]]; then
        tar -xzf "$ARCHIVE_PATH" -C ./
    elif [[ "$ARCHIVE_PATH" == *.tar ]]; then
        tar -xf "$ARCHIVE_PATH" -C ./
    fi
    echo "Extraction complete."
else
    echo "No archive file found in current directory. Checking if ./stage1_candidates already exists..."
    if [ ! -d "stage1_candidates" ]; then
        echo "ERROR: Neither candidate archive nor ./stage1_candidates directory was found!"
        exit 1
    fi
fi

# 4. Verify Database URL
echo "[4/5] Checking Database configuration..."
if [ -z "$DATABASE_URL" ]; then
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
    fi
fi

if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set."
    echo "Usage: export DATABASE_URL='postgresql://...' before running this script."
    exit 1
fi

echo "Database target verified."

# 5. Execute Stage 2 Autonomous Cloud Vectorization across all 30 days
echo "[5/5] Launching Stage 2 Vectorization across all 30 days on CUDA..."
python3 scripts/stage2_cloud_worker.py \
    --data-dir ./stage1_candidates \
    --all-days \
    --resume \
    --auto-shutdown

echo "======================================================================"
echo " Stage 2 Vectorization Complete!"
echo "======================================================================"

