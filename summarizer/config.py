import os
from typing import Optional
from dotenv import load_dotenv

class Config:
    """Configuration management class for the YouTube Transcript Summarizer."""
    
    def __init__(self):
        """Initialize configuration by loading environment variables."""
        load_dotenv()
        self._validate_required_vars()
        
    def _validate_required_vars(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = ["GEMINI_API_TOKEN"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
    
    @property
    def gemini_api_token(self) -> str:
        """Get the Gemini API token."""
        return os.getenv("GEMINI_API_TOKEN", "")
    
    @property
    def youtube_api_key(self) -> Optional[str]:
        """Get the YouTube API key if set."""
        return os.getenv("YOUTUBE_API_KEY")
    
    @property
    def language(self) -> str:
        """Get the language setting, defaulting to English."""
        return os.getenv("LANGUAGE", "en")
    
    @property
    def log_level(self) -> str:
        """Get the log level, defaulting to INFO."""
        return os.getenv("LOG_LEVEL", "INFO")
