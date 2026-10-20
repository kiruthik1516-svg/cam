# Developer guide

This guide is for the developer taking the project forward. It answers three questions:

1. **What changed** compared with the original repository, and why. (Section 7)
2. **How do I set it up and run it?** (Sections 2 and 3)
3. **What is still to be done?** (Section 9)

If anything in the older files under `docs/` contradicts this guide or the README, trust this guide and the code. See
section 12 for which older documents are out of date.

---

## Contents

1. [Start here](#1-start-here)
2. [How the system fits together](#2-how-the-system-fits-together)
3. [Setup and daily workflow](#3-setup-and-daily-workflow)
4. [Configuration reference](#4-configuration-reference)
5. [Repository map](#5-repository-map)
6. [API at a glance](#6-api-at-a-glance)
7. [What was changed](#7-what-was-changed)
8. [Verification status](#8-verification-status)
9. [Pending work](#9-pending-work)
10. [Gotchas and troubleshooting](#10-gotchas-and-troubleshooting)
11. [Field notes from the proof of concept](#11-field-notes-from-the-proof-of-concept)
12. [Repository history and older documents](#12-repository-history-and-older-documents)

---

## 1. Start here

**What it is.** A face-recognition and CCTV-analytics platform (the dashboard is branded "SENTINEL"). Cameras or an NVR feed
an *edge* process that finds faces and matches them against enrolled people. Results go to a FastAPI backend with a
PostgreSQL + pgvector database, and a Next.js dashboard shows live feeds, alerts, analytics, forensic search and an
import tool for recorded CCTV footage.

**What this repository contains.** The original code, plus a set of fixes made during a proof of concept against a real
office CCTV system (an NVR with several cameras). The fixes cover credentials, bugs, security, Docker/CI and documentation.

**How the work was done, and how much to trust it.** The changes were written with an AI coding assistant and checked
with automated tests, a real PostgreSQL run, a full Docker stack run and a short live test. **No human code review has been
done yet.** Please review them like any other contribution (section 7 says where to look).

**Branches.**

| Branch | Meaning |
|---|---|
| `main` | Latest code: everything below, plus the CI fix. Start here |
| `upstream-main` | The original `main`, unchanged apart from removed secrets |
| `fix/credentials-and-logging` | Change set 1 |
| `fix/poc-bugs` | Change set 2 (builds on 1) |
| `fix/security-hardening` | Change set 3 (builds on 2) |
| `fix/packaging-and-ci` | Change set 4 (builds on 3). **Does not contain the later CI fix that is on `main`** |

Review the change sets one at a time with `git log --oneline upstream-main..main` and `git diff <previous>..<branch>`.

**First ten minutes.**
1. Read section 3 and bring the stack up (about 10 minutes the first time, mostly the Docker build).
2. Run the smoke test (section 3.5). It must say `All checks passed`.
3. Read section 9 and pick the first item. **Items 9.1 are not code and should be done before anything else.**

---

## 2. How the system fits together

```
  Cameras / NVR (RTSP)                                   Recorded CCTV files
        |                                                        |
        v                                                        v
  +--------------------------+   HTTPS + X-API-Key   +---------------------------+      +-----------------------+
  | EDGE  facial_recognition/|---------------------->|  BACKEND  backend/        |<---->| PostgreSQL + pgvector |
  | capture -> detect ->     |  detections, frames,  |  FastAPI, WebSockets      |      +-----------------------+
  | embed -> recognise       |  health               |  auth, alerts, analytics, |<---->| Redis (WS fan-out)    |
  | local SQLite ledger      |<----------------------|  forensic search, import  |      +-----------------------+
  +--------------------------+  gallery, camera cfg  +-------------+-------------+
                                                                   | REST + WebSocket (JWT)
                                                                   v
                                                      +---------------------------+
                                                      | DASHBOARD                 |
                                                      | facial-recognition-       |
                                                      | dashboard/  (Next.js)     |
                                                      +---------------------------+
```

| Component | Where | Notes |
|---|---|---|
| Edge | `facial_recognition/` | Runs on a PC near the cameras. Uses InsightFace `buffalo_s` on ONNX Runtime. CPU entry point `run_cpu.py` (`main_cpu.py`), GPU entry point `run.py` (`main.py`). Keeps a local SQLite ledger (`facial_recognition.db`) so events survive network outages and are re-sent. |
| Backend | `backend/` | FastAPI on port 1223. Receives detections, serves the dashboard API, runs alert rules, forensic (vector) search, and the footage audit/import tools. Also holds the face model in memory when `ENABLE_FORENSIC_SEARCH=true` (needed for photo enrollment). |
| Database | PostgreSQL 16 + pgvector | 512-number face embeddings, cosine search. Tests can also run on SQLite. |
| Redis | `redis:7` | Only for WebSocket fan-out across backend instances. |
| Dashboard | `facial-recognition-dashboard/` | Next.js 16 / React 19. Two modes: **Live Surveillance** (Live Feeds & Alerts, Vector Management, Live Analytics, System Health) and **Archive / CCTV Ingest** (CCTV Audit & Ingest, Footage Detected Persons, Forensic Trajectory Search, Archive Event Trail, Historical Analytics). |

**Typical flows.**
- *Live:* camera frame -> edge detects and recognises -> `POST /api/detections` (or `/batch`) -> backend stores it, applies
  alert rules, broadcasts over WebSocket -> dashboard updates. The edge also uploads an annotated frame per camera to
  `POST /api/internal/cameras/{id}/frame`, which the dashboard shows as the live feed (MJPEG).
- *Recorded footage:* the dashboard's *CCTV Audit & Ingest* tab calls `/api/video-audit/*`. The audit checks timestamps
  between files and computes SHA-256 hashes. The ingest samples frames, finds faces and groups them into "Person N".
- *Enrollment:* upload photos on *Vector Management* (backend extracts the embedding) or build a local gallery with
  `facial_recognition/enroll.py`.

---

## 3. Setup and daily workflow

### 3.1 Prerequisites
- Docker with Compose v2 for the backend, database and dashboard.
- Python **3.11** for the edge process and for running tests outside Docker. (3.14 fails to install InsightFace; 3.11 is the
  tested version.)
- Node 20 and pnpm only if you want to run the dashboard outside Docker.
- About 8 GB of free RAM for the stack plus the edge. The backend image is about 2.2 GB.

### 3.2 First run (Docker stack)
```bash
cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
```
The stack **refuses to start without five secrets**. Generate values and append them to `.env`:
```bash
python -c "import secrets; print('POSTGRES_PASSWORD='+secrets.token_urlsafe(24)); print('REDIS_PASSWORD='+secrets.token_urlsafe(24)); print('SECRET_KEY='+secrets.token_hex(32)); print('EDGE_API_KEY='+secrets.token_hex(32)); print('ADMIN_PASSWORD='+secrets.token_urlsafe(16))" >> .env
```
Keep `POSTGRES_PASSWORD` and `REDIS_PASSWORD` URL-safe (letters, digits, `-`, `_`) because they are placed inside connection URLs.
`.env` is git-ignored. Never commit it.

```bash
docker compose up -d --build    # first build takes 5-10 minutes (InsightFace is compiled in the build stage)
docker compose ps               # backend should become "healthy" (it can take up to ~3 minutes to load the model)
```
- Dashboard: <http://localhost:3000>. Log in with user `admin` and your `ADMIN_PASSWORD`.
- API: <http://localhost:1223> (interactive docs at `/docs` unless `ENVIRONMENT=production`).
- All ports are published on `127.0.0.1` only. Set `BIND_ADDRESS` to expose them.

### 3.3 Running the edge (cameras and recognition)
On Windows (the tested path):
```powershell
.\scripts\run-cpu.ps1 -Setup      # once: creates .\myenv with Python 3.11 and installs requirements.txt
.\scripts\run-cpu.ps1             # run the CPU edge
.\scripts\run-cpu.ps1 -r 480 --tier fast --frame-skip 3   # larger detection size, see 9.3 (R2)
```
Extra arguments go to the runner (`-r` detection size, `--tier auto|fast|mid|slow`, `--frame-skip N`, `--model buffalo_s|buffalo_l`,
`--max` for the max-quality preset). On Linux, create a Python 3.11 venv, `pip install -r requirements.txt` and run
`python facial_recognition/run_cpu.py`. The GPU path (`run.py`, `Dockerfile.detector`) was never run during the proof of concept.

The edge reads `.env` from the repository root. `API_URL` (default `http://localhost:1223`) and `EDGE_API_KEY` **must match the
backend**. Press `q` in the preview window (or Ctrl-C) to stop it.

### 3.4 Connecting cameras
Set these in `.env` (names matter, see `.env.example` for comments):
```
DVR_IP=192.168.1.10
DVR_USERNAME=<read-only NVR user>
DVR_PASSWORD=<password>
DVR_RTSP_PORT=554
# One NVR, several cameras. {channel} (or channel=<n>) in the path is replaced per channel:
DVR_RTSP_PATH=cam/realmonitor?channel={channel}&subtype=1
DVR_CHANNELS=4,1,5
DVR_CAMERA_NAMES=reception,lane,staff-room
```
- Camera ids come from `DVR_CAMERA_NAMES` (lower-cased, spaces become `-`), else `dvr-ch<channel>`. Without `DVR_CHANNELS`, one camera
  named `dvr-1` is created from `DVR_RTSP_PATH` as written.
- `DVR_RTSP_PATH` shown is the Dahua / CP Plus style. Hikvision default is `Streaming/Channels/101` (use `{channel}01`-style templates).
- Extra non-credential sources can be listed under `rtsp_urls` in `facial_recognition/config.yaml` (named `rtsp-1`, `rtsp-2`, ...).
  **Do not put passwords there.**
- Use a **read-only NVR account** (live view only). Passwords are redacted in the edge's logs.
- Verify a stream before blaming the software: open the same URL in VLC. See 10.2 for NVR numbering and relay traps.
- `DISABLE_WEBCAM=true` skips the laptop webcam (the CPU runner uses it by default).

### 3.5 Verify a running stack (smoke test)
```bash
ADMIN_PASSWORD=<your password> EDGE_API_KEY=<your key> python scripts/smoke_test.py
```
Twelve checks (login, throttling, edge-key scope, camera registration, footage path restriction, dashboard page). It
registers one throw-away camera `smoke-<time>` in the database. CI runs the same script against a freshly built stack.

### 3.6 Importing recorded footage
Put clips in a folder, set `FOOTAGE_DIR` in `.env` (default `./footage`) and restart the backend. In the dashboard open
**Archive / CCTV Ingest -> CCTV Audit & Ingest** and enter the path **`/footage`** (the path *inside the container*). The
backend refuses any path outside `FOOTAGE_ROOTS` (default `/footage`). Without Docker, set `FOOTAGE_ROOTS` to your folder.
Filenames should carry a recording timestamp (Dahua, Hikvision, ISO 8601, epoch patterns are recognised).

### 3.7 Tests
```bash
# From the repo root, Python 3.11, dependencies from backend/requirements.txt (or the repo's myenv):
PYTHONPATH=backend:. DATABASE_URL=sqlite:///./test.db pytest backend/tests          # 92 tests, ~5 s
PYTHONPATH=backend:. DATABASE_URL=postgresql://postgres:<pw>@localhost:5432/test_db pytest backend/tests   # needs pgvector
```
`backend/tests/conftest.py` supplies test values for `SECRET_KEY`, `EDGE_API_KEY`, `ADMIN_PASSWORD` and `CORS_ORIGINS`.
Windows PowerShell: set the variables with `$env:PYTHONPATH = "backend;."` (semicolon).

**Important:** `backend/config.py` loads a `.env` file from the repo root automatically. A developer `.env` can therefore hide a
missing environment variable that CI (which has no `.env`) will expose. Run tests from a clean checkout, or temporarily move `.env`.

### 3.8 Development with live source mounts
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker compose restart backend      # picks up Python edits (uvicorn runs without --reload)
```
Dashboard without Docker: `cd facial-recognition-dashboard && pnpm install && pnpm dev` (<http://localhost:3000>); checks:
`pnpm exec tsc --noEmit`, `pnpm run lint`, `pnpm run build`. The production build now **fails on TypeScript errors**.

### 3.9 CI
`.github/workflows/ci.yml` runs on every push to `main`, on pull requests, and manually:

| Job | What it does |
|---|---|
| Secret scan | TruffleHog on pull requests and non-default-branch pushes (skipped on `main`). **Has not run yet**, see 9.2 (S11) |
| Backend tests (sqlite, postgres) | Installs `backend/requirements.txt`, syntax check, flake8 (syntax-level rules only), `pip-audit` (sqlite job), 92 tests. The Postgres job uses a `pgvector/pgvector:pg16` service |
| Frontend | `pnpm audit --prod --audit-level high`, `tsc`, ESLint, `next build` |
| Docker stack smoke test | Builds and starts the whole Compose stack and runs `scripts/smoke_test.py` |
| Deploy | Only on `push` to `main`, after the jobs above. Calls Render/Vercel hooks **only if** the secrets `RENDER_DEPLOY_HOOK_URL` / `VERCEL_DEPLOY_HOOK_URL` exist (none are set) |

A full run takes about 3 minutes. Run #2 on `main` (commit `8fa2243`) passed.

---

## 4. Configuration reference

All settings come from environment variables; locally from the repo-root `.env`. `.env.example` documents most of them.

### 4.1 Required (no defaults on purpose)
| Variable | Used by | Meaning |
|---|---|---|
| `POSTGRES_PASSWORD` | Compose | Database password (URL-safe) |
| `REDIS_PASSWORD` | Compose | Redis password (URL-safe) |
| `SECRET_KEY` (or `JWT_SECRET`) | Backend | Signs login tokens. If unset outside production, a random per-process secret is used (logins reset on restart). Production refuses to start without it |
| `EDGE_API_KEY` | Backend + edge | Shared key the edge sends as `X-API-Key`. Placeholder values (`default-dev-key`, `change-me`) are refused |
| `ADMIN_PASSWORD` | Backend | Dashboard login password for `ADMIN_USERNAME` (default `admin`). Login returns 503 until set |

### 4.2 Backend and security
| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | Compose builds it | `postgresql://...`. SQLite works for tests. Falling back to SQLite needs `ALLOW_SQLITE_FALLBACK=1` |
| `REDIS_URL` | Compose builds it | If empty, WebSocket broadcast is in-process only |
| `ENVIRONMENT` | `development` | `production` requires `SECRET_KEY` and hides `/docs`, `/redoc`, `/openapi.json` |
| `CORS_ORIGINS` | localhost:3000 variants | Comma-separated exact origins. `*` matches **one** DNS label (`https://*.vercel.app` matches `a.vercel.app`, not `a.b.vercel.app`). List your hosted dashboard explicitly |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `720` | Login lifetime |
| `ENABLE_FORENSIC_SEARCH` | `true` in Compose | Loads the face model in the backend. **Needed to enroll from photos and for photo-based forensic search** |
| `ENABLE_EDGE_PIPELINES` | `false` | Starts camera pipelines inside the backend process (not the normal setup) |
| `FOOTAGE_ROOTS` | `/footage` | Folders the footage tools may read (`;` or `,` separated) |
| `ALLOW_PICKLE_NPZ` | off | `1` allows loading old `.npz` files written with pickled arrays. Only for files you created |
| `CLUSTER_DISTANCE_THRESHOLD` | `0.55` | Cut-off for grouping faces into one person during footage import (0.20 to 0.95). Higher merges more |
| `UNREGISTERED_SIMILARITY_THRESHOLD`, `LIVENESS_ALERT_THRESHOLD`, `MAX_STREAM_LATENCY_SECONDS` | `0.75`, `0.45`, `900` | Live alert and unknown-subject tuning (`backend/config.py`) |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Proxy addresses whose `X-Forwarded-*` headers are trusted. Set it when behind a reverse proxy |
| `SENTRY_DSN` | unset | Enables Sentry in the backend (traces are sampled at 100%, lower it for production) |

### 4.3 Compose and deployment
`BIND_ADDRESS` (default `127.0.0.1`), `FOOTAGE_DIR` (default `./footage`), `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL`
(**baked into the dashboard bundle at build time**; change them and rebuild the `frontend` image).

### 4.4 Edge and cameras
| Variable | Meaning |
|---|---|
| `API_URL` | Backend URL the edge posts to (default `http://localhost:1223`) |
| `DVR_IP`, `DVR_USERNAME`, `DVR_PASSWORD`, `DVR_RTSP_PORT`, `DVR_RTSP_PATH`, `DVR_CHANNELS`, `DVR_CAMERA_NAMES` | NVR cameras, see 3.4 |
| `DISABLE_WEBCAM` / `NO_WEBCAM` | `true` to skip the local webcam |
| `EDGE_STREAM_FPS`, `EDGE_STREAM_JPEG_QUALITY` | Rate and quality of the annotated frames uploaded for the dashboard feed (default 8 fps, 75) |
| `COLAB_API_KEY`, `REMOTE_DETECTION_URL` | Only for the remote-GPU `pc_frame_sender.py` setup |
| `EDGE_FORENSIC_*`, `NEXT_PUBLIC_EDGE_API_URL` | **Listed in `.env.example` but not used by any code**, see 9.2 (S9) |

### 4.5 Recognition tuning (`facial_recognition/config.yaml`)
`similarity_threshold` (0.35), `quality_thresholds.high/medium` (minimum face size, confidence, sharpness, pose; medium needs
`temporal_observations_required: 5` sightings), `track_fusion.*` (how sightings are combined), `cpu_inference_frame_width/height`
(160), `cpu_frame_skip` (4), `cpu_tier`. See `docs/adaptive_quality_pipeline.md` and `docs/track_identity_fusion.md`.

---

## 5. Repository map

```
backend/                    FastAPI app (entry: main.py)
  main.py                   app setup, CORS, WebSockets, MJPEG stream, topology and tracking routes, /detect
  auth.py  middleware.py  dependencies.py   login, JWT middleware, edge-key check
  config.py  database.py  models.py  schemas.py  state.py  utils.py  websocket.py
  routers/                  analytics, cameras, detections, forensic, logs, profiles, system, unregistered, video_audit
  migrations/               Alembic (initial schema + idempotency columns)
  tests/                    92 tests (see 3.7)
facial_recognition/         Edge package (also imported by the backend for model code)
  run_cpu.py -> main_cpu.py CPU runner; run.py -> main.py GPU runner; cli.py = flags
  sources.py                camera list from .env, redact_url()      [new]
  safeio.py                 .npz loading without pickle              [new]
  capture.py  detector.py  recognizer.py  quality.py  track_fusion.py  cross_camera_tracker.py  topology.py
  event_ledger.py  sequence_manager.py  logger.py     local ledger and cloud sync (offline-safe, idempotent)
  batch_video_ingest.py  video_auditor.py              recorded-footage import and integrity audit
  config.yaml               recognition and camera settings
facial-recognition-dashboard/   Next.js app (app/, components/dashboard/, lib/api/)
scripts/                    run-cpu.ps1, smoke_test.py, generate_security_report_pdf.py
docker-compose.yml          the stack (+ docker-compose.dev.yml for source mounts, docker-compose.jarvislabs.yml for a cloud GPU host)
Dockerfile.detector         GPU edge image (never built in the proof of concept)
.github/workflows/ci.yml    CI
docs/                       design notes (see section 12 for which are stale)
```

---

## 6. API at a glance

**Who may call what** (enforced in `backend/middleware.py` and `backend/dependencies.py`):

| Caller | Credential | Allowed |
|---|---|---|
| Dashboard user | `Authorization: Bearer <JWT>` from `POST /api/auth/login` | All `/api/*` routes |
| Dashboard media tags | `?token=<JWT>` | **Only** `GET /api/cameras/{id}/stream` and `/stream/snapshot` |
| Edge node | `X-API-Key: <EDGE_API_KEY>` | `/api/internal/*`, `POST /api/detections`, `/api/detections/batch`, `/api/detections/reconcile`, `POST /api/nodes/health`, `POST /detect`, and the WebSocket `/ws/video/push/{id}?api_key=` |
| Public | none | `/health`, `/api/auth/login` |

| Area | Routes |
|---|---|
| Auth | `POST /api/auth/login` |
| System | `GET /health`, `GET /api/kpis?source=live\|archive&batch_id=`, `GET/POST /api/thresholds`, `GET/POST /api/nodes/health`, `GET /api/system/version-bundle` |
| Cameras | `GET /api/cameras?source=live\|archive`, `GET /api/cameras/{id}/stream` (MJPEG), `.../stream/snapshot`, camera config versioning `GET/POST/PUT /api/cameras/{id}/config`, `.../config/history`, `.../config/rollback` |
| Detections | `POST /api/detections`, `/batch`, `/reconcile` (edge, idempotent by `event_id`), `GET /api/detections/{event_id}/provenance` |
| Logs and alerts | `GET /api/logs`, `GET /api/logs/episodes`, `GET /api/alerts`, `POST /api/alerts/{id}/acknowledge` |
| Profiles | `GET/POST /api/profiles`, `GET/PUT/DELETE /api/profiles/{id}` (`?erase_biometrics=true`), `DELETE .../embeddings[/{id}]`, `POST /api/profiles/merge` |
| Unregistered people | `/api/unregistered-subjects` (list, rename, register, assign, merge, delete, transfer sightings) |
| Forensic | `POST /api/forensic/search` (photo or profile), `POST /api/provenance/retention` |
| Analytics | `/api/analytics/footfall`, `/attendance`, `/gender-distribution`, `/age-distribution`, `/duplicates`, `/movement-network`, `/trajectory` |
| Topology | `GET /api/topology`, `POST /api/topology/edges`, `POST /api/tracking/cross-camera-evaluate` (**topology lives in memory only**, see 9.3 R5) |
| Footage | `/api/video-audit/browse`, `/locate`, `/scan`, `/ingest`, `/status`, `/stop`, `/latest-report`, `/batches`, `DELETE /batches/{id}`, `/gpu-status` (restricted to `FOOTAGE_ROOTS`) |
| WebSockets | `/ws/alerts`, `/ws/cameras`, `/ws/kpis` (JWT or edge key in the query string), `/ws/video/push/{camera_id}` |

---

## 7. What was changed

Six commits sit on top of `upstream-main`: the four change sets below (57 files, about 2,300 lines added, one branch each), the handover notes, and the CI fix.

### 7.1 Change set 1: credentials and logging (`fix/credentials-and-logging`)
- `facial_recognition/sources.py` (new): `redact_url()` and `dvr_sources_from_env()`. The edge used to print the full camera URL,
  **including the NVR password**, in its logs (`main_cpu.py`, `capture.py`); both now redact it.
- Several NVR cameras from `.env` (`DVR_CHANNELS`, `DVR_CAMERA_NAMES`, template path), with the old single-camera behaviour kept.
- Sample camera IPs removed from `config.yaml`. Credentials removed from `DEPLOY_JARVIS_VERCEL.md` and a test.
- Client-specific quick-fill path and batch name removed from `cctv-audit-panel.tsx`.

### 7.2 Change set 2: bugs found during the proof of concept (`fix/poc-bugs`)
| Problem | Fix (where) |
|---|---|
| Dashboard header showed zeros and a red "Critical" | The UI read `connected_cameras`, `detections_today`, `system_health`, ... which the API never sent. `backend/routers/system.py` (`get_kpis`) and `schemas.py` now return them; archive mode reports batch totals |
| Live feed card listed an imported-footage camera as offline | Cameras register on their first frame (`backend/main.py`, `utils.py`, `state.py`); `GET /api/cameras?source=live` |
| `POST /api/thresholds` returned 500 | Used `asyncio.create_task` in a threadpool; now `BackgroundTasks` (`routers/system.py`) |
| Enrolling photos with no face model silently made an empty profile | Returns 503 with a clear message (`routers/profiles.py`) |
| "0.0%" confidence for unmatched people; audit banner said "zero missing frames" | Shown as "n/a"; banner no longer overclaims (`cctv-persons-tab.tsx`, `cctv-audit-panel.tsx`) |
| One person split into many identities | Cut-off made configurable (`CLUSTER_DISTANCE_THRESHOLD`, `batch_video_ingest.py`). Default unchanged |
| `facial_recognition` import required InsightFace | Lazy imports in `facial_recognition/__init__.py` |

### 7.3 Change set 3: security hardening (`fix/security-hardening`)
- **Login** (`backend/auth.py`): no default password; throttling (5 failures per 5 minutes per client address, then 429); 12-hour tokens.
- **JWT secret**: no hard-coded fallback; `python-jose` replaced by `PyJWT`.
- **Edge key** (`dependencies.py`, `middleware.py`, `main.py`): no `default-dev-key` anywhere (REST, WebSocket, video push); scoped to
  ingestion routes; header only. A JWT in `?token=` is accepted only on the two stream routes.
- **CORS** (`main.py`, `config.py`): localhost-only default; wildcard matches one label; error responses no longer echo arbitrary origins.
- **Footage tools** (`routers/video_audit.py`): browse/locate/scan/ingest are confined to `FOOTAGE_ROOTS` (symlinks and `..` resolved first).
- **Pickle**: `.npz` files load without pickle (`facial_recognition/safeio.py`), string arrays are saved as plain unicode.
- **Data handling**: camera `rtsp_url` credentials masked in API responses (`schemas.py`); profile merge rejects self-merge and moves
  transitions; `DELETE /api/profiles/{id}?erase_biometrics=true` removes stored face images and vectors; the gallery "version" is
  derived from the enrolled vectors (`utils.compute_gallery_version`); a failed item in a batch rolls back the shared session.
- **Dependencies**: FastAPI 0.149, Pydantic 2.14, python-multipart 0.0.32, PyJWT 2.15, python-dotenv 1.2.4. `pip-audit` is clean.
- `/docs`, `/redoc`, `/openapi.json` are off when `ENVIRONMENT=production`.

### 7.4 Change set 4: packaging and CI (`fix/packaging-and-ci`)
- **Compose**: removed the mounts of the host's whole `C:` and `D:` drives into the backend; ports on `127.0.0.1`; required secrets; Redis
  password; no source mounts by default (`docker-compose.dev.yml` adds them); `no-new-privileges` and `cap_drop: ALL` on backend and dashboard.
- **Images**: backend is multi-stage (no compilers in the final image) and runs as a non-root user; detector image non-root; `.dockerignore` added.
- **CI**: see 3.9. **`scripts/smoke_test.py`** added.
- **Bug found by running on PostgreSQL**: saving thresholds wrote a boolean into a numeric column (SQLite hid it). Fixed in `routers/system.py`.
- **Dashboard dependencies**: Next.js 16.3.0 -> 16.3.8, `@sentry/nextjs` 11.8, `shadcn` moved to devDependencies, overrides for transitive
  packages. Production audit: 66 vulnerabilities -> none. Build no longer ignores TypeScript errors.
- `requirements.txt`: `sqlalchemy<2.1` (2.1 makes `postgresql://` use the psycopg3 driver, which is not installed), explicit `scikit-learn`.
- `scripts/run-cpu.ps1 -Setup`, README setup section rewritten (it referenced scripts that never existed).

### 7.5 CI fix on `main` only
`python-dotenv` pinned to 1.2.4, `setuptools` upgraded before the audit, and the tests set their own `ADMIN_PASSWORD`.

### 7.6 Behaviour changes you will notice
| Area | Before | Now | What to do |
|---|---|---|---|
| Login | `admin` / `admin` if nothing set | 503 until `ADMIN_PASSWORD` set | Set it |
| Token lifetime | 7 days | 12 hours | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Edge key | `default-dev-key` accepted; opened every `/api/*` route; also via `?api_key=` | Must be set and non-placeholder; only edge routes; header only | Set `EDGE_API_KEY` on both sides |
| CORS | `*.vercel.app` and `*.jarvislabs.run` allowed by default | localhost only | List your dashboard origin in `CORS_ORIGINS` |
| Compose | worked with no `.env`, mounted `C:\` and `D:` | needs five secrets, footage via `FOOTAGE_DIR` -> `/footage` | See 3.2 |
| Footage endpoints | any folder on the server | only inside `FOOTAGE_ROOTS` | Set `FOOTAGE_ROOTS` if not using Docker |
| Gallery `.npz` | pickle loaded | refused if pickled | Re-run enrollment, or `ALLOW_PICKLE_NPZ=1` for files you made |
| API responses | `rtsp_url` returned in full | credentials masked | none |
| `GET /api/kpis` | 8 fields | adds `connected_cameras`, `total_cameras`, `detections_today`, `active_alerts`, `system_health`, ... | none (additive) |
| Dashboard build | ignored TypeScript errors | fails on them | fix the error |

---

## 8. Verification status

**Verified.**
- 92 backend tests pass on SQLite and on PostgreSQL (locally, in a Linux container, and in GitHub Actions run #2).
- Dashboard: `next build`, `tsc --noEmit`, ESLint (0 errors, 85 `any` warnings), `pnpm audit --prod` clean.
- The full Compose stack builds from tracked files and passes the 12-check smoke test (locally and in CI). Containers run as non-root with no host drives.
- A live proof of concept: an NVR with several cameras, three to four streams at once on one laptop, an import of a one-hour 1080p clip, enrollment tooling.
- Static checks: `actionlint` on the workflow, `docker buildx build --check` on both Dockerfiles.

**Not verified.**
- **The secret-scan job** has never run (9.2 S11).
- **The GPU detector image** was only syntax-checked.
- **Scale**: nothing beyond four cameras on one laptop. No numbers for 40 cameras.
- **Recognition accuracy**: tried on one real clip and a few minutes of live view. In the live test **no face was recorded at all** (section 11).
- **Frontend behaviour** was checked by build/type/lint and a few screenshots, not by browser tests. The repo has no e2e tests (`pnpm test:e2e` has nothing behind it).
- No human code review of the changes.

---

## 9. Pending work

Sizes: S under a day, M a few days, L a week or more. File paths point at where to start.

### 9.1 Do first (not code)
1. **Rotate every credential that was ever committed to the original repository** and purge or make private the original. They were: the Supabase
   database password and project references (two projects), `SECRET_KEY`, `EDGE_API_KEY`, `ADMIN_PASSWORD`, an env backup file, and a hard-coded Colab
   `API_KEY`. They are replaced by `***REMOVED***` in this repository's history but remain valid values and remain in the original.
2. **Rotate the NVR admin password** used during testing (it was printed in terminal logs before redaction existed) and restrict the `poc_view`-style
   read-only user to *Live* for only the channels in use (Search and Manual Control off).
3. **Consent and client permission for committed material**: `facial-recognition-dashboard/public/reports/` holds a client audit PDF and a screenshot
   with named employee faces, and `components/dashboard/export-report-modal.tsx` is hard-coded to that client. Decide whether to keep, replace or remove (R8).
4. **Legal basis for biometric data** (consent, retention, erasure, security) before real use. Nothing in this repo is a compliance solution.

### 9.2 Security
| ID | Item | Where | Size |
|---|---|---|---|
| S1 | **Login handling in the browser.** The JWT is in `localStorage`, there is no logout, and tokens travel in stream and WebSocket URLs (so they appear in access logs). Use an HttpOnly cookie (or short-lived one-time stream tickets), add `POST /api/auth/logout`, add server-side route protection in Next.js middleware | `lib/api/config.ts`, `lib/api/websockets.ts`, `components/providers.tsx`, `backend/auth.py`, `middleware.py`, `main.py` (`authenticate_ws`) | M |
| S2 | **Real users, roles and an audit log.** One shared admin today. Add users, roles (viewer/operator/admin), enforce them on delete/purge/merge/forensic search, and record who did what | `backend/models.py`, routers | L |
| S3 | **Remove `default-dev-key` from the edge modules.** The server rejects it, but it should not exist | `facial_recognition/camera_config.py`, `hierarchical_search.py`, `logger.py`, `recognizer.py` | S |
| S4 | **Biometric retention and protection.** No scheduled purge for detections; face crops are base64 in the `detections` table, unencrypted. Add a retention job, move crops to encrypted object storage | `models.py` (`face_image`), `routers/forensic.py` (`/api/provenance/retention` only covers lineage) | L |
| S5 | **Stop logging tokens.** `uvicorn` access logs print `?token=`. Falls away with S1; until then disable or filter the access log | `backend/Dockerfile` | S |
| S6 | **Upload and request limits.** No size, type or rate limit on photo uploads and `/detect`; `extract_face_embedding` reads the whole file | `backend/utils.py`, `routers/profiles.py`, `routers/forensic.py`, `main.py` | S |
| S7 | **Login lockout keys on client address.** Behind Docker's bridge every client can share one address, so one attacker could lock out everyone. Set `FORWARDED_ALLOW_IPS` behind a proxy and/or lock per user name too | `backend/auth.py` | S |
| S8 | **Per-device edge keys** with scopes and rotation (one shared key today) | `backend/dependencies.py`, `models.py` | M |
| S9 | **Tidy `.env.example`**: remove unused `EDGE_FORENSIC_*` (one default is `CORS_ORIGINS=*`) and `NEXT_PUBLIC_EDGE_API_URL` if nothing uses them | `.env.example`, `next.config.mjs` | S |
| S10 | Pin base images by digest, add an image scan (Trivy) to CI | Dockerfiles, `ci.yml` | S |
| S11 | **Check the secret-scan job.** It runs on pull requests and non-default-branch pushes only, so it has never executed. It reports unverified findings too, so expect noise from test fixtures on the first PR and tune it | `.github/workflows/ci.yml` | S |

### 9.3 Recognition quality and product
| ID | Item | Evidence and where to start | Size |
|---|---|---|---|
| R1 | **Faces are too small to be recorded.** The edge reads the 720p *sub-stream* and ignores faces under about 40 px (40-80 px need 5 sightings). Live test: the only camera that produced faces (a lab) gave about 47 and 31 px in the sub-stream (71 and 46 px in 1080p), so nothing was stored. Allow a **per-camera stream choice** (main stream for key cameras), revisit `quality_thresholds`, and review camera placement (face height at the door) | `facial_recognition/sources.py` (one `DVR_RTSP_PATH` template today; e.g. allow `DVR_CHANNELS=4:0,1:1`), `config.yaml`, `quality.py` | M |
| R2 | **Detection size default.** `cpu_inference_frame_width: 160` is too small for a door camera. Running with `-r 480 --tier fast --frame-skip 3` gave 8-9 analysed frames/s per camera at about 50-66% total CPU for 3-4 cameras. Make the size per camera or raise the default | `config.yaml`, `main_cpu.py`, `cli.py` | S |
| R3 | **One person split into many identities** on a high ceiling camera (7 "persons" for one individual; mean same-person similarity 0.28). Drop steep-angle faces before grouping, merge groups by centroid, show a quality score. Raising the cut-off to 0.70-0.75 helps partly | `batch_video_ingest.py` (`_cluster_unregistered_batch_subjects`) | M |
| R4 | **Clock handling.** The NVR clock was 13 minutes off until NTP was enabled. Live events use the edge PC clock, recorded clips use the NVR clock. Add a skew warning and record which clock a timestamp came from | `facial_recognition/logger.py`, `backend/routers/detections.py` | M |
| R5 | **Camera topology is in memory only** and lost on backend restart. `camera_routes` in `config.yaml` is not read by any code. Persist edges in the database and load them at start-up. (During the test the order lane -> reception -> staff-room was posted by hand to `POST /api/topology/edges`; a fourth camera `lab` was not placed) | `backend/state.py`, `main.py` (topology routes), `models.py` | M |
| R6 | **Renamed cameras linger.** After renaming a camera the backend keeps counting the old stream id until restart. `live_camera_ids` should only count cameras that have a row, and stale frame slots should expire | `backend/state.py`, `utils.py` | S |
| R7 | **Camera display names and zones.** Only ids exist; the `Camera` model has `name` and `zone` but the edge never sets them | `models.py`, `routers/cameras.py`, UI | M |
| R8 | **Report export is hard-coded to one client** (name, text, PDF, screenshots) | `components/dashboard/export-report-modal.tsx`, `public/reports/` | M |
| R9 | **Scaling claims do not hold.** `/api/internal/vector-search` loads every embedding into Python; `/api/analytics/duplicates` is an O(n^2) self-join. Use `ORDER BY embedding <=> :q LIMIT k`, benchmark, and remove unmeasured claims from the README | `backend/main.py`, `routers/analytics.py`, `README.md` | M |
| R10 | `wearing_mask` and `wearing_glasses` are hard-coded `False` on ingest, so those forensic filters never match. Implement or remove | `routers/detections.py` | S |
| R11 | **Liveness** comes from the edge client; consider a server-side check | `routers/detections.py` | M |
| R12 | **InsightFace versions differ**: the backend image pins 0.7.3, the edge environment resolves 2.1. Unify and test recognition across them | `backend/requirements.txt`, `requirements.txt` | S |
| R13 | **Import at scale** was only tried on one 1-hour clip (about 4 minutes). Try multi-day archives, multiple cameras, GPU | `batch_video_ingest.py` | M |

### 9.4 Engineering hygiene
| ID | Item | Where | Size |
|---|---|---|---|
| H1 | Remove the CV-style "I Built / Challenges / Results" README sections and unmeasured claims ("sub-100ms", "millions") | `README.md` | S |
| H2 | Reconcile or delete stale documents, including the references to scripts that do not exist (section 12) | `docs/`, `GET_STARTED.md`, `README.md`, `DEPLOY_JARVIS_VERCEL.md` | M |
| H3 | Three schema mechanisms run at start-up (`Base.metadata.create_all`, `ensure_detection_event_id_column`, Alembic). Keep Alembic only | `backend/main.py`, `database.py`, `migrations/` | M |
| H4 | Timestamps are naive IST `DateTime` columns. Move to timezone-aware UTC | `models.py`, `config.py` | L |
| H5 | `backend/main.py` is large (streaming, topology, WebSockets, `/detect`). Split into routers | `backend/main.py` | M |
| H6 | 85 ESLint `any` warnings; no frontend or e2e tests | dashboard | M |
| H7 | Add `.gitattributes` (`* text=auto eol=lf`) so Windows checkouts do not create CRLF noise | repo root | S |
| H8 | Pydantic `.dict()` and SQLAlchemy `distinct(...)` deprecation warnings | `routers/system.py`, `routers/analytics.py` | S |
| H9 | Build the GPU detector image in CI (or on a GPU runner) | `Dockerfile.detector`, `ci.yml` | M |
| H10 | flake8 only checks syntax-level rules; add `ruff` or wider rules (about 200 unused imports exist) | `ci.yml` | S |

---

## 10. Gotchas and troubleshooting

### 10.1 Stack and tests
- **`docker compose` says `Set X in .env`**: one of the five required secrets is missing (section 3.2).
- **Backend takes long to become healthy**: it loads the face model on start (`start_period` is 180 s). `ENABLE_FORENSIC_SEARCH=false` skips it, but then photo enrollment returns 503.
- **Tests pass locally but fail in CI** (this happened once): a local `.env` supplied a variable. See 3.7.
- **`sqlalchemy>=2.1`**: `postgresql://` switches to the psycopg3 driver, which is not installed. Keep `<2.1` until the driver is changed.
- **Topology edges disappear** after a backend restart (R5).
- **The smoke test leaves a camera row** named `smoke-<time>`.
- On Windows with `core.autocrlf=true`, files in the working tree show Windows line endings. Edit scripts must handle that (H7).

### 10.2 Cameras and the NVR (what cost the most time)
- **NVR channel labels are not the channel numbers.** The name printed on the video can be off by one from the `channel=` number in the RTSP URL
  (the picture labelled "Channel4" was channel 5). Look at a frame of each channel before naming cameras.
- **Vendor client relay (KVMS Pro Lite) ports change.** When the NVR was reached through a relay on `127.0.0.1` the RTSP port changed every time the
  client was relaunched, and the relay only answered after the client was fully restarted and the NVR's web view opened. Symptoms: ports accept a connection
  but reset it, and `capture not opened` repeats in the edge log. Update `DVR_RTSP_PORT` and restart the edge. A VPN to the recorder's real address
  would be more reliable.
- **Test a stream outside the project first** (VLC). If VLC cannot play it, the project cannot either.
- NVRs often limit simultaneous streams. Use the sub-stream (`subtype=1`) unless you need the main stream for faces (R1).
- Check the NVR clock (NTP). Evidence and exports depend on it (R4).

### 10.3 Performance on a laptop
Reference machine: Ryzen 7 8845HS, 16 GB RAM, no GPU used. Three to four 720p sub-streams with `-r 480 --tier fast --frame-skip 3` ran at 8-9 analysed
frames per second per camera, about 50-66% total CPU, with the edge process around 440 MB. Free memory was the tight resource (the Compose stack and a browser
use most of it).

---

## 11. Field notes from the proof of concept

- **Setup used:** an NVR with several IP cameras, viewed through the vendor's Windows client, read over RTSP on the same laptop that ran the stack.
- **Cameras:** `lane` (street, NVR channel 1), `reception` (channel 4), `staff-room` (channel 5), `lab` (channel 8). Intended walking order: lane -> reception -> staff-room.
  Cameras are mounted high with wide-angle lenses, so faces are small and often side-on or from above.
- **Recorded clip:** a one-hour 1080p/25 fps clip imported in 247 s (7,502 frames at 2 fps, motion gating on) and produced 42 detections grouped into 8 "persons" (plus 22
  single-sighting "transients"). The user identified all but one of those 8 as the same person (R3).
- **Live run:** the stack and three to four cameras ran for several hours, camera registration, health and the live feed worked, and **no face was recorded** because
  of the face-size limits (R1). A direct run of the face finder on the full 1080p frames found faces only on the lab camera.
- **Enrollment** from camera crops was prepared (a helper script that captures the clearest face for a few seconds and uploads the crops to `POST /api/profiles`)
  but no one was enrolled before hand-over. That helper is not in this repository; a version with the same idea would be a sensible addition (backend photo enrollment
  needs a *large* face, so crop the face from the frame before uploading).

---

## 12. Repository history and older documents

**History.** This repository was created from the original so that the original stays untouched. The history was rewritten with `git filter-repo`
before the first push: credentials found in any commit were replaced by `***REMOVED***`, and committed biometric and local-data files (enrolled face images, face-vector
files, databases, an env backup, build artefacts) were removed from history. Consequences:
- Commit hashes differ from the original repository, so branches here cannot be merged into it directly. To contribute back, export patches (`git format-patch`).
- The original repository still contains all of that material.
- All original authors are preserved. The code at the tip of each fix branch is exactly what was tested.

**Older documents in `docs/` and the repo root** describe the original design and may be out of date. Known examples: `README.md` (architecture section) and
`GET_STARTED.md` mention `colab_detection_service.py`, and `GET_STARTED.md` and `docs/TECHNICAL_ANALYSIS.md` mention `review_pending.py`; neither file exists.
`DEPLOY_JARVIS_VERCEL.md` describes a hosted Render/Vercel/Supabase/JarvisLabs path that was not exercised. `docs/QUICKSTART.md` and
`docs/DEPLOYMENT_GUIDE.md` were not reviewed in this work and probably predate the Compose changes. The design notes (`docs/adaptive_quality_pipeline.md`,
`track_identity_fusion.md`, `idempotent-ingestion.md`, `integrity-model.md`, `provenance-tracking.md`, `runtime-controller.md`, `runtime-sync.md`,
`version-auditability.md`, `DETERMINISTIC_EVENT_ID.md`) explain intent and are the best starting point for understanding the edge pipeline, but verify them against the code.
One claim to treat carefully: the "tamper-evident" hash chain in `facial_recognition/integrity.py` is an unkeyed SHA-256 chain that is only verified inside the edge's
local ledger, never by the backend, so it is not tamper-proof against someone with write access.
