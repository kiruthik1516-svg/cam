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
- **Frontend**: Next.js 16, React 19, TailwindCSS, Lucide Icons, `@tanstack/react-query`
- **Backend API**: Python 3.11, FastAPI, Uvicorn, WebSockets, SQLAlchemy 2.0 (ORM)
- **Computer Vision / AI**: InsightFace, ONNX Runtime, OpenCV, NumPy
- **Database**: PostgreSQL 16 with `pgvector` extension
- **Deployment**: Docker Compose v2 (Production & Dev profiles)

## Architecture Options

### Option 1: Local Edge Processing
The standard edge-to-cloud architecture:
1. **Edge CV Node (`facial_recognition/`)**: A local Python process captures live video frames from RTSP streams or webcams. `InsightFace` detects faces, extracts 512-dim embedding vectors, and identifies known profiles. It maintains a local SQLite ledger (`event_ledger.py`) for offline resilience and syncs detections to the backend API.
2. **Backend API (`backend/`)**: A FastAPI server on port 1223 ingests edge events and persists them into PostgreSQL via SQLAlchemy. When `ENABLE_FORENSIC_SEARCH=true`, it loads the face model in memory to extract embeddings from photo uploads and run forensic vector similarity searches.
3. **Database (`PostgreSQL + pgvector`)**: Stores relational models (Profiles, Cameras, Alerts, Detections) and uses `pgvector` HNSW index scans with cosine distance (`<=>`) for vector searches.
4. **Dashboard (`facial-recognition-dashboard/`)**: A Next.js application that renders real-time feeds, telemetry, analytics, vector enrollment, and recorded footage audits.

### Option 2: Remote GPU Offloaded Detection
For edge machines without dedicated GPUs:
1. **Local Edge**: Runs `facial_recognition/pc_frame_sender.py` or uses `RemoteInsightFaceDetector` in `main_cpu.py` / `main.py` with `REMOTE_DETECTION_URL`.
2. **Remote Detection Backend**: A GPU-enabled FastAPI backend instance exposes `POST /detect` secured with `EDGE_API_KEY`, performing GPU-accelerated face detection and embedding extraction before returning results.

See [GET_STARTED.md](GET_STARTED.md) and [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for detailed configuration options.

## Design & Implementation Highlights
- **Headless Server Compatibility**: Fully containerized and verified for headless Linux and Windows environments.
- **WebSocket Push & Selective Sync**: Implemented WebSocket channels (`/ws/alerts`, `/ws/cameras`, `/ws/kpis`) with client invalidations via `@tanstack/react-query`.
- **Vector Index Search & Deduplication**: Employs PostgreSQL `pgvector` HNSW index scans with cosine distance (`<=>`) for fast candidate retrieval, paired with nearest-neighbor duplicate identity detection.
- **Resilient Offline Ledger**: Edge events persist locally in SQLite with deterministic SHA-256 event IDs for idempotent multi-node sync.

## Setup

### Option A: Full Docker Stack (Recommended)
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Generate required secrets (`POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY`, `EDGE_API_KEY`, `ADMIN_PASSWORD`) as described in `docs/DEVELOPER_GUIDE.md`.
3. Launch the container stack:
   ```bash
   docker compose up -d --build
   ```
4. Verify the stack:
   ```bash
   python scripts/smoke_test.py
   ```
   - Dashboard: http://localhost:3000
   - Backend API: http://localhost:1223

### Option B: Local Development
1. **Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload --port 1223
   ```
2. **Frontend**:
   ```bash
   cd facial-recognition-dashboard
   pnpm install
   pnpm dev
   ```
3. **Edge Pipeline (Windows PowerShell)**:
   ```powershell
   .\scripts\run-cpu.ps1 -Setup      # First-time setup
   .\scripts\run-cpu.ps1             # Launch CPU edge runner
   ```

## Commands Cheat Sheet

### 1. Gallery & Unknown Faces Management
- **Dashboard Unregistered People**: View, name, assign, or merge unknown faces directly in the Sentinel Dashboard UI (`/api/unregistered-subjects`).
- **`python facial_recognition/enroll.py`**: Rebuilds the `gallery.npz` file from photos placed inside `facial_recognition/known_faces/`.

### 2. Edge Cameras & Detection
- **`.\scripts\run-cpu.ps1`**: Runs the CPU-optimized camera runner with multi-camera RTSP support.
- **`python facial_recognition/main_cpu.py --tier max`**: Runs CPU inference at 480x480 resolution for high-accuracy doorway capture.
- **`python facial_recognition/run.py`**: GPU camera runner for systems with NVIDIA CUDA support.

### 3. Verification & Auditing
- **`python scripts/smoke_test.py`**: Runs the 12-check end-to-end integration smoke test against a running backend stack.
- **`python scripts/generate_security_report_pdf.py`**: Generates the CCTV security compliance and gap audit report PDF.
- **`pytest backend/tests`**: Runs the backend automated test suite.

## Documentation
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)**: Architecture, daily workflows, configuration reference, and roadmap.
- **[Getting Started](GET_STARTED.md)**: Setup guide for distributed and remote GPU deployments.
- **[Integration Guide](docs/INTEGRATION_GUIDE.md)**: Camera NVR integration, RTSP streaming, and authentication reference.
