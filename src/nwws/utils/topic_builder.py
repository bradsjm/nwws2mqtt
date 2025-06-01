"""Builds MQTT topics for NOAA port events based on configuration."""

from nwws.models.events import TextProductEventData, XmlEventData

DEFAULT_TOPIC_PATTERN = "{prefix}/{cccc}/{product_type}/{awipsid}/{product_id}"


def get_product_type_indicator(event: TextProductEventData) -> str:
    """Determine the product type indicator for topic structure.

    Uses VTEC phenomena.significance if available, otherwise first 3 letters of AWIPS ID.

    Args:
        event: The text product event data.

    Returns:
        Product type indicator string for topic construction.

    """
    # Check for VTEC codes in product segments
    if event.product.segments:
        for segment in event.product.segments:
            if segment.vtec:
                # Use the first VTEC record's phenomena and significance
                first_vtec = segment.vtec[0]
                return f"{first_vtec.phenomena}.{first_vtec.significance}"

    # Fallback to first 3 letters of AWIPS ID for non-VTEC products
    if event.awipsid and len(event.awipsid) >= 3:
        return event.awipsid[:3].upper()

    # Final fallback for products without VTEC or sufficient AWIPS ID
    return "GENERAL"


def build_topic(
    event: TextProductEventData | XmlEventData,
    prefix: str = "nwws",
    pattern: str | None = None,
) -> str:
    """Build MQTT topic using configured pattern and event data.

    Args:
        event: The text product event data.
        prefix: Topic prefix, defaults to "nwws".
        pattern: Topic pattern for formatting, defaults to a standard structure.

    Returns:
        Formatted MQTT topic string.

    """
    # Get Product Type Indicator
    if isinstance(event, TextProductEventData):
        product_type = get_product_type_indicator(event)
    else:
        product_type = "XML"
        if event.awipsid and len(event.awipsid) >= 3:
            product_type = event.awipsid[:3].upper()

    # Use AWIPS ID or default if not available
    awipsid = event.awipsid if event.awipsid else "GENERAL"

    # Build topic components dictionary for pattern substitution
    topic_components = {
        "prefix": prefix,
        "cccc": event.cccc.strip(),
        "product_type": product_type,
        "awipsid": awipsid.strip(),
        "product_id": event.id.strip(),
        "content_type": event.content_type,
    }

    # Format topic using configured pattern
    return (pattern or DEFAULT_TOPIC_PATTERN).format(**topic_components)
