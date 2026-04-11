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
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```
For development tools:
```bash
pip install -r requirements-dev.txt
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
- Choose the summary output language from English or Russian
- Optionally specify the maximum number of tokens for the summary
- Submit to generate a summary

Supported web entry points:
- Legacy query flow: open `http://localhost:5100/?video_url=https://www.youtube.com/watch?v=demo` and the page will prefill the form and auto-submit immediately. This remains the entrypoint used by the Firefox extension and is also useful for local/manual testing.
- Mirrored `youtube.home` flow: if you expose the app on `youtube.home`, direct video routes such as `http://youtube.home/watch?v=dQw4w9WgXcQ` or `http://youtube.home/shorts/dQw4w9WgXcQ` are normalized into the canonical YouTube URL and auto-submitted without manually pasting the video link.
- Summary language selection: the dropdown controls the summary output language independently from the transcript language and currently supports only English (`en`) and Russian (`ru`).

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
summarizer = YouTubeSummarizer(api_key="your-api-key", language="en")

# Generate a summary
summary = summarizer.summarize_video("https://www.youtube.com/watch?v=example")
print(summary)
```

## Development

### Running Tests

```bash
pytest tests/
```

### Logging

The application uses Python's built-in logging module with the following configuration:
- Log level: INFO
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Output: Console (stdout)

## Requirements

- Python 3.8+
- google-genai
- youtube-transcript-api
- Flask (for web interface)
- pytest/black/isort (for development)

## License

MIT License
