# pyright: strict
"""Tests for MQTTOutput."""

from unittest.mock import AsyncMock, Mock, patch
from unittest.mock import MagicMock

import pytest


class TestMQTTOutputConfig:
    """Test cases for MQTTOutputConfig."""

    def test_config_defaults(self) -> None:
        """Test MQTTOutputConfig with default values."""
        from src.outputs.mqtt import MQTTOutputConfig
        config = MQTTOutputConfig(broker="test-broker")
        
        assert config.broker == "test-broker"
        assert config.port == 1883
        assert config.username is None
        assert config.password is None
        assert config.topic_prefix == "nwws"
        assert config.qos == 1
        assert config.retain is False
        assert config.client_id == "nwws-oi-pipeline-client"
        assert config.message_expiry_minutes == 60

    def test_config_custom_values(self) -> None:
        """Test MQTTOutputConfig with custom values."""
        from src.outputs.mqtt import MQTTOutputConfig
        config = MQTTOutputConfig(
            broker="custom-broker",
            port=8883,
            username="testuser",
            password="testpass",
            topic_prefix="custom",
            qos=2,
            retain=True,
            client_id="custom-client",
            message_expiry_minutes=30,
        )
        
        assert config.broker == "custom-broker"
        assert config.port == 8883
        assert config.username == "testuser"
        assert config.password == "testpass"
        assert config.topic_prefix == "custom"
        assert config.qos == 2
        assert config.retain is True
        assert config.client_id == "custom-client"
        assert config.message_expiry_minutes == 30


class TestMQTTOutput:
    """Test cases for MQTTOutput."""

    def test_init_default_parameters(self) -> None:
        """Test MQTTOutput initialization with default parameters."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        config = MQTTOutputConfig(broker="test-broker")
        output = MQTTOutput(config=config)
        
        assert output.output_id == "mqtt"
        assert output.config == config
        assert output._client is None
        assert output._connected is False

    def test_init_custom_parameters(self) -> None:
        """Test MQTTOutput initialization with custom parameters."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        config = MQTTOutputConfig(broker="test-broker")
        output = MQTTOutput(output_id="custom-mqtt", config=config)
        
        assert output.output_id == "custom-mqtt"
        assert output.config == config

    def test_is_connected_property(self) -> None:
        """Test is_connected property."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        config = MQTTOutputConfig(broker="test-broker")
        output = MQTTOutput(config=config)
        
        assert output.is_connected is False
        
        output._connected = True
        assert output.is_connected is True

    @patch("src.outputs.mqtt.mqtt.Client")
    async def test_start_success(self, mock_client_class: Mock) -> None:
        """Test successful start operation."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        config = MQTTOutputConfig(broker="test-broker")
        output = MQTTOutput(config=config)
        
        await output.start()
        
        # Verify client was created and configured
        mock_client_class.assert_called_once_with(client_id="nwws-oi-pipeline-client")
        mock_client.loop_start.assert_called_once()
        mock_client.connect.assert_called_once_with("test-broker", 1883, 60)
        
        # Verify callbacks were set
        assert output._client is mock_client
        assert mock_client.on_connect is not None
        assert mock_client.on_disconnect is not None

    @patch("src.outputs.mqtt.mqtt.Client")
    async def test_start_with_credentials(self, mock_client_class: Mock) -> None:
        """Test start with username and password."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        config = MQTTOutputConfig(
            broker="test-broker",
            username="testuser",
            password="testpass",
        )
        output = MQTTOutput(config=config)
        
        await output.start()
        
        mock_client.username_pw_set.assert_called_once_with("testuser", "testpass")

    @patch("src.outputs.mqtt.mqtt.Client")
    async def test_stop_success(self, mock_client_class: Mock) -> None:
        """Test successful stop operation."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        config = MQTTOutputConfig(broker="test-broker")
        output = MQTTOutput(config=config)
        
        await output.start()
        await output.stop()
        
        mock_client.disconnect.assert_called_once()
        mock_client.loop_stop.assert_called_once()

    @patch("src.outputs.mqtt.isinstance")
    async def test_send_text_product_event(self, mock_isinstance: Mock) -> None:
        """Test sending TextProductEventData."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        
        # Make isinstance return True for our mock event
        mock_isinstance.return_value = True
        
        config = MQTTOutputConfig(broker="test-broker")
        output = MQTTOutput(config=config)
        
        # Mock the client and connection
        mock_client = MagicMock()
        output._client = mock_client
        output._connected = True
        
        # Create mock event that looks like TextProductEventData
        mock_event = Mock()
        mock_event.cccc = "KTEST"
        mock_event.awipsid = "TESTAID"
        mock_event.id = "TEST123"
        mock_event.metadata = Mock()
        mock_event.metadata.event_id = "test-event-123"
        mock_product = Mock()
        mock_product.model_dump_json.return_value = '{"test": "data"}'
        mock_event.product = mock_product
        
        await output.send(mock_event)
        
        # Verify publish was called with correct parameters
        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args
        
        # Check topic format: prefix/cccc/awipsid/id
        expected_topic = "nwws/KTEST/TESTAID/TEST123"
        assert call_args[0][0] == expected_topic
        
        # Check payload is JSON
        payload = call_args[0][1]
        assert isinstance(payload, str)
        assert payload == '{"test": "data"}'
        
        # Check QoS and retain
        assert call_args[1]["qos"] == 1
        assert call_args[1]["retain"] is False

    @patch("src.outputs.mqtt.isinstance")
    async def test_send_non_text_product_event(self, mock_isinstance: Mock) -> None:
        """Test sending non-TextProductEventData does nothing."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        
        # Make isinstance return False for our mock event
        mock_isinstance.return_value = False
        
        config = MQTTOutputConfig(broker="test-broker")
        output = MQTTOutput(config=config)
        
        # Mock the client and connection
        mock_client = MagicMock()
        output._client = mock_client
        output._connected = True
        
        # Create a generic event (not TextProductEventData)
        mock_event = Mock()
        
        await output.send(mock_event)
        
        # Verify publish was NOT called
        mock_client.publish.assert_not_called()

    @patch("src.outputs.mqtt.isinstance")
    async def test_send_when_not_connected(self, mock_isinstance: Mock) -> None:
        """Test sending when client is not connected."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        
        # Make isinstance return True for our mock event
        mock_isinstance.return_value = True
        
        config = MQTTOutputConfig(broker="test-broker")
        output = MQTTOutput(config=config)
        
        # Mock the client but set as not connected
        mock_client = MagicMock()
        output._client = mock_client
        output._connected = False
        
        # Create mock event
        mock_event = Mock()
        mock_event.metadata = Mock()
        mock_event.metadata.event_id = "test-event-123"
        
        await output.send(mock_event)
        
        # Verify publish was NOT called
        mock_client.publish.assert_not_called()

    @patch("src.outputs.mqtt.isinstance")
    async def test_send_with_retain_enabled(self, mock_isinstance: Mock) -> None:
        """Test sending with retain enabled."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        
        # Make isinstance return True for our mock event
        mock_isinstance.return_value = True
        
        config = MQTTOutputConfig(broker="test-broker", retain=True)
        output = MQTTOutput(config=config)
        
        # Mock the client and connection
        mock_client = MagicMock()
        output._client = mock_client
        output._connected = True
        
        # Create mock event that looks like TextProductEventData
        mock_event = Mock()
        mock_event.cccc = "KTEST"
        mock_event.awipsid = "TESTAID"
        mock_event.id = "TEST123"
        mock_event.metadata = Mock()
        mock_event.metadata.event_id = "test-event-123"
        mock_product = Mock()
        mock_product.model_dump_json.return_value = '{"test": "data"}'
        mock_event.product = mock_product
        
        await output.send(mock_event)
        
        # Verify publish was called with retain=True
        call_args = mock_client.publish.call_args
        assert call_args[1]["retain"] is True
        assert call_args[1]["properties"] is not None

    def test_on_connect_callback_success(self) -> None:
        """Test successful connection callback."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        config = MQTTOutputConfig(broker="test-broker")
        output = MQTTOutput(config=config)
        
        # Simulate successful connection (rc=0)
        output._on_connect(None, None, {}, 0)  # type: ignore[arg-type]
        
        assert output._connected is True

    def test_on_connect_callback_failure(self) -> None:
        """Test failed connection callback."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        config = MQTTOutputConfig(broker="test-broker")
        output = MQTTOutput(config=config)
        
        # Simulate failed connection (rc!=0)
        output._on_connect(None, None, {}, 1)  # type: ignore[arg-type]
        
        assert output._connected is False

    def test_on_disconnect_callback(self) -> None:
        """Test disconnect callback."""
        from src.outputs.mqtt import MQTTOutput, MQTTOutputConfig
        config = MQTTOutputConfig(broker="test-broker")
        output = MQTTOutput(config=config)
        output._connected = True
        
        # Simulate disconnection
        output._on_disconnect(None, None, 0)  # type: ignore[arg-type]
        
        assert output._connected is False