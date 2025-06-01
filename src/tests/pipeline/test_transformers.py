# pyright: strict
"""Tests for pipeline transformers."""

from dataclasses import dataclass
from typing import Any

import pytest

from nwws.pipeline.errors import TransformerError
from nwws.pipeline.transformers import (
    ChainTransformer,
    PassThroughTransformer,
    Transformer,
    TransformerConfig,
    TransformerRegistry,
)
from nwws.pipeline.types import PipelineEvent, PipelineEventMetadata, PipelineStage


class MockTransformer(Transformer):
    """Mock transformer for testing."""

    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Mock transform method."""
        # Add a simple modification to track transformation
        return event.with_stage(PipelineStage.TRANSFORM)


@dataclass
class TestEvent(PipelineEvent):
    """Test event with content for chain testing."""

    content: str = "default"


class TestTransformerRegistry:
    """Test transformer registry functionality."""

    def test_register_and_create_passthrough(self) -> None:
        """Test registering and creating a passthrough transformer."""
        registry = TransformerRegistry()

        config = TransformerConfig(
            transformer_type="passthrough",
            transformer_id="test-passthrough",
        )

        transformer = registry.create(config)
        assert isinstance(transformer, PassThroughTransformer)
        # PassThroughTransformer uses the provided transformer_id
        assert transformer.transformer_id == "test-passthrough"

    def test_register_custom_transformer(self) -> None:
        """Test registering a custom transformer."""
        registry = TransformerRegistry()

        def mock_factory(transformer_id: str) -> MockTransformer:
            return MockTransformer(transformer_id)

        registry.register("mock", mock_factory)

        config = TransformerConfig(
            transformer_type="mock",
            transformer_id="test-mock",
        )

        transformer = registry.create(config)
        assert isinstance(transformer, MockTransformer)
        assert transformer.transformer_id == "test-mock"

    def test_create_unknown_transformer_type(self) -> None:
        """Test creating an unknown transformer type raises error."""
        registry = TransformerRegistry()

        config = TransformerConfig(
            transformer_type="unknown",
            transformer_id="test-unknown",
        )

        with pytest.raises(TransformerError, match="Unknown transformer type: unknown"):
            registry.create(config)

    def test_get_available_types(self) -> None:
        """Test getting available transformer types."""
        registry = TransformerRegistry()
        available_types = registry.get_available_types()

        # Should include built-in types
        assert "passthrough" in available_types
        assert "chain" in available_types
        assert "attribute_mapper" in available_types


class TestChainTransformerFactory:
    """Test the built-in chain transformer factory."""

    def test_create_chain_transformer_with_valid_config(self) -> None:
        """Test creating a chain transformer with valid configuration."""
        registry = TransformerRegistry()

        # Register mock transformers for chaining
        def mock1_factory(transformer_id: str) -> MockTransformer:
            return MockTransformer(transformer_id)

        def mock2_factory(transformer_id: str) -> MockTransformer:
            return MockTransformer(transformer_id)

        registry.register("mock1", mock1_factory)
        registry.register("mock2", mock2_factory)

        config = TransformerConfig(
            transformer_type="chain",
            transformer_id="test-chain",
            config={
                "transformers": [
                    {"transformer_type": "mock1", "transformer_id": "first"},
                    {"transformer_type": "mock2", "transformer_id": "second"},
                ]
            },
        )

        transformer = registry.create(config)
        assert isinstance(transformer, ChainTransformer)
        assert transformer.transformer_id == "test-chain"
        assert len(transformer.transformers) == 2
        assert transformer.transformers[0].transformer_id == "first"
        assert transformer.transformers[1].transformer_id == "second"

    def test_create_chain_transformer_with_nested_config(self) -> None:
        """Test creating a chain transformer with nested transformer configs."""
        registry = TransformerRegistry()

        # Register a mock transformer that accepts config
        class ConfigurableMockTransformer(Transformer):
            def __init__(self, transformer_id: str, **kwargs: Any) -> None:
                super().__init__(transformer_id)
                self.config: dict[str, Any] = kwargs

            def transform(self, event: PipelineEvent) -> PipelineEvent:
                return event.with_stage(PipelineStage.TRANSFORM)

        def configurable_mock_factory(
            transformer_id: str, **kwargs: Any
        ) -> ConfigurableMockTransformer:
            return ConfigurableMockTransformer(transformer_id, **kwargs)

        registry.register("configurable", configurable_mock_factory)

        config = TransformerConfig(
            transformer_type="chain",
            transformer_id="test-chain",
            config={
                "transformers": [
                    {
                        "transformer_type": "configurable",
                        "transformer_id": "first",
                        "config": {"param1": "value1"},
                    },
                    {
                        "transformer_type": "passthrough",
                        "transformer_id": "second",
                    },
                ]
            },
        )

        transformer = registry.create(config)
        assert isinstance(transformer, ChainTransformer)
        assert len(transformer.transformers) == 2
        assert hasattr(transformer.transformers[0], "config")
        first_transformer = transformer.transformers[0]
        assert isinstance(first_transformer, ConfigurableMockTransformer)
        assert first_transformer.config["param1"] == "value1"

    def test_create_chain_transformer_empty_list(self) -> None:
        """Test creating a chain transformer with empty transformers list."""
        registry = TransformerRegistry()

        config = TransformerConfig(
            transformer_type="chain",
            transformer_id="test-chain",
            config={"transformers": []},
        )

        transformer = registry.create(config)
        assert isinstance(transformer, ChainTransformer)
        assert len(transformer.transformers) == 0

    def test_create_chain_transformer_missing_transformers(self) -> None:
        """Test creating a chain transformer without transformers config."""
        registry = TransformerRegistry()

        config = TransformerConfig(
            transformer_type="chain",
            transformer_id="test-chain",
            config={},
        )

        transformer = registry.create(config)
        assert isinstance(transformer, ChainTransformer)
        assert len(transformer.transformers) == 0

    def test_create_chain_transformer_invalid_transformers_type(self) -> None:
        """Test creating a chain transformer with invalid transformers type."""
        registry = TransformerRegistry()

        config = TransformerConfig(
            transformer_type="chain",
            transformer_id="test-chain",
            config={"transformers": "not-a-list"},
        )

        with pytest.raises(
            TransformerError, match="Chain transformer requires 'transformers' list"
        ):
            registry.create(config)

    def test_create_chain_transformer_invalid_transformer_config(self) -> None:
        """Test creating a chain transformer with invalid nested transformer config."""
        registry = TransformerRegistry()

        config = TransformerConfig(
            transformer_type="chain",
            transformer_id="test-chain",
            config={
                "transformers": [
                    {"transformer_type": "passthrough"},  # Missing transformer_id
                ]
            },
        )

        with pytest.raises(
            TransformerError, match="missing 'transformer_type' or 'transformer_id'"
        ):
            registry.create(config)

    def test_create_chain_transformer_unknown_nested_type(self) -> None:
        """Test creating a chain transformer with unknown nested transformer type."""
        registry = TransformerRegistry()

        config = TransformerConfig(
            transformer_type="chain",
            transformer_id="test-chain",
            config={
                "transformers": [
                    {"transformer_type": "unknown", "transformer_id": "test"},
                ]
            },
        )

        with pytest.raises(TransformerError, match="Unknown transformer type: unknown"):
            registry.create(config)

    def test_chain_transformer_execution(self) -> None:
        """Test that chain transformer executes transformers in sequence."""
        registry = TransformerRegistry()

        # Create a transformer that adds a marker to the event
        class MarkerTransformer(Transformer):
            def __init__(self, transformer_id: str, marker: str = "default") -> None:
                super().__init__(transformer_id)
                self.marker = marker

            def transform(self, event: PipelineEvent) -> PipelineEvent:
                # Add marker to event content (assuming it has content attribute)
                if isinstance(event, TestEvent):
                    return TestEvent(
                        content=event.content + f"-{self.marker}",
                        metadata=event.metadata,
                    )
                return event

        def marker_factory(transformer_id: str, marker: str = "default") -> MarkerTransformer:
            return MarkerTransformer(transformer_id, marker)

        registry.register("marker", marker_factory)

        config = TransformerConfig(
            transformer_type="chain",
            transformer_id="test-chain",
            config={
                "transformers": [
                    {
                        "transformer_type": "marker",
                        "transformer_id": "first",
                        "config": {"marker": "A"},
                    },
                    {
                        "transformer_type": "marker",
                        "transformer_id": "second",
                        "config": {"marker": "B"},
                    },
                ]
            },
        )

        chain_transformer = registry.create(config)

        # Create a test event with content
        test_event = TestEvent(
            content="start",
            metadata=PipelineEventMetadata(
                source="test",
                stage=PipelineStage.INGEST,
            ),
        )

        # Transform the event
        result = chain_transformer.transform(test_event)

        # Verify the chain executed both transformers
        assert isinstance(result, TestEvent)
        assert result.content == "start-A-B"

    def test_create_chain_transformer_with_application_config(self) -> None:
        """Test creating a chain transformer with the actual application configuration format."""
        registry = TransformerRegistry()

        # Register the same transformers that the application uses
        class NoaaPortTransformer(Transformer):
            def transform(self, event: PipelineEvent) -> PipelineEvent:
                return event

        class XmlTransformer(Transformer):
            def transform(self, event: PipelineEvent) -> PipelineEvent:
                return event

        def noaaport_factory(transformer_id: str, **_kwargs: Any) -> NoaaPortTransformer:
            return NoaaPortTransformer(transformer_id)

        def xml_factory(transformer_id: str, **_kwargs: Any) -> XmlTransformer:
            return XmlTransformer(transformer_id)

        registry.register("noaaport", noaaport_factory)
        registry.register("xml", xml_factory)

        # Use the exact configuration format from the application
        config = TransformerConfig(
            transformer_type="chain",
            transformer_id="chain",
            config={
                "transformers": [
                    {"transformer_type": "noaaport", "transformer_id": "noaaport"},
                    {"transformer_type": "xml", "transformer_id": "xml"},
                ]
            },
        )

        transformer = registry.create(config)
        assert isinstance(transformer, ChainTransformer)
        assert transformer.transformer_id == "chain"
        assert len(transformer.transformers) == 2

        # Verify the transformers are the correct types and have correct IDs
        assert isinstance(transformer.transformers[0], NoaaPortTransformer)
        assert transformer.transformers[0].transformer_id == "noaaport"
        assert isinstance(transformer.transformers[1], XmlTransformer)
        assert transformer.transformers[1].transformer_id == "xml"
