# YouTube Transcript Summarizer

A Python application that extracts transcripts from YouTube videos and generates summaries using the Gemini API.

## Features

- Extract transcripts from YouTube videos
- Generate summaries using Google's Gemini API
- Support for multiple languages
- Configurable summary length
- Command-line interface
- Comprehensive logging

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

4. Set up your Gemini API key:
```bash
export GEMINI_API_KEY="your-api-key-here"
```

## Usage

### Command Line Interface

The simplest way to use the summarizer is through the command-line interface:

```bash
python -m summarizer.cli "https://www.youtube.com/watch?v=example"
```

#### Options

- `--language`, `-l`: Specify the language for summarization (default: "en")
- `--max-tokens`, `-t`: Set maximum number of tokens for the summary
- `--list-models`: List available Gemini models

Example with options:
```bash
python -m summarizer.cli "https://www.youtube.com/watch?v=example" --language es --max-tokens 500
```

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
- google-generativeai
- youtube-transcript-api
- pytest (for development)

## License

MIT License