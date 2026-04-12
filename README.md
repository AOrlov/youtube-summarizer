# YouTube Transcript Summarizer

A Python application that extracts transcripts from YouTube videos and generates summaries using the Gemini API.

## Features

- Extract transcripts from YouTube videos
- Generate summaries using Google's Gemini API
- Support for multiple languages
- Configurable summary length
- Comprehensive logging
- Web interface
- Docker support

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Summarizer.git
cd Summarizer
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Use Python 3.14.4 locally if possible. The Docker image runs on Python 3.14.4, and keeping local development on the same version avoids dependency-resolution drift.

3. Install dependencies:
```bash
./venv/bin/pip install -r requirements.txt
```
For development tools:
```bash
./venv/bin/pip install -r requirements-dev.txt
```

4. Set up your Gemini API key:
```bash
export GEMINI_API_KEY="your-api-key-here"
```

## Usage

### Web Interface

The application can be run as a web service using Docker:

1. Create a `.env` file in the project root (or use an existing one) and add your Gemini API key:
```bash
GEMINI_API_KEY=your-api-key-here
```

2. Start the application with Docker Compose:
```bash
docker-compose --env-file .env up --build
```

3. Access the web interface at http://localhost:5100.

The web interface provides a simple form where you can:
- Enter a YouTube video URL
- Choose the summary output language from Russian or English, with Russian selected by default in the web UI
- Optionally specify the maximum number of tokens for the summary
- Submit to generate a summary

Supported web entry points:
- Legacy query flow: open `http://localhost:5100/?video_url=https://www.youtube.com/watch?v=demo` and the page will prefill the form and auto-submit immediately. This remains the entrypoint used by the Firefox extension and is also useful for local/manual testing.
- Mirrored `youtube.home` flow: if you expose the app on `youtube.home`, direct video routes such as `http://youtube.home/watch?v=dQw4w9WgXcQ` or `http://youtube.home/shorts/dQw4w9WgXcQ` are normalized into the canonical YouTube URL and auto-submitted without manually pasting the video link.
- Summary language selection: the dropdown controls the summary output language independently from the transcript language, supports only Russian (`ru`) and English (`en`), and defaults to Russian in the web UI.

### Firefox Extension

- The Firefox WebExtension lives in `extensions/firefox`.
- Load it temporarily via `about:debugging#/runtime/this-firefox` → `Load Temporary Add-on...` → select `extensions/firefox/manifest.json`.
- Click the toolbar button while viewing a YouTube video to open the Summarizer UI in a new tab with the video URL pre-populated and automatically summarizing.
- The extension defaults to `http://localhost:5100/` as the Summarizer base. Adjust it from the extension's Options page if you host the app elsewhere.

### Python API

You can also use the summarizer programmatically:

```python
from summarizer.app import YouTubeSummarizer

# Initialize the summarizer
summarizer = YouTubeSummarizer(
    gemini_api_key="your-gemini-api-key",
    model_name="gemini-2.0-flash",
    output_dir="output",
    youtube_api_key="your-youtube-api-key",
)

# Generate a summary in a specific output language
summary = summarizer.summarize_video(
    "https://www.youtube.com/watch?v=example",
    summary_language="ru",
)
print(summary)

# Include transcript data and read the explicit language fields
result = summarizer.summarize_video(
    "https://www.youtube.com/watch?v=example",
    include_transcript=True,
    summary_language="en",
)
print(result["transcript_language"], result["summary_language"])
```

## Development

### Running Tests

```bash
./venv/bin/python -m pytest tests/
```

### Dependency Auditing

Run the dependency audit against the pinned requirements files:

```bash
./venv/bin/python -m pip_audit -r requirements.txt -r requirements-dev.txt --desc
./venv/bin/python -m pip check
```

Current notes:
- The project now targets Python 3.14.4 locally and in Docker.
- `requests` was removed from the direct requirements because it is not imported by the application code.
- `gunicorn` is now pinned in `requirements.txt` so the production server is included in audits.
- Runtime and dev dependencies are pinned to current releases that support Python 3.14.
- Re-run the audit after dependency changes instead of assuming a previously captured report is still current.

### Logging

The application emits single-line JSON logs to stdout so Loki can parse them reliably.

Common fields:
- Log level: INFO
- Output: Console (stdout)
- `event`: Stable event name such as `summary_request_completed`, `summary_request_failed`, `transcript_retrieved`, `api_summarize_response`
- `video_id`: YouTube video ID when available
- `summary_language` / `transcript_language`: Output and detected transcript languages
- `summary_cache_hit` / `transcript_cache_hit`: Cache hit booleans for summary and transcript reuse
- `summary_generation_ms` / `total_duration_ms`: Model-only latency and end-to-end request latency
- `status`: `success`, `partial_success`, or `error`

Sample LogQL queries:

```logql
{service_name="web"} | json | event="summary_request_completed"
```

```logql
sum by (summary_language) (
  count_over_time({service_name="web"} | json | event="summary_request_completed" [24h])
)
```

```logql
sum by (summary_cache_hit) (
  count_over_time({service_name="web"} | json | event="summary_request_completed" [24h])
)
```

```logql
quantile_over_time(
  0.95,
  {service_name="web"} | json | event="summary_request_completed" | unwrap total_duration_ms [24h]
)
```

```logql
topk(
  10,
  sum by (video_id) (
    count_over_time({service_name="web"} | json | event="summary_request_completed" [24h])
  )
)
```

## Requirements

- Python 3.14.4 for local development and Docker parity
- google-genai
- youtube-transcript-api
- Flask (for web interface)
- Gunicorn (for the production WSGI server)
- pytest/black/isort (for development)

## License

MIT License
