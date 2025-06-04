# pyright: standard
"""Tests for DatabaseOutput."""

from datetime import UTC, datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from nwws.models.events.noaa_port_event_data import NoaaPortEventData
from nwws.models.events.text_product_event_data import TextProductEventData
from nwws.models.events.xml_event_data import XmlEventData
from nwws.outputs.database import (
    Base,
    DatabaseConfig,
    DatabaseOutput,
    WeatherEventModel,
    WeatherEventContent,
    WeatherEventMetadata,
)
from nwws.pipeline import PipelineEventMetadata, PipelineStage


class TestDatabaseConfig:
    """Test cases for DatabaseConfig."""

    def test_init_default_parameters(self) -> None:
        """Test DatabaseConfig initialization with default parameters."""
        config = DatabaseConfig()

        assert config.database_url == "sqlite:///weather_events.db"
        assert config.echo_sql is False
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.create_tables is True

    def test_init_custom_parameters(self) -> None:
        """Test DatabaseConfig initialization with custom parameters."""
        config = DatabaseConfig(
            database_url="postgresql://user:pass@localhost/test",
            echo_sql=True,
            pool_size=10,
            max_overflow=20,
            create_tables=False,
        )

        assert config.database_url == "postgresql://user:pass@localhost/test"
        assert config.echo_sql is True
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.create_tables is False

    def test_engine_kwargs_sqlite(self) -> None:
        """Test engine kwargs for SQLite database."""
        config = DatabaseConfig(database_url="sqlite:///test.db", echo_sql=True)
        kwargs = config.engine_kwargs

        assert kwargs == {"echo": True}

    def test_engine_kwargs_postgresql(self) -> None:
        """Test engine kwargs for PostgreSQL database."""
        config = DatabaseConfig(
            database_url="postgresql://user:pass@localhost/test",
            echo_sql=True,
            pool_size=10,
            max_overflow=20,
        )
        kwargs = config.engine_kwargs

        expected = {
            "echo": True,
            "pool_size": 10,
            "max_overflow": 20,
        }
        assert kwargs == expected


class TestDatabaseModels:
    """Test cases for database models."""

    @pytest.fixture
    def engine(self) -> Engine:
        """Create in-memory SQLite engine for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine

    def test_weather_event_creation(self, engine: Engine) -> None:
        """Test WeatherEvent model creation and storage."""
        event_id = str(uuid4())
        issue_time = datetime.now(timezone.utc)

        with Session(engine) as session:
            weather_event = WeatherEventModel(
                event_id=event_id,
                awipsid="CAPTEST",
                cccc="KBOU",
                product_id="TEST123",
                issue_time=issue_time,
                subject="Test Subject",
                ttaaii="TTAA01",
                content_type="text/plain",
                event_type="test",
            )

            session.add(weather_event)
            session.commit()

            # Verify storage
            stored = session.query(WeatherEventModel).filter_by(event_id=event_id).first()
            assert stored is not None
            assert stored.event_id == event_id
            assert stored.awipsid == "CAPTEST"
            assert stored.cccc == "KBOU"
            assert stored.product_id == "TEST123"
            # SQLite stores datetime without timezone, so compare naive versions
            assert stored.issue_time.replace(tzinfo=timezone.utc) == issue_time
            assert stored.subject == "Test Subject"
            assert stored.ttaaii == "TTAA01"
            assert stored.content_type == "text/plain"
            assert stored.event_type == "test"

    def test_weather_event_content_relationship(self, engine: Engine) -> None:
        """Test WeatherEvent and WeatherEventContent relationship."""
        event_id = str(uuid4())

        with Session(engine) as session:
            weather_event = WeatherEventModel(
                event_id=event_id,
                awipsid="CAPTEST",
                cccc="KBOU",
                product_id="TEST123",
                issue_time=datetime.now(UTC),
                subject="Test Subject",
                ttaaii="TTAA01",
                content_type="text/plain",
                event_type="test",
            )

            session.add(weather_event)
            session.flush()  # Get the ID

            content = WeatherEventContent(
                event_id=weather_event.id,
                noaaport_content="Raw NOAA Port content",
                processed_content='{"processed": "content"}',
            )

            session.add(content)
            session.commit()

            # Test relationship
            stored_event = session.query(WeatherEventModel).filter_by(event_id=event_id).first()
            assert stored_event is not None
            assert stored_event.raw_content is not None
            assert stored_event.raw_content.noaaport_content == "Raw NOAA Port content"
            assert stored_event.raw_content.processed_content == '{"processed": "content"}'

    def test_weather_event_metadata_relationship(self, engine: Engine) -> None:
        """Test WeatherEvent and WeatherEventMetadata relationship."""
        event_id = str(uuid4())

        with Session(engine) as session:
            weather_event = WeatherEventModel(
                event_id=event_id,
                awipsid="CAPTEST",
                cccc="KBOU",
                product_id="TEST123",
                issue_time=datetime.now(timezone.utc),
                subject="Test Subject",
                ttaaii="TTAA01",
                content_type="text/plain",
                event_type="test",
            )

            session.add(weather_event)
            session.flush()  # Get the ID

            metadata1 = WeatherEventMetadata(
                event_id=weather_event.id,
                key="test_key1",
                value="test_value1",
            )

            metadata2 = WeatherEventMetadata(
                event_id=weather_event.id,
                key="test_key2",
                value="test_value2",
            )

            session.add_all([metadata1, metadata2])
            session.commit()

            # Test relationship
            stored_event = session.query(WeatherEventModel).filter_by(event_id=event_id).first()
            assert stored_event is not None
            assert len(stored_event.metadata_entries) == 2

            metadata_dict = {m.key: m.value for m in stored_event.metadata_entries}
            assert metadata_dict["test_key1"] == "test_value1"
            assert metadata_dict["test_key2"] == "test_value2"


class TestDatabaseOutput:
    """Test cases for DatabaseOutput."""

    @pytest.fixture
    def config(self) -> DatabaseConfig:
        """Create test database configuration."""
        return DatabaseConfig(database_url="sqlite:///:memory:")

    @pytest.fixture
    def mock_text_product_event(self) -> TextProductEventData:
        """Create mock TextProductEventData."""
        mock_product = Mock()
        mock_product.model_dump_json.return_value = '{"test": "data"}'

        return TextProductEventData(
            metadata=PipelineEventMetadata(
                event_id=str(uuid4()),
                source="test",
                stage=PipelineStage.INGEST,
            ),
            awipsid="CAPTEST",
            cccc="KBOU",
            id="TEST123",
            issue=datetime.now(timezone.utc),
            subject="Test Subject",
            ttaaii="TTAA01",
            delay_stamp=None,
            noaaport="Raw NOAA Port content",
            content_type="text/plain",
            product=mock_product,
        )

    @pytest.fixture
    def mock_xml_event(self) -> XmlEventData:
        """Create mock XmlEventData."""
        return XmlEventData(
            metadata=PipelineEventMetadata(
                event_id=str(uuid4()),
                source="test",
                stage=PipelineStage.INGEST,
            ),
            awipsid="CAPTEST",
            cccc="KBOU",
            id="XML123",
            issue=datetime.now(timezone.utc),
            subject="XML Subject",
            ttaaii="TTAA01",
            delay_stamp=None,
            noaaport="Raw XML content",
            content_type="application/xml",
            xml="<xml>content</xml>",
        )

    @pytest.fixture
    def mock_noaa_port_event(self) -> NoaaPortEventData:
        """Create mock NoaaPortEventData."""
        return NoaaPortEventData(
            metadata=PipelineEventMetadata(
                event_id=str(uuid4()),
                source="test",
                stage=PipelineStage.INGEST,
            ),
            awipsid="CAPTEST",
            cccc="KBOU",
            id="NOAA123",
            issue=datetime.now(timezone.utc),
            subject="NOAA Subject",
            ttaaii="TTAA01",
            delay_stamp=None,
            noaaport="Raw NOAA content",
            content_type="text/plain",
        )

    def test_init_default_parameters(self, config: DatabaseConfig) -> None:
        """Test DatabaseOutput initialization with default parameters."""
        output = DatabaseOutput(config=config)

        assert output.output_id == "database"
        assert output.config == config
        assert output._engine is None
        assert output.stats["events_stored"] == 0
        assert output.stats["events_failed"] == 0
        assert output.stats["last_event_time"] is None

    def test_init_custom_parameters(self, config: DatabaseConfig) -> None:
        """Test DatabaseOutput initialization with custom parameters."""
        output = DatabaseOutput(output_id="custom-db", config=config)

        assert output.output_id == "custom-db"
        assert output.config == config

    async def test_start_success(self, config: DatabaseConfig) -> None:
        """Test successful database output start."""
        output = DatabaseOutput(config=config)

        await output.start()

        assert output.is_started
        assert output._engine is not None
        assert output.is_connected

    async def test_start_connection_failure(self) -> None:
        """Test database output start with connection failure."""
        config = DatabaseConfig(database_url="postgresql://invalid:invalid@localhost/invalid")
        output = DatabaseOutput(config=config)

        with pytest.raises(Exception):
            await output.start()

        assert output._engine is None

    async def test_stop_success(self, config: DatabaseConfig) -> None:
        """Test successful database output stop."""
        output = DatabaseOutput(config=config)
        await output.start()

        await output.stop()

        assert not output.is_started
        assert output._engine is None

    async def test_send_text_product_event(
        self,
        config: DatabaseConfig,
        mock_text_product_event: TextProductEventData
    ) -> None:
        """Test sending TextProductEventData."""
        output = DatabaseOutput(config=config)
        await output.start()

        await output.send(mock_text_product_event)

        # Verify event was stored
        with Session(output._engine) as session:
            stored_event = session.query(WeatherEventModel).filter_by(
                event_id=mock_text_product_event.metadata.event_id
            ).first()

            assert stored_event is not None
            assert stored_event.awipsid == mock_text_product_event.awipsid
            assert stored_event.event_type == "text_product"
            assert stored_event.raw_content is not None
            assert stored_event.raw_content.processed_content == '{"test": "data"}'

        assert output.stats["events_stored"] == 1
        assert output.stats["events_failed"] == 0

    async def test_send_xml_event(
        self,
        config: DatabaseConfig,
        mock_xml_event: XmlEventData
    ) -> None:
        """Test sending XmlEventData."""
        output = DatabaseOutput(config=config)
        await output.start()

        await output.send(mock_xml_event)

        # Verify event was stored
        with Session(output._engine) as session:
            stored_event = session.query(WeatherEventModel).filter_by(
                event_id=mock_xml_event.metadata.event_id
            ).first()

            assert stored_event is not None
            assert stored_event.awipsid == mock_xml_event.awipsid
            assert stored_event.event_type == "xml"
            assert stored_event.raw_content is not None
            assert stored_event.raw_content.processed_content == "<xml>content</xml>"

    async def test_send_noaa_port_event(
        self,
        config: DatabaseConfig,
        mock_noaa_port_event: NoaaPortEventData
    ) -> None:
        """Test sending basic NoaaPortEventData."""
        output = DatabaseOutput(config=config)
        await output.start()

        await output.send(mock_noaa_port_event)

        # Verify event was stored
        with Session(output._engine) as session:
            stored_event = session.query(WeatherEventModel).filter_by(
                event_id=mock_noaa_port_event.metadata.event_id
            ).first()

            assert stored_event is not None
            assert stored_event.awipsid == mock_noaa_port_event.awipsid
            assert stored_event.event_type == "noaa_port"
            assert stored_event.raw_content is not None
            assert stored_event.raw_content.processed_content is None

    async def test_send_duplicate_event(
        self,
        config: DatabaseConfig,
        mock_text_product_event: TextProductEventData
    ) -> None:
        """Test sending duplicate event (should skip)."""
        output = DatabaseOutput(config=config)
        await output.start()

        # Send event twice
        await output.send(mock_text_product_event)
        await output.send(mock_text_product_event)

        # Verify only one event was stored
        with Session(output._engine) as session:
            count = session.query(WeatherEventModel).filter_by(
                event_id=mock_text_product_event.metadata.event_id
            ).count()

            assert count == 1

        assert output.stats["events_stored"] == 1

    async def test_send_non_noaa_port_event(self, config: DatabaseConfig) -> None:
        """Test sending non-NoaaPortEventData (should skip)."""
        output = DatabaseOutput(config=config)
        await output.start()

        # Create generic pipeline event
        mock_event = Mock()
        mock_event.__class__.__name__ = "PipelineEvent"

        await output.send(mock_event)

        # Verify no events were stored
        with Session(output._engine) as session:
            count = session.query(WeatherEventModel).count()
            assert count == 0

        assert output.stats["events_stored"] == 0

    async def test_send_without_engine(
        self,
        config: DatabaseConfig,
        mock_text_product_event: TextProductEventData
    ) -> None:
        """Test sending event without engine available."""
        output = DatabaseOutput(config=config)
        # Don't start the output

        await output.send(mock_text_product_event)

        assert output.stats["events_stored"] == 0

    async def test_metadata_storage(
        self,
        config: DatabaseConfig,
        mock_text_product_event: TextProductEventData
    ) -> None:
        """Test that pipeline metadata is stored correctly."""
        # Add custom metadata
        mock_text_product_event.metadata = mock_text_product_event.metadata.with_custom_updates(
            custom_key="custom_value",
            another_key="another_value"
        )

        output = DatabaseOutput(config=config)
        await output.start()

        await output.send(mock_text_product_event)

        # Verify metadata was stored
        with Session(output._engine) as session:
            stored_event = session.query(WeatherEventModel).filter_by(
                event_id=mock_text_product_event.metadata.event_id
            ).first()

            assert stored_event is not None
            metadata_dict = {m.key: m.value for m in stored_event.metadata_entries}

            # Check pipeline metadata
            assert "pipeline_source" in metadata_dict
            assert "pipeline_stage" in metadata_dict
            assert metadata_dict["pipeline_source"] == "test"
            assert metadata_dict["pipeline_stage"] == "ingest"

            # Check custom metadata
            assert "custom_custom_key" in metadata_dict
            assert "custom_another_key" in metadata_dict
            assert metadata_dict["custom_custom_key"] == "custom_value"
            assert metadata_dict["custom_another_key"] == "another_value"

    def test_mask_database_url(self, config: DatabaseConfig) -> None:
        """Test database URL masking for security."""
        output = DatabaseOutput(config=config)

        # Test with password
        masked = output._mask_database_url("postgresql://user:password@localhost/db")
        assert masked == "postgresql://user:***@localhost/db"

        # Test without password
        masked = output._mask_database_url("postgresql://user@localhost/db")
        assert masked == "postgresql://***@localhost/db"

        # Test SQLite URL
        masked = output._mask_database_url("sqlite:///test.db")
        assert masked == "sqlite:///test.db"

    def test_get_output_metadata_noaa_port_event(
        self,
        config: DatabaseConfig,
        mock_noaa_port_event: NoaaPortEventData
    ) -> None:
        """Test get_output_metadata for NoaaPortEventData."""
        output = DatabaseOutput(config=config)

        metadata = output.get_output_metadata(mock_noaa_port_event)

        assert metadata["database_connected"] is False  # Not started
        assert metadata["database_event_processed"] is True
        assert metadata["database_event_type"] == "noaa_port"
        assert metadata["database_content_size"] == len(mock_noaa_port_event.noaaport)
        assert "database_stats" in metadata

    def test_get_output_metadata_non_noaa_port_event(self, config: DatabaseConfig) -> None:
        """Test get_output_metadata for non-NoaaPortEventData."""
        output = DatabaseOutput(config=config)
        mock_event = Mock()
        mock_event.__class__.__name__ = "PipelineEvent"

        metadata = output.get_output_metadata(mock_event)

        assert metadata["database_event_processed"] is False
        assert metadata["database_skip_reason"] == "not_noaa_port_event"

    async def test_store_event_error_handling(
        self,
        config: DatabaseConfig,
        mock_text_product_event: TextProductEventData
    ) -> None:
        """Test error handling during event storage."""
        output = DatabaseOutput(config=config)
        await output.start()

        # Force an error by closing the engine
        if output._engine is not None:
            output._engine.dispose()
            output._engine = None

        await output.send(mock_text_product_event)

        assert output.stats["events_failed"] == 0  # Error in send, not store_event
        assert output.stats["events_stored"] == 0

    def test_is_connected_no_engine(self, config: DatabaseConfig) -> None:
        """Test is_connected property without engine."""
        output = DatabaseOutput(config=config)

        assert output.is_connected is False

    async def test_is_connected_with_engine(self, config: DatabaseConfig) -> None:
        """Test is_connected property with engine."""
        output = DatabaseOutput(config=config)
        await output.start()

        assert output.is_connected is True
