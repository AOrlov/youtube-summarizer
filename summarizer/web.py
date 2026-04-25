import logging
import os
import time
from urllib.parse import urlencode

import flask
from dotenv import load_dotenv

from .app import YouTubeSummarizer
from .config import Config
from .utils import get_logger, log_event
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

logger = get_logger(__name__)


def load_environment():
    """Load environment variables from the specified file."""
    env_file = os.getenv("ENV_FILE")
    if env_file and os.path.exists(env_file):
        load_dotenv(env_file)
        log_event(logger, logging.INFO, "environment_loaded", env_file=env_file)
    else:
        log_event(logger, logging.WARNING, "environment_missing", env_file=env_file)


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
    transcript_cache_dir=config.transcript_cache_dir,
)


@app.before_request
def start_request_timer():
    flask.g.request_started_at = time.perf_counter()


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
            log_event(
                logger,
                logging.INFO,
                "mirrored_request_redirect",
                host=flask.request.host,
                path=flask.request.path,
                video_id=url_validator.extract_video_id(requested_video_url),
                summary_language=requested_summary_language,
                explicit_video_url=bool(explicit_video_url),
            )
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
        model_name=config.gemini_model,
        summary_language_options=SUMMARY_LANGUAGE_OPTIONS,
    )


@app.route("/api/summarize", methods=["POST"])
def summarize():
    try:
        data = flask.request.get_json(silent=True) or {}
        video_url = data.get("video_url")
        summary_language = data.get("summary_language")
        video_id = url_validator.extract_video_id(video_url) if video_url else None

        if not video_url:
            log_event(
                logger,
                logging.WARNING,
                "api_summarize_invalid_request",
                reason="missing_video_url",
                host=flask.request.host,
                path=flask.request.path,
            )
            return flask.jsonify({"error": "Video URL is required"}), 400

        if (
            summary_language is not None
            and summary_language not in ALLOWED_SUMMARY_LANGUAGES
        ):
            log_event(
                logger,
                logging.WARNING,
                "api_summarize_invalid_request",
                reason="invalid_summary_language",
                host=flask.request.host,
                path=flask.request.path,
                video_id=video_id,
                summary_language=summary_language,
            )
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

        request_duration_ms = round(
            (time.perf_counter() - flask.g.request_started_at) * 1000, 3
        )
        log_event(
            logger,
            logging.INFO,
            "api_summarize_response",
            host=flask.request.host,
            path=flask.request.path,
            video_id=response_payload["video_id"],
            transcript_language=response_payload["transcript_language"],
            summary_language=response_payload["summary_language"],
            status=response_payload["status"],
            status_code=200,
            summary_available=bool(response_payload["summary"]),
            transcript_available=bool(response_payload["transcript"]),
            request_duration_ms=request_duration_ms,
        )

        return flask.jsonify(response_payload)

    except Exception as e:
        status_code = 400 if isinstance(e, ValueError) else 500
        request_duration_ms = round(
            (time.perf_counter() - flask.g.request_started_at) * 1000, 3
        )
        log_event(
            logger,
            logging.ERROR,
            "api_summarize_response",
            host=flask.request.host,
            path=flask.request.path,
            status="error",
            status_code=status_code,
            error=str(e),
            error_type=type(e).__name__,
            request_duration_ms=request_duration_ms,
        )
        return flask.jsonify({"error": str(e), "status": "error"}), status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100)
