"""Logging configuration with Loguru."""

import logging
import os
import sys
from pathlib import Path

from loguru import logger

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"

# Console handler with colors
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# File handler without colors
FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} - "
    "{message}"
)

_LOGGING_CONFIGURED = False


class InterceptHandler(logging.Handler):
    """Intercept standard logging and redirect to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to Loguru."""
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def get_logger(name: str):
    """Get a logger with module binding.

    Args:
        name: Module name for logger identification

    Returns:
        Bound logger instance
    """
    return logger.bind(module=name)


def _enable_diagnostics() -> bool:
    """Determine whether diagnostic stack inspection should be enabled."""
    environment = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
    debug_enabled = os.getenv("DEBUG", "0").lower() in {"1", "true", "yes", "on"}
    return debug_enabled or environment not in {"prod", "production"}


def intercept_standard_logging() -> None:
    """Intercept all standard logging calls and redirect to Loguru."""
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(os.getenv("LOG_LEVEL", "INFO"))

    for name in logging.root.manager.loggerDict:
        if name.startswith("loguru"):
            continue
        target_logger = logging.getLogger(name)
        target_logger.handlers = []
        target_logger.propagate = True

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def setup_logging() -> None:
    """Configure Loguru and standard logging interception explicitly."""
    global _LOGGING_CONFIGURED

    if _LOGGING_CONFIGURED:
        return

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    diagnostics_enabled = _enable_diagnostics()
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_filename = os.getenv("LOG_FILENAME", "app.log")

    logger.remove()
    logger.add(
        sys.stdout,
        format=CONSOLE_FORMAT,
        level=log_level,
        colorize=True,
        backtrace=diagnostics_enabled,
        diagnose=diagnostics_enabled,
    )
    logger.add(
        LOGS_DIR / log_filename,
        format=FILE_FORMAT,
        level=log_level,
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        backtrace=diagnostics_enabled,
        diagnose=diagnostics_enabled,
    )

    intercept_standard_logging()
    _LOGGING_CONFIGURED = True
