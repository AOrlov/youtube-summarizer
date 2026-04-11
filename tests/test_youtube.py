from types import SimpleNamespace

import pytest

import summarizer.youtube as youtube_module
from summarizer.youtube import YouTubeTranscriptExtractor, YouTubeURLValidator


def test_standard_watch_urls_are_valid():
    validator = YouTubeURLValidator()
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "youtube.com/watch?v=dQw4w9WgXcQ",
    ]

    for url in urls:
        assert validator.extract_video_id(url) == "dQw4w9WgXcQ"
        assert validator.is_valid_url(url)
        assert validator.validate_url(url) == "dQw4w9WgXcQ"


def test_mirrored_watch_urls_are_valid():
    validator = YouTubeURLValidator()
    urls = [
        "https://youtube.home/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.home/watch?v=dQw4w9WgXcQ&t=43",
        "youtube.home/watch?v=dQw4w9WgXcQ",
    ]

    for url in urls:
        assert validator.extract_video_id(url) == "dQw4w9WgXcQ"
        assert validator.is_valid_url(url)


def test_shorts_urls_are_valid_for_canonical_and_mirrored_hosts():
    validator = YouTubeURLValidator()
    urls = [
        "https://youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share",
        "https://youtube.home/shorts/dQw4w9WgXcQ",
        "youtube.home/shorts/dQw4w9WgXcQ?si=test",
    ]

    for url in urls:
        assert validator.extract_video_id(url) == "dQw4w9WgXcQ"
        assert validator.is_valid_url(url)


def test_embed_short_and_old_format_urls_are_valid():
    validator = YouTubeURLValidator()
    urls = [
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/v/dQw4w9WgXcQ",
    ]

    for url in urls:
        assert validator.extract_video_id(url) == "dQw4w9WgXcQ"
        assert validator.is_valid_url(url)
        assert validator.validate_url(url) == "dQw4w9WgXcQ"


def test_invalid_non_video_urls_are_rejected():
    validator = YouTubeURLValidator()
    urls = [
        "https://www.youtube.com",
        "https://www.youtube.com/playlist?list=PL1234567890",
        "https://youtube.home/channel/test",
        "https://youtube.home/channel/test?v=dQw4w9WgXcQ",
        "https://www.google.com",
        "not a url",
        "",
    ]

    for url in urls:
        assert validator.extract_video_id(url) is None
        assert not validator.is_valid_url(url)
        with pytest.raises(ValueError):
            validator.validate_url(url)


def test_transcript_extractor_returns_cached_transcript(tmp_path):
    extractor = YouTubeTranscriptExtractor(cache_dir=str(tmp_path))
    extractor._save_to_cache("video123", "ru", "cached transcript")

    assert extractor.get_transcript("video123") == (
        "video123",
        "ru",
        "cached transcript",
    )


def test_transcript_extractor_fetches_formats_and_caches_transcript(
    monkeypatch, tmp_path
):
    class FakeTranscript:
        language_code = "en"

        def fetch(self):
            return SimpleNamespace(
                snippets=[
                    SimpleNamespace(text="first line"),
                    SimpleNamespace(text="second line"),
                ]
            )

    class FakeTranscriptList:
        def __init__(self):
            self.transcript = FakeTranscript()

        def find_transcript(self, preferred_languages):
            assert preferred_languages == ["ru", "en"]
            return self.transcript

        def __iter__(self):
            return iter([self.transcript])

    class FakeTranscriptApi:
        def list(self, video_id):
            assert video_id == "video123"
            return FakeTranscriptList()

    monkeypatch.setattr(youtube_module, "YouTubeTranscriptApi", FakeTranscriptApi)

    extractor = YouTubeTranscriptExtractor(cache_dir=str(tmp_path))
    assert extractor.get_transcript("video123") == (
        "video123",
        "en",
        "first line\nsecond line",
    )
    assert extractor._load_from_cache("video123", "en") == "first line\nsecond line"


def test_available_languages_uses_transcript_list(monkeypatch, tmp_path):
    class FakeTranscriptApi:
        def list(self, video_id):
            assert video_id == "video123"
            return [
                SimpleNamespace(language_code="en"),
                SimpleNamespace(language_code="ru"),
            ]

    monkeypatch.setattr(youtube_module, "YouTubeTranscriptApi", FakeTranscriptApi)

    extractor = YouTubeTranscriptExtractor(cache_dir=str(tmp_path))
    assert extractor.get_available_languages("video123") == ["en", "ru"]


def test_transcript_extractor_raises_no_transcript_found_when_fallback_is_empty(
    monkeypatch, tmp_path
):
    class FakeTranscriptList:
        def find_transcript(self, preferred_languages):
            raise youtube_module.transcript_errors.NoTranscriptFound(
                video_id="video123",
                requested_language_codes=preferred_languages,
                transcript_data=[],
            )

        def __iter__(self):
            return iter(())

    class FakeTranscriptApi:
        def list(self, video_id):
            assert video_id == "video123"
            return FakeTranscriptList()

    monkeypatch.setattr(youtube_module, "YouTubeTranscriptApi", FakeTranscriptApi)

    extractor = YouTubeTranscriptExtractor(cache_dir=str(tmp_path))
    with pytest.raises(youtube_module.transcript_errors.NoTranscriptFound):
        extractor.get_transcript("video123")


def test_transcript_extractor_raises_transcripts_disabled(monkeypatch, tmp_path):
    class FakeTranscriptApi:
        def list(self, video_id):
            raise youtube_module.transcript_errors.TranscriptsDisabled(video_id)

    monkeypatch.setattr(youtube_module, "YouTubeTranscriptApi", FakeTranscriptApi)

    extractor = YouTubeTranscriptExtractor(cache_dir=str(tmp_path))
    with pytest.raises(youtube_module.transcript_errors.TranscriptsDisabled):
        extractor.get_transcript("video123")


def test_transcript_extractor_retries_before_raising(monkeypatch, tmp_path):
    attempts = {"count": 0}

    class FakeTranscriptApi:
        def list(self, video_id):
            attempts["count"] += 1
            raise RuntimeError("boom")

    monkeypatch.setattr(youtube_module, "YouTubeTranscriptApi", FakeTranscriptApi)

    extractor = YouTubeTranscriptExtractor(cache_dir=str(tmp_path))
    with pytest.raises(Exception, match="Error fetching transcript: boom"):
        extractor.get_transcript("video123")

    assert attempts["count"] == 5
