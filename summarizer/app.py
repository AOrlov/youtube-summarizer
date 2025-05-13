import os
from typing import Any, Dict, Optional

from .file_handler import FileHandler
from .gemini import GeminiSummarizer
from .utils import get_logger
from .youtube import YouTubeTranscriptExtractor, YouTubeURLValidator

logger = get_logger(__name__)


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
        self.transcript_extractor = YouTubeTranscriptExtractor(
            api_key=youtube_api_key)
        self.summarizer = GeminiSummarizer(gemini_api_key, model_name)
        self.file_handler = FileHandler(output_dir)

        logger.info(f"Initialized YouTubeSummarizer with model: {model_name}")

    def _validate_inputs(self, video_url: str, max_tokens: Optional[int]) -> None:
        """Validate input parameters."""
        if not self.url_validator.is_valid_url(video_url):
            raise ValueError("Invalid YouTube URL")

        if max_tokens is not None and max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

    def summarize_video(
        self,
        video_url: str,
        max_tokens: Optional[int] = None,
        save_to_file: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Extract transcript and generate summary for a YouTube video.

        Args:
            video_url: The URL of the YouTube video
            max_tokens: Optional maximum number of tokens for the summary
            save_to_file: Whether to save the summary to a file
            metadata: Optional metadata to save with the summary

        Returns:
            The generated summary

        Raises:
            ValueError: If the video URL is invalid
            Exception: If there's an error during transcript extraction or summarization
        """
        try:
            # Validate inputs
            self._validate_inputs(video_url, max_tokens)

            logger.info(f"Processing video: {video_url}")

            # Extract video ID
            video_id = self.url_validator.extract_video_id(video_url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")

            video_lang = self.transcript_extractor.get_video_language(video_id)

            def get_cached_summary_if_available(video_id: str, video_lang: str) -> Optional[str]:
                existing_summary = self.file_handler.get_summary_path(
                    video_id, video_lang
                )
                if existing_summary and os.path.exists(existing_summary):
                    logger.info(f"Found existing summary for video {video_id}")
                    with open(existing_summary, "r") as f:
                        return f.read()

            # Check for existing summary if video language is available
            if video_lang:
                cached = get_cached_summary_if_available(video_id, video_lang)
                if cached:
                    return cached

            # Extract transcript
            video_id, video_lang, transcript = self.transcript_extractor.get_transcript(
                video_id, video_lang
            )
            logger.info(f"Extracted transcript for video {video_id}")

            # Generate summary
            summary = self.summarizer.summarize(
                transcript, video_lang, max_tokens)
            logger.info(f"Generated summary for video {video_id}")

            # Save summary if requested
            if save_to_file:
                self.file_handler.save_summary(
                    video_id, video_lang, summary, metadata)
                logger.info(f"Saved summary for video {video_id}")

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
