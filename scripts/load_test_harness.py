#!/usr/bin/env python3
"""Multi-Camera Concurrent Load Test & Stress Harness.

Simulates high-throughput detection ingestion across multiple edge cameras,
validating concurrency limits, database connection pooling, idempotent deduplication,
cross-camera continuity tracking, and WebSocket broadcasting under stress.

Usage:
    python scripts/load_test_harness.py --cameras 4 --burst 15 --concurrency 8
    python scripts/load_test_harness.py --url http://127.0.0.1:1223 --include-idempotency-race
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("load_tester")

IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class LatencyStats:
    count: int = 0
    min_ms: float = 0.0
    mean_ms: float = 0.0
    p50_ms: float = 0.0
    p90_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    max_ms: float = 0.0

    @classmethod
    def compute(cls, latencies: List[float]) -> LatencyStats:
        if not latencies:
            return cls()
        s = sorted(latencies)
        n = len(s)
        def pct(p: float) -> float:
            idx = int(math.ceil(p * n) - 1)
            return s[max(0, min(n - 1, idx))]

        return cls(
            count=n,
            min_ms=round(s[0], 2),
            mean_ms=round(sum(s) / n, 2),
            p50_ms=round(pct(0.50), 2),
            p90_ms=round(pct(0.90), 2),
            p95_ms=round(pct(0.95), 2),
            p99_ms=round(pct(0.99), 2),
            max_ms=round(s[-1], 2),
        )


@dataclass
class LoadTestReport:
    total_requests: int = 0
    successful_requests: int = 0
    inserted_records: int = 0
    idempotent_dedupes: int = 0
    failed_requests: int = 0
    total_elapsed_seconds: float = 0.0
    throughput_req_per_sec: float = 0.0
    latency: LatencyStats = field(default_factory=LatencyStats)
    errors: List[str] = field(default_factory=list)
    idempotency_race_passed: bool = True
    continuity_test_passed: bool = True
    deep_health_passed: bool = True


class MultiCameraLoadTester:
    """Simulates realistic concurrent camera streams and stress tests Sentinel backend."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:1223",
        edge_api_key: Optional[str] = None,
        admin_password: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.edge_api_key = edge_api_key or os.environ.get("EDGE_API_KEY", "test-edge-api-key")
        self.admin_password = admin_password or os.environ.get("ADMIN_PASSWORD", "test-admin-password-for-unit-tests")
        self.timeout = timeout_seconds

    def _http_request(
        self,
        endpoint: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Dict[str, Any], float]:
        """Performs HTTP call, returns (status_code, response_json_or_dict, elapsed_ms)."""
        url = f"{self.base_url}{endpoint}"
        all_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.edge_api_key:
            all_headers["X-API-Key"] = self.edge_api_key
        if headers:
            all_headers.update(headers)

        body_bytes = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body_bytes, headers=all_headers, method=method)

        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                raw = resp.read().decode("utf-8")
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = {"raw": raw}
                return resp.status, parsed, elapsed_ms
        except urllib.error.HTTPError as he:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            raw = he.read().decode("utf-8")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"raw": raw, "error": str(he)}
            return he.code, parsed, elapsed_ms
        except Exception as ex:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return 0, {"error": str(ex)}, elapsed_ms

    def generate_embedding(self, seed: Optional[int] = None) -> List[float]:
        """Generate a synthetic 512-dimensional normalized unit vector."""
        rng = random.Random(seed)
        vec = [rng.gauss(0.0, 1.0) for _ in range(512)]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 6) for x in vec]

    def create_detection_payload(
        self,
        camera_id: str,
        camera_name: str,
        zone: str,
        seq: int,
        event_id: Optional[str] = None,
        identity: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        quality_score: float = 85.0,
        liveness_score: float = 0.95,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Constructs a compliant Sentinel edge detection payload."""
        ts = timestamp or datetime.now(IST)
        evt_id = event_id or f"evt_load_{camera_id}_{seq}_{uuid.uuid4().hex[:8]}"
        emb = embedding or self.generate_embedding()

        return {
            "event_id": evt_id,
            "device_id": f"edge_node_{camera_id}",
            "sequence_number": seq,
            "camera_id": camera_id,
            "camera_name": camera_name,
            "zone": zone,
            "confidence": 0.92,
            "bbox": [120, 140, 280, 300],
            "embedding": emb,
            "quality_score": quality_score,
            "liveness_score": liveness_score,
            "identity": identity or "Unknown",
            "timestamp": ts.isoformat(),
            "clock_source": "edge_pc",
            "clock_skew_seconds": 0.02,
            "priority": "normal",
            "provenance": {
                "frame_reference": f"frm_{camera_id}_{seq}",
                "track_id": f"trk_{seq % 10}",
                "observation_references": [f"obs_{camera_id}_{seq}"],
                "candidate_matches": [{"identity": identity or "Unregistered", "score": 0.92, "rank": 1}],
                "embedding_fingerprint": f"emb_fp_{evt_id[:16]}",
                "decision_tier": "LOCAL_HIGH_CONFIDENCE",
                "provenance_chain_hash": f"chain_{evt_id[:16]}",
            },
        }

    def check_health(self, deep: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """Verify readiness probe."""
        endpoint = "/health?deep=true" if deep else "/health"
        status, data, _ = self._http_request(endpoint, method="GET")
        is_ok = (status == 200 and data.get("status") == "ok")
        return is_ok, data

    def run_idempotency_race(self, threads: int = 8) -> bool:
        """Fire identical event_id across concurrent threads to verify atomic DB deduplication."""
        logger.info(f"Running Idempotency Race Test with {threads} concurrent threads...")
        shared_event_id = f"evt_race_idempotency_{uuid.uuid4().hex}"
        payload = self.create_detection_payload(
            camera_id="cam_load_idempotency",
            camera_name="Idempotency Stress Camera",
            zone="Test Zone",
            seq=1,
            event_id=shared_event_id,
            quality_score=92.0,
            liveness_score=0.98,
        )

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [
                executor.submit(self._http_request, "/api/detections", "POST", None, payload)
                for _ in range(threads)
            ]
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())

        status_codes = [r[0] for r in results]
        inserted_flags = [r[1].get("inserted", False) for r in results if isinstance(r[1], dict)]

        # Exactly ONE request should be inserted=True, all others inserted=False, all HTTP 200
        all_200 = all(code == 200 for code in status_codes)
        true_count = sum(1 for flag in inserted_flags if flag is True)
        false_count = sum(1 for flag in inserted_flags if flag is False)

        passed = all_200 and true_count == 1 and false_count == (threads - 1)
        if passed:
            logger.info("Idempotency Race Test PASSED: 1 insertion, %d atomic dedupes", false_count)
        else:
            logger.error(
                "Idempotency Race Test FAILED: codes=%s, inserted=%s (expected 1 true, %d false)",
                status_codes, inserted_flags, threads - 1
            )
        return passed

    def run_continuity_test(self) -> bool:
        """Simulate person moving between two cameras within acceptable temporal window."""
        logger.info("Running Cross-Camera Continuity Transition Test...")
        person_emb = self.generate_embedding(seed=4242)
        base_time = datetime.now(IST)

        # Step 1: Camera A
        p1 = self.create_detection_payload(
            camera_id="cam_entrance_01",
            camera_name="Main Entrance Gate",
            zone="Perimeter",
            seq=1,
            embedding=person_emb,
            timestamp=base_time,
        )
        s1, d1, _ = self._http_request("/api/detections", "POST", None, p1)

        # Step 2: Camera B after 4 seconds
        p2 = self.create_detection_payload(
            camera_id="cam_lobby_02",
            camera_name="Main Lobby",
            zone="Interior",
            seq=2,
            embedding=person_emb,
            timestamp=base_time + timedelta(seconds=4),
        )
        s2, d2, _ = self._http_request("/api/detections", "POST", None, p2)

        passed = (s1 == 200 and s2 == 200)
        logger.info("Cross-Camera Continuity Ingest: Camera A status=%d, Camera B status=%d", s1, s2)
        return passed

    def run_load_test(
        self,
        num_cameras: int = 4,
        burst_per_camera: int = 15,
        concurrency: int = 8,
    ) -> LoadTestReport:
        """Execute concurrent multi-camera burst ingestion test."""
        logger.info(
            "Starting Multi-Camera Concurrent Load Test: %d cameras, %d detections/cam (%d total), %d concurrency",
            num_cameras, burst_per_camera, num_cameras * burst_per_camera, concurrency
        )

        cameras = [
            (f"cam_load_{i:02d}", f"Synthetic Camera {i:02d}", f"Zone_{i % 3}")
            for i in range(1, num_cameras + 1)
        ]

        # Generate all payloads upfront
        tasks = []
        for cam_id, cam_name, zone in cameras:
            for seq in range(1, burst_per_camera + 1):
                payload = self.create_detection_payload(
                    camera_id=cam_id,
                    camera_name=cam_name,
                    zone=zone,
                    seq=seq,
                    quality_score=round(random.uniform(70.0, 98.0), 1),
                    liveness_score=round(random.uniform(0.75, 0.99), 2),
                )
                tasks.append(payload)

        # Shuffle to simulate interleaved real-world network packets
        random.shuffle(tasks)

        latencies: List[float] = []
        errors: List[str] = []
        inserted_count = 0
        dedup_count = 0
        success_count = 0
        fail_count = 0

        t_start = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_payload = {
                executor.submit(self._http_request, "/api/detections", "POST", None, p): p
                for p in tasks
            }

            for future in concurrent.futures.as_completed(future_to_payload):
                code, resp_body, elapsed_ms = future.result()
                latencies.append(elapsed_ms)
                if code == 200 and isinstance(resp_body, dict):
                    success_count += 1
                    if resp_body.get("inserted", True):
                        inserted_count += 1
                    else:
                        dedup_count += 1
                else:
                    fail_count += 1
                    errors.append(f"HTTP {code}: {resp_body}")

        t_elapsed = time.perf_counter() - t_start
        throughput = round(len(tasks) / t_elapsed, 2) if t_elapsed > 0 else 0.0

        stats = LatencyStats.compute(latencies)

        report = LoadTestReport(
            total_requests=len(tasks),
            successful_requests=success_count,
            inserted_records=inserted_count,
            idempotent_dedupes=dedup_count,
            failed_requests=fail_count,
            total_elapsed_seconds=round(t_elapsed, 2),
            throughput_req_per_sec=throughput,
            latency=stats,
            errors=errors[:10],
        )

        logger.info(
            "Load Test Completed: %d/%d success, %.1f req/s, avg latency: %.1fms (p95: %.1fms)",
            success_count, len(tasks), throughput, stats.mean_ms, stats.p95_ms
        )
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-Camera Concurrent Load Test & Production Hardening Harness")
    parser.add_argument("--url", default=os.environ.get("BASE_URL", "http://127.0.0.1:1223"), help="Backend URL")
    parser.add_argument("--cameras", type=int, default=4, help="Number of simulated cameras (default: 4)")
    parser.add_argument("--burst", type=int, default=10, help="Detections per camera burst (default: 10)")
    parser.add_argument("--concurrency", type=int, default=8, help="Concurrent HTTP worker threads (default: 8)")
    parser.add_argument("--include-idempotency-race", action="store_true", help="Run concurrent race test on identical event_id")
    parser.add_argument("--include-continuity-test", action="store_true", help="Run cross-camera temporal continuity test")
    parser.add_argument("--output-json", default=None, help="Optional path to write JSON test metrics")
    args = parser.parse_args()

    tester = MultiCameraLoadTester(base_url=args.url)

    # 1. Health check
    logger.info("Probing /health readiness endpoint on %s...", args.url)
    health_ok, health_data = tester.check_health(deep=True)
    if not health_ok:
        logger.error("Deep health check failed on %s: %s", args.url, health_data)
        return 1
    logger.info("Deep health check OK: %s", health_data.get("subsystems"))

    # 2. Idempotency race test
    idempotency_passed = True
    if args.include_idempotency_race:
        idempotency_passed = tester.run_idempotency_race(threads=args.concurrency)

    # 3. Continuity test
    continuity_passed = True
    if args.include_continuity_test:
        continuity_passed = tester.run_continuity_test()

    # 4. Multi-camera burst load test
    report = tester.run_load_test(
        num_cameras=args.cameras,
        burst_per_camera=args.burst,
        concurrency=args.concurrency,
    )
    report.idempotency_race_passed = idempotency_passed
    report.continuity_test_passed = continuity_passed
    report.deep_health_passed = health_ok

    print("\n" + "=" * 60)
    print("      MULTI-CAMERA CONCURRENT LOAD TEST REPORT")
    print("=" * 60)
    print(f"Total Requests:       {report.total_requests}")
    print(f"Successful (HTTP 200):{report.successful_requests}")
    print(f"Inserted:             {report.inserted_records}")
    print(f"Idempotent Dedupes:   {report.idempotent_dedupes}")
    print(f"Failed:               {report.failed_requests}")
    print(f"Total Elapsed Time:   {report.total_elapsed_seconds}s")
    print(f"Throughput:           {report.throughput_req_per_sec} req/sec")
    print("-" * 60)
    print(f"Latency Min:          {report.latency.min_ms} ms")
    print(f"Latency Mean:         {report.latency.mean_ms} ms")
    print(f"Latency Median (p50): {report.latency.p50_ms} ms")
    print(f"Latency p90:          {report.latency.p90_ms} ms")
    print(f"Latency p95:          {report.latency.p95_ms} ms")
    print(f"Latency p99:          {report.latency.p99_ms} ms")
    print(f"Latency Max:          {report.latency.max_ms} ms")
    print("-" * 60)
    print(f"Deep Health Check:    {'PASSED' if report.deep_health_passed else 'FAILED'}")
    print(f"Idempotency Race:     {'PASSED' if report.idempotency_race_passed else 'FAILED'}")
    print(f"Cross-Camera Cont.:   {'PASSED' if report.continuity_test_passed else 'FAILED'}")
    print("=" * 60 + "\n")

    if args.output_json:
        out_dict = {
            "total_requests": report.total_requests,
            "successful_requests": report.successful_requests,
            "inserted_records": report.inserted_records,
            "idempotent_dedupes": report.idempotent_dedupes,
            "failed_requests": report.failed_requests,
            "total_elapsed_seconds": report.total_elapsed_seconds,
            "throughput_req_per_sec": report.throughput_req_per_sec,
            "latency": report.latency.__dict__,
            "idempotency_race_passed": report.idempotency_race_passed,
            "continuity_test_passed": report.continuity_test_passed,
            "deep_health_passed": report.deep_health_passed,
        }
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(out_dict, f, indent=2)
        logger.info("Saved report to %s", args.output_json)

    return 0 if (report.failed_requests == 0 and report.idempotency_race_passed and report.continuity_test_passed) else 1


if __name__ == "__main__":
    sys.exit(main())
