"""Camera source helpers: URL redaction and NVR/DVR sources built from the environment.

Kept free of heavy imports (no OpenCV / InsightFace) so it is cheap to import and test.
"""
from __future__ import annotations

import os
import re
from typing import Any, List, Mapping, Optional, Tuple
from urllib.parse import quote

_USERINFO = re.compile(r"(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*://)[^/@\s]+@")


def redact_url(value: Any) -> str:
    """Return ``value`` as text with any ``user:password@`` part of a URL replaced by ``***@``.

    Safe to call with non-URL values (for example a webcam index) and with URLs that carry no credentials.
    """
    return _USERINFO.sub(r"\g<scheme>***@", str(value))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")


def _parse_channel_entry(entry: str) -> Tuple[str, Optional[str]]:
    """Parse a channel item such as '4', '4:0', '4:main', '1:sub', '1:02'."""
    parts = [p.strip() for p in entry.split(":", 1)]
    channel = parts[0]
    if not channel.isdigit():
        raise ValueError(f"DVR_CHANNELS entry {entry!r} is not a valid channel number")

    if len(parts) == 1:
        return channel, None

    raw_subtype = parts[1].lower()
    if raw_subtype in ("0", "main", "high", "01"):
        return channel, "0"
    if raw_subtype in ("1", "sub", "low", "02", "substream"):
        return channel, "1"
    if raw_subtype.isdigit():
        return channel, raw_subtype
    raise ValueError(f"Invalid stream/subtype {raw_subtype!r} in DVR_CHANNELS entry {entry!r}")


def _channel_path(path: str, channel: str, subtype: Optional[str] = None) -> str:
    res = path
    if "{channel}" in res:
        res = res.replace("{channel}", channel)
    elif re.search(r"channel=\d+", res):
        res = re.sub(r"channel=\d+", f"channel={channel}", res, count=1)
    else:
        raise ValueError(
            "DVR_RTSP_PATH must contain '{channel}' or 'channel=<n>' when DVR_CHANNELS is set"
        )

    # Subtype substitution for Dahua (subtype=0/1) or Hikvision (Channels/101 vs Channels/102)
    if subtype is not None:
        sub_num = "0" if subtype in ("0", "main") else ("1" if subtype in ("1", "sub") else subtype)
        hik_suffix = "01" if sub_num == "0" else ("02" if sub_num == "1" else f"{int(sub_num):02d}")

        if "{subtype}" in res:
            res = res.replace("{subtype}", sub_num)
        elif "{stream}" in res:
            res = res.replace("{stream}", hik_suffix)
        elif re.search(r"subtype=\d+", res):
            res = re.sub(r"subtype=\d+", f"subtype={sub_num}", res, count=1)
        elif re.search(r"(Streaming/Channels/\d+)(01|02)", res):
            res = re.sub(r"(Streaming/Channels/\d+)(01|02)", rf"\g<1>{hik_suffix}", res, count=1)
    else:
        if "{subtype}" in res:
            res = res.replace("{subtype}", "1")
        elif "{stream}" in res:
            res = res.replace("{stream}", "01")

    return res


class CameraSource(tuple):
    """Camera source tuple ``(camera_id, url)`` with optional rich metadata.

    Inherits from tuple so that existing tuple unpacking ``camera_id, url = source``,
    positional indexing ``source[0]``, and tuple equality ``source == (camera_id, url)``
    continue to work seamlessly without regressions.
    """
    camera_id: str
    url: str
    name: str
    zone: Optional[str]
    stream_type: str  # 'main' or 'sub'

    def __new__(
        cls,
        camera_id: str,
        url: str,
        name: Optional[str] = None,
        zone: Optional[str] = None,
        stream_type: Optional[str] = None,
    ) -> CameraSource:
        inst = super().__new__(cls, (camera_id, url))
        inst.camera_id = camera_id
        inst.url = url
        inst.name = name or camera_id
        inst.zone = zone
        if stream_type:
            inst.stream_type = stream_type
        elif "subtype=0" in url or re.search(r"Streaming/Channels/\d+01", url):
            inst.stream_type = "main"
        else:
            inst.stream_type = "sub"
        return inst

    def __repr__(self) -> str:
        return (
            f"CameraSource(camera_id={self.camera_id!r}, url={self.url!r}, "
            f"name={self.name!r}, zone={self.zone!r}, stream_type={self.stream_type!r})"
        )


def dvr_sources_from_env(env: Optional[Mapping[str, str]] = None) -> List[CameraSource]:
    """Build ``(camera_id, rtsp_url)`` pairs for an NVR/DVR from environment variables.

    Variables:
      DVR_IP, DVR_USERNAME, DVR_PASSWORD   required; nothing is returned if any is missing
      DVR_RTSP_PORT                        default 554
      DVR_RTSP_PATH                        default Streaming/Channels/101
      DVR_CHANNELS                         optional, e.g. "4,1,5" or "4:0,1:1" (channel:stream)
      DVR_CAMERA_NAMES                     optional, e.g. "reception,lane,entrance", aligned with DVR_CHANNELS
      DVR_CAMERA_DISPLAY_NAMES             optional, e.g. "Reception Desk, Gate Lane, Main Entrance"
      DVR_CAMERA_ZONES                     optional, e.g. "Lobby, Perimeter, Main Lobby"

    Without DVR_CHANNELS the legacy behaviour is kept: a single camera named ``dvr-1`` using DVR_RTSP_PATH as is.
    With DVR_CHANNELS, DVR_RTSP_PATH is used as a template: its ``channel=<n>`` (or a ``{channel}`` placeholder)
    is replaced per channel. Channel entries may include a stream subtype (e.g. ``4:0`` for main-stream, ``1:1``
    for sub-stream). Camera ids come from DVR_CAMERA_NAMES, else ``dvr-ch<channel>``.
    """
    env = os.environ if env is None else env
    ip = env.get("DVR_IP", "").strip()
    username = env.get("DVR_USERNAME", "").strip()
    password = env.get("DVR_PASSWORD", "")
    if not (ip and username and password):
        return []

    port = env.get("DVR_RTSP_PORT", "554").strip()
    path = env.get("DVR_RTSP_PATH", "Streaming/Channels/101").strip().lstrip("/")
    base = f"rtsp://{quote(username, safe='')}:{quote(password, safe='')}@{ip}:{port}/"

    raw_channels = [c.strip() for c in env.get("DVR_CHANNELS", "").split(",") if c.strip()]
    if not raw_channels:
        disp_name = env.get("DVR_CAMERA_DISPLAY_NAMES", "").split(",")[0].strip()
        raw_name = env.get("DVR_CAMERA_NAMES", "").split(",")[0].strip()
        zone = env.get("DVR_CAMERA_ZONES", "").split(",")[0].strip() or None
        name = disp_name or raw_name or "dvr-1"
        stream_type = "main" if "subtype=0" in path or re.search(r"Streaming/Channels/\d+01", path) else "sub"
        return [CameraSource("dvr-1", base + path, name=name, zone=zone, stream_type=stream_type)]

    names = [n.strip() for n in env.get("DVR_CAMERA_NAMES", "").split(",")]
    display_names = [n.strip() for n in env.get("DVR_CAMERA_DISPLAY_NAMES", "").split(",")]
    zones = [z.strip() for z in env.get("DVR_CAMERA_ZONES", "").split(",")]
    sources: List[CameraSource] = []
    seen = set()
    for index, raw_channel in enumerate(raw_channels):
        channel, subtype = _parse_channel_entry(raw_channel)
        name = _slug(names[index]) if index < len(names) and names[index] else ""
        camera_id = name or f"dvr-ch{channel}"
        if camera_id in seen:
            raise ValueError(f"Duplicate camera id {camera_id!r} from DVR_CHANNELS / DVR_CAMERA_NAMES")
        seen.add(camera_id)

        display_name = ""
        if index < len(display_names) and display_names[index]:
            display_name = display_names[index]
        elif index < len(names) and names[index]:
            display_name = names[index]
        else:
            display_name = camera_id.replace("-", " ").title()

        zone = zones[index] if index < len(zones) and zones[index] else None

        stream_type = "main" if subtype in ("0", "main", "01") else ("sub" if subtype in ("1", "sub", "02") else None)
        resolved_url = base + _channel_path(path, channel, subtype)

        sources.append(CameraSource(camera_id, resolved_url, name=display_name, zone=zone, stream_type=stream_type))
    return sources
