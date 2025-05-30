# pyright: strict
"""Test message filter for rejecting test messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwws.pipeline.filters import Filter

if TYPE_CHECKING:
    from nwws.pipeline.types import PipelineEvent


class TestMessageFilter(Filter):
    """Filter that rejects test messages with awipsid='TSTMSG'."""

    def __init__(self, filter_id: str = "test-msg-filter") -> None:
        """Initialize the test message filter.

        Args:
            filter_id: Unique identifier for this filter instance.

        """
        super().__init__(filter_id)

    def should_process(self, event: PipelineEvent) -> bool:
        """Determine if the event should be processed.

        Rejects events where awipsid equals 'TSTMSG' (case-insensitive).

        Args:
            event: The pipeline event to evaluate.

        Returns:
            False if awipsid is 'TSTMSG', True otherwise.

        """
        if not hasattr(event, "awipsid"):
            # If no awipsid attribute, allow processing
            return True

        awipsid = getattr(event, "awipsid", "")

        # Reject test messages (case-insensitive comparison)
        return not (isinstance(awipsid, str) and awipsid.upper() == "TSTMSG")
