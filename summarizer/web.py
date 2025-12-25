import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from .app import YouTubeSummarizer
from .config import Config


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

# Initialize the summarizer
summarizer = YouTubeSummarizer(
    gemini_api_key=config.gemini_api_token,
    model_name=config.gemini_model,
    youtube_api_key=config.youtube_api_key,
    output_dir=config.output_dir,
)


@app.route("/")
def index():
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
