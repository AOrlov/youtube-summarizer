import os

import summarizer.app as app_module
from summarizer.file_handler import FileHandler


class FakeURLValidator:
    def is_valid_url(self, video_url):
        return video_url.startswith("https://youtube.com/")

    def extract_video_id(self, video_url):
        return "video123"


class FakeTranscriptExtractor:
    def __init__(self, api_key):
        self.api_key = api_key
        self.calls = []

    def get_transcript(self, video_id, include_stats=False):
        self.calls.append(video_id)
        result = ("video123", "en", "Transcript text")
        if include_stats:
            return result + (
                {
                    "cache_hit": True,
                    "cache_source": "preferred_language_cache",
                    "duration_ms": 1.0,
                    "fetch_attempts": 0,
                    "transcript_chars": len("Transcript text"),
                },
            )
        return result


class FakeGeminiSummarizer:
    def __init__(self, api_key, model_name):
        self.api_key = api_key
        self.model_name = model_name
        self.calls = []

    def summarize(self, transcript, summary_language, max_tokens):
        self.calls.append(
            {
                "transcript": transcript,
                "summary_language": summary_language,
                "max_tokens": max_tokens,
            }
        )
        return f"{summary_language} summary"


def test_save_summary_records_both_languages_in_filename_and_metadata(tmp_path):
    handler = FileHandler(str(tmp_path))

    saved_path = handler.save_summary(
        "video123",
        "en",
        "ru",
        "Summary text",
        metadata={"title": "Example"},
    )

    assert saved_path.name.startswith("summary_video123_en_ru_")
    assert saved_path.suffix == ".md"

    content = saved_path.read_text(encoding="utf-8")
    assert "Summary text" in content
    assert "- **title**: Example" in content
    assert "- **transcript_language**: en" in content
    assert "- **summary_language**: ru" in content


def test_get_summary_path_distinguishes_summary_language(tmp_path):
    handler = FileHandler(str(tmp_path))

    english_path = handler.save_summary("video123", "en", "en", "English summary")
    russian_path = handler.save_summary("video123", "en", "ru", "Russian summary")

    assert handler.get_summary_path("video123", "en", "en") == english_path
    assert handler.get_summary_path("video123", "en", "ru") == russian_path
    assert handler.get_summary_path("video123", "ru", "ru") is None


def test_get_summary_path_falls_back_to_legacy_same_language_cache(tmp_path):
    handler = FileHandler(str(tmp_path))
    legacy_path = tmp_path / "summary_video123_en_20260101_010101.md"
    legacy_path.write_text("Legacy summary", encoding="utf-8")

    assert handler.get_summary_path("video123", "en", "en") == legacy_path
    assert handler.get_summary_path("video123", "en", "ru") is None


def test_get_summary_path_same_language_does_not_match_new_other_language_cache(
    tmp_path,
):
    handler = FileHandler(str(tmp_path))
    handler.save_summary("video123", "en", "ru", "Russian summary")

    assert handler.get_summary_path("video123", "en", "en") is None


def test_load_summary_extracts_body_without_metadata(tmp_path):
    handler = FileHandler(str(tmp_path))
    summary_path = handler.save_summary(
        "video123",
        "en",
        "ru",
        "Summary body",
        metadata={"title": "Example"},
    )

    assert handler.load_summary(summary_path) == "Summary body"


def test_load_summary_round_trips_embedded_metadata_heading(tmp_path):
    handler = FileHandler(str(tmp_path))
    summary_text = "Intro\n\n## Metadata\nThis heading belongs to the summary."
    summary_path = handler.save_summary("video123", "en", "ru", summary_text)

    assert handler.load_summary(summary_path) == summary_text


def test_load_summary_supports_legacy_metadata_delimiter(tmp_path):
    handler = FileHandler(str(tmp_path))
    legacy_summary_path = tmp_path / "summary_video123_en_en_20260101_010101.md"
    legacy_summary_path.write_text(
        "## Summary\nLegacy summary body\n\n## Metadata\n- **title**: Example\n",
        encoding="utf-8",
    )

    assert handler.load_summary(legacy_summary_path) == "Legacy summary body"


def test_cleanup_old_summaries_removes_aged_markdown_files(tmp_path):
    handler = FileHandler(str(tmp_path))
    old_path = handler.save_summary("video123", "en", "en", "Old summary")
    fresh_path = handler.save_summary("video123", "en", "ru", "Fresh summary")
    os.utime(old_path, (0, 0))

    handler.cleanup_old_summaries(max_age_days=30)

    assert not old_path.exists()
    assert fresh_path.exists()


def test_summarizer_cache_separates_transcript_and_summary_languages(
    monkeypatch, tmp_path
):
    fake_url_validator = FakeURLValidator()
    fake_transcript_extractor = FakeTranscriptExtractor(api_key="youtube-key")
    fake_gemini_summarizer = FakeGeminiSummarizer(
        api_key="gemini-key",
        model_name="gemini-model",
    )

    monkeypatch.setattr(
        app_module,
        "YouTubeURLValidator",
        lambda: fake_url_validator,
    )
    monkeypatch.setattr(
        app_module,
        "YouTubeTranscriptExtractor",
        lambda api_key: fake_transcript_extractor,
    )
    monkeypatch.setattr(
        app_module,
        "GeminiSummarizer",
        lambda api_key, model_name: fake_gemini_summarizer,
    )

    summarizer = app_module.YouTubeSummarizer(
        gemini_api_key="gemini-key",
        model_name="gemini-model",
        output_dir=str(tmp_path),
        youtube_api_key="youtube-key",
    )
    video_url = "https://youtube.com/watch?v=dQw4w9WgXcQ"

    english_summary = summarizer.summarize_video(
        video_url=video_url,
        save_to_file=True,
        summary_language="en",
    )
    russian_summary = summarizer.summarize_video(
        video_url=video_url,
        save_to_file=True,
        summary_language="ru",
    )
    cached_english_summary = summarizer.summarize_video(
        video_url=video_url,
        save_to_file=True,
        summary_language="en",
    )

    assert english_summary == "en summary"
    assert russian_summary == "ru summary"
    assert cached_english_summary == "en summary"
    assert fake_gemini_summarizer.calls == [
        {
            "transcript": "Transcript text",
            "summary_language": "en",
            "max_tokens": None,
        },
        {
            "transcript": "Transcript text",
            "summary_language": "ru",
            "max_tokens": None,
        },
    ]
    assert sorted(path.name for path in tmp_path.glob("summary_*.md")) == [
        next(tmp_path.glob("summary_video123_en_en_*.md")).name,
        next(tmp_path.glob("summary_video123_en_ru_*.md")).name,
    ]
