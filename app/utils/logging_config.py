"""Centralized logging configuration for NWWS2MQTT application."""

import sys
from typing import Optional

from loguru import logger


class LoggingConfig:
    """Centralized logging configuration that can be applied across the application."""

    _configured = False
    _log_level = "INFO"
    _log_file: Optional[str] = None

    @classmethod
    def configure(cls, log_level: str, log_file: Optional[str] = None) -> None:
        """Configure logging for the entire application.

        Args:
            log_level: The logging level (DEBUG, INFO, WARNING, ERROR)
            log_file: Optional log file path for file logging
        """
        if cls._configured:
            return

        cls._log_level = log_level
        cls._log_file = log_file

        # Remove default handler
        logger.remove()

        # Configure console logging with custom formatter
        def format_record(record):
            """Custom formatter that handles structured data."""
            # Format the basic message first
            basic_format = (
                "<green>{time:MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            )

            # Use loguru's formatter to format the basic message
            formatted_message = basic_format.format_map(record)

            # Append extra data
            if record["extra"]:
                extra_str = " | ".join([f"<cyan>{k}</cyan>=<magenta>{v}</magenta>" for k, v in record["extra"].items()])
                formatted_message += f" | {extra_str}"

            return formatted_message + "\n"

        logger.add(
            sys.stdout,
            level=log_level,
            format=format_record,
            serialize=False,
        )

        # Only add file logging if log_file is specified
        if log_file:

            def format_file_record(record):
                """File formatter without color codes."""
                # Format the basic message first
                basic_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"
                formatted_message = basic_format.format_map(record)

                # Append extra data
                if record["extra"]:
                    extra_str = " | ".join([f"{k}={v}" for k, v in record["extra"].items()])
                    formatted_message += f" | {extra_str}"

                return formatted_message + "\n"

            logger.add(
                log_file,
                level=log_level,
                rotation="10 MB",
                retention="7 days",
                format=format_file_record,
            )
            logger.info("File logging enabled", log_file=log_file)

        cls._configured = True
        logger.info("Logging configuration applied", level=log_level)

    @classmethod
    def ensure_configured(cls) -> None:
        """Ensure logging is configured with default settings if not already done."""
        if not cls._configured:
            cls.configure(cls._log_level, cls._log_file)

    @classmethod
    def is_configured(cls) -> bool:
        """Check if logging has been configured."""
        return cls._configured

    @classmethod
    def reconfigure_for_thread(cls) -> None:
        """Reconfigure logging for a new thread context.

        This ensures that loguru configuration is properly applied
        in threads that may not inherit the main configuration.
        """
        if cls._configured:
            # Force reconfiguration in the current thread
            cls._configured = False
            cls.configure(cls._log_level, cls._log_file)
