import importlib
import sys
from urllib.parse import parse_qs, urlparse

import pytest

import summarizer.app as app_module


class FakeYouTubeSummarizer:
    def __init__(self, *args, **kwargs):
        self.init_kwargs = kwargs
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
    monkeypatch.setenv("TRANSCRIPT_CACHE_DIR", str(tmp_path / "cache" / "transcripts"))
    monkeypatch.setattr(app_module, "YouTubeSummarizer", FakeYouTubeSummarizer)

    sys.modules.pop("summarizer.web", None)
    module = importlib.import_module("summarizer.web")
    module.app.config.update(TESTING=True)
    return module


@pytest.fixture
def client(web_module):
    return web_module.app.test_client()


def test_web_initializes_summarizer_with_configured_directories(web_module, tmp_path):
    assert web_module.summarizer.init_kwargs["output_dir"] == str(tmp_path / "output")
    assert web_module.summarizer.init_kwargs["transcript_cache_dir"] == str(
        tmp_path / "cache" / "transcripts"
    )


def test_index_renders_summary_language_dropdown_with_explicit_labels(client):
    response = client.get("/")

    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="intake-grid"' in html
    assert 'id="summaryLanguage"' in html
    assert "form-select form-select-sm" in html
    assert 'aria-label="Summary language"' in html
    assert '<option value="ru" selected>Russian</option>' in html
    assert '<option value="en">English</option>' in html
    assert "Output" in html
    assert "Transcript language" in html
    assert "summary_language: summaryLanguageSelect.value" in html
    assert "marked.parse" in html
    assert "DOMPurify.sanitize" in html


def test_mirrored_watch_route_preserves_summary_language_on_redirect(client):
    response = client.get(
        "/watch?v=dQw4w9WgXcQ&summary_language=ru",
        base_url="http://youtube.home",
    )

    assert response.status_code == 302

    location = urlparse(response.headers["Location"])
    assert location.path == "/"
    assert parse_qs(location.query) == {
        "video_url": ["https://youtube.com/watch?v=dQw4w9WgXcQ"],
        "summary_language": ["ru"],
    }


def test_root_query_renders_selected_summary_language_and_autosubmit_script(client):
    response = client.get(
        "/?video_url=https://youtube.com/watch?v=dQw4w9WgXcQ&summary_language=ru"
    )

    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<option value="ru" selected>Russian</option>' in html
    assert "const allowQueryAutoSubmit = true;" in html
    assert (
        "const prefilledUrl = params.get('video_url') || params.get('video');" in html
    )
    assert (
        "summarizeForm.dispatchEvent(new Event('submit', { cancelable: true }));"
        in html
    )


def test_mirrored_watch_route_renders_index_with_dropdown_when_following_redirects(
    client,
):
    response = client.get(
        "/watch?v=dQw4w9WgXcQ",
        base_url="http://youtube.home",
        follow_redirects=True,
    )

    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="summaryLanguage"' in html
    assert '<option value="ru" selected>Russian</option>' in html


def test_watch_route_redirects_to_root_with_canonical_video_url(client):
    response = client.get(
        "/watch?v=dQw4w9WgXcQ&t=43",
        base_url="http://youtube.home",
    )

    assert response.status_code == 302

    location = urlparse(response.headers["Location"])
    assert location.path == "/"
    assert parse_qs(location.query) == {
        "video_url": ["https://youtube.com/watch?v=dQw4w9WgXcQ&t=43"],
        "summary_language": ["ru"],
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
        "video_url": ["https://youtube.com/shorts/dQw4w9WgXcQ?si=test"],
        "summary_language": ["ru"],
    }


def test_explicit_video_url_override_wins_over_mirrored_request(client):
    response = client.get(
        "/watch?v=wrong&video_url=https://youtu.be/dQw4w9WgXcQ",
        base_url="http://youtube.home",
    )

    assert response.status_code == 302

    location = urlparse(response.headers["Location"])
    assert parse_qs(location.query) == {
        "video_url": ["https://youtu.be/dQw4w9WgXcQ"],
        "summary_language": ["ru"],
    }


def test_invalid_non_video_path_renders_index_without_redirect(client):
    response = client.get("/channel/test", base_url="http://youtube.home")

    assert response.status_code == 200
    assert b"YouTube Video Summarizer" in response.data


def test_invalid_non_video_path_with_v_query_does_not_redirect(client):
    response = client.get(
        "/channel/test?v=dQw4w9WgXcQ",
        base_url="http://youtube.home",
    )

    assert response.status_code == 200
    assert b"YouTube Video Summarizer" in response.data


def test_invalid_non_video_path_with_explicit_video_url_does_not_redirect(client):
    response = client.get(
        "/channel/test?video_url=https://youtube.com/watch?v=dQw4w9WgXcQ",
        base_url="http://youtube.home",
    )

    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert b"YouTube Video Summarizer" in response.data
    assert "const allowQueryAutoSubmit = false;" in html


def test_non_mirrored_unknown_path_returns_404(client):
    response = client.get("/channel/test")

    assert response.status_code == 404


def test_non_mirrored_unknown_path_with_explicit_video_url_returns_404(client):
    response = client.get("/foo?video_url=https://youtube.com/watch?v=dQw4w9WgXcQ")

    assert response.status_code == 404


def test_api_summarize_get_keeps_method_not_allowed(client):
    response = client.get("/api/summarize")

    assert response.status_code == 405


def test_api_summarize_get_with_video_url_keeps_method_not_allowed(client):
    response = client.get(
        "/api/summarize?video_url=https://youtube.com/watch?v=dQw4w9WgXcQ"
    )

    assert response.status_code == 405


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


def test_api_summarize_defaults_summary_language_to_transcript_language(
    client, web_module
):
    response = client.post(
        "/api/summarize",
        json={"video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ"},
    )

    assert response.status_code == 200
    assert response.get_json()["summary_language"] == "en"
    assert web_module.summarizer.calls == [
        {
            "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "max_tokens": web_module.config.max_tokens,
            "include_transcript": True,
            "allow_summary_failure": True,
            "summary_language": None,
        }
    ]


def test_api_summarize_returns_partial_success_when_summary_is_missing(
    client, web_module
):
    web_module.summarizer.next_result.update(
        {
            "summary": None,
            "summary_error": "Gemini failed",
        }
    )

    response = client.post(
        "/api/summarize",
        json={"video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "summary": None,
        "transcript": "transcript",
        "transcript_language": "en",
        "summary_language": "en",
        "language": "en",
        "video_id": "video123",
        "summary_error": "Gemini failed",
        "status": "partial_success",
    }


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
