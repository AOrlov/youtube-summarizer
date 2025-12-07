# syntax=docker/dockerfile:1.6
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y \
        build-essential \
        && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt gunicorn

# Copy the rest of the application
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p output cache && \
    chown -R appuser:appuser output cache

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=summarizer.web
ENV FLASK_ENV=production

# Switch to non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "120", "summarizer.web:app"] 
