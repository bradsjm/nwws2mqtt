# pyright: strict
"""Database output for pipeline events using SQLAlchemy."""

from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from loguru import logger
from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    and_,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from nwws.models.events.noaa_port_event_data import NoaaPortEventData
from nwws.models.events.text_product_event_data import TextProductEventData
from nwws.models.events.xml_event_data import XmlEventData
from nwws.pipeline import Output, PipelineEvent

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


class Base(DeclarativeBase):
    """Base class for all database models."""


class WeatherEventModel(Base):
    """Weather event database model."""

    __tablename__ = "weather_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    awipsid: Mapped[str] = mapped_column(String(10), index=True)
    cccc: Mapped[str] = mapped_column(String(4), index=True)
    product_id: Mapped[str] = mapped_column(String(50), index=True)
    issue_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    subject: Mapped[str] = mapped_column(String(255))
    ttaaii: Mapped[str] = mapped_column(String(8), index=True)
    delay_stamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_type: Mapped[str] = mapped_column(String(50))
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    # Content relationships
    raw_content: Mapped[WeatherEventContent | None] = relationship(
        "WeatherEventContent",
        back_populates="event",
        cascade="all, delete-orphan",
        uselist=False,
    )

    # Metadata relationship
    metadata_entries: Mapped[list[WeatherEventMetadata]] = relationship(
        "WeatherEventMetadata", back_populates="event", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Return string representation of weather event."""
        return (
            f"WeatherEvent(id={self.id!r}, event_id={self.event_id!r}, "
            f"awipsid={self.awipsid!r}, product_id={self.product_id!r})"
        )


class WeatherEventContent(Base):
    """Weather event content storage."""

    __tablename__ = "weather_event_content"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("weather_events.id"), unique=True)
    noaaport_content: Mapped[str] = mapped_column(Text)
    processed_content: Mapped[str | None] = mapped_column(Text)

    # Relationship back to event
    event: Mapped[WeatherEventModel] = relationship("WeatherEvent", back_populates="raw_content")

    def __repr__(self) -> str:
        """Return string representation of content."""
        content_preview = (
            self.noaaport_content[:50] + "..."
            if len(self.noaaport_content) > 50
            else self.noaaport_content
        )
        return f"WeatherEventContent(event_id={self.event_id!r}, preview={content_preview!r})"


class WeatherEventMetadata(Base):
    """Weather event metadata storage."""

    __tablename__ = "weather_event_metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("weather_events.id"))
    key: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)

    # Relationship back to event
    event: Mapped[WeatherEventModel] = relationship(
        "WeatherEvent", back_populates="metadata_entries"
    )

    def __repr__(self) -> str:
        """Return string representation of metadata."""
        value_preview = self.value[:50] + "..." if len(self.value) > 50 else self.value
        return f"WeatherEventMetadata(key={self.key!r}, value={value_preview!r})"


@dataclass
class CleanupResults:
    """Results from database cleanup operation."""

    product_expired: int = 0
    event_expired: int = 0
    product_specific: int = 0
    time_based: int = 0

    @property
    def total_deleted(self) -> int:
        """Total number of events deleted."""
        return self.product_expired + self.event_expired + self.product_specific + self.time_based


@dataclass
class DatabaseConfig:
    """Configuration for database output."""

    # Core database settings
    database_url: str = field(default="sqlite:///weather_events.db")
    echo_sql: bool = field(default=False)
    create_tables: bool = field(default=True)
    pool_size: int = field(default=5)
    max_overflow: int = field(default=10)
    pool_timeout: int = field(default=30)
    pool_recycle: int = field(default=3600)

    # Enhanced cleanup configuration based on NWS standards
    cleanup_enabled: bool = field(default=False)
    cleanup_interval_hours: int = field(default=6)  # More frequent for weather data

    # Respect NWS product timing standards
    respect_product_expiration: bool = field(default=True)
    respect_vtec_expiration: bool = field(default=True)
    respect_ugc_expiration: bool = field(default=True)

    # Product-specific retention rules
    use_product_specific_retention: bool = field(default=True)

    # Safety settings
    vtec_expiration_buffer_hours: int = field(default=2)  # Keep 2 hours past VTEC expiration
    max_deletions_per_cycle: int = field(default=500)  # Limit deletions to prevent overload
    dry_run_mode: bool = field(default=False)  # Test without actually deleting

    # Fallback retention for products without expiration data
    default_retention_days: int = field(default=7)

    # Product-specific retention periods (based on NWS specifications)
    short_duration_retention_hours: int = field(default=1)  # TOR, SVR, EWW, SMW
    medium_duration_retention_hours: int = field(default=24)  # FFW, FLW, CFW
    long_duration_retention_hours: int = field(default=72)  # WSW, watches
    routine_retention_hours: int = field(default=12)  # ZFP, NOW
    administrative_retention_days: int = field(default=30)  # PNS, LSR, PSH

    @property
    def engine_kwargs(self) -> dict[str, Any]:
        """Get engine configuration kwargs."""
        kwargs: dict[str, Any] = {"echo": self.echo_sql}

        # Only add pool settings for non-SQLite databases
        if not self.database_url.startswith("sqlite"):
            kwargs.update(
                {
                    "pool_size": self.pool_size,
                    "max_overflow": self.max_overflow,
                    "pool_timeout": self.pool_timeout,
                    "pool_recycle": self.pool_recycle,
                }
            )

        return kwargs


class WeatherProductCleanupService:
    """Enhanced cleanup service using NWS product timing standards."""

    def __init__(self, config: DatabaseConfig, engine: Engine) -> None:
        """Initialize cleanup service.

        Args:
            config: Database configuration with cleanup settings
            engine: SQLAlchemy database engine

        """
        self.config = config
        self.engine = engine
        self._cleanup_task: asyncio.Task[None] | None = None

        # Product-specific retention rules based on NWS specifications
        self._retention_rules = {
            # Short-duration warnings (from Severe Weather docs)
            "TOR": timedelta(
                hours=self.config.short_duration_retention_hours
            ),  # "15 to 45 minutes from issuance"
            "SVR": timedelta(
                hours=self.config.short_duration_retention_hours
            ),  # "30 to 60 minutes of issuance"
            "EWW": timedelta(hours=3),  # "Up to three hours"
            "SMW": timedelta(hours=self.config.short_duration_retention_hours),  # Marine warnings
            # Medium-duration products
            "FFW": timedelta(
                hours=self.config.medium_duration_retention_hours
            ),  # Flash flood warnings
            "FLW": timedelta(hours=self.config.medium_duration_retention_hours),  # Flood warnings
            "NPW": timedelta(hours=48),  # Non-precipitation warnings
            "CFW": timedelta(
                hours=self.config.medium_duration_retention_hours
            ),  # Coastal flood products
            # Longer-duration products
            "FFA": timedelta(hours=48),  # Flood watches
            "WSW": timedelta(
                hours=self.config.long_duration_retention_hours
            ),  # Winter storm products
            # Routine products
            "ZFP": timedelta(hours=self.config.routine_retention_hours),  # Zone forecasts
            "AFD": timedelta(days=1),  # Area forecast discussions
            "NOW": timedelta(hours=6),  # Short term forecasts
            "SPS": timedelta(hours=6),  # Special weather statements
            "HWO": timedelta(hours=24),  # Hazardous weather outlook
            # Administrative/reports
            "PNS": timedelta(
                days=self.config.administrative_retention_days
            ),  # Public information statements
            "LSR": timedelta(days=self.config.administrative_retention_days),  # Local storm reports
            "PSH": timedelta(days=self.config.administrative_retention_days),  # Post-storm reports
            "ADM": timedelta(days=7),  # Administrative messages
        }

    async def start_cleanup_scheduler(self) -> None:
        """Start the periodic cleanup task."""
        if not self.config.cleanup_enabled:
            logger.info("Database cleanup is disabled")
            return

        logger.info(
            "Starting database cleanup scheduler",
            interval_hours=self.config.cleanup_interval_hours,
            dry_run=self.config.dry_run_mode,
        )

        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_scheduler(self) -> None:
        """Stop the periodic cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None
            logger.info("Database cleanup scheduler stopped")

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup execution."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval_hours * 3600)
                results = await self.cleanup_expired_events()

                if results.total_deleted > 0:
                    logger.info(
                        "Database cleanup completed",
                        product_expired=results.product_expired,
                        event_expired=results.event_expired,
                        product_specific=results.product_specific,
                        time_based=results.time_based,
                        total_deleted=results.total_deleted,
                        dry_run=self.config.dry_run_mode,
                    )
                else:
                    logger.debug("Database cleanup completed - no expired events found")

            except (OSError, RuntimeError, ValueError) as e:
                logger.error("Database cleanup failed", error=str(e), exc_info=True)
            except Exception as e:  # noqa: BLE001
                logger.error("Unexpected database cleanup error", error=str(e), exc_info=True)

    async def cleanup_expired_events(self) -> CleanupResults:
        """Multi-tiered cleanup based on NWS product specifications.

        Returns:
            CleanupResults with counts of deleted events by category

        """
        results = CleanupResults()

        with Session(self.engine) as session:
            try:
                # Phase 1: Product Expiration-Based Cleanup
                if self.config.respect_product_expiration:
                    results.product_expired = await self._cleanup_by_product_expiration(session)

                # Phase 2: VTEC Event-Based Cleanup
                if self.config.respect_vtec_expiration:
                    results.event_expired = await self._cleanup_by_vtec_expiration(session)

                # Phase 3: Product-Type-Specific Cleanup
                if self.config.use_product_specific_retention:
                    results.product_specific = await self._cleanup_by_product_type(session)

                # Phase 4: Fallback Time-Based Cleanup
                results.time_based = await self._cleanup_by_age(session)

                if not self.config.dry_run_mode:
                    session.commit()
                else:
                    session.rollback()

            except Exception as e:
                session.rollback()
                logger.error("Database cleanup transaction failed", error=str(e))
                raise

        return results

    async def _cleanup_by_product_expiration(self, session: Session) -> int:
        """Clean up products past their documented expiration times.

        Args:
            session: Database session

        Returns:
            Number of events deleted

        """
        try:
            # From docs: "For W/W/A products, should not exceed 24 hours from issuance"
            # Parse UGC expiration times from stored metadata
            current_time = datetime.now(UTC)

            expired_products = (
                session.query(WeatherEventModel.id)
                .join(WeatherEventMetadata)
                .filter(
                    and_(
                        WeatherEventMetadata.key == "ugc_expiration_time",
                        WeatherEventMetadata.value != "null",
                        WeatherEventMetadata.value != "",
                        func.cast(WeatherEventMetadata.value, DateTime) < current_time,
                    )
                )
                .distinct()
                .all()
            )

            return await self._delete_events(
                session, [row[0] for row in expired_products], "product_expiration"
            )

        except (OSError, RuntimeError, ValueError) as e:
            logger.warning("Product expiration cleanup failed", error=str(e))
            return 0

    async def _cleanup_by_vtec_expiration(self, session: Session) -> int:
        """Clean up based on VTEC event ending times.

        Args:
            session: Database session

        Returns:
            Number of events deleted

        """
        try:
            current_time = datetime.now(UTC)
            buffer_time = current_time - timedelta(hours=self.config.vtec_expiration_buffer_hours)

            # VTEC ending times from P-VTEC strings
            expired_events = (
                session.query(WeatherEventModel.id)
                .join(WeatherEventMetadata)
                .filter(
                    and_(
                        WeatherEventMetadata.key == "vtec_event_end_time",
                        WeatherEventMetadata.value != "000000T0000Z",  # Not "Until Further Notice"
                        WeatherEventMetadata.value != "null",
                        WeatherEventMetadata.value != "",
                        func.cast(WeatherEventMetadata.value, DateTime) < buffer_time,
                    )
                )
                .distinct()
                .all()
            )

            return await self._delete_events(
                session, [row[0] for row in expired_events], "vtec_expiration"
            )

        except (OSError, RuntimeError, ValueError) as e:
            logger.warning("VTEC expiration cleanup failed", error=str(e))
            return 0

    async def _cleanup_by_product_type(self, session: Session) -> int:
        """Clean up based on product-specific retention rules.

        Args:
            session: Database session

        Returns:
            Number of events deleted

        """
        total_deleted = 0
        current_time = datetime.now(UTC)

        try:
            for awipsid_pattern, retention_period in self._retention_rules.items():
                cutoff_time = current_time - retention_period

                expired_ids = (
                    session.query(WeatherEventModel.id)
                    .filter(
                        and_(
                            WeatherEventModel.awipsid.like(f"{awipsid_pattern}%"),
                            WeatherEventModel.created_at < cutoff_time,
                        )
                    )
                    .all()
                )

                if expired_ids:
                    deleted_count = await self._delete_events(
                        session,
                        [row[0] for row in expired_ids],
                        f"product_type_{awipsid_pattern}",
                    )
                    total_deleted += deleted_count

        except (OSError, RuntimeError, ValueError) as e:
            logger.warning("Product type cleanup failed", error=str(e))

        return total_deleted

    async def _cleanup_by_age(self, session: Session) -> int:
        """Fallback cleanup based on age for products without expiration data.

        Args:
            session: Database session

        Returns:
            Number of events deleted

        """
        try:
            current_time = datetime.now(UTC)
            cutoff_time = current_time - timedelta(days=self.config.default_retention_days)

            # Find old events not already cleaned up by other methods
            old_events = (
                session.query(WeatherEventModel.id)
                .filter(WeatherEventModel.created_at < cutoff_time)
                .limit(self.config.max_deletions_per_cycle)
                .all()
            )

            return await self._delete_events(session, [row[0] for row in old_events], "age_based")

        except (OSError, RuntimeError, ValueError) as e:
            logger.warning("Age-based cleanup failed", error=str(e))
            return 0

    async def _delete_events(self, session: Session, event_ids: list[int], reason: str) -> int:
        """Delete events and related data.

        Args:
            session: Database session
            event_ids: List of event IDs to delete
            reason: Reason for deletion (for logging)

        Returns:
            Number of events actually deleted

        """
        if not event_ids:
            return 0

        # Apply max deletion limit
        if len(event_ids) > self.config.max_deletions_per_cycle:
            logger.warning(
                "Deletion limit exceeded, truncating deletion list",
                requested=len(event_ids),
                limit=self.config.max_deletions_per_cycle,
                reason=reason,
            )
            event_ids = event_ids[: self.config.max_deletions_per_cycle]

        if self.config.dry_run_mode:
            logger.info("DRY RUN: Would delete events", count=len(event_ids), reason=reason)
            return len(event_ids)

        try:
            # Delete related content and metadata using ORM for better type safety

            # Delete metadata entries
            metadata_deleted = (
                session.query(WeatherEventMetadata)
                .filter(WeatherEventMetadata.event_id.in_(event_ids))
                .delete(synchronize_session=False)
            )

            # Delete content entries
            content_deleted = (
                session.query(WeatherEventContent)
                .filter(WeatherEventContent.event_id.in_(event_ids))
                .delete(synchronize_session=False)
            )

            # Delete the events themselves
            events_deleted = (
                session.query(WeatherEventModel)
                .filter(WeatherEventModel.id.in_(event_ids))
                .delete(synchronize_session=False)
            )

            session.commit()

            if events_deleted > 0:
                logger.debug(
                    "Deleted expired events",
                    events=events_deleted,
                    content_records=content_deleted,
                    metadata_records=metadata_deleted,
                    reason=reason,
                )
        except (OSError, RuntimeError, ValueError) as e:
            logger.error(
                "Failed to delete events",
                event_count=len(event_ids),
                reason=reason,
                error=str(e),
            )
            raise
        else:
            return events_deleted


class DatabaseOutput(Output):
    """Output that stores pipeline events in a relational database."""

    def __init__(self, output_id: str = "database", *, config: DatabaseConfig) -> None:
        """Initialize the database output.

        Args:
            output_id: Unique identifier for this output.
            config: Database configuration object.

        """
        super().__init__(output_id)
        self.config = config
        self._engine: Engine | None = None
        self._cleanup_service: WeatherProductCleanupService | None = None
        self._stats: dict[str, int | float | None] = {
            "events_stored": 0,
            "events_failed": 0,
            "last_event_time": None,
        }

        logger.info("Database Output initialized", output_id=self.output_id)

    async def start(self) -> None:
        """Start database output and create tables if needed."""
        await super().start()

        try:
            # Create engine
            self._engine = create_engine(self.config.database_url, **self.config.engine_kwargs)

            # Test connection
            with Session(self._engine) as session:
                session.execute(func.count(1))

            # Create tables if configured
            if self.config.create_tables:
                Base.metadata.create_all(self._engine)
                logger.info(
                    "Database tables created/verified",
                    output_id=self.output_id,
                    url=self._mask_database_url(self.config.database_url),
                )

            # Initialize cleanup service
            self._cleanup_service = WeatherProductCleanupService(self.config, self._engine)
            await self._cleanup_service.start_cleanup_scheduler()

            logger.info(
                "Database output started successfully",
                output_id=self.output_id,
                url=self._mask_database_url(self.config.database_url),
                cleanup_enabled=self.config.cleanup_enabled,
            )

        except (ConnectionError, OSError, ValueError) as e:
            logger.error(
                "Failed to start database output",
                output_id=self.output_id,
                error=str(e),
                url=self._mask_database_url(self.config.database_url),
            )
            if self._engine:
                self._engine.dispose()
                self._engine = None
            raise

    async def stop(self) -> None:
        """Stop database output and cleanup connections."""
        logger.info("Stopping database output", output_id=self.output_id)

        # Stop cleanup service first
        if self._cleanup_service:
            await self._cleanup_service.stop_cleanup_scheduler()
            self._cleanup_service = None

        if self._engine:
            try:
                self._engine.dispose()
                logger.info(
                    "Database output stopped successfully",
                    output_id=self.output_id,
                    stats=self._stats,
                )
            except (ConnectionError, OSError) as e:
                logger.error(
                    "Error stopping database output",
                    output_id=self.output_id,
                    error=str(e),
                )
            finally:
                self._engine = None

        await super().stop()

    async def send(self, event: PipelineEvent) -> None:
        """Store the event in the database.

        Args:
            event: The pipeline event to store.

        """
        if not isinstance(event, NoaaPortEventData):
            logger.debug(
                "Skipping non-NOAA Port event",
                output_id=self.output_id,
                event_type=type(event).__name__,
            )
            return

        if not self._engine:
            logger.warning(
                "Database engine not available, skipping event storage",
                output_id=self.output_id,
                event_id=event.metadata.event_id,
            )
            return

        try:
            stored = await self._store_event(event)
            if stored:
                if isinstance(self._stats["events_stored"], int):
                    self._stats["events_stored"] += 1
                self._stats["last_event_time"] = time.time()

                logger.debug(
                    "Event stored successfully",
                    output_id=self.output_id,
                    event_id=event.metadata.event_id,
                    product_id=event.id,
                    awipsid=event.awipsid,
                )
            else:
                logger.debug(
                    "Event skipped (duplicate)",
                    output_id=self.output_id,
                    event_id=event.metadata.event_id,
                    product_id=event.id,
                )

        except (ConnectionError, OSError, ValueError) as e:
            if isinstance(self._stats["events_failed"], int):
                self._stats["events_failed"] += 1
            logger.error(
                "Failed to store event in database",
                output_id=self.output_id,
                event_id=event.metadata.event_id,
                product_id=event.id,
                error=str(e),
            )

    async def _store_event(self, event: NoaaPortEventData) -> bool:
        """Store a NOAA Port event in the database.

        Args:
            event: The NOAA Port event to store.

        Returns:
            True if event was stored, False if skipped (duplicate).

        """
        if not self._engine:
            msg = "Database engine not available"
            raise RuntimeError(msg)

        with Session(self._engine) as session:
            try:
                # Check if event already exists
                existing = (
                    session.query(WeatherEventModel)
                    .filter_by(event_id=event.metadata.event_id)
                    .first()
                )

                if existing:
                    logger.debug(
                        "Event already exists in database, skipping",
                        output_id=self.output_id,
                        event_id=event.metadata.event_id,
                        existing_id=existing.id,
                    )
                    return False

                # Determine event type
                event_type = self._get_event_type(event)

                # Create weather event record
                weather_event = WeatherEventModel(
                    event_id=event.metadata.event_id,
                    awipsid=event.awipsid,
                    cccc=event.cccc,
                    product_id=event.id,
                    issue_time=event.issue,
                    subject=event.subject,
                    ttaaii=event.ttaaii,
                    delay_stamp=event.delay_stamp,
                    content_type=event.content_type,
                    event_type=event_type,
                )

                session.add(weather_event)
                session.flush()  # Get the ID

                # Store content
                content = WeatherEventContent(
                    event_id=weather_event.id,
                    noaaport_content=event.noaaport,
                    processed_content=self._get_processed_content(event),
                )
                session.add(content)

                # Store metadata
                metadata_entries = self._create_metadata_entries(weather_event.id, event)
                session.add_all(metadata_entries)

                session.commit()

            except (ConnectionError, OSError, ValueError) as e:
                session.rollback()
                logger.error(
                    "Database transaction failed",
                    output_id=self.output_id,
                    event_id=event.metadata.event_id,
                    error=str(e),
                )
                raise
            else:
                return True

    def _get_event_type(self, event: NoaaPortEventData) -> str:
        """Determine the event type string.

        Args:
            event: The event to classify.

        Returns:
            Event type string.

        """
        if isinstance(event, TextProductEventData):
            return "text_product"
        if isinstance(event, XmlEventData):
            return "xml"
        return "noaa_port"

    def _get_processed_content(self, event: NoaaPortEventData) -> str | None:
        """Get processed content from the event.

        Args:
            event: The event to extract content from.

        Returns:
            Processed content string or None.

        """
        if isinstance(event, TextProductEventData):
            return event.product.model_dump_json(indent=2, exclude_defaults=True, by_alias=True)
        if isinstance(event, XmlEventData):
            return event.xml
        return None

    def _create_metadata_entries(
        self, event_db_id: int, event: NoaaPortEventData
    ) -> list[WeatherEventMetadata]:
        """Create metadata entries for the event.

        Args:
            event_db_id: Database ID of the weather event.
            event: The pipeline event.

        Returns:
            List of metadata entries.

        """
        entries: list[WeatherEventMetadata] = []

        # Pipeline metadata
        pipeline_metadata = {
            "source": event.metadata.source,
            "stage": event.metadata.stage.value,
            "timestamp": str(event.metadata.timestamp),
            "trace_id": event.metadata.trace_id or "",
        }

        for key, value in pipeline_metadata.items():
            if value:
                entries.append(
                    WeatherEventMetadata(
                        event_id=event_db_id,
                        key=f"pipeline_{key}",
                        value=str(value),
                    )
                )

        # Custom metadata
        for key, value in event.metadata.custom.items():
            entries.append(
                WeatherEventMetadata(
                    event_id=event_db_id,
                    key=f"custom_{key}",
                    value=str(value),
                )
            )

        return entries

    def _mask_database_url(self, url: str) -> str:
        """Mask sensitive information in database URL.

        Args:
            url: Database URL to mask.

        Returns:
            Masked URL string.

        """
        if "://" in url and "@" in url:
            protocol, rest = url.split("://", 1)
            if "@" in rest:
                auth, host_part = rest.split("@", 1)
                # Mask password but keep username
                if ":" in auth:
                    username, _ = auth.split(":", 1)
                    return f"{protocol}://{username}:***@{host_part}"
                return f"{protocol}://***@{host_part}"
        return url

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        if not self._engine:
            return False

        try:
            with Session(self._engine) as session:
                session.execute(func.count(1))
        except (ConnectionError, OSError):
            return False
        else:
            return True

    @property
    def stats(self) -> dict[str, Any]:
        """Get database output statistics."""
        return self._stats.copy()

    def get_output_metadata(self, event: PipelineEvent) -> dict[str, Any]:
        """Get metadata about the database output operation."""
        metadata = super().get_output_metadata(event)

        # Add database-specific metadata
        metadata[f"{self.output_id}_connected"] = self.is_connected
        metadata[f"{self.output_id}_engine_url"] = self._mask_database_url(self.config.database_url)
        metadata[f"{self.output_id}_stats"] = self.stats

        if isinstance(event, NoaaPortEventData):
            metadata[f"{self.output_id}_event_processed"] = True
            metadata[f"{self.output_id}_event_type"] = self._get_event_type(event)
            metadata[f"{self.output_id}_content_size"] = len(event.noaaport)
        else:
            metadata[f"{self.output_id}_event_processed"] = False
            metadata[f"{self.output_id}_skip_reason"] = "not_noaa_port_event"

        return metadata

    async def trigger_cleanup(self) -> CleanupResults:
        """Manually trigger database cleanup.

        Returns:
            CleanupResults with counts of deleted events by category

        """
        if not self._cleanup_service:
            logger.warning("Cleanup service not initialized")
            return CleanupResults()

        logger.info("Manual cleanup triggered", output_id=self.output_id)
        return await self._cleanup_service.cleanup_expired_events()

    def get_cleanup_stats(self) -> dict[str, Any]:
        """Get cleanup service statistics and configuration.

        Returns:
            Dictionary with cleanup configuration and status

        """
        return {
            "cleanup_enabled": self.config.cleanup_enabled,
            "cleanup_interval_hours": self.config.cleanup_interval_hours,
            "dry_run_mode": self.config.dry_run_mode,
            "respect_product_expiration": self.config.respect_product_expiration,
            "respect_vtec_expiration": self.config.respect_vtec_expiration,
            "respect_ugc_expiration": self.config.respect_ugc_expiration,
            "use_product_specific_retention": self.config.use_product_specific_retention,
            "vtec_expiration_buffer_hours": self.config.vtec_expiration_buffer_hours,
            "max_deletions_per_cycle": self.config.max_deletions_per_cycle,
            "default_retention_days": self.config.default_retention_days,
            "cleanup_service_running": self._cleanup_service is not None,
        }
