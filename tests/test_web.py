import importlib
import sys
from urllib.parse import parse_qs, urlparse

import pytest

import summarizer.app as app_module


class FakeYouTubeSummarizer:
    def __init__(self, *args, **kwargs):
        self.calls = []

    def summarize_video(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "summary": "summary",
            "transcript": "transcript",
            "language": "en",
            "video_id": "video123",
            "summary_error": None,
        }


@pytest.fixture
def web_module(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-youtube-key")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setattr(app_module, "YouTubeSummarizer", FakeYouTubeSummarizer)

    sys.modules.pop("summarizer.web", None)
    module = importlib.import_module("summarizer.web")
    module.app.config.update(TESTING=True)
    return module


@pytest.fixture
def client(web_module):
    return web_module.app.test_client()


def test_watch_route_redirects_to_root_with_canonical_video_url(client):
    response = client.get(
        "/watch?v=dQw4w9WgXcQ&t=43",
        base_url="http://youtube.home",
    )

    assert response.status_code == 302

    location = urlparse(response.headers["Location"])
    assert location.path == "/"
    assert parse_qs(location.query) == {
        "video_url": ["https://youtube.com/watch?v=dQw4w9WgXcQ&t=43"]
    }


def test_shorts_route_redirects_to_root_with_canonical_video_url(client):
    response = client.get(
        "/shorts/dQw4w9WgXcQ?si=test",
        base_url="http://youtube.home",
    )

    assert response.status_code == 302

    location = urlparse(response.headers["Location"])
    assert location.path == "/"
    assert parse_qs(location.query) == {
        "video_url": ["https://youtube.com/shorts/dQw4w9WgXcQ?si=test"]
    }


def test_explicit_video_url_override_wins_over_mirrored_request(client):
    response = client.get(
        "/watch?v=wrong&video_url=https://youtu.be/dQw4w9WgXcQ",
        base_url="http://youtube.home",
    )

    assert response.status_code == 302

    location = urlparse(response.headers["Location"])
    assert parse_qs(location.query) == {
        "video_url": ["https://youtu.be/dQw4w9WgXcQ"]
    }


def test_invalid_non_video_path_renders_index_without_redirect(client):
    response = client.get("/channel/test", base_url="http://youtube.home")

    assert response.status_code == 200
    assert b"YouTube Video Summarizer" in response.data
