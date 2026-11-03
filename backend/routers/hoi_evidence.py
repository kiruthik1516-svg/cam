"""HOI (Human-Object Interaction) Evidence & Video Streaming Router.

Provides API endpoints for:
1. Listing equipment incidents, operational sessions, and compound zone events detected by Engine v2.
2. High-performance RFC 7233 partial-content (HTTP 206) video streaming for 3K MP4 evidence clips,
   enabling HTML5 video players to seek, scrub, and buffer smoothly in web browsers.
3. Serving 17-keypoint skeletal sniper snapshots (.jpg).
4. Providing forensic manifests and forensic summary JSON data.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hoi", tags=["HOI Equipment Evidence"])

# Master evidence root directory
_DEFAULT_EVIDENCE_ROOT = Path(__file__).resolve().parent.parent.parent / "incident_evidence_v2"
EVIDENCE_ROOT = Path(os.getenv("OUTPUT_MASTER_DIR", str(_DEFAULT_EVIDENCE_ROOT))).resolve()


class HoiIncidentSummary(BaseModel):
    incident_id: str
    day: int
    start_time: str
    peak_time: str
    end_time: str
    duration_sec: float
    zone_id: str
    zone_name: str
    severity: str
    interaction_type: str
    active_hand: str
    min_wrist_distance_px: float
    track_id: str
    clip_filename: str
    snapshot_filename: str
    file_size_mb: Optional[float] = None
    video_url: str
    snapshot_url: str


def _parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    """Parse HTTP Range header into start and end byte offsets."""
    m = re.match(r"^bytes=(\d*)-(\d*)$", range_header.strip())
    if not m:
        return 0, file_size - 1

    start_str, end_str = m.groups()
    if start_str and end_str:
        start = int(start_str)
        end = min(int(end_str), file_size - 1)
    elif start_str:
        start = int(start_str)
        end = file_size - 1
    elif end_str:
        start = max(0, file_size - int(end_str))
        end = file_size - 1
    else:
        start = 0
        end = file_size - 1

    return max(0, start), min(end, file_size - 1)


def _file_chunk_generator(file_path: Path, start: int, length: int, chunk_size: int = 512 * 1024) -> Generator[bytes, None, None]:
    """Yield file chunks from a specified byte offset for range streaming."""
    with open(file_path, "rb") as f:
        f.seek(start)
        bytes_left = length
        while bytes_left > 0:
            read_size = min(chunk_size, bytes_left)
            chunk = f.read(read_size)
            if not chunk:
                break
            bytes_left -= len(chunk)
            yield chunk


@router.get("/evidence/incidents", response_model=List[HoiIncidentSummary])
def get_hoi_incidents(
    day: Optional[int] = Query(None, description="Optional day index (e.g. 25)"),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, SEVERE, ELEVATED)"),
    zone: Optional[str] = Query(None, description="Filter by zone ID (e.g. ZONE_SWITCH)")
):
    """List all detected equipment incidents and operational sessions across days."""
    if not EVIDENCE_ROOT.exists():
        return []

    # Clean default Query objects if invoked directly in python
    clean_day = day if isinstance(day, int) else None
    clean_severity = severity.strip().upper() if isinstance(severity, str) and severity.strip() else None
    clean_zone = zone.strip().upper() if isinstance(zone, str) and zone.strip() else None

    results: List[HoiIncidentSummary] = []
    
    # Identify target day folders
    if clean_day is not None:
        raw_candidates = [EVIDENCE_ROOT / f"day_{clean_day:02d}", EVIDENCE_ROOT / f"day_{clean_day}"]
        seen_paths = set()
        day_folders = []
        for d in raw_candidates:
            if d.exists() and d.resolve() not in seen_paths:
                seen_paths.add(d.resolve())
                day_folders.append(d)
    else:
        day_folders = sorted([d for d in EVIDENCE_ROOT.iterdir() if d.is_dir() and d.name.startswith("day_")])

    for d_folder in day_folders:
        manifest_files = list(d_folder.glob("*Incident_Manifest.csv"))
        if not manifest_files:
            continue
        
        manifest_path = manifest_files[0]
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Apply optional filters
                    row_sev = row.get("severity", "").strip().upper()
                    row_zone = row.get("zone_id", "").strip().upper()
                    if clean_severity and row_sev != clean_severity:
                        continue
                    if clean_zone and row_zone != clean_zone:
                        continue

                    clip_name = row.get("clip_filename", "")
                    snap_name = row.get("snapshot_filename", "")
                    clip_path = d_folder / clip_name
                    snap_path = d_folder / snap_name
                    
                    file_size_mb = round(clip_path.stat().st_size / (1024 * 1024), 1) if clip_path.exists() else None
                    day_val = int(row.get("day", 0))

                    results.append(HoiIncidentSummary(
                        incident_id=row.get("incident_id", ""),
                        day=day_val,
                        start_time=row.get("start_time", ""),
                        peak_time=row.get("peak_time", ""),
                        end_time=row.get("end_time", ""),
                        duration_sec=float(row.get("duration_sec", 0.0)),
                        zone_id=row.get("zone_id", ""),
                        zone_name=row.get("zone_name", ""),
                        severity=row.get("severity", "ELEVATED"),
                        interaction_type=row.get("interaction_type", "WRIST_CONTACT"),
                        active_hand=row.get("active_hand", "BOTH"),
                        min_wrist_distance_px=float(row.get("min_wrist_distance_px", 0.0)),
                        track_id=row.get("track_id", ""),
                        clip_filename=clip_name,
                        snapshot_filename=snap_name,
                        file_size_mb=file_size_mb,
                        video_url=f"/api/hoi/evidence/video/{day_val}/{clip_name}",
                        snapshot_url=f"/api/hoi/evidence/snapshot/{day_val}/{snap_name}" if snap_path.exists() else ""
                    ))
        except Exception as e:
            logger.warning(f"Failed to read manifest {manifest_path}: {e}")

    return results


@router.get("/evidence/video/{day}/{filename}")
def stream_hoi_video(day: int, filename: str, request: Request):
    """Stream 3K MP4 evidence clips with RFC 7233 byte-range support for browser HTML5 video scrubbing."""
    day_folders = [EVIDENCE_ROOT / f"day_{day:02d}", EVIDENCE_ROOT / f"day_{day}"]
    video_path = None
    for df in day_folders:
        candidate = df / filename
        if candidate.exists() and candidate.is_file():
            video_path = candidate
            break

    if not video_path:
        raise HTTPException(status_code=404, detail=f"Evidence video clip '{filename}' for Day {day} not found")

    file_size = video_path.stat().st_size
    range_header = request.headers.get("range")

    if not range_header:
        # Full content response
        headers = {
            "Content-Type": "video/mp4",
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
        }
        return StreamingResponse(
            _file_chunk_generator(video_path, 0, file_size),
            status_code=status.HTTP_200_OK,
            headers=headers
        )

    # Partial content (206) response
    start, end = _parse_range_header(range_header, file_size)
    if start >= file_size or start > end:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail=f"Requested range {range_header} not satisfiable for file size {file_size}"
        )

    content_length = (end - start) + 1
    headers = {
        "Content-Type": "video/mp4",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Content-Length": str(content_length),
        "Accept-Ranges": "bytes",
    }

    return StreamingResponse(
        _file_chunk_generator(video_path, start, content_length),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers
    )


@router.get("/evidence/snapshot/{day}/{filename}")
def get_hoi_snapshot(day: int, filename: str):
    """Serve the 17-keypoint sniper screenshot image."""
    day_folders = [EVIDENCE_ROOT / f"day_{day:02d}", EVIDENCE_ROOT / f"day_{day}"]
    snap_path = None
    for df in day_folders:
        candidate = df / filename
        if candidate.exists() and candidate.is_file():
            snap_path = candidate
            break

    if not snap_path:
        raise HTTPException(status_code=404, detail=f"Evidence snapshot '{filename}' for Day {day} not found")

    return FileResponse(snap_path, media_type="image/jpeg")


@router.get("/evidence/summary/{day}")
def get_hoi_day_summary(day: int):
    """Return the raw DayXX_Forensic_Summary.json audit summary."""
    day_folders = [EVIDENCE_ROOT / f"day_{day:02d}", EVIDENCE_ROOT / f"day_{day}"]
    summary_path = None
    for df in day_folders:
        cand = df / f"Day{day}_Forensic_Summary.json"
        if cand.exists():
            summary_path = cand
            break
        cand2 = df / f"Day{day:02d}_Forensic_Summary.json"
        if cand2.exists():
            summary_path = cand2
            break

    if not summary_path or not summary_path.exists():
        raise HTTPException(status_code=404, detail=f"Forensic summary JSON for Day {day} not found")

    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)
