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

    def get_transcript(self, video_id):
        self.calls.append(video_id)
        return ("video123", "en", "Transcript text")


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
    summarizer.summarize_video(
        video_url=video_url,
        save_to_file=True,
        summary_language="en",
    )

    assert english_summary == "en summary"
    assert russian_summary == "ru summary"
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
