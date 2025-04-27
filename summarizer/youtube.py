import os
import re
import json
from typing import Optional, List, Dict
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from .utils import get_logger

logger = get_logger(__name__)

class YouTubeURLValidator:
    """Class for validating YouTube URLs and extracting video IDs."""
    
    # Regular expressions for different YouTube URL formats
    URL_PATTERNS = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&]+)',  # Standard URL
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([^/?]+)',    # Embed URL
        r'(?:https?://)?(?:www\.)?youtu\.be/([^/?]+)',            # Short URL
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([^/?]+)',       # Old format
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
        if parsed.netloc in ['www.youtube.com', 'youtube.com']:
            query = parse_qs(parsed.query)
            if 'v' in query:
                return query['v'][0]
        
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
    
    def __init__(self, language: str = "en", cache_dir: str = "cache/transcripts"):
        """
        Initialize the transcript extractor.
        
        Args:
            language: The language code for the transcript (default: "en")
            cache_dir: Directory to store cached transcripts (default: "cache/transcripts")
        """
        self.language = language
        self.cache_dir = cache_dir
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        logger.info(f"Initialized transcript cache in {cache_dir}")
    
    def _get_cache_path(self, video_id: str) -> str:
        """Get the path to the cached transcript file."""
        return os.path.join(self.cache_dir, f"{video_id}_{self.language}.json")
    
    def _load_from_cache(self, video_id: str) -> Optional[str]:
        """Load transcript from cache if available."""
        cache_path = self._get_cache_path(video_id)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded transcript from cache for video {video_id}")
                    return data['transcript']
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error reading cache for {video_id}: {str(e)}")
                return None
        return None
    
    def _save_to_cache(self, video_id: str, transcript: str) -> None:
        """Save transcript to cache."""
        cache_path = self._get_cache_path(video_id)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'video_id': video_id,
                    'language': self.language,
                    'transcript': transcript
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved transcript to cache for video {video_id}")
        except Exception as e:
            logger.warning(f"Error saving cache for {video_id}: {str(e)}")
    
    def get_transcript(self, video_id: str) -> str:
        """
        Get the transcript for a YouTube video.
        
        Args:
            video_id: The YouTube video ID
            
        Returns:
            The transcript text
            
        Raises:
            TranscriptsDisabled: If transcripts are disabled for the video
            NoTranscriptFound: If no transcript is available in the requested language
            Exception: For other errors
        """
        try:
            # Try to load from cache first
            cached_transcript = self._load_from_cache(video_id)
            if cached_transcript:
                return cached_transcript
            
            # If not in cache, fetch from YouTube
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_transcript([self.language])
            
            # Format the transcript as plain text
            transcript_data = transcript.fetch()
            formatted_transcript = "\n".join(
                f"{item['text']}" for item in transcript_data
            )
            
            # Save to cache
            self._save_to_cache(video_id, formatted_transcript)
            
            return formatted_transcript
            
        except TranscriptsDisabled:
            raise TranscriptsDisabled(f"Transcripts are disabled for video: {video_id}")
        except NoTranscriptFound:
            raise NoTranscriptFound(
                video_id=video_id,
                requested_language_codes=[self.language],
                transcript_data=[]
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
