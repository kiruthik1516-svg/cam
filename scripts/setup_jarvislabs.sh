#!/usr/bin/env bash
# ==============================================================================
# JarvisLabs Cloud GPU Automated Setup Script for Engine 1 & Engine 2
# Platform: Ubuntu 20.04 / 22.04 LTS (NVIDIA RTX 4090 / A5000 / A6000 / A100)
# ==============================================================================
set -e

echo "======================================================================"
echo " Starting JarvisLabs Cloud GPU Environment Provisioning"
echo " Target: Sentinel Surveillance Platform (Engine 1 + Engine 2)"
echo "======================================================================"

# 1. System Libraries (FFmpeg, decompression tools, OpenGL for OpenCV)
echo "\n[1/5] Installing essential system packages (ffmpeg, 7z, unrar, libgl1)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y > /dev/null 2>&1 || true
apt-get install -y ffmpeg p7zip-full unrar libgl1 libglib2.0-0 curl wget > /dev/null 2>&1 || true

# 2. Verify GPU status
echo "\n[2/5] Checking NVIDIA GPU architecture..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
else
    echo "WARNING: nvidia-smi not detected. Pipeline will run on CPU mode."
fi

# 3. Python dependencies & CUDA PyTorch
echo "\n[3/5] Installing Python packages with CUDA 12 acceleration..."
python3 -m pip install --upgrade pip

if command -v nvidia-smi &> /dev/null; then
    # Install PyTorch with CUDA 12.1
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
else
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi

# Install pinned cloud dependencies
if [ -f "requirements-cloud.txt" ]; then
    pip install -r requirements-cloud.txt
else
    pip install ultralytics insightface onnxruntime-gpu opencv-python-headless psycopg2-binary sqlalchemy numpy scipy pandas tqdm reportlab python-dotenv
fi

# 4. Pre-download models to cache
echo "\n[4/5] Pre-caching Neural Network Models (YOLOv8-pose & InsightFace)..."
python3 -c "
import sys
try:
    print('  - Downloading/verifying YOLOv8-pose weights...')
    from ultralytics import YOLO
    model = YOLO('yolov8n-pose.pt')
    print('    [OK] YOLOv8-pose ready.')
except Exception as e:
    print(f'    [WARN] YOLOv8-pose download error: {e}')

try:
    print('  - Initializing InsightFace buffalo_l recognition weights...')
    import insightface
    from insightface.app import FaceAnalysis
    app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    print('    [OK] InsightFace buffalo_l models ready.')
except Exception as e:
    print(f'    [WARN] InsightFace prep warning: {e}')
"

# 5. Diagnostic Verification
echo "\n[5/5] Running Pre-flight Diagnostic Verification..."
python3 -c "
import torch, cv2, ultralytics
print('======================================================================')
print(' DIAGNOSTIC SUMMARY:')
print(f'  - PyTorch Version:   {torch.__version__}')
print(f'  - CUDA Available:    {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'  - GPU Device:        {torch.cuda.get_device_name(0)}')
    print(f'  - CUDA Capability:   {torch.cuda.get_device_capability(0)}')
print(f'  - OpenCV Version:    {cv2.__version__}')
print(f'  - Ultralytics Ver:   {ultralytics.__version__}')
print('======================================================================')
"

echo "\n======================================================================"
echo " JARVISLABS SETUP COMPLETE!"
echo " You can now run the 30-day pipeline using:"
echo "   bash run_30day_jarvislabs.sh --engine all --days 1-30"
echo "======================================================================"
