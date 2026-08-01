import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging():
    # Logs stored Path
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers if setup_logging()
    # is accidentally called more than once
    if logger.handlers:
        return

    # Log Format - Date  Time | Log level | file path | Message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # Console logging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # File logging with rotational file, file size = 5 mb

    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # Send logs to both places
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)