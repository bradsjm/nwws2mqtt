# pyright: strict
"""Test message filter for rejecting test messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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

    def get_filter_decision_metadata(
        self, event: PipelineEvent, *, result: bool
    ) -> dict[str, Any]:
        """Get metadata about the test message filter decision."""
        metadata = super().get_filter_decision_metadata(event, result=result)

        # Add test message specific metadata
        if hasattr(event, "awipsid"):
            awipsid = getattr(event, "awipsid", "")
            metadata[f"{self.filter_id}_awipsid"] = awipsid

            if not result and isinstance(awipsid, str) and awipsid.upper() == "TSTMSG":
                metadata[f"{self.filter_id}_reason"] = "test_message_filtered"
            elif result:
                metadata[f"{self.filter_id}_reason"] = "not_test_message"
            else:
                metadata[f"{self.filter_id}_reason"] = "invalid_awipsid"
        else:
            metadata[f"{self.filter_id}_reason"] = "missing_awipsid"

        return metadata
