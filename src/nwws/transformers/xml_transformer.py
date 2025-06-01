# pyright: strict
"""Transformer for parsing CAP (Common Alerting Protocol) XML messages."""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

from nwws.models.events import TextProductEventData
from nwws.models.events.xml_event_data import XmlEventData
from nwws.pipeline import (
    PipelineEvent,
    Transformer,
)


class XmlTransformer(Transformer):
    """Transforms TextProductEventData containing XML into XmlEventData."""

    def __init__(self, transformer_id: str = "xml_transformer") -> None:
        """Initialize the CAP transformer.

        Args:
            transformer_id: Unique identifier for this transformer.

        """
        super().__init__(transformer_id)

    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Transform TextProductEventData with CAP content into CapEventData.

        Args:
            event: Pipeline event to process.

        Returns:
            CapEventData if CAP XML detected and parsed, otherwise original event.

        """
        if not isinstance(event, TextProductEventData):
            logger.debug(
                "Event is not TextProductEventData, passing through",
                event_type=type(event).__name__,
            )
            return event

        # Extract XML from the text product
        xml = self._extract_xml(event)

        if not xml:
            logger.debug(
                "No XML detected in message, passing through",
                awipsid=event.awipsid,
            )
            return event

        logger.info(
            "XML message identified",
            awipsid=event.awipsid,
            event_id=event.id,
        )

        # Create new XmlEventData using simplified helper method
        return self.create_transformed_event(
            source_event=event,
            target_event_class=XmlEventData,
            awipsid=event.awipsid,
            cccc=event.cccc,
            id=event.id,
            issue=event.issue,
            subject=event.subject,
            ttaaii=event.ttaaii,
            delay_stamp=event.delay_stamp,
            xml=xml,
            noaaport=event.noaaport,
            content_type="text/xml",
        )

    def _extract_xml(self, event: TextProductEventData) -> str | None:
        """Extract XML from the TextProductEventData if located.

        Args:
            event: TextProductEventData containing potential CAP XML.

        Returns:
            Extracted XML string or None if not found.

        """
        text = event.product.text.strip()

        # Look for XML declaration or CAP alert tag
        xml_match = re.search(
            r"(<\?xml.*?\?>\s*<([a-zA-Z0-9:_-]+)[^>]*>.*?</\2>)",
            text,
            re.DOTALL,
        )
        if xml_match:
            return self._clean_xml_content(xml_match.group(1))

        return None

    def _clean_xml_content(self, xml_content: str) -> str:
        """Clean XML content for parsing.

        Args:
            xml_content: Raw XML content.

        Returns:
            Cleaned XML content.

        """
        # Remove control characters except for \r, \n, and \t
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", xml_content)
        cleaned = (
            cleaned.replace("\r\n", "\n").replace("\r", "\n").replace("\n\n", "\n")
        )

        # Ensure XML declaration is present
        if not cleaned.lstrip().startswith("<?xml"):
            cleaned = '<?xml version="1.0" encoding="UTF-8"?>\n' + cleaned

        return cleaned.strip()

    def get_transformation_metadata(
        self, input_event: PipelineEvent, output_event: PipelineEvent
    ) -> dict[str, Any]:
        """Get metadata about the XML transformation."""
        metadata = super().get_transformation_metadata(input_event, output_event)

        # Add XML specific transformation metadata
        if isinstance(input_event, TextProductEventData):
            metadata[f"{self.transformer_id}_text_length"] = len(
                input_event.product.text
            )

        if isinstance(output_event, XmlEventData):
            metadata[f"{self.transformer_id}_xml_detected"] = True
            metadata[f"{self.transformer_id}_xml_length"] = len(output_event.xml)
            metadata[f"{self.transformer_id}_content_type"] = "text/xml"
            metadata[f"{self.transformer_id}_xml_cleaned"] = True

        return metadata
