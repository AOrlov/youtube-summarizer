from typing import Any, Dict, Optional, Union

from .file_handler import FileHandler
from .gemini import GeminiSummarizer
from .utils import get_logger
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
    ):
        """
        Initialize the summarizer.

        Args:
            gemini_api_key: The Gemini API key
            language: The language code for the transcript
            output_dir: Directory to save summaries
            model_name: The name of the Gemini model to use
        """
        self.url_validator = YouTubeURLValidator()
        self.transcript_extractor = YouTubeTranscriptExtractor(api_key=youtube_api_key)
        self.summarizer = GeminiSummarizer(gemini_api_key, model_name)
        self.file_handler = FileHandler(output_dir)

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

        Returns:
            The generated summary or a dictionary containing both summary and transcript when requested

        Raises:
            ValueError: If the video URL is invalid
            Exception: If there's an error during transcript extraction or summarization
        """
        try:
            # Validate inputs
            self._validate_inputs(video_url, max_tokens, summary_language)

            logger.info(f"Processing video: {video_url}")

            # Extract video ID
            video_id = self.url_validator.extract_video_id(video_url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")

            # Extract transcript
            video_id, video_lang, transcript = self.transcript_extractor.get_transcript(
                video_id
            )
            logger.info(f"Extracted transcript for video {video_id}")
            requested_summary_language = summary_language or video_lang

            # Summary cache keys must include transcript and output language so
            # switching the requested summary language cannot return stale data.
            summary_path = self.file_handler.get_summary_path(
                video_id, video_lang, requested_summary_language
            )
            summary = None
            summary_error = None
            summary_loaded_from_cache = False

            if summary_path and summary_path.exists():
                logger.info(f"Found existing summary for video {video_id}")
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary = f.read()
                summary_loaded_from_cache = True

            # Generate summary if not cached
            if summary is None:
                try:
                    summary = self.summarizer.summarize(
                        transcript, requested_summary_language, max_tokens
                    )
                    logger.info(f"Generated summary for video {video_id}")
                except Exception as e:
                    summary_error = str(e)
                    logger.error(f"Error during summarization: {summary_error}")
                    if not (include_transcript and allow_summary_failure):
                        raise

            # Save summary if requested and newly generated
            if save_to_file and summary and not summary_loaded_from_cache:
                self.file_handler.save_summary(
                    video_id,
                    video_lang,
                    requested_summary_language,
                    summary,
                    metadata,
                )
                logger.info(f"Saved summary for video {video_id}")

            if include_transcript:
                return {
                    "video_id": video_id,
                    "transcript_language": video_lang,
                    "summary_language": requested_summary_language,
                    "transcript": transcript,
                    "summary": summary,
                    "summary_error": summary_error,
                }

            if summary is None:
                raise ValueError("Summary could not be generated.")

            return summary

        except Exception as e:
            logger.error(f"Error summarizing video: {str(e)}")
            raise

    def get_available_models(self) -> list:
        """Get list of available Gemini models."""
        return self.summarizer.get_available_models()

    def cleanup_old_summaries(self, days: int) -> None:
        """Clean up summaries older than specified days."""
        self.file_handler.cleanup_old_summaries(days)
