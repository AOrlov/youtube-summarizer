import importlib
import sys
from urllib.parse import parse_qs, urlparse

import pytest

import summarizer.app as app_module


class FakeYouTubeSummarizer:
    def __init__(self, *args, **kwargs):
        self.calls = []
        self.next_result = {
            "summary": "summary",
            "transcript": "transcript",
            "transcript_language": "en",
            "summary_language": "en",
            "video_id": "video123",
            "summary_error": None,
        }

    def summarize_video(self, **kwargs):
        self.calls.append(kwargs)
        result = dict(self.next_result)
        result["summary_language"] = (
            kwargs.get("summary_language") or result["summary_language"]
        )
        return result


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
    assert parse_qs(location.query) == {"video_url": ["https://youtu.be/dQw4w9WgXcQ"]}


def test_invalid_non_video_path_renders_index_without_redirect(client):
    response = client.get("/channel/test", base_url="http://youtube.home")

    assert response.status_code == 200
    assert b"YouTube Video Summarizer" in response.data


def test_api_summarize_passes_summary_language_and_returns_distinct_fields(
    client, web_module
):
    response = client.post(
        "/api/summarize",
        json={
            "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "summary_language": "ru",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "summary": "summary",
        "transcript": "transcript",
        "transcript_language": "en",
        "summary_language": "ru",
        "language": "en",
        "video_id": "video123",
        "summary_error": None,
        "status": "success",
    }
    assert web_module.summarizer.calls == [
        {
            "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "max_tokens": web_module.config.max_tokens,
            "include_transcript": True,
            "allow_summary_failure": True,
            "summary_language": "ru",
        }
    ]


def test_api_summarize_rejects_invalid_summary_language(client, web_module):
    response = client.post(
        "/api/summarize",
        json={
            "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "summary_language": "es",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "summary_language must be one of: en, ru",
        "status": "error",
    }
    assert web_module.summarizer.calls == []
