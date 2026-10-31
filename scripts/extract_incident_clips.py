#!/usr/bin/env python3
"""
extract_incident_clips.py
Autonomous Multi-Chunk Lossless Incident Video Extractor with Post-Extraction Verification.
Direct drop-in replacement maintaining full compatibility with all command-line arguments.
"""

from extract_clean_incident_clips import extract_incident_clips
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract incident clips from raw CCTV footage")
    parser.add_argument("--raw-footage-root", default="E:/RO WATER SEP", help="Path to raw footage root directory")
    parser.add_argument("--target-day", type=int, default=None, help="Specific day to extract (1-30)")
    parser.add_argument("--force-reextract", action="store_true", help="Force re-extraction of clips")
    args = parser.parse_args()

    extract_incident_clips(
        raw_root=args.raw_footage_root,
        target_day=args.target_day,
        force_reextract=args.force_reextract
    )
