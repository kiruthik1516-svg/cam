"""
Engine v2: Continuous HOI Computer Vision Incident Engine.
Standalone CLI Entrypoint. Keeps all legacy systems completely untouched.
"""
import argparse
import sys
import os

from .pipeline import process_day
from .config import OUTPUT_MASTER_DIR

def main():
    parser = argparse.ArgumentParser(
        description="Engine v2: Failproof Human-Object Interaction Incident Surveillance Engine."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--day", type=int, help="Target day number to process (1 to 30)")
    group.add_argument("--all-days", action="store_true", help="Process all 30 days in sequence")
    group.add_argument("--range", nargs=2, type=int, metavar=("START", "END"), help="Process range of days [START, END]")

    parser.add_argument("--output-dir", type=str, default=OUTPUT_MASTER_DIR, help="Base directory for v2 outputs")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--hours", nargs=2, type=int, metavar=("START_H", "END_H"), default=None, help="Optional hour filter (0 to 23)")

    args = parser.parse_args()

    print("=" * 70, flush=True)
    print(" ENGINE v2: STANDALONE HOI COMPUTER VISION INCIDENT SYSTEM", flush=True)
    print(" Architecture: YOLOv8-Pose + Multi-Zone Spatial Envelope + FFmpeg Splicing", flush=True)
    print(f" Output Location: {args.output_dir}", flush=True)
    if args.hours:
        print(f" Hour Filter: {args.hours[0]:02d}:00 to {args.hours[1]:02d}:59", flush=True)
    print("=" * 70, flush=True)

    if args.day:
        days = [args.day]
    elif args.range:
        days = list(range(args.range[0], args.range[1] + 1))
    elif args.all_days:
        days = list(range(1, 31))
    else:
        days = []

    hour_range = tuple(args.hours) if args.hours else None

    for d in days:
        print(f"\n>>> Starting Processing for Day {d}...", flush=True)
        try:
            incidents = process_day(d, output_base_dir=args.output_dir, max_workers=args.workers, hour_range=hour_range)
            print(f">>> Day {d} finished with {len(incidents)} confirmed incident clips.", flush=True)
        except Exception as e:
            print(f"[ERROR] Failed to process Day {d}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
