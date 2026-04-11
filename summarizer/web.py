import logging
import os
from urllib.parse import urlencode

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for

from .app import YouTubeSummarizer
from .config import Config
from .youtube import YouTubeURLValidator


def load_environment():
    """Load environment variables from the specified file."""
    env_file = os.getenv("ENV_FILE")
    if env_file and os.path.exists(env_file):
        load_dotenv(env_file)
        logging.info("Loaded environment variables from %s", env_file)
    else:
        logging.warning("No environment file specified or file not found")

app = Flask(__name__)

load_environment()
config = Config()
url_validator = YouTubeURLValidator()

# Initialize the summarizer
summarizer = YouTubeSummarizer(
    gemini_api_key=config.gemini_api_token,
    model_name=config.gemini_model,
    youtube_api_key=config.youtube_api_key,
    output_dir=config.output_dir,
)


def get_requested_video_url(path, query_args):
    """Return an explicit or reconstructed video URL for the current request."""
    explicit_video_url = query_args.get("video_url")
    if explicit_video_url:
        return explicit_video_url

    normalized_path = f"/{path.lstrip('/')}" if path else "/"
    filtered_query_items = []

    for key, values in query_args.lists():
        if key == "video_url":
            continue
        for value in values:
            filtered_query_items.append((key, value))

    candidate_url = f"https://youtube.com{normalized_path}"
    if filtered_query_items:
        candidate_url = (
            f"{candidate_url}?{urlencode(filtered_query_items, doseq=True)}"
        )

    if url_validator.is_valid_url(candidate_url):
        return candidate_url

    return None


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def index(path):
    requested_video_url = get_requested_video_url(path, request.args)
    if path and requested_video_url:
        return redirect(url_for("index", video_url=requested_video_url))

    return render_template("index.html")


@app.route("/api/summarize", methods=["POST"])
def summarize():
    try:
        data = request.get_json()
        video_url = data.get("video_url")

        if not video_url:
            return jsonify({"error": "Video URL is required"}), 400

        result = summarizer.summarize_video(
            video_url=video_url,
            max_tokens=config.max_tokens,
            include_transcript=True,
            allow_summary_failure=True,
        )

        status = "success" if result.get("summary") else "partial_success"

        response_payload = {
            "summary": result.get("summary"),
            "transcript": result.get("transcript"),
            "language": result.get("language"),
            "video_id": result.get("video_id"),
            "summary_error": result.get("summary_error"),
            "status": status,
        }

        return jsonify(response_payload)

    except Exception as e:
        status_code = 400 if isinstance(e, ValueError) else 500
        return jsonify({"error": str(e), "status": "error"}), status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100)
