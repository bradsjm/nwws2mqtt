# pyright: strict
"""Duplicate filter for rejecting duplicate products within a time window."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from loguru import logger

from nwws.pipeline.filters import Filter

if TYPE_CHECKING:
    from nwws.pipeline.types import PipelineEvent

type ProductId = str
type Timestamp = float


class DuplicateFilter(Filter):
    """Filter that rejects duplicate products within a configurable time window.

    Uses the product 'id' field as the key for duplicate detection.
    Maintains an in-memory cache of recently seen product IDs with timestamps.

    Example:
        # Create filter with 5-minute window (default)
        filter = DuplicateFilter()

        # Create filter with custom 10-minute window
        filter = DuplicateFilter("my-filter", window_seconds=600.0)

        # Use in pipeline
        result = filter.should_process(event)  # True for first occurrence
        result = filter.should_process(event)  # False for duplicate within window

        # Get cache statistics
        stats = filter.get_cache_stats()
        print(f"Tracking {stats['total_tracked']} products")

    """

    def __init__(
        self,
        filter_id: str = "duplicate-filter",
        window_seconds: float = 300.0,  # 5 minutes default
    ) -> None:
        """Initialize the duplicate filter.

        Args:
            filter_id: Unique identifier for this filter instance.
            window_seconds: Time window in seconds to track duplicates (default: 5 minutes).

        """
        super().__init__(filter_id)
        self.window_seconds = window_seconds
        self._seen_products: dict[ProductId, Timestamp] = {}

    def should_process(self, event: PipelineEvent) -> bool:
        """Determine if the event should be processed.

        Rejects events with product IDs that have been seen within the time window.

        Args:
            event: The pipeline event to evaluate.

        Returns:
            False if product ID was seen within window, True otherwise.

        """
        # Clean up expired entries before processing
        self._cleanup_expired_entries()

        # Check if event has an 'id' attribute (product ID)
        if not hasattr(event, "id"):
            logger.warning(
                "Event missing product id attribute",
                filter_id=self.filter_id,
                event_id=event.metadata.event_id,
                event_type=type(event).__name__,
            )
            # Allow events without product ID to pass through
            return True

        product_id = getattr(event, "id", "")
        if not isinstance(product_id, str) or not product_id:
            logger.warning(
                "Invalid product id",
                filter_id=self.filter_id,
                event_id=event.metadata.event_id,
                product_id=product_id,
            )
            # Allow events with invalid product ID to pass through
            return True

        current_time = time.time()

        # Check if we've seen this product ID recently
        if product_id in self._seen_products:
            last_seen = self._seen_products[product_id]
            time_since_last = current_time - last_seen

            if time_since_last < self.window_seconds:
                logger.debug(
                    "Filtering duplicate product",
                    filter_id=self.filter_id,
                    event_id=event.metadata.event_id,
                    product_id=product_id,
                    time_since_last_seconds=round(time_since_last, 2),
                    window_seconds=self.window_seconds,
                )
                return False

        # Record this product ID with current timestamp
        self._seen_products[product_id] = current_time

        logger.debug(
            "Allowing new product",
            filter_id=self.filter_id,
            event_id=event.metadata.event_id,
            product_id=product_id,
            total_tracked_products=len(self._seen_products),
        )

        return True

    def _cleanup_expired_entries(self) -> None:
        """Remove expired entries from the seen products cache."""
        current_time = time.time()
        expired_keys = [
            product_id
            for product_id, timestamp in self._seen_products.items()
            if current_time - timestamp >= self.window_seconds
        ]

        for product_id in expired_keys:
            del self._seen_products[product_id]

        if expired_keys:
            logger.debug(
                "Cleaned up expired duplicate tracking entries",
                filter_id=self.filter_id,
                expired_count=len(expired_keys),
                remaining_count=len(self._seen_products),
            )

    def get_cache_stats(self) -> dict[str, int | float]:
        """Get statistics about the duplicate filter cache.

        Returns:
            Dictionary containing cache statistics.

        """
        current_time = time.time()
        return {
            "total_tracked": len(self._seen_products),
            "window_seconds": self.window_seconds,
            "oldest_entry_age": (
                current_time - min(self._seen_products.values())
                if self._seen_products
                else 0.0
            ),
        }

