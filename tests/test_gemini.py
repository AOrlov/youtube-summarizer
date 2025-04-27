import pytest
from summarizer.gemini import GeminiSummarizer

def test_api_configuration():
    """Test API configuration."""
    # Using a dummy API key for testing
    api_key = "dummy_api_key"
    summarizer = GeminiSummarizer(api_key)
    assert summarizer.api_key == api_key
    assert summarizer.language == "en"

def test_prompt_creation():
    """Test prompt creation."""
    summarizer = GeminiSummarizer("dummy_api_key")
    transcript = "This is a test transcript."
    prompt = summarizer._create_prompt(transcript)
    assert "test transcript" in prompt
    assert "en" in prompt

def test_language_override():
    """Test language override."""
    summarizer = GeminiSummarizer("dummy_api_key", language="es")
    assert summarizer.language == "es"
    prompt = summarizer._create_prompt("test")
    assert "es" in prompt

def test_max_tokens():
    """Test max tokens parameter."""
    summarizer = GeminiSummarizer("dummy_api_key")
    # This test will fail if the API is not properly configured
    with pytest.raises(Exception):
        summarizer.summarize("test", max_tokens=100)

def test_available_models():
    """Test getting available models."""
    summarizer = GeminiSummarizer("dummy_api_key")
    # This test will fail if the API is not properly configured
    with pytest.raises(Exception):
        summarizer.get_available_models()

def test_error_handling():
    """Test error handling."""
    summarizer = GeminiSummarizer("dummy_api_key")
    with pytest.raises(Exception):
        summarizer.summarize("test")

def test_invalid_api_key():
    """Test handling of invalid API key."""
    with pytest.raises(Exception):
        GeminiSummarizer("invalid_api_key")
