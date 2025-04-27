import pytest
from summarizer.youtube import YouTubeURLValidator
from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound
from summarizer.youtube import YouTubeTranscriptExtractor

def test_standard_url():
    """Test extraction from standard YouTube URLs."""
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

def test_embed_url():
    """Test extraction from embed URLs."""
    validator = YouTubeURLValidator()
    urls = [
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "http://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://youtube.com/embed/dQw4w9WgXcQ",
    ]
    for url in urls:
        assert validator.extract_video_id(url) == "dQw4w9WgXcQ"
        assert validator.is_valid_url(url)
        assert validator.validate_url(url) == "dQw4w9WgXcQ"

def test_short_url():
    """Test extraction from short URLs."""
    validator = YouTubeURLValidator()
    urls = [
        "https://youtu.be/dQw4w9WgXcQ",
        "http://youtu.be/dQw4w9WgXcQ",
        "youtu.be/dQw4w9WgXcQ",
    ]
    for url in urls:
        assert validator.extract_video_id(url) == "dQw4w9WgXcQ"
        assert validator.is_valid_url(url)
        assert validator.validate_url(url) == "dQw4w9WgXcQ"

def test_old_format_url():
    """Test extraction from old format URLs."""
    validator = YouTubeURLValidator()
    urls = [
        "https://www.youtube.com/v/dQw4w9WgXcQ",
        "http://www.youtube.com/v/dQw4w9WgXcQ",
    ]
    for url in urls:
        assert validator.extract_video_id(url) == "dQw4w9WgXcQ"
        assert validator.is_valid_url(url)
        assert validator.validate_url(url) == "dQw4w9WgXcQ"

def test_invalid_urls():
    """Test handling of invalid URLs."""
    validator = YouTubeURLValidator()
    urls = [
        "https://www.youtube.com",
        "https://www.youtube.com/playlist?list=PL1234567890",
        "https://www.google.com",
        "not a url",
        "",
    ]
    for url in urls:
        assert validator.extract_video_id(url) is None
        assert not validator.is_valid_url(url)
        with pytest.raises(ValueError):
            validator.validate_url(url)

def test_url_with_extra_parameters():
    """Test URLs with extra parameters."""
    validator = YouTubeURLValidator()
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=youtu.be",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=123",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL1234567890",
    ]
    for url in urls:
        assert validator.extract_video_id(url) == "dQw4w9WgXcQ"
        assert validator.is_valid_url(url)
        assert validator.validate_url(url) == "dQw4w9WgXcQ"

def test_transcript_extraction():
    """Test transcript extraction for a known video with transcripts."""
    extractor = YouTubeTranscriptExtractor()
    # Using a known video ID that has transcripts
    video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
    transcript = extractor.get_transcript(video_id)
    assert isinstance(transcript, str)
    assert len(transcript) > 0

def test_transcript_language():
    """Test transcript extraction in different languages."""
    extractor = YouTubeTranscriptExtractor(language="en")
    video_id = "dQw4w9WgXcQ"
    transcript = extractor.get_transcript(video_id)
    assert isinstance(transcript, str)
    assert len(transcript) > 0

def test_available_languages():
    """Test getting available languages for a video."""
    extractor = YouTubeTranscriptExtractor()
    video_id = "dQw4w9WgXcQ"
    languages = extractor.get_available_languages(video_id)
    assert isinstance(languages, list)
    assert len(languages) > 0
    assert "en" in languages

def test_transcripts_disabled():
    """Test handling of videos with disabled transcripts."""
    extractor = YouTubeTranscriptExtractor()
    # Using a video ID that has transcripts disabled
    video_id = "invalid_video_id"
    with pytest.raises(TranscriptsDisabled):
        extractor.get_transcript(video_id)

def test_no_transcript_found():
    """Test handling of videos with no transcript in requested language."""
    extractor = YouTubeTranscriptExtractor(language="xx")  # Invalid language code
    video_id = "dQw4w9WgXcQ"
    with pytest.raises(NoTranscriptFound):
        extractor.get_transcript(video_id)

def test_invalid_video_id():
    """Test handling of invalid video IDs."""
    extractor = YouTubeTranscriptExtractor()
    video_id = "invalid_video_id"
    with pytest.raises(Exception):
        extractor.get_transcript(video_id)
