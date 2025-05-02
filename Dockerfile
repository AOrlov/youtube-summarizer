FROM python:3.13.3-slim

WORKDIR /app

# Install system dependencies
RUN apk update && apk add --no-cache \
    build-base \
    && rm -rf /var/cache/apk/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p output cache

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=summarizer/app.py
ENV FLASK_ENV=production

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["flask", "run", "--host=0.0.0.0"] 