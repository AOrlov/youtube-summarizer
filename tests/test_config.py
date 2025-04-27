import os
import pytest
from summarizer.config import Config

def test_config_initialization():
    """Test that Config initializes without error when required vars are set."""
    os.environ["GEMINI_API_TOKEN"] = "test_token"
    config = Config()
    assert config.gemini_api_token == "test_token"
    assert config.language == "en"  # Default value
    assert config.log_level == "INFO"  # Default value

def test_missing_required_vars():
    """Test that Config raises ValueError when required vars are missing."""
    if "GEMINI_API_TOKEN" in os.environ:
        del os.environ["GEMINI_API_TOKEN"]
    with pytest.raises(ValueError):
        Config()

def test_optional_vars():
    """Test that optional variables work correctly."""
    os.environ["GEMINI_API_TOKEN"] = "test_token"
    os.environ["YOUTUBE_API_KEY"] = "youtube_key"
    os.environ["LANGUAGE"] = "es"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    config = Config()
    assert config.youtube_api_key == "youtube_key"
    assert config.language == "es"
    assert config.log_level == "DEBUG"

def test_default_values():
    """Test that default values are used when optional vars are not set."""
    os.environ["GEMINI_API_TOKEN"] = "test_token"
    if "YOUTUBE_API_KEY" in os.environ:
        del os.environ["YOUTUBE_API_KEY"]
    if "LANGUAGE" in os.environ:
        del os.environ["LANGUAGE"]
    if "LOG_LEVEL" in os.environ:
        del os.environ["LOG_LEVEL"]
    
    config = Config()
    assert config.youtube_api_key is None
    assert config.language == "en"
    assert config.log_level == "INFO" 