import pytest

from summarizer.config import Config


def _set_required_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test_token")
    monkeypatch.setenv("YOUTUBE_API_KEY", "youtube_key")


def test_config_initialization(monkeypatch):
    """Test that Config initializes without error when required vars are set."""
    _set_required_env(monkeypatch)

    config = Config()

    assert config.gemini_api_token == "test_token"
    assert config.youtube_api_key == "youtube_key"
    assert config.language == "en"
    assert config.log_level == "INFO"


def test_missing_required_vars(monkeypatch):
    """Test that Config raises ValueError when required vars are missing."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    with pytest.raises(ValueError):
        Config()


def test_optional_vars(monkeypatch):
    """Test that optional variables work correctly."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("LANGUAGE", "es")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    config = Config()

    assert config.youtube_api_key == "youtube_key"
    assert config.language == "es"
    assert config.log_level == "DEBUG"


def test_default_values(monkeypatch):
    """Test that default values are used when optional vars are not set."""
    _set_required_env(monkeypatch)
    monkeypatch.delenv("LANGUAGE", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    config = Config()

    assert config.youtube_api_key == "youtube_key"
    assert config.language == "en"
    assert config.log_level == "INFO"
