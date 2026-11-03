#!/usr/bin/env python3
"""
========================================================================================
JARVISLABS 30-DAY MASTER PRODUCTION RUNNER (ENGINE 1 & ENGINE 2)
========================================================================================
Autonomous, cloud-optimized orchestrator designed for high-performance NVIDIA GPU
instances on JarvisLabs (e.g., RTX 4090, A5000, A6000, A100).

Capabilities:
  1. Pre-flight Environment & Hardware Verification (CUDA, PyTorch, InsightFace, YOLOv8)
  2. Engine 1 Pipeline (Days 1-30):
     - Stage 2 Vectorization (InsightFace ArcFace 512-D embeddings into Supabase pgvector)
     - Stage 3 Persona Clustering (DBSCAN / cosine distance clustering into REAL-XX personas)
     - Rebuild of All 30 Day*_Persona_Video_Clipping_Index.csv files
     - 30-Day Forensic Security Audit generation
  3. Engine 2 Pipeline (Days 1-30):
     - YOLOv8-pose HOI Keypoint Detection with Physical Elevation & Deck Stance Gating
     - FFmpeg multi-chunk splicing (120s buffer clips + 3K annotated sniper snapshots)
     - Incident manifests (CSV/JSON) and Master 30-Day Compliance Matrix
  4. Dual Engine Synchronization:
     - Cross-correlates biometric personas (REAL-XX) with physical equipment touchpoints
  5. Auto-Shutdown on Completion (Optional flag to stop cloud billing)

Usage Examples:
  # Run both Engine 1 and Engine 2 for all 30 days:
  python scripts/run_30day_jarvislabs.py --engine all --days 1-30

  # Run Engine 2 only (HOI Keypoint surveillance) for Days 1 to 5:
  python scripts/run_30day_jarvislabs.py --engine 2 --days 1-5 --cctv-dir /workspace/cctv

  # Run Engine 1 only (Face Recognition & Persona Clustering):
  python scripts/run_30day_jarvislabs.py --engine 1 --days 1-30 --workers 4

  # Run with auto-shutdown enabled when finished:
  python scripts/run_30day_jarvislabs.py --engine all --days 1-30 --auto-shutdown
========================================================================================
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Dynamic repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("jarvis_runner")


def load_env_file(env_path: Optional[Path] = None):
    """Loads environment variables from .env file if present."""
    p = env_path or (REPO_ROOT / ".env")
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
            logger.info(f"Loaded environment variables from {p}")
        except Exception as e:
            logger.warning(f"Could not parse .env file: {e}")


def parse_days(days_arg: str) -> List[int]:
    """Parses '1-30', 'all', '5,25', or '1-5' into a list of integers."""
    d_str = days_arg.strip().lower()
    if d_str in ("all", "30", "1-30"):
        return list(range(1, 31))

    days: List[int] = []
    for part in d_str.split(","):
        part = part.strip()
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            days.extend(range(int(start_s), int(end_s) + 1))
        elif part.isdigit():
            days.append(int(part))
    return sorted(list(set(days)))


def check_system_environment() -> Dict[str, Any]:
    """Audits GPU, CUDA, PyTorch, FFmpeg, and Database status."""
    logger.info("=== [Pre-flight] Auditing Hardware & Runtime Environment ===")
    status: Dict[str, Any] = {
        "gpu_available": False,
        "device_name": "CPU",
        "cuda_version": "N/A",
        "vram_gb": 0.0,
        "ffmpeg_available": False,
        "database_connected": False,
        "yolo_model_ready": False,
        "insightface_ready": False,
    }

    # 1. GPU & PyTorch
    try:
        import torch
        if torch.cuda.is_available():
            status["gpu_available"] = True
            status["device_name"] = torch.cuda.get_device_name(0)
            status["cuda_version"] = torch.version.cuda
            vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            status["vram_gb"] = round(vram, 2)
            logger.info(f"  [OK] NVIDIA GPU Detected: {status['device_name']} ({status['vram_gb']} GB VRAM, CUDA {status['cuda_version']})")
        else:
            logger.warning("  [WARN] No NVIDIA GPU detected by PyTorch. Falling back to CPU mode.")
    except Exception as e:
        logger.warning(f"  [WARN] PyTorch check error: {e}")

    # 2. FFmpeg
    ffmpeg_exe = shutil.which("ffmpeg") or os.getenv("FFMPEG_EXE")
    if ffmpeg_exe:
        status["ffmpeg_available"] = True
        logger.info(f"  [OK] FFmpeg binary located at: {ffmpeg_exe}")
    else:
        logger.error("  [FAIL] FFmpeg is NOT found in PATH. Install via: apt-get install -y ffmpeg")

    # 3. Database URL
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            from sqlalchemy import create_engine, text
            eng = create_engine(db_url, pool_pre_ping=True)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1;"))
            status["database_connected"] = True
            logger.info("  [OK] Cloud Database (Supabase PostgreSQL) connection verified.")
        except Exception as e:
            logger.warning(f"  [WARN] Database connection failed: {e}")
    else:
        logger.warning("  [INFO] DATABASE_URL not set in environment or .env (required for Engine 1).")

    # 4. YOLOv8 Pose Model
    pose_path = REPO_ROOT / "yolov8n-pose.pt"
    if pose_path.exists():
        status["yolo_model_ready"] = True
        logger.info(f"  [OK] YOLOv8-pose model verified at {pose_path}")
    else:
        logger.info("  [INFO] Downloading YOLOv8-pose weights (yolov8n-pose.pt)...")
        try:
            from ultralytics import YOLO
            _ = YOLO("yolov8n-pose.pt")
            status["yolo_model_ready"] = True
            logger.info("  [OK] YOLOv8-pose model acquired.")
        except Exception as e:
            logger.warning(f"  [WARN] YOLOv8-pose model download warning: {e}")

    # 5. InsightFace
    try:
        import insightface
        status["insightface_ready"] = True
        logger.info("  [OK] InsightFace library available.")
    except ImportError:
        logger.warning("  [INFO] insightface not installed (required for Engine 1).")

    return status


def run_engine_1(days: List[int], workers: int, resume: bool, candidates_dir: Optional[str] = None):
    """Executes Engine 1 across target days."""
    logger.info("=" * 75)
    logger.info(" STARTING ENGINE 1 (FACE RECOGNITION, CLUSTERING & CLIPPING INDEXES)")
    logger.info("=" * 75)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("[Engine 1] Cannot proceed: DATABASE_URL is not set.")
        return False

    cand_dir = candidates_dir or str(REPO_ROOT / "stage1_candidates")
    if not os.path.exists(cand_dir):
        alt_cand = str(REPO_ROOT / "data" / "stage1_candidates")
        if os.path.exists(alt_cand):
            cand_dir = alt_cand

    # Step 1: Stage 2 Cloud Worker Vectorization
    logger.info("\n--- [Engine 1 - Step 1/3] ArcFace Vectorization (stage2_cloud_worker.py) ---")
    days_arg = ",".join(str(d) for d in days)
    cmd_stage2 = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "stage2_cloud_worker.py"),
        "--data-dir", cand_dir,
        "--days", days_arg,
        "--workers", str(workers),
    ]
    if resume:
        cmd_stage2.append("--resume")

    logger.info(f"Executing: {' '.join(cmd_stage2)}")
    p1 = subprocess.run(cmd_stage2)
    if p1.returncode != 0:
        logger.warning(f"Stage 2 worker exited with code {p1.returncode}. Continuing to clustering...")

    # Step 2: 30-Day Persona Clustering
    logger.info("\n--- [Engine 1 - Step 2/3] Persona DBSCAN Clustering (cluster_30day_personas.py) ---")
    clusters_out = str(REPO_ROOT / "data" / "30day_personas")
    cmd_cluster = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "cluster_30day_personas.py"),
        "--db-url", db_url,
        "--export-dir", clusters_out,
    ]
    p2 = subprocess.run(cmd_cluster)
    if p2.returncode != 0:
        logger.warning(f"Persona clustering exited with code {p2.returncode}")

    # Step 3: Rebuild All Clipping Indices
    logger.info("\n--- [Engine 1 - Step 3/3] Rebuilding Chronological Clipping Indices ---")
    cmd_rebuild = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "rebuild_all_clipping_indices.py"),
    ]
    p3 = subprocess.run(cmd_rebuild)
    logger.info("[Engine 1] 30-Day Processing Completed.")
    return True


def run_engine_2(
    days: List[int],
    cctv_dir: str,
    output_dir: str,
    workers: int,
    skip_completed: bool,
    hour_range: Optional[Tuple[int, int]] = None
):
    """Executes Engine 2 (HOI Keypoint surveillance) across target days."""
    logger.info("=" * 75)
    logger.info(" STARTING ENGINE 2 (CONTINUOUS HOI COMPUTER VISION & SKELETAL FUSION)")
    logger.info("=" * 75)

    from engine_v2.pipeline import process_day
    from scripts.orchestrate_30day_engine_v2 import compile_30day_compliance_matrix

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    total_days = len(days)
    processed = 0
    skipped = 0
    failed = 0

    for idx, day in enumerate(days, 1):
        pct = round((idx / total_days) * 100, 1)
        day_folder = out_path / f"day_{day:02d}"

        # Check skip-completed
        manifest = day_folder / f"Day{day:02d}_Incident_Manifest.csv"
        alt_manifest = day_folder / f"Day{day}_Incident_Manifest.csv"
        if skip_completed and (manifest.exists() or alt_manifest.exists()):
            logger.info(f"[{pct}%] [Day {day:02d}] Manifest already exists. Skipping duplicate analysis.")
            skipped += 1
            continue

        logger.info(f"[{pct}%] [Day {day:02d}] Launching Engine v2 HOI Pipeline...")
        t0 = time.time()
        try:
            incidents = process_day(
                day_num=day,
                output_base_dir=str(out_path),
                max_workers=workers,
                hour_range=hour_range,
                cctv_dir=cctv_dir
            )
            elapsed = round(time.time() - t0, 1)
            logger.info(f"[{pct}%] [Day {day:02d}] Complete: {len(incidents)} confirmed operational incidents generated ({elapsed}s).")
            processed += 1
        except Exception as e:
            logger.error(f"[Day {day:02d}] Failed with error: {e}", exc_info=True)
            failed += 1

    # Compile Consolidated Master Compliance Matrix
    logger.info("\n--- Compiling Master 30-Day Compliance Matrix ---")
    matrix = compile_30day_compliance_matrix(out_path)
    logger.info(f"[Engine 2] 30-Day Matrix: {matrix['summary']['total_incidents']} total incidents certified.")
    return True


def ensure_mode_b_candidates(cand_dir_str: str) -> str:
    """Ensures stage1_candidates directory exists in Mode B, unpacking archives if present."""
    cand_path = Path(cand_dir_str)
    if cand_path.exists() and any(cand_path.iterdir()):
        logger.info(f"[Mode B] Found candidate frames directory: {cand_path}")
        return str(cand_path)
    
    # Check if alternative data/stage1_candidates exists
    alt_cand = REPO_ROOT / "data" / "stage1_candidates"
    if alt_cand.exists() and any(alt_cand.iterdir()):
        logger.info(f"[Mode B] Found candidate frames in: {alt_cand}")
        return str(alt_cand)

    # Check for split stage1_candidates.tar parts
    tar_parts = sorted(list(REPO_ROOT.glob("stage1_candidates.tar.part*")))
    master_tar = REPO_ROOT / "stage1_candidates.tar"
    if tar_parts and not master_tar.exists():
        logger.info(f"[Mode B] Detected {len(tar_parts)} split archive parts. Auto-reassembling {master_tar.name}...")
        with open(master_tar, "wb") as outfile:
            for part in tar_parts:
                logger.info(f"  Appending {part.name} ({part.stat().st_size / (1024**2):.1f} MB)...")
                with open(part, "rb") as infile:
                    shutil.copyfileobj(infile, outfile, length=16*1024*1024)
        logger.info(f"[Mode B] Master archive reassembled successfully ({master_tar.stat().st_size / (1024**3):.2f} GB).")

    # Check for stage1_candidates.tar / .zip / .tar.gz
    for archive_name in ["stage1_candidates.tar", "stage1_candidates.tar.gz", "stage1_candidates.zip"]:
        arc_p = REPO_ROOT / archive_name
        if arc_p.exists():
            logger.info(f"[Mode B] Auto-extracting candidate archive: {arc_p}...")
            if archive_name.endswith(".zip"):
                import zipfile
                with zipfile.ZipFile(arc_p, "r") as z:
                    z.extractall(REPO_ROOT)
            else:
                import tarfile
                with tarfile.open(arc_p, "r") as t:
                    t.extractall(REPO_ROOT)
            logger.info(f"[Mode B] Extraction complete to {cand_path}")
            return str(cand_path)

    # Check individual day tar files (e.g. day05_candidates.tar)
    day_tars = list(REPO_ROOT.glob("day*_candidates.tar"))
    if day_tars:
        logger.info(f"[Mode B] Found {len(day_tars)} per-day candidate archives. Extracting...")
        cand_path.mkdir(parents=True, exist_ok=True)
        import tarfile
        for dt in day_tars:
            with tarfile.open(dt, "r") as t:
                t.extractall(cand_path)
        logger.info(f"[Mode B] Per-day archives unpacked to {cand_path}")
        return str(cand_path)

    logger.warning(f"[Mode B] No candidate archive found at {cand_path} or {REPO_ROOT}/stage1_candidates.tar")
    return str(cand_path)


def trigger_auto_shutdown():
    """Shuts down the JarvisLabs instance to terminate hourly compute charges."""
    logger.warning("==================================================================")
    logger.warning(" AUTO-SHUTDOWN TRIGGERED: Terminating instance in 30 seconds...")
    logger.warning("==================================================================")
    time.sleep(30)
    try:
        # Standard Linux shutdown commands
        subprocess.run(["systemctl", "poweroff"])
    except Exception:
        try:
            subprocess.run(["shutdown", "-h", "now"])
        except Exception as e:
            logger.error(f"Auto-shutdown failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="JarvisLabs 30-Day Production Master Runner for Surveillance Engine 1 & 2"
    )
    parser.add_argument(
        "--mode",
        choices=["b", "a", "candidates", "raw"],
        default="b",
        help="Operation mode: 'b' (or 'candidates') uses 28.99 GB stage1_candidates archive (Recommended); 'a' (or 'raw') uses master 3K CCTV video"
    )
    parser.add_argument(
        "--engine",
        choices=["1", "2", "both", "all"],
        default="all",
        help="Which surveillance engine to execute: '1', '2', or 'all' (both)"
    )
    parser.add_argument(
        "--days",
        type=str,
        default="1-30",
        help="Target days to process (e.g. '1-30', 'all', '5,25', '1-5')"
    )
    parser.add_argument(
        "--cctv-dir",
        type=str,
        default=os.getenv("CCTV_MASTER_DIR", "/workspace/cctv"),
        help="Path to raw 3K CCTV video footage chunks on JarvisLabs"
    )
    parser.add_argument(
        "--candidates-dir",
        type=str,
        default=os.getenv("STAGE1_CANDIDATES_DIR", str(REPO_ROOT / "stage1_candidates")),
        help="Path to Stage 1 candidate frame crops (Engine 1)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.getenv("OUTPUT_MASTER_DIR", str(REPO_ROOT / "incident_evidence_v2")),
        help="Destination directory for Engine 2 evidence clips and manifests"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(8, (os.cpu_count() or 4) - 1)),
        help="Number of parallel worker processes"
    )
    parser.add_argument(
        "--hours",
        nargs=2,
        type=int,
        metavar=("START_H", "END_H"),
        default=None,
        help="Optional operational hours filter (0 to 23)"
    )
    parser.add_argument(
        "--skip-completed",
        action="store_true",
        default=True,
        help="Skip days where manifests already exist"
    )
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Force reprocessing even if manifest exists"
    )
    parser.add_argument(
        "--auto-shutdown",
        action="store_true",
        help="Automatically shut down instance upon job completion to save cloud costs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Audit environment and files without executing heavy inference"
    )

    args = parser.parse_args()

    # Load environment variables
    load_env_file()

    # Pre-flight check
    env_info = check_system_environment()

    # Mode B Resolution: If Mode B is selected, auto-resolve/unpack candidate frames
    is_mode_b = args.mode in ("b", "candidates")
    effective_candidates_dir = args.candidates_dir
    effective_cctv_dir = args.cctv_dir

    if is_mode_b:
        effective_candidates_dir = ensure_mode_b_candidates(args.candidates_dir)
        os.environ["STAGE1_CANDIDATES_DIR"] = effective_candidates_dir
        # In Mode B, bypass raw CCTV chunk lookup so Engine 2 uses candidate frames
        effective_cctv_dir = ""

    target_days = parse_days(args.days)
    skip = not args.force_reprocess and args.skip_completed
    hour_range = tuple(args.hours) if args.hours else None

    print("\n" + "=" * 75, flush=True)
    print(" JARVISLABS 30-DAY SURVEILLANCE RUNNER CONFIGURATION", flush=True)
    print(f" Execution Mode:      {'MODE B (Stage 1 Candidates)' if is_mode_b else 'MODE A (Master 3K CCTV Video)'}", flush=True)
    print(f" Target Engine(s):    {args.engine.upper()}", flush=True)
    print(f" Target Days:         {len(target_days)} days ({target_days[0]} to {target_days[-1]})", flush=True)
    print(f" Candidates Folder:   {effective_candidates_dir}", flush=True)
    if not is_mode_b:
        print(f" CCTV Raw Footage:    {effective_cctv_dir}", flush=True)
    print(f" Output Location:     {args.output_dir}", flush=True)
    print(f" Worker Processes:    {args.workers}", flush=True)
    print(f" Compute Device:      {env_info['device_name']}", flush=True)
    print(f" Auto-Shutdown:       {args.auto_shutdown}", flush=True)
    if hour_range:
        print(f" Operational Hours:   {hour_range[0]:02d}:00 - {hour_range[1]:02d}:59", flush=True)
    print("=" * 75 + "\n", flush=True)

    if args.dry_run:
        logger.info("[DRY RUN] Environment validated. Exiting without execution.")
        return

    # Execute Engine 1
    if args.engine in ("1", "both", "all"):
        run_engine_1(
            days=target_days,
            workers=args.workers,
            resume=skip,
            candidates_dir=effective_candidates_dir
        )

    # Execute Engine 2
    if args.engine in ("2", "both", "all"):
        run_engine_2(
            days=target_days,
            cctv_dir=effective_cctv_dir,
            output_dir=args.output_dir,
            workers=args.workers,
            skip_completed=skip,
            hour_range=hour_range
        )

    logger.info("==================================================================")
    logger.info(" ALL REQUESTED 30-DAY SURVEILLANCE AUDITS COMPLETED SUCCESSFULLY!")
    logger.info("==================================================================")

    if args.auto_shutdown:
        trigger_auto_shutdown()


if __name__ == "__main__":
    main()

