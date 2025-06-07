# pyright: strict
"""Tests for outputs package initialization."""

from unittest.mock import Mock, patch

class TestOutputsPackage:
    """Test cases for outputs package initialization."""

    def test_console_output_import(self) -> None:
        """Test that ConsoleOutput can be imported from package."""
        from nwws.outputs import ConsoleOutput
        assert ConsoleOutput is not None
        assert hasattr(ConsoleOutput, "__init__")
        assert hasattr(ConsoleOutput, "send")

    def test_mqtt_output_import(self) -> None:
        """Test that MQTTOutput can be imported from package."""
        from nwws.outputs import MQTTOutput
        assert MQTTOutput is not None
        assert hasattr(MQTTOutput, "__init__")
        assert hasattr(MQTTOutput, "send")
        assert hasattr(MQTTOutput, "start")
        assert hasattr(MQTTOutput, "stop")

    @patch("nwws.outputs.console.Console")
    def test_console_output_instantiation(self, _mock_console_class: Mock) -> None:
        """Test that ConsoleOutput can be instantiated."""
        from nwws.outputs import ConsoleOutput
        output = ConsoleOutput()
        assert output.output_id == "console"

    def test_mqtt_output_instantiation(self) -> None:
        """Test that MQTTOutput can be instantiated with minimal config."""
        from nwws.outputs import MQTTOutput, MQTTConfig

        config = MQTTConfig()
        output = MQTTOutput(config=config)
        assert output.output_id == "mqtt"
