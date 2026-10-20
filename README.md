# Facial Recognition & Analytics Platform

An end-to-end, real-time facial recognition and vector-search analytics platform designed to bridge local edge-inference with a cloud-native Next.js dashboard.

## Description
This system processes live RTSP and webcam video feeds on local edge devices, extracting 512-dimensional facial embeddings using ONNX and InsightFace. It synchronizes captures with a cloud-hosted PostgreSQL vector database (`pgvector`) via a dual-write pipeline. A full-stack Next.js and FastAPI cloud dashboard consumes this data via WebSockets to provide real-time security alerts, footfall analytics, and forensic similarity searches across recorded detections.

## Key Features
- **Real-Time Edge Inference**: Low-latency face detection and recognition using the `buffalo_l` model running on ONNX CPU/GPU Execution Providers.
- **`pgvector` Forensic Search**: Execute cosine-similarity searches (`<=>`) natively in PostgreSQL using HNSW indexing to find matching suspects from static photo uploads.
- **Live-Streaming Telemetry**: Bi-directional WebSockets push instantaneous security alerts, camera health events, and KPI changes directly to the React frontend.
- **Resilient Dual-Write Pipeline**: Employs a local `.csv` transaction log paired with asynchronous SQLAlchemy cloud inserts, ensuring resilience during network partitions.
- **Identity Deduplication**: Nearest-neighbor index scans compute vector distances to surface duplicate identities for merge review.
- **Robust Error Handling**: Granular React Error Boundaries prevent individual dashboard widgets from crashing the global UI.
- **Distributed Processing**: Offload heavy ML inference to GPU instances using the frame sender and detection service.

## Tech Stack
- **Frontend**: Next.js 14, React 18, TailwindCSS, Shadcn UI, Lucide Icons, `@tanstack/react-query`
- **Backend API**: Python, FastAPI, Uvicorn, WebSockets, SQLAlchemy (ORM)
- **Computer Vision / AI**: InsightFace, ONNX Runtime, OpenCV, NumPy
- **Database**: PostgreSQL (Supabase) with the `pgvector` extension
- **Deployment**: Vercel (Frontend), Render (Backend), Local PC (Edge CV Pipeline), Google Colab/Kaggle (Remote Detection)

## Architecture Options

### Option 1: Local Processing (Original)
The architecture utilizes a distributed Edge-to-Cloud pattern:
1. **Edge CV Node (`facial_recognition/`)**: A local Python process captures live video frames. `InsightFace` detects faces, extracts the 512-dim embedding tensors, and identifies known profiles. It synchronously writes the event to a local CSV archive while async-POSTing the data to the Cloud API.
2. **Cloud API (`backend/`)**: A FastAPI server running on Render ingests edge events and inserts them into Supabase via SQLAlchemy. It also securely houses the ONNX models in memory during its `lifespan` to process manual image uploads (Forensic Search) without taxing the edge nodes.
3. **Cloud Database (`Supabase`)**: Stores relational metadata (Profiles, Cameras, Alerts) and uses `pgvector` to index the 512-dim embedding arrays, allowing for mathematical cosine distance queries.
4. **Cloud Dashboard (`facial-recognition-dashboard/`)**: A Next.js application that fetches historical aggregated analytics via REST and listens to FastAPI WebSockets for live React Query invalidations, ensuring the UI is perpetually up-to-date.

### Option 2: Distributed Processing (New)
For users who want to offload heavy ML inference to cloud GPUs:
1. **Local PC**: Runs `pc_frame_sender.py` to capture video and send frames to remote detection service
2. **Remote Detection Service** (Google Colab/Kaggle): Runs `colab_detection_service.py` to perform face detection/recognition using InsightFace GPUs
3. **Cloud API (`backend/`)**: Same as Option 1 - receives detection events (either from local edge or remote service) and inserts into Supabase
4. **Cloud Database (`Supabase`)**: Same as Option 1
5. **Cloud Dashboard (`facial-recognition-dashboard/`)**: Same as Option 1

See [GET_STARTED.md](GET_STARTED.md) for detailed setup instructions for the distributed processing option.

## Design & Implementation Highlights
- **Headless Server Compatibility**: Configured `opencv-python-headless` dependencies for headless Linux and containerized environments.
- **WebSocket Push & Selective Sync**: Implemented a WebSocket pub/sub architecture in FastAPI (`/ws/alerts`), triggering client cache invalidations via `@tanstack/react-query` to eliminate polling overhead.
- **Vector Index Search & Deduplication**: Employs PostgreSQL `pgvector` HNSW index scans with cosine distance (`<=>`) for fast candidate retrieval, paired with nearest-neighbor duplicate identity detection.
- **Hybrid Inference Flexibility**: Supports local edge inference with ONNX runtime as well as optional remote inference integration.

## Setup
Choose your preferred processing option:

### Option A: Local Processing (Recommended for machines with GPU)
1. **Database Setup**: Spin up a Supabase PostgreSQL instance and enable the `pgvector` extension.
2. **Backend**: 
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
3. **Frontend**:
   ```bash
   cd facial-recognition-dashboard
   pnpm install
   pnpm dev
   ```
4. **Edge CV**:
   ```bash
   cd facial_recognition
   python run.py          # With GPU
   # or
   python main_cpu.py     # CPU optimized
   ```

### Option B: Distributed Processing (For GPU acceleration via Colab/Kaggle)
See [GET_STARTED.md](GET_STARTED.md) for complete step-by-step instructions.

## Commands Cheat Sheet

### 1. Naming Unknown Faces (Gallery Management)
Run these from inside the `facial_recognition/` folder:
- **`python review_pending.py`**: Reviews unknown faces saved in the `pending/` folder, prompts you for their name via a GUI, and adds them to the known gallery.
- **`python enroll.py`**: Rebuilds the `gallery.npz` file from scratch using images placed inside `known_faces/`.

### 2. Running the Edge Cameras (Local Processing)
Run these from inside the `facial_recognition/` folder:
- **`python main_cpu.py`**: Runs the highly-optimized camera script tuned for laptops/CPUs (skips frames, limits threads).
- **`python run.py`**: The standard camera execution script, best used with a dedicated NVIDIA GPU.

### 3. Running the Distributed System
- **`python facial_recognition/pc_frame_sender.py`**: Sends frames from local PC to remote detection service (see GET_STARTED.md for setup)

### 4. Running the FastAPI Backend
- **`.\scripts\run-backend.ps1`** (from root): A PowerShell wrapper to launch the Python backend.
- **`uvicorn main:app --reload`** (from `backend/`): Manually starts the FastAPI server on `localhost:1223`.

### 5. Running the Next.js Dashboard
- **`.\scripts\run-frontend.ps1`** (from root): A PowerShell wrapper to launch the web interface.
- **`pnpm dev`** (from `facial-recognition-dashboard/`): Manually starts the Next.js UI on `localhost:3000`.

### 6. Setup & Validation
Run these from the root folder:
- **`.\scripts\setup-all.ps1`**: Automatically creates Python virtual environments, installs requirements, and runs `pnpm install` for the frontend.
- **`.\scripts\DEPLOYMENT_CHECKLIST.ps1`**: A helper script to quickly verify that all `.env` variables are correctly set before deployment.

## Links
- **GitHub Repository**: [Your Link Here]
- **Live Demo**: [Your Link Here]
- **Getting Started Guide**: [GET_STARTED.md](GET_STARTED.md)
