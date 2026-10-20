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


def dvr_sources_from_env(env: Optional[Mapping[str, str]] = None) -> List[Tuple[str, str]]:
    """Build ``(camera_id, rtsp_url)`` pairs for an NVR/DVR from environment variables.

    Variables:
      DVR_IP, DVR_USERNAME, DVR_PASSWORD   required; nothing is returned if any is missing
      DVR_RTSP_PORT                        default 554
      DVR_RTSP_PATH                        default Streaming/Channels/101
      DVR_CHANNELS                         optional, e.g. "4,1,5" or "4:0,1:1" (channel:stream)
      DVR_CAMERA_NAMES                     optional, e.g. "reception,lane,entrance", aligned with DVR_CHANNELS

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
        return [("dvr-1", base + path)]

    names = [n.strip() for n in env.get("DVR_CAMERA_NAMES", "").split(",")]
    sources: List[Tuple[str, str]] = []
    seen = set()
    for index, raw_channel in enumerate(raw_channels):
        channel, subtype = _parse_channel_entry(raw_channel)
        name = _slug(names[index]) if index < len(names) and names[index] else ""
        camera_id = name or f"dvr-ch{channel}"
        if camera_id in seen:
            raise ValueError(f"Duplicate camera id {camera_id!r} from DVR_CHANNELS / DVR_CAMERA_NAMES")
        seen.add(camera_id)
        sources.append((camera_id, base + _channel_path(path, channel, subtype)))
    return sources
