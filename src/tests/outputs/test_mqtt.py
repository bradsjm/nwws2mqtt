# pyright: standard
"""Tests for MQTTOutput."""

from unittest.mock import Mock, patch
from unittest.mock import MagicMock

class TestMqttConfig:
    """Test cases for MqttConfig."""

    def test_config_defaults(self) -> None:
        """Test MqttConfig with default values."""
        from nwws.outputs import MQTTConfig
        config = MQTTConfig()

        assert config.mqtt_broker == "localhost"
        assert config.mqtt_port == 1883
        assert config.mqtt_username is None
        assert config.mqtt_password is None
        assert config.mqtt_topic_prefix == "nwws"
        assert config.mqtt_qos == 1
        assert config.mqtt_client_id == "nwws-oi-client"

    def test_config_custom_values(self) -> None:
        """Test MqttConfig with custom values."""
        from nwws.outputs.mqtt import MQTTConfig
        config = MQTTConfig(
            mqtt_broker="custom-broker",
            mqtt_port=8883,
            mqtt_username="testuser",
            mqtt_password="testpass",
            mqtt_topic_prefix="custom",
            mqtt_qos=2,
            mqtt_client_id="custom-client",
        )

        assert config.mqtt_broker == "custom-broker"
        assert config.mqtt_port == 8883
        assert config.mqtt_username == "testuser"
        assert config.mqtt_password == "testpass"
        assert config.mqtt_topic_prefix == "custom"
        assert config.mqtt_qos == 2
        assert config.mqtt_client_id == "custom-client"


class TestMQTTOutput:
    """Test cases for MQTTOutput."""

    def test_init_default_parameters(self) -> None:
        """Test MQTTOutput initialization with default parameters."""
        from nwws.outputs.mqtt import MQTTOutput, MQTTConfig
        config = MQTTConfig()
        output = MQTTOutput(config=config)

        assert output.output_id == "mqtt"
        assert output.config == config
        assert output._client is None
        assert output._connected is False

    def test_init_custom_parameters(self) -> None:
        """Test MQTTOutput initialization with custom parameters."""
        from nwws.outputs.mqtt import MQTTOutput, MQTTConfig
        config = MQTTConfig()
        output = MQTTOutput(output_id="custom-mqtt", config=config)

        assert output.output_id == "custom-mqtt"
        assert output.config == config

    def test_is_connected_property(self) -> None:
        """Test is_connected property."""
        from nwws.outputs.mqtt import MQTTOutput, MQTTConfig
        config = MQTTConfig()
        output = MQTTOutput(config=config)

        assert output.is_connected is False

        output._connected = True
        assert output.is_connected is True

    @patch("nwws.outputs.mqtt.mqtt.Client")
    async def test_start_success(self, mock_client_class: Mock) -> None:
        """Test successful start operation."""
        from nwws.outputs.mqtt import MQTTOutput, MQTTConfig
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        config = MQTTConfig()
        output = MQTTOutput(config=config)

        await output.start()

        # Verify client was created and configured
        mock_client_class.assert_called_once_with(client_id="nwws-oi-client")
        mock_client.loop_start.assert_called_once()
        mock_client.connect.assert_called_once_with("localhost", 1883, 60)

        # Verify callbacks were set
        assert output._client is mock_client
        assert mock_client.on_connect is not None
        assert mock_client.on_disconnect is not None

    @patch("nwws.outputs.mqtt.mqtt.Client")
    async def test_start_with_credentials(self, mock_client_class: Mock) -> None:
        """Test start with username and password."""
        from nwws.outputs.mqtt import MQTTOutput, MQTTConfig
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        config = MQTTConfig(
            mqtt_broker="test-broker",
            mqtt_username="testuser",
            mqtt_password="testpass",
        )
        output = MQTTOutput(config=config)

        await output.start()

        mock_client.username_pw_set.assert_called_once_with("testuser", "testpass")

    @patch("nwws.outputs.mqtt.mqtt.Client")
    async def test_stop_success(self, mock_client_class: Mock) -> None:
        """Test successful stop operation."""
        from nwws.outputs.mqtt import MQTTOutput, MQTTConfig
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        config = MQTTConfig()
        output = MQTTOutput(config=config)

        await output.start()
        await output.stop()

        mock_client.disconnect.assert_called_once()
        mock_client.loop_stop.assert_called_once()

    @patch("nwws.outputs.mqtt.isinstance")
    async def test_send_non_text_product_event(self, mock_isinstance: Mock) -> None:
        """Test sending non-TextProductEventData does nothing."""
        from nwws.outputs.mqtt import MQTTOutput, MQTTConfig

        # Make isinstance return False for our mock event
        mock_isinstance.return_value = False

        config = MQTTConfig()
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

    @patch("nwws.outputs.mqtt.isinstance")
    async def test_send_when_not_connected(self, mock_isinstance: Mock) -> None:
        """Test sending when client is not connected."""
        from nwws.outputs.mqtt import MQTTOutput, MQTTConfig

        # Make isinstance return True for our mock event
        mock_isinstance.return_value = True

        config = MQTTConfig()
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

    def test_on_connect_callback_success(self) -> None:
        """Test successful connection callback."""
        from nwws.outputs.mqtt import MQTTOutput, MQTTConfig
        config = MQTTConfig()
        output = MQTTOutput(config=config)

        # Simulate successful connection (rc=0)
        output._on_connect(None, None, {}, 0)  # type: ignore[arg-type]

        assert output._connected is True

    def test_on_connect_callback_failure(self) -> None:
        """Test failed connection callback."""
        from nwws.outputs.mqtt import MQTTOutput, MQTTConfig
        config = MQTTConfig()
        output = MQTTOutput(config=config)

        # Simulate failed connection (rc!=0)
        output._on_connect(None, None, {}, 1)  # type: ignore[arg-type]

        assert output._connected is False

    def test_on_disconnect_callback(self) -> None:
        """Test disconnect callback."""
        from nwws.outputs.mqtt import MQTTOutput, MQTTConfig
        config = MQTTConfig()
        output = MQTTOutput(config=config)
        output._connected = True

        # Simulate disconnection
        output._on_disconnect(None, None, 0)  # type: ignore[arg-type]

        assert output._connected is False
