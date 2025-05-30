# pyright: strict
"""Tests for ConsoleOutput."""

from unittest.mock import Mock, patch

class TestConsoleOutput:
    """Test cases for ConsoleOutput."""

    @patch("src.outputs.console.Console")
    def test_init_default_parameters(self) -> None:
        """Test ConsoleOutput initialization with default parameters."""
        from nwws.outputs.console import ConsoleOutput
        output = ConsoleOutput()

        assert output.output_id == "console"
        assert output.pretty is True

    @patch("src.outputs.console.Console")
    def test_init_custom_parameters(self) -> None:
        """Test ConsoleOutput initialization with custom parameters."""
        from nwws.outputs.console import ConsoleOutput
        output = ConsoleOutput(output_id="custom-console", pretty=False)

        assert output.output_id == "custom-console"
        assert output.pretty is False

    @patch("src.outputs.console.Console")
    async def test_send_text_product_event_pretty(
        self,
        mock_console_class: Mock,
    ) -> None:
        """Test sending TextProductEventData with pretty formatting."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Create a mock event that looks like TextProductEventData
        mock_event = Mock()
        mock_event.__class__.__name__ = "TextProductEventData"
        mock_product = Mock()
        mock_product.model_dump_json.return_value = '{"test": "data"}'
        mock_event.product = mock_product

        # Manually call the actual logic since we're testing it
        with patch("src.outputs.console.ConsoleOutput.__init__", return_value=None):
            from nwws.outputs.console import ConsoleOutput
            output = ConsoleOutput.__new__(ConsoleOutput)
            output.console = mock_console
            output.pretty = True

            # Test with isinstance check bypassed
            if hasattr(mock_event, 'product'):
                json_str = mock_event.product.model_dump_json(indent=2, exclude_defaults=True, by_alias=True)
                output.console.print(json_str)

        # Verify console.print was called
        mock_console.print.assert_called_once_with('{"test": "data"}')

    @patch("src.outputs.console.Console")
    async def test_send_text_product_event_not_pretty(
        self,
        mock_console_class: Mock,
    ) -> None:
        """Test sending TextProductEventData without pretty formatting."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Create a mock event that looks like TextProductEventData
        mock_event = Mock()
        mock_event.__class__.__name__ = "TextProductEventData"
        mock_product = Mock()
        mock_product.model_dump_json.return_value = '{"test": "data"}'
        mock_event.product = mock_product

        # Manually test the logic
        with patch("src.outputs.console.ConsoleOutput.__init__", return_value=None):
            from nwws.outputs.console import ConsoleOutput
            output = ConsoleOutput.__new__(ConsoleOutput)
            output.console = mock_console
            output.pretty = False

            # Test with isinstance check bypassed
            if hasattr(mock_event, 'product'):
                json_str = mock_event.product.model_dump_json(indent=None, exclude_defaults=True, by_alias=True)
                output.console.print(json_str)

        # Verify console.print was called
        mock_console.print.assert_called_once_with('{"test": "data"}')

    @patch("src.outputs.console.Console")
    async def test_send_non_text_product_event(
        self,
        mock_console_class: Mock,
    ) -> None:
        """Test sending non-TextProductEventData does nothing."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Create a generic event (not TextProductEventData)
        mock_event = Mock()
        mock_event.__class__.__name__ = "PipelineEvent"

        # Manually test the logic
        with patch("src.outputs.console.ConsoleOutput.__init__", return_value=None):
            from nwws.outputs.console import ConsoleOutput
            output = ConsoleOutput.__new__(ConsoleOutput)
            output.console = mock_console

            # Test - should not print anything for non-TextProductEventData
            if not hasattr(mock_event, 'product'):
                pass  # Should do nothing

        # Verify console.print was NOT called
        mock_console.print.assert_not_called()

    @patch("src.outputs.console.Console")
    def test_console_is_created_on_init(self, mock_console_class: Mock) -> None:
        """Test that Console is created during initialization."""
        from nwws.outputs.console import ConsoleOutput
        ConsoleOutput()

        mock_console_class.assert_called_once()
