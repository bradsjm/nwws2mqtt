# pyright: strict
"""Database output for pipeline events using SQLAlchemy."""

from __future__ import annotations

import asyncio
import contextlib
import os
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
    """Base class for all SQLAlchemy database models.

    This class serves as the declarative base for all database models in the
    weather event processing system. It provides the foundational mapping
    configuration and metadata management for SQLAlchemy ORM operations.
    All model classes inherit from this base to ensure consistent database
    schema generation and relationship handling.
    """


class WeatherEventModel(Base):
    """SQLAlchemy model representing a weather event record in the database.

    This model stores the core weather event data received from NOAA Port feeds,
    including event identification, timing information, product metadata, and
    classification details. The model serves as the primary entity for weather
    event storage and provides relationships to content and metadata tables
    for comprehensive event tracking.

    The model includes indexed fields for efficient querying by AWIPS ID, CCCC
    code, product ID, issue time, and event type. Foreign key relationships
    enable cascading operations for content and metadata management.

    Attributes:
        id: Primary key auto-increment identifier
        event_id: Unique event identifier (UUID format, indexed)
        awipsid: AWIPS product identifier (10 chars max, indexed)
        cccc: 4-character originating office code (indexed)
        product_id: Product identifier string (50 chars max, indexed)
        issue_time: Product issuance timestamp (timezone-aware, indexed)
        subject: Product subject line (255 chars max)
        ttaaii: WMO header identifier (8 chars max, indexed)
        delay_stamp: Optional delay timestamp for late products
        content_type: MIME content type classification
        event_type: Event classification (text_product, xml, noaa_port)
        created_at: Record creation timestamp (timezone-aware, indexed)
        raw_content: One-to-one relationship to content storage
        metadata_entries: One-to-many relationship to metadata entries

    """

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
        """Return a string representation of the weather event model.

        Provides a concise summary of the weather event including the database
        ID, unique event identifier, AWIPS ID, and product ID for debugging
        and logging purposes.

        Returns:
            Formatted string containing key event identifiers.

        """
        return (
            f"WeatherEvent(id={self.id!r}, event_id={self.event_id!r}, "
            f"awipsid={self.awipsid!r}, product_id={self.product_id!r})"
        )


class WeatherEventContent(Base):
    """SQLAlchemy model for storing weather event content data.

    This model manages the storage of both raw NOAA Port content and processed
    content derived from weather events. The separation of content from the
    main event record enables efficient querying when content data is not
    needed and supports large text storage without impacting event metadata
    operations.

    The model maintains a one-to-one relationship with WeatherEventModel
    through a foreign key constraint, ensuring referential integrity and
    enabling cascading delete operations when events are removed.

    Attributes:
        id: Primary key auto-increment identifier
        event_id: Foreign key reference to weather_events.id (unique)
        noaaport_content: Raw content from NOAA Port feed (unlimited text)
        processed_content: Parsed/transformed content (unlimited text, nullable)
        event: Back-reference to the parent WeatherEventModel

    """

    __tablename__ = "weather_event_content"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("weather_events.id"), unique=True)
    noaaport_content: Mapped[str] = mapped_column(Text)
    processed_content: Mapped[str | None] = mapped_column(Text)

    # Relationship back to event
    event: Mapped[WeatherEventModel] = relationship("WeatherEvent", back_populates="raw_content")

    def __repr__(self) -> str:
        """Return a string representation of the weather event content.

        Provides the associated event ID and a preview of the content for
        debugging purposes. Content is truncated to 50 characters to prevent
        excessive output in logs and debugging sessions.

        Returns:
            Formatted string with event ID and content preview.

        """
        content_preview = (
            self.noaaport_content[:50] + "..."
            if len(self.noaaport_content) > 50
            else self.noaaport_content
        )
        return f"WeatherEventContent(event_id={self.event_id!r}, preview={content_preview!r})"


class WeatherEventMetadata(Base):
    """SQLAlchemy model for storing flexible metadata associated with weather events.

    This model provides extensible key-value storage for weather event metadata
    that doesn't fit into the structured fields of the main event model. It
    supports pipeline metadata, custom attributes, VTEC information, UGC data,
    and other dynamic properties that vary by event type and processing stage.

    The model uses a many-to-one relationship with WeatherEventModel, allowing
    multiple metadata entries per event while maintaining referential integrity
    through foreign key constraints and cascading delete operations.

    Attributes:
        id: Primary key auto-increment identifier
        event_id: Foreign key reference to weather_events.id
        key: Metadata key identifier (100 chars max)
        value: Metadata value content (unlimited text)
        event: Back-reference to the parent WeatherEventModel

    """

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
        """Return a string representation of the weather event metadata.

        Provides the metadata key and a preview of the value for debugging
        purposes. Values are truncated to 50 characters to prevent excessive
        output in logs and debugging sessions.

        Returns:
            Formatted string with metadata key and value preview.

        """
        value_preview = self.value[:50] + "..." if len(self.value) > 50 else self.value
        return f"WeatherEventMetadata(key={self.key!r}, value={value_preview!r})"


@dataclass
class CleanupResults:
    """Results container for database cleanup operations.

    This dataclass aggregates the results of different cleanup phases performed
    by the WeatherProductCleanupService. It tracks the number of events deleted
    in each cleanup category to provide comprehensive reporting and monitoring
    of cleanup effectiveness.

    The results enable administrators to understand which cleanup strategies
    are most active and monitor the health of the database retention system.

    Attributes:
        product_expired: Events deleted due to product expiration times
        event_expired: Events deleted due to VTEC event expiration
        product_specific: Events deleted by product-specific retention rules
        time_based: Events deleted by fallback age-based cleanup

    """

    product_expired: int = 0
    event_expired: int = 0
    product_specific: int = 0
    time_based: int = 0

    @property
    def total_deleted(self) -> int:
        """Calculate the total number of events deleted across all cleanup phases.

        Returns:
            Sum of all deletion counts from different cleanup strategies.

        """
        return self.product_expired + self.event_expired + self.product_specific + self.time_based


@dataclass
class DatabaseConfig:
    """Configuration container for database output and cleanup operations.

    This dataclass centralizes all database-related configuration including
    connection parameters, cleanup settings, and retention policies. It supports
    both programmatic configuration and environment variable initialization,
    enabling flexible deployment scenarios from development to production.

    The configuration implements NWS-specific retention standards and provides
    safety mechanisms like dry-run mode and deletion limits to prevent
    accidental data loss during cleanup operations.

    The configuration supports both SQLite and PostgreSQL deployments with
    appropriate connection pooling settings that are automatically adjusted
    based on the database type.

    Attributes:
        database_url: Database connection URL (supports SQLite and PostgreSQL)
        echo_sql: Enable SQLAlchemy SQL logging for debugging
        create_tables: Automatically create database tables on startup
        pool_size: Connection pool size (PostgreSQL only)
        max_overflow: Maximum connection overflow (PostgreSQL only)
        pool_timeout: Connection acquisition timeout in seconds
        pool_recycle: Connection recycling interval in seconds
        cleanup_enabled: Enable automatic database cleanup
        cleanup_interval_hours: Interval between cleanup cycles
        respect_product_expiration: Honor product-specific expiration times
        respect_vtec_expiration: Honor VTEC event expiration times
        respect_ugc_expiration: Honor UGC zone expiration times
        use_product_specific_retention: Apply product-type retention rules
        vtec_expiration_buffer_hours: Buffer time past VTEC expiration
        max_deletions_per_cycle: Safety limit on deletions per cleanup cycle
        dry_run_mode: Test cleanup without actually deleting data
        default_retention_days: Fallback retention for products without expiration
        short_duration_retention_hours: Retention for short-lived warnings
        medium_duration_retention_hours: Retention for medium-duration products
        long_duration_retention_hours: Retention for long-duration products
        routine_retention_hours: Retention for routine forecast products
        administrative_retention_days: Retention for administrative messages

    """

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

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        """Create database configuration from environment variables.

        This factory method initializes a DatabaseConfig instance by reading
        configuration values from environment variables. It provides sensible
        defaults for all settings while allowing complete customization through
        environment variables in production deployments.

        The method handles type conversion for non-string values and supports
        boolean environment variables using string representations ("true"/"false").
        All database connection, cleanup, and retention settings can be configured
        through environment variables with the "DATABASE_" prefix.

        Environment Variables:
            DATABASE_URL: Database connection string
            DATABASE_ECHO_SQL: Enable SQL logging (true/false)
            DATABASE_CREATE_TABLES: Auto-create tables (true/false)
            DATABASE_POOL_SIZE: Connection pool size (integer)
            DATABASE_MAX_OVERFLOW: Maximum connection overflow (integer)
            DATABASE_POOL_TIMEOUT: Connection timeout seconds (integer)
            DATABASE_POOL_RECYCLE: Connection recycle seconds (integer)
            DATABASE_CLEANUP_ENABLED: Enable cleanup (true/false)
            DATABASE_CLEANUP_INTERVAL_HOURS: Cleanup interval (integer)
            DATABASE_RESPECT_PRODUCT_EXPIRATION: Honor product expiration (true/false)
            DATABASE_RESPECT_VTEC_EXPIRATION: Honor VTEC expiration (true/false)
            DATABASE_RESPECT_UGC_EXPIRATION: Honor UGC expiration (true/false)
            DATABASE_USE_PRODUCT_SPECIFIC_RETENTION: Use product rules (true/false)
            DATABASE_VTEC_EXPIRATION_BUFFER_HOURS: VTEC buffer hours (integer)
            DATABASE_MAX_DELETIONS_PER_CYCLE: Deletion limit per cycle (integer)
            DATABASE_DRY_RUN_MODE: Dry run mode (true/false)
            DATABASE_DEFAULT_RETENTION_DAYS: Default retention days (integer)
            DATABASE_SHORT_DURATION_RETENTION_HOURS: Short duration hours (integer)
            DATABASE_MEDIUM_DURATION_RETENTION_HOURS: Medium duration hours (integer)
            DATABASE_LONG_DURATION_RETENTION_HOURS: Long duration hours (integer)
            DATABASE_ROUTINE_RETENTION_HOURS: Routine retention hours (integer)
            DATABASE_ADMINISTRATIVE_RETENTION_DAYS: Administrative retention days (integer)

        Returns:
            Configured DatabaseConfig instance with values from environment.

        """
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///weather_events.db"),
            echo_sql=os.getenv("DATABASE_ECHO_SQL", "false").lower() == "true",
            create_tables=os.getenv("DATABASE_CREATE_TABLES", "true").lower() == "true",
            pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
            pool_timeout=int(os.getenv("DATABASE_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DATABASE_POOL_RECYCLE", "3600")),
            cleanup_enabled=os.getenv("DATABASE_CLEANUP_ENABLED", "false").lower() == "true",
            cleanup_interval_hours=int(os.getenv("DATABASE_CLEANUP_INTERVAL_HOURS", "6")),
            respect_product_expiration=os.getenv(
                "DATABASE_RESPECT_PRODUCT_EXPIRATION", "true"
            ).lower()
            == "true",
            respect_vtec_expiration=os.getenv("DATABASE_RESPECT_VTEC_EXPIRATION", "true").lower()
            == "true",
            respect_ugc_expiration=os.getenv("DATABASE_RESPECT_UGC_EXPIRATION", "true").lower()
            == "true",
            use_product_specific_retention=os.getenv(
                "DATABASE_USE_PRODUCT_SPECIFIC_RETENTION", "true"
            ).lower()
            == "true",
            vtec_expiration_buffer_hours=int(
                os.getenv("DATABASE_VTEC_EXPIRATION_BUFFER_HOURS", "2")
            ),
            max_deletions_per_cycle=int(os.getenv("DATABASE_MAX_DELETIONS_PER_CYCLE", "500")),
            dry_run_mode=os.getenv("DATABASE_DRY_RUN_MODE", "false").lower() == "true",
            default_retention_days=int(os.getenv("DATABASE_DEFAULT_RETENTION_DAYS", "7")),
            short_duration_retention_hours=int(
                os.getenv("DATABASE_SHORT_DURATION_RETENTION_HOURS", "1")
            ),
            medium_duration_retention_hours=int(
                os.getenv("DATABASE_MEDIUM_DURATION_RETENTION_HOURS", "24")
            ),
            long_duration_retention_hours=int(
                os.getenv("DATABASE_LONG_DURATION_RETENTION_HOURS", "72")
            ),
            routine_retention_hours=int(os.getenv("DATABASE_ROUTINE_RETENTION_HOURS", "12")),
            administrative_retention_days=int(
                os.getenv("DATABASE_ADMINISTRATIVE_RETENTION_DAYS", "30")
            ),
        )

    @property
    def engine_kwargs(self) -> dict[str, Any]:
        """Generate SQLAlchemy engine configuration parameters.

        This property creates a dictionary of engine configuration parameters
        suitable for SQLAlchemy engine creation. It automatically adjusts
        the configuration based on the database type, applying connection
        pooling settings only for databases that support them (PostgreSQL)
        while using appropriate settings for SQLite.

        The method ensures that connection pooling parameters are not applied
        to SQLite databases, which use a different connection model and would
        generate warnings or errors with pooling configuration.

        Returns:
            Dictionary containing engine configuration parameters including
            echo settings and conditional pooling parameters based on database type.

        """
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
    """Intelligent database cleanup service implementing NWS product timing standards.

    This service manages automated database cleanup operations using a multi-tiered
    approach that respects National Weather Service product specifications and
    timing standards. It implements cleanup strategies based on product expiration
    times, VTEC event lifecycles, product-specific retention rules, and fallback
    time-based cleanup for comprehensive database maintenance.

    The service operates asynchronously with configurable scheduling and includes
    safety mechanisms like deletion limits, dry-run mode, and transaction rollback
    to prevent accidental data loss. It maintains detailed logging of cleanup
    operations and provides statistics for monitoring and debugging.

    The cleanup strategies are prioritized to first remove events that have
    definitively expired according to NWS standards, then apply product-specific
    retention rules based on operational requirements, and finally use age-based
    cleanup as a safety net for products without explicit expiration data.

    Key Features:
        - Multi-phase cleanup with NWS standard compliance
        - Asynchronous operation with configurable scheduling
        - Safety limits and dry-run testing capabilities
        - Comprehensive logging and error handling
        - Product-specific retention rule engine
        - VTEC event lifecycle awareness
        - UGC zone expiration time handling
        - Transaction safety with rollback protection
    """

    def __init__(self, config: DatabaseConfig, engine: Engine) -> None:
        """Initialize the cleanup service with configuration and database engine.

        Sets up the cleanup service with database access and retention rule
        configuration. The initialization creates product-specific retention
        rules based on NWS operational standards and prepares the asynchronous
        task management system for scheduled cleanup operations.

        The service configures retention rules for different product types
        based on their operational characteristics and NWS specifications.
        Short-duration products like tornado warnings receive minimal retention,
        while administrative products are retained longer for historical purposes.

        Args:
            config: Database configuration containing cleanup settings and retention rules.
            engine: SQLAlchemy database engine for database operations.

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
        """Start the asynchronous periodic cleanup task scheduler.

        Initiates the background cleanup scheduler if cleanup is enabled in the
        configuration. The scheduler runs as an independent asyncio task that
        performs cleanup operations at the configured interval. The task is
        stored as a reference to prevent garbage collection and enable proper
        shutdown handling.

        The method logs the startup status and configuration details for
        monitoring and debugging purposes. If cleanup is disabled, the method
        returns immediately without starting the scheduler.

        Raises:
            asyncio.CancelledError: If the cleanup task is cancelled during startup.

        """
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
        """Stop the periodic cleanup task scheduler gracefully.

        Cancels the running cleanup task and waits for it to complete gracefully.
        The method uses contextlib.suppress to handle the expected CancelledError
        that occurs when the task is cancelled, preventing it from propagating
        to the caller.

        The method ensures proper cleanup of the task reference and logs the
        shutdown status for monitoring purposes. If no cleanup task is running,
        the method returns immediately without performing any operations.
        """
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None
            logger.info("Database cleanup scheduler stopped")

    async def _cleanup_loop(self) -> None:
        """Execute the periodic cleanup loop with error handling and scheduling.

        This internal method implements the main cleanup scheduler loop that
        runs continuously until cancelled. It sleeps for the configured interval
        between cleanup cycles and executes cleanup operations with comprehensive
        error handling to prevent scheduler failure from isolated cleanup errors.

        The loop logs cleanup results when events are deleted and handles
        various exception types appropriately. Network and system errors are
        logged as errors, while unexpected exceptions are logged with full
        stack traces for debugging purposes.

        The method uses asyncio.sleep for the interval timing, which is
        interruptible by task cancellation for clean shutdown handling.

        Raises:
            asyncio.CancelledError: When the cleanup task is cancelled for shutdown.

        """
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
        """Execute comprehensive multi-tiered cleanup of expired weather events.

        This method implements the core cleanup logic using a four-phase approach
        that progressively applies different cleanup strategies based on data
        availability and NWS standards. The phases are executed in order of
        preference, with more specific cleanup methods applied before general
        fallback strategies.

        Phase 1 removes events that have explicit product expiration times from
        UGC lines or other product specifications. Phase 2 handles VTEC events
        that have reached their ending times with appropriate buffer periods.
        Phase 3 applies product-type-specific retention rules based on operational
        requirements. Phase 4 provides age-based fallback cleanup for products
        without specific expiration data.

        All operations are performed within a database transaction that is
        committed only if all phases complete successfully. In dry-run mode,
        the transaction is rolled back to prevent actual data deletion while
        still providing accurate deletion counts for testing.

        Returns:
            CleanupResults object containing deletion counts for each cleanup phase
            and total events processed.

        Raises:
            ConnectionError: If database connection is lost during cleanup.
            OSError: For database I/O errors during cleanup operations.
            ValueError: For invalid data encountered during cleanup processing.

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
        """Clean up weather products that have exceeded their documented expiration times.

        This method implements Phase 1 cleanup by identifying and removing products
        that have explicit expiration times stored in their metadata. It specifically
        looks for UGC (Universal Geographic Code) expiration times that are commonly
        found in Watch/Warning/Advisory products and indicate when the product
        should no longer be considered active.

        The method queries the metadata table for events with "ugc_expiration_time"
        entries that contain valid timestamps before the current time. Products
        with null, empty, or invalid expiration times are skipped to prevent
        accidental deletion of products that should remain active.

        This cleanup strategy has the highest priority because it uses explicit
        expiration information provided by the National Weather Service in the
        product content itself, making it the most authoritative cleanup method.

        Args:
            session: Active database session for executing queries and deletions.

        Returns:
            Number of events deleted based on product expiration times.

        Raises:
            OSError: For database connection or query execution errors.
            RuntimeError: For session management or transaction errors.
            ValueError: For invalid timestamp data in metadata entries.

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
        """Clean up weather events based on VTEC event ending times with buffer period.

        This method implements Phase 2 cleanup by processing events that have
        VTEC (Valid Time Event Code) event ending times that have passed. VTEC
        is used in hazardous weather products to specify the valid time period
        for weather events, and the ending time indicates when the event is
        no longer expected to be active.

        The method includes a configurable buffer period past the VTEC ending
        time to account for potential event extensions or late updates. Events
        with "Until Further Notice" ending times (000000T0000Z) are explicitly
        excluded to prevent deletion of ongoing events without defined end times.

        This cleanup strategy has high priority because VTEC timing is specified
        by the National Weather Service and represents the operational lifetime
        of weather events as determined by meteorologists.

        Args:
            session: Active database session for executing queries and deletions.

        Returns:
            Number of events deleted based on VTEC event expiration times.

        Raises:
            OSError: For database connection or query execution errors.
            RuntimeError: For session management or transaction errors.
            ValueError: For invalid VTEC timestamp data in metadata entries.

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
        """Clean up events using product-specific retention rules based on AWIPS ID patterns.

        This method implements Phase 3 cleanup by applying retention rules that
        are specific to different types of weather products. Each product type
        has different operational requirements and typical lifespans, so the
        retention periods are customized based on NWS operational practices
        and the nature of the weather phenomena.

        The method iterates through predefined retention rules that map AWIPS ID
        patterns to retention periods. For example, tornado warnings (TOR) have
        very short retention periods because they are typically valid for less
        than an hour, while administrative products (PNS) are retained longer
        for historical reference.

        Product-specific cleanup is applied when events don't have explicit
        expiration data but can be classified by their product type. This
        provides appropriate retention management while respecting the operational
        characteristics of different weather products.

        Args:
            session: Active database session for executing queries and deletions.

        Returns:
            Total number of events deleted across all product-specific retention rules.

        Raises:
            OSError: For database connection or query execution errors.
            RuntimeError: For session management or transaction errors.
            ValueError: For invalid data encountered during retention rule processing.

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
        """Execute fallback cleanup based on event age for products without specific expiration data.

        This method implements Phase 4 cleanup as a safety net for events that
        don't have explicit expiration times or don't match product-specific
        retention rules. It removes events older than the configured default
        retention period to prevent unlimited database growth while being
        conservative about deletion.

        The age-based cleanup uses the event creation timestamp rather than
        the product issue time to ensure that even delayed or reprocessed
        events are eventually cleaned up. The method respects the maximum
        deletion limit per cycle to prevent system overload from large
        batch deletions.

        This cleanup strategy has the lowest priority and serves as a fallback
        to ensure database maintenance even for products that don't fit into
        the other cleanup categories. It provides a safety net against
        database growth while being conservative about data retention.

        Args:
            session: Active database session for executing queries and deletions.

        Returns:
            Number of events deleted based on age-based retention rules.

        Raises:
            OSError: For database connection or query execution errors.
            RuntimeError: For session management or transaction errors.
            ValueError: For invalid data encountered during age-based processing.

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
        """Delete weather events and all related data with safety checks and logging.

        This method handles the actual deletion of events and their associated
        content and metadata records. It implements several safety mechanisms
        including deletion limits, dry-run mode, and comprehensive error handling
        to prevent accidental data loss and system overload.

        The deletion process removes data in the correct order to maintain
        referential integrity: metadata entries first, then content records,
        and finally the events themselves. The method uses ORM-based deletion
        for better type safety and automatic relationship handling.

        In dry-run mode, the method calculates and logs what would be deleted
        without actually performing the deletions, enabling safe testing of
        cleanup configurations. The method respects configured deletion limits
        to prevent system overload from large batch operations.

        Args:
            session: Active database session for executing deletions.
            event_ids: List of weather event IDs to delete.
            reason: Description of the cleanup reason for logging purposes.

        Returns:
            Number of events actually deleted (or that would be deleted in dry-run mode).

        Raises:
            OSError: For database connection or deletion execution errors.
            RuntimeError: For session management or transaction errors.
            ValueError: For invalid event ID data or deletion parameters.

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
    """Pipeline output component for storing weather events in a relational database.

    This output component provides comprehensive database storage for weather events
    processed through the pipeline system. It manages database connections, table
    creation, event storage, and automated cleanup operations while providing
    detailed monitoring and error handling capabilities.

    The component supports both SQLite and PostgreSQL databases with appropriate
    connection pooling and configuration management. It includes an integrated
    cleanup service that implements NWS-specific retention policies to manage
    database growth while preserving operationally relevant data.

    The output processes NOAA Port events by storing the core event data, raw
    content, processed content, and flexible metadata in a normalized relational
    schema. It provides duplicate detection, transaction safety, and comprehensive
    logging for production-grade reliability.

    Key Features:
        - Multi-database support (SQLite, PostgreSQL) with connection pooling
        - Automatic table creation and schema management
        - Duplicate event detection and prevention
        - Integrated cleanup service with NWS retention standards
        - Comprehensive error handling and logging
        - Production monitoring with statistics and health checks
        - Flexible metadata storage for pipeline and custom data
        - Transaction safety with rollback protection
        - Connection masking for security in logs
    """

    def __init__(self, output_id: str = "database", *, config: DatabaseConfig | None) -> None:
        """Initialize the database output component with configuration and monitoring.

        Sets up the database output with the provided configuration or creates
        a default configuration from environment variables. Initializes internal
        state for connection management, cleanup service, and statistics tracking.

        The initialization prepares the output for database operations but does
        not establish database connections or create tables. Those operations
        are performed during the start() method to enable proper error handling
        and resource management in the pipeline lifecycle.

        Args:
            output_id: Unique identifier for this output component in the pipeline.
            config: Database configuration object, or None to use environment variables.

        """
        super().__init__(output_id)
        self.config = config or DatabaseConfig.from_env()
        self._engine: Engine | None = None
        self._cleanup_service: WeatherProductCleanupService | None = None
        self._stats: dict[str, int | float | None] = {
            "events_stored": 0,
            "events_failed": 0,
            "last_event_time": None,
        }

        logger.info("Database Output initialized", output_id=self.output_id)

    async def start(self) -> None:
        """Start the database output component and initialize all database resources.

        This method establishes the database connection, creates tables if configured,
        tests connectivity, and starts the cleanup scheduler. It implements
        comprehensive error handling to ensure proper resource cleanup if any
        initialization step fails.

        The startup process includes creating the SQLAlchemy engine with appropriate
        configuration for the database type, testing the connection with a simple
        query, creating database tables if enabled, and initializing the cleanup
        service with its scheduler.

        All database connection details are logged with sensitive information
        masked for security. If any step fails, the method cleans up partially
        initialized resources and propagates the error to the caller.

        Raises:
            ConnectionError: If database connection cannot be established.
            OSError: For database I/O errors during initialization.
            ValueError: For invalid configuration or database URL format.

        """
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
        """Stop the database output component and cleanup all resources gracefully.

        This method performs an orderly shutdown of the database output by stopping
        the cleanup scheduler, disposing of database connections, and cleaning up
        internal state. It logs final statistics and handles errors during shutdown
        to prevent exceptions from interrupting the pipeline shutdown process.

        The shutdown process first stops the cleanup service to prevent new cleanup
        operations, then disposes of the database engine to close all connections
        and release resources. Statistics are logged for monitoring purposes.

        Errors during shutdown are logged but do not prevent the shutdown process
        from completing. This ensures that the pipeline can shut down cleanly
        even if database resources are in an inconsistent state.
        """
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
        """Process and store a pipeline event in the database with error handling.

        This method receives pipeline events and stores NOAA Port events in the
        database while skipping other event types. It provides comprehensive
        error handling, duplicate detection, and statistics tracking for monitoring
        and debugging purposes.

        The method validates that the database engine is available, attempts to
        store the event, and updates internal statistics based on the operation
        result. Events that are successfully stored increment the stored counter,
        while failures increment the failed counter for monitoring purposes.

        Non-NOAA Port events are skipped with debug logging to indicate the
        filtering behavior. Database connection issues are handled gracefully
        with warning messages that don't crash the pipeline.

        Args:
            event: Pipeline event to process and potentially store in the database.

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
        """Store a NOAA Port event in the database with duplicate detection and transaction safety.

        This internal method handles the detailed process of storing weather events
        in the database schema. It performs duplicate detection based on event IDs,
        creates the normalized data structure with event, content, and metadata
        records, and manages database transactions for consistency.

        The storage process creates a WeatherEventModel record with core event
        data, stores raw and processed content in WeatherEventContent, and saves
        pipeline and custom metadata in WeatherEventMetadata entries. The method
        uses database transactions to ensure atomicity and rolls back changes
        if any step fails.

        Duplicate events are detected by checking for existing records with the
        same event ID. This prevents duplicate storage while allowing reprocessing
        of events that may arrive multiple times through the pipeline.

        Args:
            event: NOAA Port event data to store in the database.

        Returns:
            True if the event was stored successfully, False if skipped due to duplication.

        Raises:
            RuntimeError: If the database engine is not available.
            ConnectionError: For database connection issues during storage.
            OSError: For database I/O errors during transaction processing.
            ValueError: For invalid event data or database constraint violations.

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
        """Determine the event type classification string based on event class.

        This method classifies the event into a string category based on its
        Python class type. The classification is used for database storage
        and querying to enable filtering and analysis by event type.

        The method supports text product events, XML events, and generic
        NOAA Port events, returning appropriate string identifiers for
        each category that can be used in database queries and reports.

        Args:
            event: NOAA Port event to classify by type.

        Returns:
            String identifier for the event type: "text_product", "xml", or "noaa_port".

        """
        if isinstance(event, TextProductEventData):
            return "text_product"
        if isinstance(event, XmlEventData):
            return "xml"
        return "noaa_port"

    def _get_processed_content(self, event: NoaaPortEventData) -> str | None:
        """Extract processed content from the event based on event type.

        This method extracts the processed or parsed content from weather events
        when available. For text product events, it serializes the parsed product
        model to JSON format. For XML events, it returns the XML content directly.
        For generic NOAA Port events, no processed content is available.

        The processed content provides a structured representation of the weather
        data that can be used for analysis, debugging, and integration with other
        systems that need parsed rather than raw content.

        Args:
            event: NOAA Port event to extract processed content from.

        Returns:
            Processed content as a string, or None if no processed content is available.

        """
        if isinstance(event, TextProductEventData):
            return event.product.model_dump_json(indent=2, exclude_defaults=True, by_alias=True)
        if isinstance(event, XmlEventData):
            return event.xml
        return None

    def _create_metadata_entries(
        self, event_db_id: int, event: NoaaPortEventData
    ) -> list[WeatherEventMetadata]:
        """Create metadata entries for flexible storage of event attributes.

        This method generates a list of metadata entries that capture both
        pipeline metadata and custom event attributes in a flexible key-value
        format. The metadata system enables storage of dynamic attributes that
        don't fit into the structured event fields.

        Pipeline metadata includes information about event processing such as
        source, stage, timestamp, and trace ID. Custom metadata includes any
        additional attributes added during event processing such as VTEC data,
        UGC information, or product-specific details.

        The method prefixes metadata keys to organize them by source and prevent
        naming conflicts between pipeline and custom metadata entries.

        Args:
            event_db_id: Database ID of the weather event for foreign key reference.
            event: NOAA Port event containing metadata to store.

        Returns:
            List of WeatherEventMetadata objects ready for database insertion.

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
        """Mask sensitive authentication information in database URLs for secure logging.

        This method processes database connection URLs to hide passwords and other
        sensitive authentication information while preserving enough detail for
        debugging and monitoring purposes. It handles standard database URL
        formats that include authentication credentials.

        The masking preserves the protocol, username (if present), and host
        information while replacing passwords with asterisks. This enables
        log analysis and debugging without exposing sensitive credentials
        in log files or monitoring systems.

        Args:
            url: Database connection URL that may contain sensitive authentication data.

        Returns:
            Masked URL string with password information replaced by asterisks.

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
        """Check if the database connection is active and responsive.

        This property performs a simple database connectivity test by executing
        a basic query against the database. It provides a reliable way to check
        database health without requiring specific table access or complex
        operations.

        The connectivity check uses a simple COUNT query that should work with
        any database system and returns quickly. Connection errors are caught
        and handled gracefully, returning False to indicate connection issues.

        Returns:
            True if database connection is active and responsive, False otherwise.

        """
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
        """Get current database output statistics for monitoring and debugging.

        This property returns a copy of the internal statistics dictionary
        that tracks database output performance and activity. The statistics
        include counters for successful and failed operations as well as
        timing information for monitoring purposes.

        The returned dictionary is a copy to prevent external modification
        of internal statistics while providing access to current values
        for monitoring, debugging, and reporting purposes.

        Returns:
            Dictionary containing current statistics including events stored,
            events failed, and last event timestamp.

        """
        return self._stats.copy()

    def get_output_metadata(self, event: PipelineEvent) -> dict[str, Any]:
        """Generate comprehensive metadata about the database output operation.

        This method creates detailed metadata about the database output's handling
        of a specific event. The metadata includes database connectivity status,
        connection information, statistics, and event-specific processing details
        that enable monitoring and debugging of database operations.

        For NOAA Port events, the metadata includes processing confirmation,
        event type classification, and content size information. For other event
        types, it indicates why the event was skipped. Database connection
        information is masked for security.

        The metadata follows the pipeline's metadata conventions by prefixing
        keys with the output ID to prevent naming conflicts with other components.

        Args:
            event: Pipeline event that was processed by the database output.

        Returns:
            Dictionary containing comprehensive metadata about the database operation
            including connectivity, statistics, and event-specific details.

        """
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
        """Manually trigger an immediate database cleanup operation.

        This method provides on-demand cleanup capabilities for administrative
        purposes or emergency maintenance. It bypasses the scheduled cleanup
        interval and executes a full cleanup cycle immediately, returning
        detailed results about the cleanup operation.

        The manual trigger is useful for testing cleanup configurations,
        responding to disk space issues, or performing maintenance operations
        outside of the regular cleanup schedule. It uses the same cleanup
        logic as the scheduled operations.

        Returns:
            CleanupResults object containing deletion counts by cleanup phase,
            or empty results if cleanup service is not initialized.

        """
        if not self._cleanup_service:
            logger.warning("Cleanup service not initialized")
            return CleanupResults()

        logger.info("Manual cleanup triggered", output_id=self.output_id)
        return await self._cleanup_service.cleanup_expired_events()

    def get_cleanup_stats(self) -> dict[str, Any]:
        """Get comprehensive cleanup service statistics and configuration information.

        This method returns detailed information about the cleanup service
        configuration and operational status. It provides visibility into
        cleanup settings, retention policies, and service state for monitoring,
        debugging, and administrative purposes.

        The returned information includes all cleanup configuration parameters,
        retention settings for different product types, operational flags like
        dry-run mode, and the current status of the cleanup service. This
        enables administrators to verify cleanup configuration and monitor
        cleanup service health.

        Returns:
            Dictionary containing cleanup configuration parameters, retention
            settings, operational flags, and service status information.

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
