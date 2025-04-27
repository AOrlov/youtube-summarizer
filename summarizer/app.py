import os
import json
import logging
from typing import Optional, Dict, Any
from .youtube import YouTubeURLValidator, YouTubeTranscriptExtractor
from .gemini import GeminiSummarizer
from .file_handler import FileHandler
from .utils import get_logger

logger = get_logger(__name__)

class YouTubeSummarizer:
    """Main class for summarizing YouTube videos."""
    
    def __init__(
        self,
        gemini_api_key: str,
        language: str = "en",
        output_dir: str = "output",
        model_name: str = "gemini-1.5-flash-latest"
    ):
        """
        Initialize the summarizer.
        
        Args:
            gemini_api_key: The Gemini API key
            language: The language code for the transcript (default: "en")
            output_dir: Directory to save summaries (default: "output")
            model_name: The name of the Gemini model to use (default: "gemini-1.5-flash-latest")
        """
        self.url_validator = YouTubeURLValidator()
        self.transcript_extractor = YouTubeTranscriptExtractor(language)
        self.summarizer = GeminiSummarizer(gemini_api_key, language, model_name)
        self.file_handler = FileHandler(output_dir)
        
        logger.info(f"Initialized YouTubeSummarizer with language: {language}, model: {model_name}")
    
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
        metadata: Optional[Dict[str, Any]] = None
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
            
            # Check for existing summary
            if save_to_file:
                existing_summary = self.file_handler.get_summary_path(video_id)
                if existing_summary and os.path.exists(existing_summary):
                    logger.info(f"Found existing summary for video {video_id}")
                    with open(existing_summary, 'r') as f:
                        return f.read()
            
            # Extract transcript
            transcript = self.transcript_extractor.get_transcript(video_id)
            logger.info(f"Extracted transcript for video {video_id}")
            
            # Generate summary
            summary = self.summarizer.summarize(transcript, max_tokens)
            logger.info(f"Generated summary for video {video_id}")
            
            # Save summary if requested
            if save_to_file:
                self.file_handler.save_summary(video_id, summary, metadata)
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