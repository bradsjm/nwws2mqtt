"""Centralized logging configuration for NWWS2MQTT application."""

import sys
from contextlib import suppress
from typing import Any

from loguru import logger


class LoggingConfig:
    """Centralized logging configuration that can be applied across the application."""

    _configured = False
    _log_level = "INFO"
    _log_file: str | None = None

    @classmethod
    def configure(cls, log_level: str, log_file: str | None = None) -> None:
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
        logger.add(
            sys.stdout,
            level=log_level,
            format=cls._console_formatter,
            serialize=False,
        )

        # Only add file logging if log_file is specified
        if log_file:
            logger.add(
                log_file,
                level=log_level,
                rotation="10 MB",
                retention="7 days",
                format=cls._file_formatter,
            )
            logger.info("File logging enabled", log_file=log_file)

        cls._configured = True
        logger.info("Logging configuration applied", level=log_level)

    @classmethod
    def _escape_loguru_braces(cls, value: Any) -> str:
        """Safely escape curly braces for loguru formatting.

        Args:
            value: The value to escape

        Returns:
            String with curly braces properly escaped for loguru

        """
        try:
            # Convert to string first
            str_value = str(value)
            # Escape curly braces by doubling them for loguru
            return str_value.replace("{", "{{").replace("}", "}}")
        except (TypeError, ValueError, AttributeError):
            # Fallback to a safe representation if conversion fails
            return "<unprintable>"

    @classmethod
    def _format_extra_data(cls, extra: dict[str, Any]) -> str:
        """Safely format extra logging data.

        Args:
            extra: Dictionary of extra logging data

        Returns:
            Formatted string of extra data

        """
        if not extra:
            return ""

        try:
            formatted_pairs: list[str] = []
            for key, value in extra.items():
                # Ensure key is safe
                safe_key = cls._escape_loguru_braces(key)
                safe_value = cls._escape_loguru_braces(value)
                formatted_pairs.append(f"{safe_key}={safe_value}")

            return " | ".join(formatted_pairs)
        except (TypeError, ValueError, AttributeError, KeyError):
            # If anything goes wrong, return a safe fallback
            return "<extra_data_formatting_error>"

    @classmethod
    def _console_formatter(cls, record: Any) -> str:
        """Format log record for console output with color codes.

        Args:
            record: Loguru record object

        Returns:
            Formatted log message string

        """
        try:
            # Basic format parts
            time_part = record["time"].strftime("%m-%d %H:%M:%S")
            level_part = f"{record['level'].name: <8}"
            location_part = f"{record['name']}:{record['function']}:{record['line']}"
            # Safely escape braces in the message to prevent loguru format conflicts
            message_part = cls._escape_loguru_braces(record["message"])

            # Build basic message with colors
            formatted_message = (
                f"<green>{time_part}</green> | "
                f"<level>{level_part}</level> | "
                f"<cyan>{location_part}</cyan> | "
                f"<level>{message_part}</level>"
            )

            # Safely append extra data if present
            extra = record.get("extra", {})
            if extra:
                extra_data = cls._format_extra_data(extra)
                if extra_data:
                    # Add colors to extra data for console
                    colored_parts: list[str] = []
                    for pair in extra_data.split(" | "):
                        if "=" in pair:
                            key_part, value_part = pair.split("=", 1)
                            colored_parts.append(
                                f"<cyan>{key_part}</cyan>=<magenta>{value_part}</magenta>"
                            )
                        else:
                            colored_parts.append(pair)

                    if colored_parts:
                        formatted_message += " | " + " | ".join(colored_parts)

            return formatted_message + "\n"

        except (TypeError, ValueError, KeyError, AttributeError):
            # Fallback to basic formatting if our custom formatting fails
            try:
                return (
                    f"{record.get('time', 'TIME')} | "
                    f"{record.get('level', {}).get('name', 'LEVEL'): <8} | "
                    f"{record.get('name', 'NAME')}:{record.get('function', 'FUNC')}:{record.get('line', 'LINE')} | "
                    f"{record.get('message', 'MESSAGE')} | <formatting_error>\n"
                )
            except (TypeError, ValueError, KeyError, AttributeError, LookupError):
                # Ultimate fallback
                return "LOG | <critical_formatting_error>\n"

    @classmethod
    def _file_formatter(cls, record: Any) -> str:
        """Format log record for file output without color codes.

        Args:
            record: Loguru record object

        Returns:
            Formatted log message string

        """
        try:
            # Basic format parts without colors
            time_part = record["time"].strftime("%Y-%m-%d %H:%M:%S")
            level_part = f"{record['level'].name: <8}"
            location_part = f"{record['name']}:{record['function']}:{record['line']}"
            # Safely escape braces in the message to prevent loguru format conflicts
            message_part = cls._escape_loguru_braces(record["message"])

            # Build basic message
            formatted_message = f"{time_part} | {level_part} | {location_part} | {message_part}"

            # Safely append extra data if present
            extra = record.get("extra", {})
            if extra:
                extra_data = cls._format_extra_data(extra)
                if extra_data:
                    formatted_message += f" | {extra_data}"

            return formatted_message + "\n"

        except (TypeError, ValueError, KeyError, AttributeError):
            # Fallback to basic formatting if our custom formatting fails
            try:
                return (
                    f"{record.get('time', 'TIME')} | "
                    f"{record.get('level', {}).get('name', 'LEVEL'): <8} | "
                    f"{record.get('name', 'NAME')}:{record.get('function', 'FUNC')}:{record.get('line', 'LINE')} | "
                    f"{record.get('message', 'MESSAGE')} | <formatting_error>\n"
                )
            except (TypeError, ValueError, KeyError, AttributeError, LookupError):
                # Ultimate fallback
                return "LOG | <critical_formatting_error>\n"

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

    @classmethod
    def reset(cls) -> None:
        """Reset logging configuration state.

        This is primarily useful for testing purposes.
        """
        cls._configured = False
        cls._log_level = "INFO"
        cls._log_file = None
        with suppress(ValueError):
            logger.remove()
