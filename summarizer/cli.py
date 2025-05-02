import os
import sys
import json
import logging
from typing import Optional
from dotenv import load_dotenv
from .app import YouTubeSummarizer
from .utils import setup_logging
from .config import Config


def parse_metadata(metadata_str: str) -> dict:
    """Parse metadata JSON string into a dictionary."""
    try:
        return json.loads(metadata_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid metadata JSON: {e}")


def load_environment():
    """Load environment variables from the specified file."""
    env_file = os.getenv("ENV_FILE")
    if env_file and os.path.exists(env_file):
        load_dotenv(env_file)
        logging.info(f"Loaded environment variables from {env_file}")
    else:
        logging.warning("No environment file specified or file not found")


def main():
    """Main entry point for the CLI."""
    load_environment()
    setup_logging()

    import argparse

    parser = argparse.ArgumentParser(
        description="YouTube Video Summarizer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("url", nargs="?", help="YouTube video URL to summarize")
    parser.add_argument(
        "--language",
        default=os.getenv("LANGUAGE", "en"),
        help="Language code for the summary",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.getenv("MAX_TOKENS", "500")),
        help="Maximum number of tokens for the summary",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("OUTPUT_DIR", "output"),
        help="Directory to save summaries",
    )
    parser.add_argument(
        "--no-save", action="store_true", help="Disable saving summary to file"
    )

    parser.add_argument(
        "--list-models", action="store_true", help="List available Gemini models"
    )
    parser.add_argument(
        "--cleanup",
        type=int,
        metavar="DAYS",
        help="Clean up summaries older than specified days",
    )

    args = parser.parse_args()
    config = Config()

    summarizer = YouTubeSummarizer(
        gemini_api_key=config.gemini_api_token,
        model_name=config.gemini_model,
        output_dir=args.output_dir,
        youtube_api_key=config.youtube_api_key,
    )

    if args.list_models:
        try:
            models = summarizer.get_available_models()
            print("Available Gemini models:")
            for model in models:
                print(f"- {model}")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Failed to list models: {e}")
            sys.exit(1)

    if not args.url:
        parser.error("URL is required")

    try:
        summary = summarizer.summarize_video(
            args.url,
            max_tokens=args.max_tokens,
            save_to_file=not args.no_save,
        )
        print(summary)
    except Exception as e:
        logging.error(f"Failed to summarize video: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
