#!/usr/bin/env python3
"""Test script to verify the pub-sub refactoring works correctly."""

import sys
import os
import asyncio
import time
from threading import Thread

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from messaging import MessageBus, ProductMessage, Topics
from handlers import OutputConfig, OutputManager

def test_pubsub():
    """Test the pub-sub messaging system."""
    print("Testing pub-sub messaging system...")
    
    # Create a simple output config for console only
    config = OutputConfig(enabled_handlers=["console"])
    
    # Create output manager (which subscribes to product messages)
    manager = OutputManager(config)
    
    # Start the output manager
    async def start_manager():
        await manager.start()
        print("Output manager started and subscribed to topics")
    
    # Run manager startup in a thread
    def run_manager_startup():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(start_manager())
        finally:
            loop.close()
    
    manager_thread = Thread(target=run_manager_startup, daemon=True)
    manager_thread.start()
    manager_thread.join()  # Wait for startup to complete
    
    # Give a moment for the subscription to be established
    time.sleep(0.1)
    
    # Check if there are subscribers
    print(f"Subscribers to {Topics.PRODUCT_RECEIVED}: {len(MessageBus.get_topic_subscribers(Topics.PRODUCT_RECEIVED))}")
    
    # Create a test product message
    test_message = ProductMessage(
        source="TEST",
        afos="TST",
        product_id="TEST123",
        structured_data='{"test": "message"}',
        subject="Test Subject"
    )
    
    print(f"Publishing test message: {test_message.product_id}")
    
    # Publish the message
    MessageBus.publish(Topics.PRODUCT_RECEIVED, message=test_message)
    
    # Give time for the message to be processed
    time.sleep(1)
    
    print("Test completed! If you saw the test message output above, the pub-sub system is working.")
    
    # Cleanup
    async def stop_manager():
        await manager.stop()
    
    def run_manager_stop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(stop_manager())
        finally:
            loop.close()
    
    stop_thread = Thread(target=run_manager_stop, daemon=True)
    stop_thread.start()
    stop_thread.join()

if __name__ == "__main__":
    test_pubsub()
