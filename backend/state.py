import asyncio
import dataclasses
import time
from typing import Dict, Any, Optional

try:
    from facial_recognition.topology import CameraTopologyGraph
    from facial_recognition.cross_camera_tracker import CrossCameraContinuityTracker
    from facial_recognition.version_bundle import ModelConfigVersionBundle
except ImportError:
    CameraTopologyGraph = None
    CrossCameraContinuityTracker = None
    ModelConfigVersionBundle = None

# Global state for AI models and camera pipelines
ai_models: Dict[str, Any] = {}
node_health_store: Dict[str, Dict[str, Any]] = {}

# camera_id -> CameraPipeline
camera_pipelines: Dict[str, Any] = {}

# Initialize global topology graph and cross-camera tracker
topology_graph = CameraTopologyGraph() if CameraTopologyGraph else None
continuity_tracker = CrossCameraContinuityTracker(topology_graph=topology_graph) if CrossCameraContinuityTracker else None
active_version_bundle = ModelConfigVersionBundle() if ModelConfigVersionBundle else None

# ---------- Frame relay store ----------
# camera_id -> latest raw JPEG bytes pushed by the edge node.
@dataclasses.dataclass
class _FrameSlot:
    jpeg: bytes = b""
    event: asyncio.Event = dataclasses.field(default_factory=asyncio.Event)
    last_frame_at: float = 0.0   # time.time() of the latest pushed frame, 0.0 = never
    registered: bool = False     # Camera row created for this live camera

# Populated lazily; access only from the event-loop thread.
_frame_store: Dict[str, _FrameSlot] = {}

def get_frame_slot(camera_id: str) -> _FrameSlot:
    if camera_id not in _frame_store:
        _frame_store[camera_id] = _FrameSlot()
    return _frame_store[camera_id]


# A live camera counts as connected while it has pushed a frame this recently.
LIVE_FRAME_MAX_AGE_SECONDS = 30.0


def known_stream_camera_ids() -> set:
    """Ids of cameras that have pushed at least one live frame since the backend started."""
    return {camera_id for camera_id, slot in _frame_store.items() if slot.last_frame_at}


def streaming_camera_ids(max_age: float = LIVE_FRAME_MAX_AGE_SECONDS) -> set:
    """Ids of cameras whose latest live frame is at most ``max_age`` seconds old."""
    now = time.time()
    return {
        camera_id for camera_id, slot in _frame_store.items()
        if slot.last_frame_at and now - slot.last_frame_at <= max_age
    }


def prune_stale_stream_slots(max_idle_seconds: float = 3600.0) -> int:
    """Prune frame store slots that have been idle longer than max_idle_seconds (solves R6 lingering renamed cameras)."""
    now = time.time()
    stale_keys = [
        cam_id for cam_id, slot in _frame_store.items()
        if slot.last_frame_at and (now - slot.last_frame_at > max_idle_seconds)
    ]
    for k in stale_keys:
        del _frame_store[k]
    return len(stale_keys)
