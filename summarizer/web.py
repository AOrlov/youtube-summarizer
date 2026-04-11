import logging
import os
from urllib.parse import urlencode

import flask
from dotenv import load_dotenv

from .app import YouTubeSummarizer
from .config import Config
from .youtube import YouTubeURLValidator

ALLOWED_SUMMARY_LANGUAGES = {"en", "ru"}
SUMMARY_LANGUAGE_OPTIONS = (
    ("ru", "Russian"),
    ("en", "English"),
)
DEFAULT_SUMMARY_LANGUAGE = "ru"
MIRRORED_YOUTUBE_HOSTS = {
    "youtube.home",
    "www.youtube.home",
    "m.youtube.home",
}


def load_environment():
    """Load environment variables from the specified file."""
    env_file = os.getenv("ENV_FILE")
    if env_file and os.path.exists(env_file):
        load_dotenv(env_file)
        logging.info("Loaded environment variables from %s", env_file)
    else:
        logging.warning("No environment file specified or file not found")


app = flask.Flask(__name__)

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


def is_mirrored_youtube_host(host):
    """Return True when the request host is one of the mirrored youtube.home hosts."""
    return host.split(":", 1)[0].lower() in MIRRORED_YOUTUBE_HOSTS


def get_explicit_video_url(query_args):
    """Return the explicit video URL query parameter when present."""
    return query_args.get("video_url")


def get_requested_video_url(path, query_args, allow_reconstructed_url=True):
    """Return a reconstructed video URL for the current request path."""
    if not allow_reconstructed_url:
        return None

    normalized_path = f"/{path.lstrip('/')}" if path else "/"
    filtered_query_items = []

    for key, values in query_args.lists():
        if key in {"video_url", "summary_language"}:
            continue
        for value in values:
            filtered_query_items.append((key, value))

    candidate_url = f"https://youtube.com{normalized_path}"
    if filtered_query_items:
        candidate_url = f"{candidate_url}?{urlencode(filtered_query_items, doseq=True)}"

    if url_validator.is_valid_url(candidate_url):
        return candidate_url

    return None


def get_requested_summary_language(query_args):
    """Return a valid requested summary language or the default."""
    summary_language = query_args.get("summary_language")
    if summary_language in ALLOWED_SUMMARY_LANGUAGES:
        return summary_language

    return DEFAULT_SUMMARY_LANGUAGE


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def index(path):
    mirrored_host = is_mirrored_youtube_host(flask.request.host)
    explicit_video_url = get_explicit_video_url(flask.request.args)
    reconstructed_video_url = get_requested_video_url(
        path,
        flask.request.args,
        allow_reconstructed_url=mirrored_host,
    )
    requested_video_url = explicit_video_url or reconstructed_video_url
    requested_summary_language = get_requested_summary_language(flask.request.args)

    if path:
        if path == "api/summarize":
            flask.abort(405)
        if path.startswith("api/") or "." in path.rsplit("/", 1)[-1]:
            flask.abort(404)
        if not mirrored_host:
            flask.abort(404)
        if reconstructed_video_url:
            return flask.redirect(
                flask.url_for(
                    "index",
                    video_url=requested_video_url,
                    summary_language=requested_summary_language,
                )
            )

    return flask.render_template(
        "index.html",
        allow_query_autosubmit=not path,
        default_summary_language=requested_summary_language,
        summary_language_options=SUMMARY_LANGUAGE_OPTIONS,
    )


@app.route("/api/summarize", methods=["POST"])
def summarize():
    try:
        data = flask.request.get_json(silent=True) or {}
        video_url = data.get("video_url")
        summary_language = data.get("summary_language")

        if not video_url:
            return flask.jsonify({"error": "Video URL is required"}), 400

        if (
            summary_language is not None
            and summary_language not in ALLOWED_SUMMARY_LANGUAGES
        ):
            return (
                flask.jsonify(
                    {
                        "error": "summary_language must be one of: en, ru",
                        "status": "error",
                    }
                ),
                400,
            )

        result = summarizer.summarize_video(
            video_url=video_url,
            max_tokens=config.max_tokens,
            include_transcript=True,
            allow_summary_failure=True,
            summary_language=summary_language,
        )

        status = "success" if result.get("summary") else "partial_success"
        transcript_language = result.get("transcript_language") or result.get(
            "language"
        )
        response_summary_language = (
            result.get("summary_language") or transcript_language
        )

        response_payload = {
            "summary": result.get("summary"),
            "transcript": result.get("transcript"),
            "transcript_language": transcript_language,
            "summary_language": response_summary_language,
            "language": transcript_language,
            "video_id": result.get("video_id"),
            "summary_error": result.get("summary_error"),
            "status": status,
        }

        return flask.jsonify(response_payload)

    except Exception as e:
        status_code = 400 if isinstance(e, ValueError) else 500
        return flask.jsonify({"error": str(e), "status": "error"}), status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100)
