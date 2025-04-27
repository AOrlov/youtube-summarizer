import logging
import os
import tempfile
from pathlib import Path
from summarizer.utils import setup_logging, get_logger

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
            log_level="INFO",
            log_file=temp_file.name,
            console_output=False
        )
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)
        
        # Test logging to file
        test_message = "Test log message"
        logger.info(test_message)
        
        # Read the log file
        with open(temp_file.name, "r") as f:
            log_content = f.read()
            assert test_message in log_content

def test_setup_logging_both():
    """Test setting up logging with both console and file output."""
    with tempfile.NamedTemporaryFile() as temp_file:
        logger = setup_logging(
            log_level="WARNING",
            log_file=temp_file.name,
            console_output=True
        )
        assert logger.level == logging.WARNING
        assert len(logger.handlers) == 2
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

def test_get_logger():
    """Test getting a logger instance."""
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"

def test_logger_inheritance():
    """Test that child loggers inherit parent configuration."""
    parent_logger = setup_logging(log_level="DEBUG")
    child_logger = get_logger("summarizer.child")
    assert child_logger.level == logging.DEBUG
    assert len(child_logger.handlers) == 1
