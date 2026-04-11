from types import SimpleNamespace

import pytest

from summarizer.gemini import GeminiSummarizer


class FakeModelsAPI:
    def __init__(self, response_text="Generated summary"):
        self.response_text = response_text
        self.generate_calls = []
        self.available_models = [
            SimpleNamespace(name="models/gemini-2.0-flash"),
            SimpleNamespace(name="models/gemini-1.5-flash"),
        ]

    def generate_content(self, *, model, contents, config):
        self.generate_calls.append(
            {"model": model, "contents": contents, "config": config}
        )
        return SimpleNamespace(text=self.response_text)

    def list(self):
        return self.available_models


class FakeClient:
    def __init__(self, models_api):
        self.models = models_api


@pytest.fixture
def fake_models_api():
    return FakeModelsAPI()


@pytest.fixture
def fake_client(fake_models_api):
    return FakeClient(fake_models_api)


@pytest.fixture(autouse=True)
def fake_gemini_client(monkeypatch, fake_client):
    monkeypatch.setattr(
        GeminiSummarizer,
        "_configure_api",
        lambda self: fake_client,
    )


def test_api_configuration_uses_provided_model_name(fake_client):
    summarizer = GeminiSummarizer("dummy_api_key", "gemini-2.0-flash")

    assert summarizer.api_key == "dummy_api_key"
    assert summarizer.model_name == "models/gemini-2.0-flash"
    assert summarizer.client is fake_client


def test_prompt_creation_uses_requested_summary_language():
    summarizer = GeminiSummarizer("dummy_api_key")

    prompt = summarizer._create_prompt("This is a test transcript.", "ru")

    assert "This is a test transcript." in prompt
    assert "Output in Russian language:" in prompt


def test_summarize_uses_requested_summary_language_and_max_tokens(
    fake_models_api,
):
    summarizer = GeminiSummarizer("dummy_api_key", "gemini-2.0-flash")

    result = summarizer.summarize("Transcript text", "ru", max_tokens=123)

    assert result == "Generated summary"
    assert len(fake_models_api.generate_calls) == 1

    call = fake_models_api.generate_calls[0]
    assert call["model"] == "models/gemini-2.0-flash"
    assert "Transcript text" in call["contents"]
    assert "Output in Russian language:" in call["contents"]
    assert call["config"].max_output_tokens == 123


def test_available_models_returns_client_model_names():
    summarizer = GeminiSummarizer("dummy_api_key")

    models = summarizer.get_available_models()

    assert models == ["models/gemini-2.0-flash", "models/gemini-1.5-flash"]


def test_empty_summary_response_raises_value_error(fake_models_api):
    fake_models_api.response_text = ""
    summarizer = GeminiSummarizer("dummy_api_key")

    with pytest.raises(ValueError, match="empty response"):
        summarizer.summarize("Transcript text", "en")
