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

1. Build and run the Docker container:
# 1. Create a `.env` file in the project root (or use an existing one) and add your Gemini API key:
GEMINI_API_KEY=your-api-key-here

# 2. Start the application with Docker Compose:
docker-compose --env-file .env up --build

2. Access the web interface at http://localhost:5100. You can also open the page with a
   `video_url` query parameter (for example http://localhost:5100/?video_url=https://www.youtube.com/watch?v=demo)
   and the form will auto-fill and trigger summarization immediately.

The web interface provides a simple form where you can:
- Enter a YouTube video URL
- Optionally specify the maximum number of tokens for the summary
- Submit to generate a summary

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
