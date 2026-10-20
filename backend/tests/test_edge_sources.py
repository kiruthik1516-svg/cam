"""Tests for camera source helpers: URL redaction and NVR sources built from the environment."""

import pytest

from facial_recognition.sources import dvr_sources_from_env, redact_url

BASE_ENV = {
    "DVR_IP": "10.0.0.5",
    "DVR_USERNAME": "viewer",
    "DVR_PASSWORD": "s3cret",
    "DVR_RTSP_PORT": "554",
}


def test_redact_url_hides_credentials():
    text = redact_url("rtsp://viewer:s3cret@10.0.0.5:554/cam/realmonitor?channel=1")
    assert "s3cret" not in text and "viewer" not in text
    assert text == "rtsp://***@10.0.0.5:554/cam/realmonitor?channel=1"


def test_redact_url_leaves_other_values_alone():
    assert redact_url(0) == "0"
    assert redact_url("rtsp://10.0.0.5:554/stream") == "rtsp://10.0.0.5:554/stream"
    assert redact_url("clip.mp4") == "clip.mp4"


def test_redact_url_handles_percent_encoded_password():
    assert "p%40ss" not in redact_url("rtsp://u:p%40ss@host/x")


def test_no_credentials_means_no_sources():
    assert dvr_sources_from_env({"DVR_IP": "10.0.0.5"}) == []
    assert dvr_sources_from_env({**BASE_ENV, "DVR_PASSWORD": ""}) == []


def test_legacy_single_camera_is_unchanged():
    env = {**BASE_ENV, "DVR_RTSP_PATH": "/Streaming/Channels/101"}
    assert dvr_sources_from_env(env) == [
        ("dvr-1", "rtsp://viewer:s3cret@10.0.0.5:554/Streaming/Channels/101")
    ]


def test_default_path_when_unset():
    (camera_id, url), = dvr_sources_from_env(BASE_ENV)
    assert camera_id == "dvr-1" and url.endswith("/Streaming/Channels/101")


def test_channels_with_names():
    env = {
        **BASE_ENV,
        "DVR_RTSP_PATH": "cam/realmonitor?channel=4&subtype=1",
        "DVR_CHANNELS": "4, 1,5",
        "DVR_CAMERA_NAMES": "Reception, Lane ,Main Entrance",
    }
    sources = dvr_sources_from_env(env)
    assert [s[0] for s in sources] == ["reception", "lane", "main-entrance"]
    assert sources[0][1].endswith("/cam/realmonitor?channel=4&subtype=1")
    assert sources[1][1].endswith("/cam/realmonitor?channel=1&subtype=1")
    assert sources[2][1].endswith("/cam/realmonitor?channel=5&subtype=1")


def test_channel_placeholder_template_and_default_names():
    env = {**BASE_ENV, "DVR_RTSP_PATH": "Streaming/Channels/{channel}01", "DVR_CHANNELS": "2,3"}
    assert dvr_sources_from_env(env) == [
        ("dvr-ch2", "rtsp://viewer:s3cret@10.0.0.5:554/Streaming/Channels/201"),
        ("dvr-ch3", "rtsp://viewer:s3cret@10.0.0.5:554/Streaming/Channels/301"),
    ]


def test_fewer_names_than_channels_falls_back_to_default_ids():
    env = {
        **BASE_ENV,
        "DVR_RTSP_PATH": "cam/realmonitor?channel=1&subtype=1",
        "DVR_CHANNELS": "1,2",
        "DVR_CAMERA_NAMES": "door",
    }
    assert [s[0] for s in dvr_sources_from_env(env)] == ["door", "dvr-ch2"]


def test_special_characters_in_credentials_are_encoded():
    env = {**BASE_ENV, "DVR_USERNAME": "a b", "DVR_PASSWORD": "p@ss:w/rd"}
    (_, url), = dvr_sources_from_env(env)
    assert url.startswith("rtsp://a%20b:p%40ss%3Aw%2Frd@10.0.0.5:554/")


def test_invalid_configuration_is_rejected():
    template = {**BASE_ENV, "DVR_RTSP_PATH": "cam/realmonitor?channel=1&subtype=1"}
    with pytest.raises(ValueError):
        dvr_sources_from_env({**template, "DVR_CHANNELS": "1,abc"})
    with pytest.raises(ValueError):
        dvr_sources_from_env({**template, "DVR_CHANNELS": "1,2", "DVR_CAMERA_NAMES": "door,door"})
    with pytest.raises(ValueError):
        dvr_sources_from_env({**BASE_ENV, "DVR_RTSP_PATH": "Streaming/Channels/101", "DVR_CHANNELS": "1"})


def test_per_camera_stream_choice_dahua():
    env = {
        **BASE_ENV,
        "DVR_RTSP_PATH": "cam/realmonitor?channel={channel}&subtype=1",
        "DVR_CHANNELS": "4:0, 1:1, 5:main, 2:sub",
        "DVR_CAMERA_NAMES": "Door, Corridor, Entrance, Lane",
    }
    sources = dvr_sources_from_env(env)
    assert [s[0] for s in sources] == ["door", "corridor", "entrance", "lane"]
    assert sources[0][1].endswith("/cam/realmonitor?channel=4&subtype=0")  # Main-stream for door
    assert sources[1][1].endswith("/cam/realmonitor?channel=1&subtype=1")  # Sub-stream for corridor
    assert sources[2][1].endswith("/cam/realmonitor?channel=5&subtype=0")  # Main-stream for entrance
    assert sources[3][1].endswith("/cam/realmonitor?channel=2&subtype=1")  # Sub-stream for lane


def test_per_camera_stream_choice_hikvision():
    env = {
        **BASE_ENV,
        "DVR_RTSP_PATH": "Streaming/Channels/{channel}01",
        "DVR_CHANNELS": "2:main, 3:sub, 4:02",
    }
    sources = dvr_sources_from_env(env)
    assert [s[0] for s in sources] == ["dvr-ch2", "dvr-ch3", "dvr-ch4"]
    assert sources[0][1].endswith("/Streaming/Channels/201")  # Main
    assert sources[1][1].endswith("/Streaming/Channels/302")  # Sub
    assert sources[2][1].endswith("/Streaming/Channels/402")  # Sub


def test_invalid_stream_choice_rejected():
    template = {**BASE_ENV, "DVR_RTSP_PATH": "cam/realmonitor?channel=1&subtype=1"}
    with pytest.raises(ValueError, match="Invalid stream/subtype"):
        dvr_sources_from_env({**template, "DVR_CHANNELS": "1:invalid_sub"})

