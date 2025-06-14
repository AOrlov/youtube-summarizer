import json
import os
import re
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

from googleapiclient.discovery import build
from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (NoTranscriptFound,
                                            TranscriptsDisabled)

from .utils import get_logger

logger = get_logger(__name__)


class YouTubeURLValidator:
    """Class for validating YouTube URLs and extracting video IDs."""

    # Regular expressions for different YouTube URL formats
    URL_PATTERNS = [
        # Standard URL
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&]+)",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/([^/?]+)",  # Embed URL
        r"(?:https?://)?(?:www\.)?youtu\.be/([^/?]+)",  # Short URL
        r"(?:https?://)?(?:www\.)?youtube\.com/v/([^/?]+)",  # Old format
    ]

    def __init__(self):
        """Initialize the validator with compiled regex patterns."""
        self.patterns = [re.compile(pattern) for pattern in self.URL_PATTERNS]

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from a YouTube URL.

        Args:
            url: The YouTube URL to process

        Returns:
            The video ID if found, None otherwise
        """
        # Try each pattern
        for pattern in self.patterns:
            match = pattern.search(url)
            if match:
                return match.group(1)

        # Try parsing as a standard URL with query parameters
        parsed = urlparse(url)
        if parsed.netloc in ["www.youtube.com", "youtube.com"]:
            query = parse_qs(parsed.query)
            if "v" in query:
                return query["v"][0]

        return None

    def is_valid_url(self, url: str) -> bool:
        """
        Check if a URL is a valid YouTube video URL.

        Args:
            url: The URL to validate

        Returns:
            True if the URL is valid, False otherwise
        """
        return self.extract_video_id(url) is not None

    def validate_url(self, url: str) -> str:
        """
        Validate a YouTube URL and return the video ID.

        Args:
            url: The YouTube URL to validate

        Returns:
            The video ID if the URL is valid

        Raises:
            ValueError: If the URL is invalid
        """
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError(f"Invalid YouTube URL: {url}")
        return video_id


class YouTubeTranscriptExtractor:
    """Class for extracting transcripts from YouTube videos."""

    def __init__(
        self,
        language: str = "auto",
        cache_dir: str = "cache/transcripts",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the transcript extractor.

        Args:
            cache_dir: Directory to store cached transcripts (default: "cache/transcripts")
            api_key: YouTube Data API key (optional)
        """
        self.cache_dir = cache_dir
        self.api_key = api_key

        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        logger.info(f"Initialized transcript cache in {cache_dir}")

    def _get_cache_path(self, video_id: str, language: str) -> str:
        """Get the path to the cached transcript file."""
        return os.path.join(self.cache_dir, f"{video_id}_{language}.json")

    def _load_from_cache(self, video_id: str, language: str) -> Optional[str]:
        """Load transcript from cache if available."""
        cache_path = self._get_cache_path(video_id, language)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(
                        f"Loaded transcript from cache for video {video_id}")
                    return data["transcript"]
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error reading cache for {video_id}: {str(e)}")
                return None
        return None

    def _save_to_cache(self, video_id: str, language: str, transcript: str) -> None:
        """Save transcript to cache."""
        cache_path = self._get_cache_path(video_id, language)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "video_id": video_id,
                        "language": language,
                        "transcript": transcript,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            logger.info(f"Saved transcript to cache for video {video_id}")
        except Exception as e:
            logger.warning(f"Error saving cache for {video_id}: {str(e)}")

    def get_video_language(self, video_id: str) -> Optional[str]:
        """
        Get the default audio language of a YouTube video using the YouTube Data API.

        Args:
            video_id: The YouTube video ID

        Returns:
            The language code if available, None otherwise
        """
        if not self.api_key:
            logger.warning(
                "YouTube API key not provided, cannot detect video language")
            return None

        try:
            youtube = build("youtube", "v3", developerKey=self.api_key)
            request = youtube.videos().list(part="snippet", id=video_id)
            response = request.execute()

            if response["items"]:
                video = response["items"][0]
                return video["snippet"].get("defaultAudioLanguage") or video["snippet"].get("defaultLanguage")

            return None
        except Exception as e:
            logger.warning(f"Error getting video language: {str(e)}")
            return None

    def get_transcript(self, video_id: str, language: Optional[str]) -> tuple[str, str, str]:
        """
        Get the transcript for a YouTube video.

        Args:
            video_id: The YouTube video ID
            language: The language code for the transcript. If None, the default language will be used.

        Returns:
            A tuple containing the transcript text and the video language

        Raises:
            TranscriptsDisabled: If transcripts are disabled for the video
            NoTranscriptFound: If no transcript is available in the requested language
            Exception: For other errors
        """
        try:
            # Try to load from cache first if language is not None
            if language is not None:
                cached_transcript = self._load_from_cache(video_id, language)
                if cached_transcript:
                    return (video_id, language, cached_transcript)

            # If not in cache, fetch from YouTube
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_transcript(
                [language]) if language else transcript_list.find_transcript(["ru", "en"])

            language = language if language else transcript.language_code
            logger.info(f"Using transcript language: {language}")

            # Format the transcript as plain text
            retry_times = 5
            for i in range(retry_times):
                try:
                    transcript_data = transcript.fetch()
                    break
                except Exception as retry_e:
                    if i == retry_times - 1:
                        logger.error(
                            f"Failed to fetch transcript after {retry_times} attempts: {str(retry_e)}")
                        raise retry_e
                    logger.warning(
                        f"Retrying transcript fetch due to error: {str(retry_e)}")

            formatted_transcript = "\n".join(
                f"{item.text}" for item in transcript_data.snippets
            )

            # Save to cache
            self._save_to_cache(video_id, language, formatted_transcript)

            return (video_id, language, formatted_transcript)

        except TranscriptsDisabled:
            raise TranscriptsDisabled(
                f"Transcripts are disabled for video: {video_id}")
        except NoTranscriptFound:
            raise NoTranscriptFound(
                video_id=video_id,
                requested_language_codes=[language],
                transcript_data=[],
            )
        except Exception as e:
            raise Exception(f"Error fetching transcript: {str(e)}")

    def get_available_languages(self, video_id: str) -> List[str]:
        """
        Get list of available languages for a video's transcript.

        Args:
            video_id: The YouTube video ID

        Returns:
            List of language codes

        Raises:
            Exception: If there's an error fetching the languages
        """
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            return [transcript.language_code for transcript in transcript_list]
        except Exception as e:
            raise Exception(f"Error fetching available languages: {str(e)}")
