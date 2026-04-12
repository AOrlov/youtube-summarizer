import logging
import tempfile
import json

from summarizer.utils import JsonFormatter, get_logger, log_event, setup_logging


def test_setup_logging_console():
    """Test setting up logging with console output."""
    logger = setup_logging(log_level="DEBUG", console_output=True)

    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)


def test_setup_logging_file():
    """Test setting up logging with file output."""
    with tempfile.NamedTemporaryFile() as temp_file:
        logger = setup_logging(
            log_level="INFO", log_file=temp_file.name, console_output=False
        )

        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)

        test_message = "Test log message"
        logger.info(test_message)

        with open(temp_file.name, "r") as f:
            log_content = f.read()

        assert test_message in log_content


def test_setup_logging_both():
    """Test setting up logging with both console and file output."""
    with tempfile.NamedTemporaryFile() as temp_file:
        logger = setup_logging(
            log_level="WARNING", log_file=temp_file.name, console_output=True
        )

        assert logger.level == logging.WARNING
        assert len(logger.handlers) == 2
        assert any(
            isinstance(handler, logging.FileHandler) for handler in logger.handlers
        )
        assert any(
            isinstance(handler, logging.StreamHandler) for handler in logger.handlers
        )


def test_get_logger():
    """Test getting a logger instance."""
    logger = get_logger("test_logger")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"


def test_logger_inheritance():
    """Test that child loggers inherit parent configuration."""
    parent_logger = setup_logging(log_level="DEBUG")
    child_logger = get_logger("summarizer.child")

    assert parent_logger.level == logging.DEBUG
    assert parent_logger.propagate is False
    assert child_logger.level == logging.NOTSET
    assert child_logger.getEffectiveLevel() == logging.DEBUG
    assert len(child_logger.handlers) == 0


def test_log_event_writes_json_with_extra_fields():
    with tempfile.NamedTemporaryFile() as temp_file:
        logger = setup_logging(
            log_level="INFO", log_file=temp_file.name, console_output=False
        )

        log_event(
            logger,
            logging.INFO,
            "summary_request_completed",
            video_id="video123",
            summary_language="ru",
            total_duration_ms=12.5,
        )

        with open(temp_file.name, "r", encoding="utf-8") as f:
            payload = json.loads(f.read().strip())

        assert payload["event"] == "summary_request_completed"
        assert payload["video_id"] == "video123"
        assert payload["summary_language"] == "ru"
        assert payload["total_duration_ms"] == 12.5
        assert payload["level"] == "info"
        assert payload["logger"] == "summarizer"


def test_json_formatter_omits_python_task_name():
    record = logging.makeLogRecord(
        {"name": "summarizer.test", "msg": "hello", "levelname": "INFO", "levelno": 20}
    )

    payload = json.loads(JsonFormatter().format(record))

    assert "taskName" not in payload
