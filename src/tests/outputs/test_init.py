# pyright: strict
"""Tests for outputs package initialization."""

from unittest.mock import patch

import pytest


class TestOutputsPackage:
    """Test cases for outputs package initialization."""

    def test_console_output_import(self) -> None:
        """Test that ConsoleOutput can be imported from package."""
        from src.outputs import ConsoleOutput
        assert ConsoleOutput is not None
        assert hasattr(ConsoleOutput, "__init__")
        assert hasattr(ConsoleOutput, "send")

    def test_mqtt_output_import(self) -> None:
        """Test that MQTTOutput can be imported from package."""
        from src.outputs import MQTTOutput
        assert MQTTOutput is not None
        assert hasattr(MQTTOutput, "__init__")
        assert hasattr(MQTTOutput, "send")
        assert hasattr(MQTTOutput, "start")
        assert hasattr(MQTTOutput, "stop")

    def test_all_exports(self) -> None:
        """Test that __all__ exports are available."""
        from src.outputs import __all__
        
        expected_exports = ["ConsoleOutput", "MQTTOutput"]
        assert set(__all__) == set(expected_exports)

    @patch("src.outputs.console.Console")
    def test_console_output_instantiation(self, mock_console_class) -> None:
        """Test that ConsoleOutput can be instantiated."""
        from src.outputs import ConsoleOutput
        output = ConsoleOutput()
        assert output.output_id == "console"

    def test_mqtt_output_instantiation(self) -> None:
        """Test that MQTTOutput can be instantiated with minimal config."""
        from src.outputs import MQTTOutput
        from src.outputs.mqtt import MQTTOutputConfig
        
        config = MQTTOutputConfig(broker="test-broker")
        output = MQTTOutput(config=config)
        assert output.output_id == "mqtt"