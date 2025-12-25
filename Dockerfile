# syntax=docker/dockerfile:1.6
FROM python:3.13-slim AS wheels

WORKDIR /wheels

COPY requirements.txt .
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --prefer-binary -r requirements.txt gunicorn

FROM python:3.13-slim

WORKDIR /app

# Create a non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy requirements first to leverage Docker cache
COPY --from=wheels /wheels /wheels
COPY requirements.txt .
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install --no-index --find-links=/wheels -r requirements.txt gunicorn \
    && rm -rf /wheels

# Copy the rest of the application
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN install -d -o appuser -g appuser /app/output /app/cache

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=summarizer.web
ENV FLASK_ENV=production
ENV WEB_CONCURRENCY=1

# Switch to non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application with Gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:8080 --workers ${WEB_CONCURRENCY:-1} --timeout 120 summarizer.web:app"]
