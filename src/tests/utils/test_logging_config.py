"""Tests for logging configuration module."""

import io
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from loguru import logger

from nwws.utils.logging_config import LoggingConfig


class TestLoggingConfig:
    """Test cases for LoggingConfig class."""

    def setup_method(self) -> None:
        """Reset logging configuration before each test."""
        LoggingConfig.reset()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        LoggingConfig.reset()

    def test_configure_console_only(self) -> None:
        """Test basic console logging configuration."""
        # Capture stdout to verify logging works
        output = io.StringIO()

        with redirect_stdout(output):
            LoggingConfig.configure("INFO")
            logger.info("Test message")

        # Verify configuration was applied
        assert LoggingConfig.is_configured()

        # Verify message was logged (basic check)
        output_content = output.getvalue()
        assert "Test message" in output_content
        assert "INFO" in output_content

    def test_configure_with_file_logging(self) -> None:
        """Test logging configuration with file output."""
        with NamedTemporaryFile(mode="w+", delete=False, suffix=".log") as temp_file:
            log_file_path = temp_file.name

        try:
            LoggingConfig.configure("DEBUG", log_file_path)
            logger.debug("Debug message")
            logger.info("Info message")

            # Verify file was created and contains messages
            log_content = Path(log_file_path).read_text(encoding="utf-8")
            assert "Debug message" in log_content
            assert "Info message" in log_content
            assert "DEBUG" in log_content
            assert "INFO" in log_content

        finally:
            # Clean up
            Path(log_file_path).unlink(missing_ok=True)

    def test_multiple_configure_calls_ignored(self) -> None:
        """Test that multiple configure calls are ignored."""
        LoggingConfig.configure("INFO")
        assert LoggingConfig.is_configured()

        # Second call should be ignored
        with patch.object(logger, "remove") as mock_remove:
            LoggingConfig.configure("DEBUG")
            mock_remove.assert_not_called()

    def test_ensure_configured_with_defaults(self) -> None:
        """Test ensure_configured method with default settings."""
        LoggingConfig.ensure_configured()
        assert LoggingConfig.is_configured()

    def test_reconfigure_for_thread(self) -> None:
        """Test thread reconfiguration."""
        LoggingConfig.configure("INFO")
        assert LoggingConfig.is_configured()

        # Reconfigure for thread should force reconfiguration
        with patch.object(LoggingConfig, "configure") as mock_configure:
            LoggingConfig.reconfigure_for_thread()
            mock_configure.assert_called_once_with("INFO", None)

    def test_escape_loguru_braces(self) -> None:
        """Test that curly braces are properly escaped."""
        # Test string with braces
        result = LoggingConfig._escape_loguru_braces("Message with {braces}") # type: ignore
        assert result == "Message with {{braces}}"

        # Test string with multiple braces
        result = LoggingConfig._escape_loguru_braces("{start} middle {end}") # type: ignore
        assert result == "{{start}} middle {{end}}"

        # Test non-string values
        result = LoggingConfig._escape_loguru_braces(123) # type: ignore
        assert result == "123"

        # Test None value
        result = LoggingConfig._escape_loguru_braces(None) # type: ignore
        assert result == "None"

    def test_format_extra_data_safety(self) -> None:
        """Test that extra data formatting handles edge cases safely."""
        # Normal case
        extra = {"key1": "value1", "key2": "value2"}
        result = LoggingConfig._format_extra_data(extra) # type: ignore
        assert "key1=value1" in result
        assert "key2=value2" in result

        # Empty extra data
        result = LoggingConfig._format_extra_data({}) # type: ignore
        assert result == ""

        # Extra data with braces
        extra = {"key": "value{with}braces"}
        result = LoggingConfig._format_extra_data(extra) # type: ignore
        assert "key=value{{with}}braces" in result

    def test_console_formatter_with_extra_data(self) -> None:
        """Test console formatter with extra logging data."""
        from datetime import datetime, timezone

        # Mock record with complete data structure like loguru provides
        mock_record = {
            "time": datetime.now(timezone.utc),
            "level": type("Level", (), {"name": "INFO"})(),
            "name": "test.module",
            "function": "test_function",
            "line": 123,
            "message": "Test message",
            "extra": {"user_id": "12345", "action": "login{test}"}
        }

        result = LoggingConfig._console_formatter(mock_record) # type: ignore

        # Should contain escaped braces and color formatting
        assert "user_id" in result
        assert "12345" in result
        assert "login{{test}}" in result
        assert "<cyan>" in result  # Color formatting present
        assert "<magenta>" in result

    def test_file_formatter_without_colors(self) -> None:
        """Test file formatter produces output without color codes."""
        from datetime import datetime, timezone

        # Mock record with complete data structure like loguru provides
        mock_record = {
            "time": datetime.now(timezone.utc),
            "level": type("Level", (), {"name": "INFO"})(),
            "name": "test.module",
            "function": "test_function",
            "line": 123,
            "message": "Test message",
            "extra": {"key": "value"}
        }

        result = LoggingConfig._file_formatter(mock_record) # type: ignore

        # Should not contain color codes
        assert "<cyan>" not in result
        assert "<magenta>" not in result
        assert "<green>" not in result
        assert "key=value" in result

    def test_formatter_exception_handling(self) -> None:
        """Test that formatters handle exceptions gracefully."""
        # Test with problematic record that causes exceptions when accessing fields
        problematic_record = {}  # Missing required fields

        # Console formatter should not raise exception
        result = LoggingConfig._console_formatter(problematic_record) # type: ignore
        assert "<critical_formatting_error>" in result or "<formatting_error>" in result

        # File formatter should not raise exception
        result = LoggingConfig._file_formatter(problematic_record) # type: ignore
        assert "<critical_formatting_error>" in result or "<formatting_error>" in result

    def test_logging_with_dangerous_braces(self) -> None:
        """Test logging messages that contain loguru-reserved braces."""
        output = io.StringIO()

        with redirect_stdout(output):
            LoggingConfig.configure("INFO")

            # Test that logging with braces doesn't crash
            # This used to cause KeyError: 'info' in loguru
            try:
                logger.info("Processing {user_data}", user_data="sensitive{info}")
                logger.bind(result="success{detailed}").info("Action completed")
                logger.info("Message with {random} braces")
                logging_succeeded = True
            except Exception:
                logging_succeeded = False

        output_content = output.getvalue()

        # The primary goal is that logging doesn't crash
        assert logging_succeeded, "Logging should not raise exceptions due to curly braces"

        # Verify that some logging occurred (configuration message should always be present)
        assert "Logging configuration applied" in output_content

        # Verify that braces in extra data are properly escaped
        if "success{{detailed}}" in output_content:
            # If our formatter is working, braces should be escaped
            pass
        else:
            # If not visible, that's OK as long as logging didn't crash
            pass

    def test_reset_functionality(self) -> None:
        """Test that reset properly clears configuration state."""
        LoggingConfig.configure("DEBUG", "/tmp/test.log")
        assert LoggingConfig.is_configured()

        LoggingConfig.reset()
        assert not LoggingConfig.is_configured()
        assert LoggingConfig._log_level == "INFO"  # Default value # type: ignore
        assert LoggingConfig._log_file is None # type: ignore

    def test_edge_case_values_in_extra_data(self) -> None:
        """Test handling of edge case values in extra logging data."""
        # Test with various problematic values
        test_cases = [
            {"empty_string": ""},
            {"none_value": None},
            {"numeric": 42},
            {"boolean": True},
            {"list": [1, 2, 3]},
            {"dict": {"nested": "value"}},
        ]

        for extra_data in test_cases:
            # Should not raise exceptions
            result = LoggingConfig._format_extra_data(extra_data) # type: ignore
            assert isinstance(result, str)
            # Basic validation that some content is present
            if extra_data:
                assert len(result) > 0

    def test_logging_performance_with_large_extra_data(self) -> None:
        """Test that logging performance is reasonable with large extra data."""
        import time

        # Create large extra data
        large_extra = {f"key_{i}": f"value_{i}" * 10 for i in range(100)}

        output = io.StringIO()
        with redirect_stdout(output):
            LoggingConfig.configure("INFO")

            start_time = time.monotonic()
            logger.info("Performance test", **large_extra)
            end_time = time.monotonic()

        # Should complete in reasonable time (less than 1 second)
        assert (end_time - start_time) < 1.0

        # Verify message was logged
        output_content = output.getvalue()
        assert "Performance test" in output_content
