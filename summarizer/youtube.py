import json
import os
import re
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import _errors as transcript_errors
from youtube_transcript_api._api import YouTubeTranscriptApi

from .utils import get_logger

logger = get_logger(__name__)


class YouTubeURLValidator:
    """Class for validating YouTube URLs and extracting video IDs."""

    YOUTUBE_DOMAINS = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtube.home",
        "www.youtube.home",
        "m.youtube.home",
    }
    SHORT_DOMAINS = {"youtu.be", "www.youtu.be"}
    SCHEME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")

    def _normalize_url(self, url: str) -> Optional[str]:
        """Normalize partial YouTube URLs so urlparse can inspect them."""
        if not url:
            return None

        candidate = url.strip()
        if not candidate:
            return None

        if self.SCHEME_PATTERN.match(candidate):
            return candidate

        bare_domain_prefixes = tuple(self.YOUTUBE_DOMAINS | self.SHORT_DOMAINS)
        if candidate.startswith(bare_domain_prefixes):
            return f"https://{candidate}"

        return candidate

    @staticmethod
    def _extract_path_segment(path: str, prefix: str) -> Optional[str]:
        normalized_path = path.strip("/")
        expected_prefix = f"{prefix}/"
        if not normalized_path.startswith(expected_prefix):
            return None

        segments = normalized_path.split("/")
        if len(segments) < 2 or not segments[1]:
            return None

        return segments[1]

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from a YouTube URL.

        Args:
            url: The YouTube URL to process

        Returns:
            The video ID if found, None otherwise
        """
        normalized_url = self._normalize_url(url)
        if not normalized_url:
            return None

        parsed = urlparse(normalized_url)
        netloc = parsed.netloc.lower()

        if netloc in self.YOUTUBE_DOMAINS:
            if parsed.path == "/watch":
                query = parse_qs(parsed.query)
                if "v" in query and query["v"]:
                    return query["v"][0]

            for prefix in ("shorts", "embed", "v"):
                video_id = self._extract_path_segment(parsed.path, prefix)
                if video_id:
                    return video_id

        if netloc in self.SHORT_DOMAINS:
            segments = [segment for segment in parsed.path.split("/") if segment]
            if segments:
                return segments[0]

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
                    logger.info(f"Loaded transcript from cache for video {video_id}")
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

    def _load_any_cached_transcript(self, video_id: str) -> Optional[tuple[str, str]]:
        """Load any cached transcript for a video when preferred-language caches miss."""
        try:
            for filename in sorted(os.listdir(self.cache_dir)):
                if not filename.startswith(f"{video_id}_") or not filename.endswith(
                    ".json"
                ):
                    continue

                language = filename[len(video_id) + 1 : -5]
                cached_transcript = self._load_from_cache(video_id, language)
                if cached_transcript:
                    return (language, cached_transcript)
        except FileNotFoundError:
            return None

        return None

    def get_transcript(self, video_id: str) -> tuple[str, str, str]:
        """
        Get the transcript for a YouTube video.
        Prefer Russian, then English, then fall back to any available transcript.

        Args:
            video_id: The YouTube video ID

        Returns:
            A tuple containing the transcript text and the video language

        Raises:
            TranscriptsDisabled: If transcripts are disabled for the video
            NoTranscriptFound: If no transcript is available in the requested language
            Exception: For other errors
        """
        try:
            preferred_languages = ["ru", "en"]

            # Try to load from cache first using preferred languages
            for preferred_language in preferred_languages:
                cached_transcript = self._load_from_cache(video_id, preferred_language)
                if cached_transcript:
                    return (video_id, preferred_language, cached_transcript)

            fallback_cached_transcript = self._load_any_cached_transcript(video_id)
            if fallback_cached_transcript:
                language, transcript = fallback_cached_transcript
                return (video_id, language, transcript)

            # Format the transcript as plain text
            retry_times = 5
            for i in range(retry_times):
                try:
                    transcript_list = YouTubeTranscriptApi().list(video_id)
                    transcript = transcript_list.find_transcript(preferred_languages)
                    transcript_data = transcript.fetch()
                    language = transcript.language_code
                    logger.info(
                        "Using transcript language: %s for video %s",
                        language,
                        video_id,
                    )
                    break
                except transcript_errors.NoTranscriptFound:
                    try:
                        transcript_list = YouTubeTranscriptApi().list(video_id)
                        transcript = next(iter(transcript_list), None)
                        if transcript is None:
                            raise
                        transcript_data = transcript.fetch()
                        language = transcript.language_code
                        logger.info(
                            "Falling back to transcript language: %s for video %s",
                            language,
                            video_id,
                        )
                        break
                    except Exception as retry_e:
                        if i == retry_times - 1:
                            logger.error(
                                "Failed to fetch transcript after %s attempts: %s",
                                retry_times,
                                str(retry_e),
                            )
                            raise retry_e
                        logger.warning(
                            "Retrying transcript fetch due to error: %s",
                            str(retry_e),
                        )
                except Exception as retry_e:
                    if i == retry_times - 1:
                        logger.error(
                            "Failed to fetch transcript after %s attempts: %s",
                            retry_times,
                            str(retry_e),
                        )
                        raise retry_e
                    logger.warning(
                        "Retrying transcript fetch due to error: %s",
                        str(retry_e),
                    )

            formatted_transcript = "\n".join(
                f"{item.text}" for item in transcript_data.snippets
            )

            # Save to cache
            self._save_to_cache(video_id, language, formatted_transcript)

            return (video_id, language, formatted_transcript)

        except transcript_errors.TranscriptsDisabled:
            raise transcript_errors.TranscriptsDisabled(
                f"Transcripts are disabled for video: {video_id}"
            )
        except transcript_errors.NoTranscriptFound:
            raise transcript_errors.NoTranscriptFound(
                video_id=video_id,
                requested_language_codes=preferred_languages,
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
            transcript_list = YouTubeTranscriptApi().list(video_id)
            return [transcript.language_code for transcript in transcript_list]
        except Exception as e:
            raise Exception(f"Error fetching available languages: {str(e)}")
