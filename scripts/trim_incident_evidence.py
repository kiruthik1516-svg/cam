"""Lossless 3K MP4 Evidence Video Trimmer.

Uses FFmpeg in stream copy mode (-c copy) to extract precise incident clips
from raw master surveillance footage without re-encoding or quality loss.
"""

import argparse
from pathlib import Path
import subprocess


def find_clip_file(master_root, clip_name):
    root_path = Path(master_root)
    if not root_path.exists():
        return None

    # Search directly in day subdirectories 1..30
    for day_dir in root_path.iterdir():
        if day_dir.is_dir():
            target = day_dir / clip_name
            if target.exists():
                return target
    return None


def trim_evidence_clip(
    master_root,
    clip_name,
    start_offset_sec,
    duration_sec,
    output_path,
):
    clip_file = find_clip_file(master_root, clip_name)
    if not clip_file:
        print(f"ERROR: Source clip '{clip_name}' not found under {master_root}")
        return False

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(max(0.0, start_offset_sec)),
        "-i",
        str(clip_file),
        "-t",
        str(duration_sec),
        "-c",
        "copy",
        "-avoid_negative_ts",
        "make_zero",
        str(out_file),
    ]

    print(
        f"Trimming lossless 3K evidence: {clip_file.name} [{start_offset_sec}s -> +{duration_sec}s]"
    )
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0 and out_file.exists():
        size_mb = out_file.stat().st_size / 1024 / 1024
        print(f"[OK] Lossless clip saved: {out_file} ({size_mb:.2f} MB)")
        return True
    else:
        print(f"ERROR trimming clip: {res.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Lossless 3K Evidence Video Trimmer")
    parser.add_argument(
        "--master-root",
        type=str,
        default="E:/RO WATER SEP",
        help="Path to raw master footage drive",
    )
    parser.add_argument(
        "--clip",
        type=str,
        required=True,
        help="Clip filename (e.g. 56_8_DBGT_IPC56_...mp4)",
    )
    parser.add_argument(
        "--start-sec",
        type=float,
        default=0.0,
        help="Start offset in seconds within clip",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Duration of evidence clip in seconds",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./data/evidence_clips/incident.mp4",
        help="Output MP4 file path",
    )
    args = parser.parse_args()

    trim_evidence_clip(
        master_root=args.master_root,
        clip_name=args.clip,
        start_offset_sec=args.start_sec,
        duration_sec=args.duration,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
