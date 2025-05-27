#!/usr/bin/env python3
"""Test script to verify MQTT handler functionality."""

import asyncio
import sys
import os

# Add app directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "app")))

from models import OutputConfig
from handlers.mqtt import MQTTOutputHandler
from messaging import ProductMessage
import time


async def test_mqtt_handler():
    """Test MQTT handler connection and publishing."""
    print("Testing MQTT handler...")

    # Create config from environment
    config = OutputConfig.from_env()
    print(f"MQTT Config: broker={config.mqtt_broker}, port={config.mqtt_port}")

    # Create MQTT handler
    handler = MQTTOutputHandler(config)

    try:
        # Start handler
        print("Starting MQTT handler...")
        await handler.start()
        print(f"Handler connected: {handler.is_connected}")

        if handler.is_connected:
            # Test publishing a message
            print("Publishing test message...")
            test_data = '{"test": "message", "timestamp": "' + str(time.time()) + '"}'
            await handler.publish("TEST", "FXXX01", "TEST123", test_data, "Test Message")
            print("Message published successfully!")

        # Stop handler
        print("Stopping handler...")
        await handler.stop()
        print("Handler stopped")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mqtt_handler())
