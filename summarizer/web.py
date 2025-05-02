from flask import Flask, request, jsonify, render_template
from .app import YouTubeSummarizer
import os
from .cli import load_environment
from .config import Config

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
        max_tokens = data.get("max_tokens")

        if not video_url:
            return jsonify({"error": "Video URL is required"}), 400

        summary = summarizer.summarize_video(
            video_url=video_url,
            max_tokens=max_tokens,
        )

        return jsonify({"summary": summary, "status": "success"})

    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100)
