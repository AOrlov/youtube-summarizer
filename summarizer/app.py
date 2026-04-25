import logging
from time import perf_counter
from typing import Any, Dict, Optional, Union

from .file_handler import FileHandler
from .gemini import GeminiSummarizer
from .utils import get_logger, log_event
from .youtube import YouTubeTranscriptExtractor, YouTubeURLValidator

logger = get_logger(__name__)

ALLOWED_SUMMARY_LANGUAGES = {"en", "ru"}


class YouTubeSummarizer:
    """Main class for summarizing YouTube videos."""

    def __init__(
        self,
        gemini_api_key: str,
        model_name: str,
        output_dir: str,
        youtube_api_key: str,
        transcript_cache_dir: str = "cache/transcripts",
    ):
        """
        Initialize the summarizer.

        Args:
            gemini_api_key: The Gemini API key
            language: The language code for the transcript
            output_dir: Directory to save summaries
            model_name: The name of the Gemini model to use
            transcript_cache_dir: Directory to cache fetched transcripts
        """
        self.url_validator = YouTubeURLValidator()
        self.transcript_extractor = YouTubeTranscriptExtractor(
            api_key=youtube_api_key,
            cache_dir=transcript_cache_dir,
        )
        self.summarizer = GeminiSummarizer(gemini_api_key, model_name)
        self.file_handler = FileHandler(output_dir)
        self.model_name = model_name

        logger.info(f"Initialized YouTubeSummarizer with model: {model_name}")

    def _validate_inputs(
        self,
        video_url: str,
        max_tokens: Optional[int],
        summary_language: Optional[str] = None,
    ) -> None:
        """Validate input parameters."""
        if not self.url_validator.is_valid_url(video_url):
            raise ValueError("Invalid YouTube URL")

        if max_tokens is not None and max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        if (
            summary_language is not None
            and summary_language not in ALLOWED_SUMMARY_LANGUAGES
        ):
            raise ValueError("summary_language must be one of: en, ru")

    def summarize_video(
        self,
        video_url: str,
        max_tokens: Optional[int] = None,
        save_to_file: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        include_transcript: bool = False,
        allow_summary_failure: bool = False,
        summary_language: Optional[str] = None,
        force_regenerate: bool = False,
    ) -> Union[str, Dict[str, Any]]:
        """
        Extract transcript and generate summary for a YouTube video.

        Args:
            video_url: The URL of the YouTube video
            max_tokens: Optional maximum number of tokens for the summary
            save_to_file: Whether to save the summary to a file
            metadata: Optional metadata to save with the summary
            include_transcript: Whether to return the transcript along with the summary
            allow_summary_failure: If True, return transcript even when summary generation fails
            summary_language: Optional summary output language code
            force_regenerate: If True, skip cached summaries and generate a new one

        Returns:
            The generated summary or a dictionary containing both summary and transcript when requested

        Raises:
            ValueError: If the video URL is invalid
            Exception: If there's an error during transcript extraction or summarization
        """
        request_started_at = perf_counter()
        video_id = None
        requested_summary_language = summary_language
        transcript_stats = {
            "cache_hit": None,
            "cache_source": None,
            "duration_ms": None,
            "fetch_attempts": None,
            "transcript_chars": None,
        }
        summary_generation_ms = None
        summary_loaded_from_cache = False
        summary_model_name = None
        summary_model_status = "unavailable"

        try:
            # Validate inputs
            self._validate_inputs(video_url, max_tokens, summary_language)

            # Extract video ID
            video_id = self.url_validator.extract_video_id(video_url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")

            log_event(
                logger,
                logging.INFO,
                "summary_request_started",
                video_id=video_id,
                requested_summary_language=summary_language,
                include_transcript=include_transcript,
                allow_summary_failure=allow_summary_failure,
                save_to_file=save_to_file,
                max_tokens=max_tokens,
                current_model_name=self.model_name,
                force_regenerate=force_regenerate,
            )

            # Extract transcript
            (
                video_id,
                video_lang,
                transcript,
                transcript_stats,
            ) = self.transcript_extractor.get_transcript(video_id, include_stats=True)
            logger.info(f"Extracted transcript for video {video_id}")
            requested_summary_language = summary_language or video_lang

            # Summary cache keys must include transcript and output language so
            # switching the requested summary language cannot return stale data.
            summary_path = None
            if not force_regenerate:
                summary_path = self.file_handler.get_summary_path(
                    video_id, video_lang, requested_summary_language
                )
            summary = None
            summary_error = None

            if summary_path and summary_path.exists():
                logger.info(f"Found existing summary for video {video_id}")
                summary_record = self.file_handler.load_summary_record(summary_path)
                if summary_record is not None:
                    summary = summary_record["summary"]
                    summary_model_name = summary_record["metadata"].get("model_name")
                    summary_loaded_from_cache = summary is not None

            # Generate summary if not cached
            if summary is None:
                try:
                    generation_started_at = perf_counter()
                    summary = self.summarizer.summarize(
                        transcript, requested_summary_language, max_tokens
                    )
                    summary_generation_ms = round(
                        (perf_counter() - generation_started_at) * 1000, 3
                    )
                    summary_model_name = self.model_name
                    logger.info(f"Generated summary for video {video_id}")
                except Exception as e:
                    summary_generation_ms = round(
                        (perf_counter() - generation_started_at) * 1000, 3
                    )
                    summary_error = str(e)
                    logger.error(f"Error during summarization: {summary_error}")
                    if not (include_transcript and allow_summary_failure):
                        raise

            if summary:
                if not summary_model_name:
                    summary_model_status = "unknown"
                elif summary_model_name == self.model_name:
                    summary_model_status = "current"
                else:
                    summary_model_status = "stale"

            # Save summary if requested and newly generated
            if save_to_file and summary and not summary_loaded_from_cache:
                summary_metadata = dict(metadata or {})
                summary_metadata["model_name"] = self.model_name
                self.file_handler.save_summary(
                    video_id,
                    video_lang,
                    requested_summary_language,
                    summary,
                    summary_metadata,
                )
                logger.info(f"Saved summary for video {video_id}")

            total_ms = round((perf_counter() - request_started_at) * 1000, 3)
            status = "success" if summary else "partial_success"
            log_event(
                logger,
                logging.INFO,
                "summary_request_completed",
                video_id=video_id,
                transcript_language=video_lang,
                summary_language=requested_summary_language,
                transcript_cache_hit=transcript_stats["cache_hit"],
                transcript_cache_source=transcript_stats["cache_source"],
                transcript_fetch_attempts=transcript_stats["fetch_attempts"],
                transcript_duration_ms=transcript_stats["duration_ms"],
                transcript_chars=transcript_stats["transcript_chars"],
                summary_cache_hit=summary_loaded_from_cache,
                summary_model_name=summary_model_name,
                current_model_name=self.model_name,
                summary_model_status=summary_model_status,
                force_regenerate=force_regenerate,
                summary_generation_ms=summary_generation_ms,
                summary_chars=len(summary) if summary else 0,
                summary_saved=bool(
                    save_to_file and summary and not summary_loaded_from_cache
                ),
                summary_error=summary_error,
                status=status,
                total_duration_ms=total_ms,
            )

            if include_transcript:
                return {
                    "video_id": video_id,
                    "transcript_language": video_lang,
                    "summary_language": requested_summary_language,
                    "transcript": transcript,
                    "summary": summary,
                    "summary_error": summary_error,
                    "summary_cache_hit": summary_loaded_from_cache,
                    "summary_model_name": summary_model_name,
                    "current_model_name": self.model_name,
                    "summary_model_status": summary_model_status,
                }

            if summary is None:
                raise ValueError("Summary could not be generated.")

            return summary

        except Exception as e:
            total_ms = round((perf_counter() - request_started_at) * 1000, 3)
            log_event(
                logger,
                logging.ERROR,
                "summary_request_failed",
                video_id=video_id,
                requested_summary_language=requested_summary_language,
                current_model_name=self.model_name,
                force_regenerate=force_regenerate,
                error=str(e),
                error_type=type(e).__name__,
                total_duration_ms=total_ms,
            )
            logger.error(f"Error summarizing video: {str(e)}")
            raise

    def get_available_models(self) -> list:
        """Get list of available Gemini models."""
        return self.summarizer.get_available_models()

    def cleanup_old_summaries(self, days: int) -> None:
        """Clean up summaries older than specified days."""
        self.file_handler.cleanup_old_summaries(days)
