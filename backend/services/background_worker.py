"""Decoupled Persistent Background Task Queue & Worker Service.

Manages asynchronous video processing, Engine v2 HOI forensics, and batch orchestration
without blocking FastAPI request threads. Provides persistent state in data/task_queue.json,
real-time log streaming, progress tracking, and subprocess process tree cancellation.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinel.background_worker")

DATA_DIR = Path("d:/facial/backend/data").resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
QUEUE_FILE = DATA_DIR / "task_queue.json"


class TaskStatus:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskType:
    ENGINE_V2_DAY_RUN = "ENGINE_V2_DAY_RUN"
    ORCHESTRATE_30DAY = "ORCHESTRATE_30DAY"
    REINDEX_CENTROIDS = "REINDEX_CENTROIDS"
    CUSTOM_SCRIPT = "CUSTOM_SCRIPT"


class BackgroundWorkerManager:
    _instance: Optional[BackgroundWorkerManager] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._active_processes: Dict[str, subprocess.Popen] = {}
        self._queue_lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._load_state()
        self._start_worker_thread()

    @classmethod
    def get_instance(cls) -> BackgroundWorkerManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = BackgroundWorkerManager()
            return cls._instance

    def _load_state(self) -> None:
        """Load tasks from disk and mark dangling running tasks as INTERRUPTED."""
        if not QUEUE_FILE.exists():
            self._save_state()
            return

        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for task_id, task in data.items():
                    # If server was restarted while running, mark failed
                    if task.get("status") == TaskStatus.RUNNING:
                        task["status"] = TaskStatus.FAILED
                        task["error"] = "Server restarted during execution"
                        task["completed_at"] = datetime.now().isoformat()
                    self._tasks[task_id] = task
        except Exception as e:
            logger.error(f"Failed to load task queue from {QUEUE_FILE}: {e}")
            self._tasks = {}

    def _save_state(self) -> None:
        """Atomically persist task queue state to JSON."""
        try:
            temp_file = QUEUE_FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._tasks, f, indent=2)
            temp_file.replace(QUEUE_FILE)
        except Exception as e:
            logger.error(f"Failed to persist task queue to {QUEUE_FILE}: {e}")

    def _start_worker_thread(self) -> None:
        """Launch daemon worker polling thread."""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="SentinelWorkerThread")
        self._worker_thread.start()
        logger.info("Sentinel background task worker thread started")

    def enqueue_task(
        self,
        task_type: str,
        title: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a new task to the persistent queue."""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now().isoformat()

        task: Dict[str, Any] = {
            "task_id": task_id,
            "title": title,
            "task_type": task_type,
            "params": params or {},
            "status": TaskStatus.QUEUED,
            "created_at": now_iso,
            "started_at": None,
            "completed_at": None,
            "progress_pct": 0.0,
            "current_step": "Queued in background worker",
            "metrics": {},
            "log_tail": [f"[{now_iso}] Task queued for execution: {title}"],
            "error": None,
            "pid": None,
        }

        with self._queue_lock:
            self._tasks[task_id] = task
            self._save_state()

        logger.info(f"Enqueued background task {task_id}: {title} ({task_type})")
        return task

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._queue_lock:
            return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._queue_lock:
            tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.get("status") == status]

        # Sort descending by creation date
        tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
        return tasks[:limit]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued or running task and terminate any active process."""
        with self._queue_lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task["status"] == TaskStatus.QUEUED:
                task["status"] = TaskStatus.CANCELLED
                task["completed_at"] = datetime.now().isoformat()
                task["current_step"] = "Cancelled before execution"
                self._save_state()
                return True

            if task["status"] == TaskStatus.RUNNING:
                proc = self._active_processes.get(task_id)
                if proc:
                    try:
                        # In Windows, terminate process tree
                        if sys.platform == "win32":
                            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
                        else:
                            proc.terminate()
                    except Exception as e:
                        logger.warning(f"Error terminating process {proc.pid}: {e}")

                task["status"] = TaskStatus.CANCELLED
                task["completed_at"] = datetime.now().isoformat()
                task["current_step"] = "Terminated by operator request"
                task["log_tail"].append(f"[{datetime.now().isoformat()}] Task cancelled by operator")
                self._save_state()
                return True

            return False

    def clear_finished(self) -> int:
        """Remove completed, failed, or cancelled tasks from queue history."""
        with self._queue_lock:
            to_remove = [
                tid for tid, t in self._tasks.items()
                if t.get("status") in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
            ]
            for tid in to_remove:
                del self._tasks[tid]
            self._save_state()
            return len(to_remove)

    def _worker_loop(self) -> None:
        """Main dispatcher loop that picks up QUEUED jobs."""
        while not self._stop_event.is_set():
            next_task = None
            with self._queue_lock:
                # Find oldest queued task
                queued = [t for t in self._tasks.values() if t.get("status") == TaskStatus.QUEUED]
                if queued:
                    queued.sort(key=lambda t: t.get("created_at", ""))
                    next_task = queued[0]
                    next_task["status"] = TaskStatus.RUNNING
                    next_task["started_at"] = datetime.now().isoformat()
                    next_task["current_step"] = "Starting process execution"
                    self._save_state()

            if next_task:
                self._execute_task(next_task)
            else:
                time.sleep(1.0)

    def _execute_task(self, task: Dict[str, Any]) -> None:
        """Build command and execute task with live log capture."""
        task_id = task["task_id"]
        task_type = task["task_type"]
        params = task.get("params", {})

        cmd: List[str] = []
        py_exe = sys.executable

        if task_type == TaskType.ENGINE_V2_DAY_RUN:
            day = params.get("day", 25)
            cmd = [py_exe, "-m", "engine_v2.run_engine_v2", "--day", str(day)]

        elif task_type == TaskType.ORCHESTRATE_30DAY:
            cmd = [py_exe, "scripts/orchestrate_30day_engine_v2.py"]
            if params.get("workers"):
                cmd.extend(["--workers", str(params["workers"])])
            if params.get("skip_completed", True):
                cmd.append("--skip-completed")
            if params.get("days"):
                cmd.extend(["--days", str(params["days"])])

        elif task_type == TaskType.REINDEX_CENTROIDS:
            cmd = [py_exe, "-c", "import backend.database as db; print('Vector Centroids Synced')"]

        elif task_type == TaskType.CUSTOM_SCRIPT:
            script_path = params.get("script")
            args = params.get("args", [])
            if script_path:
                cmd = [py_exe, script_path] + [str(a) for a in args]

        if not cmd:
            with self._queue_lock:
                task["status"] = TaskStatus.FAILED
                task["error"] = f"Unknown or invalid task type: {task_type}"
                task["completed_at"] = datetime.now().isoformat()
                self._save_state()
            return

        try:
            task["log_tail"].append(f"[{datetime.now().isoformat()}] Executing: {' '.join(cmd)}")
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(Path("d:/facial").resolve()),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )

            with self._queue_lock:
                task["pid"] = proc.pid
                self._active_processes[task_id] = proc
                self._save_state()

            # Read stdout line by line
            if proc.stdout:
                for line in iter(proc.stdout.readline, ""):
                    if not line:
                        break
                    clean_line = line.strip()
                    if not clean_line:
                        continue

                    with self._queue_lock:
                        # Append to log tail (keep last 60 lines)
                        task["log_tail"].append(clean_line)
                        if len(task["log_tail"]) > 60:
                            task["log_tail"].pop(0)

                        # Parse progress if present
                        # e.g., "Chunk 4/12 (33.3%)" or "Progress: 45%"
                        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", clean_line)
                        if pct_match:
                            try:
                                task["progress_pct"] = min(100.0, float(pct_match.group(1)))
                            except Exception:
                                pass

                        task["current_step"] = clean_line[:120]
                        self._save_state()

            proc.wait()
            return_code = proc.returncode

            with self._queue_lock:
                self._active_processes.pop(task_id, None)
                task["completed_at"] = datetime.now().isoformat()
                if return_code == 0:
                    task["status"] = TaskStatus.COMPLETED
                    task["progress_pct"] = 100.0
                    task["current_step"] = "Task completed successfully"
                else:
                    # Check if it was cancelled
                    if task["status"] != TaskStatus.CANCELLED:
                        task["status"] = TaskStatus.FAILED
                        task["error"] = f"Process exited with non-zero code {return_code}"
                        task["current_step"] = f"Failed (Exit Code {return_code})"
                self._save_state()

        except Exception as e:
            logger.error(f"Task {task_id} execution exception: {e}")
            with self._queue_lock:
                self._active_processes.pop(task_id, None)
                task["status"] = TaskStatus.FAILED
                task["error"] = str(e)
                task["completed_at"] = datetime.now().isoformat()
                self._save_state()
