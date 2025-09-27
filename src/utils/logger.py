"""
Logging utilities for epub2tts.

This module provides centralized logging configuration and utilities.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from loguru import logger
import structlog


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_type: str = "structured"
) -> None:
    """
    Setup logging configuration for the application.

    Args:
        level: Logging level (logging.DEBUG, INFO, etc.)
        log_file: Optional file to write logs to
        format_type: Type of logging format ('simple', 'detailed', 'structured')
    """
    # Clear any existing handlers
    logging.getLogger().handlers.clear()

    # Configure based on format type
    if format_type == "structured":
        _setup_structured_logging(level, log_file)
    else:
        _setup_standard_logging(level, log_file, format_type)


def _setup_standard_logging(
    level: int,
    log_file: Optional[Path],
    format_type: str
) -> None:
    """Setup standard Python logging."""

    # Define formats
    formats = {
        'simple': '%(levelname)s: %(message)s',
        'detailed': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'debug': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    }

    formatter = logging.Formatter(
        formats.get(format_type, formats['detailed']),
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler to prevent huge log files
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)


def _setup_structured_logging(
    level: int,
    log_file: Optional[Path]
) -> None:
    """Setup structured logging with structlog."""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer(colors=True)
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard logging as fallback
    _setup_standard_logging(level, log_file, 'detailed')


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)


class PerformanceLogger:
    """Logger for performance monitoring."""

    def __init__(self, operation_name: str):
        """Initialize performance logger."""
        self.operation_name = operation_name
        self.logger = logging.getLogger('performance')
        self.start_time = None

    def __enter__(self):
        """Start performance monitoring."""
        import time
        self.start_time = time.perf_counter()
        self.logger.debug(f"Starting operation: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End performance monitoring and log results."""
        import time
        if self.start_time:
            duration = time.perf_counter() - self.start_time
            if exc_type:
                self.logger.warning(
                    f"Operation failed: {self.operation_name} "
                    f"(duration: {duration:.3f}s, error: {exc_type.__name__})"
                )
            else:
                self.logger.info(
                    f"Operation completed: {self.operation_name} "
                    f"(duration: {duration:.3f}s)"
                )


def log_function_call(func):
    """Decorator to log function calls with arguments and return values."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")

        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} returned: {type(result)}")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} raised {type(e).__name__}: {e}")
            raise

    return wrapper


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def set_log_level(level: int) -> None:
    """
    Set logging level for all handlers.

    Args:
        level: New logging level
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in root_logger.handlers:
        handler.setLevel(level)


def add_file_handler(
    log_file: Path,
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> None:
    """
    Add a file handler to the root logger.

    Args:
        log_file: Path to log file
        level: Logging level for this handler
        format_string: Optional custom format string
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    formatter = logging.Formatter(format_string, datefmt='%Y-%m-%d %H:%M:%S')

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    logging.getLogger().addHandler(file_handler)


class ProgressLogger:
    """Logger for tracking progress of long-running operations."""

    def __init__(self, operation: str, total: int, logger_name: Optional[str] = None):
        """
        Initialize progress logger.

        Args:
            operation: Name of the operation
            total: Total number of items to process
            logger_name: Optional logger name
        """
        self.operation = operation
        self.total = total
        self.current = 0
        self.logger = logging.getLogger(logger_name or 'progress')
        self.last_percent = 0

    def update(self, increment: int = 1) -> None:
        """
        Update progress.

        Args:
            increment: Number to increment by
        """
        self.current += increment
        percent = int((self.current / self.total) * 100)

        # Log every 10% or at completion
        if percent >= self.last_percent + 10 or self.current >= self.total:
            self.logger.info(
                f"{self.operation}: {self.current}/{self.total} ({percent}%)"
            )
            self.last_percent = percent

    def finish(self) -> None:
        """Mark operation as finished."""
        self.logger.info(f"{self.operation}: Completed ({self.total}/{self.total})")


def configure_third_party_loggers() -> None:
    """Configure logging levels for common third-party libraries."""
    third_party_loggers = {
        'urllib3.connectionpool': logging.WARNING,
        'requests.packages.urllib3': logging.WARNING,
        'PIL.PngImagePlugin': logging.WARNING,
        'transformers': logging.WARNING,
        'huggingface_hub': logging.WARNING,
        'torch': logging.WARNING,
        'tensorflow': logging.WARNING,
    }

    for logger_name, level in third_party_loggers.items():
        logging.getLogger(logger_name).setLevel(level)