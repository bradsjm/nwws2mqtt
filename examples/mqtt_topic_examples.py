#!/usr/bin/env python3
# pyright: basic
# ruff: noqa: T201 SLF001 EXE001
"""Example script demonstrating MQTT topic structure patterns.

This script shows how different NWS products would be mapped to MQTT topics
using the new topic structure, and demonstrates various subscription patterns.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import UTC, datetime

from nwws.models.events import TextProductEventData
from nwws.models.weather import (
    TextProductModel,
    TextProductSegmentModel,
    VTECModel,
)
from nwws.outputs.mqtt import MQTTOutput, MQTTOutputConfig
from nwws.pipeline import PipelineEventMetadata


def create_sample_product(  # noqa: PLR0913
    cccc: str,
    awipsid: str,
    product_id: str,
    vtec_records: list[VTECModel] | None = None,
    subject: str = "Test Product",
    ttaaii: str = "WFUS51",
) -> TextProductEventData:
    """Create a sample TextProductEventData for demonstration."""
    # Create segments with VTEC if provided
    segments = []
    if vtec_records:
        segment = TextProductSegmentModel(
            segmentText="Sample segment text",
            vtecRecords=vtec_records,
        )
        segments.append(segment)

    # Use timezone-aware datetime
    dt = datetime(2023, 7, 13, 19, 15, 0, tzinfo=UTC)

    # Create product model
    product = TextProductModel(
        text="Sample product text",
        processedUtcTimestamp=dt,
        productSegments=segments,
    )

    # Create event metadata
    metadata = PipelineEventMetadata(
        event_id=f"event-{product_id}",
        timestamp=dt.timestamp(),
        source="example",
    )

    # Create event
    return TextProductEventData(
        metadata=metadata,
        product=product,
        cccc=cccc,
        awipsid=awipsid,
        id=product_id,
        issue=dt,
        subject=subject,
        ttaaii=ttaaii,
        delay_stamp=None,
    )


def create_vtec(phenomena: str, significance: str) -> VTECModel:
    """Create a sample VTEC model."""
    return VTECModel(
        line=f"/O.NEW.KALY.{phenomena}.{significance}.0001.230713T1915Z-230713T2000Z/",
        status="O",
        action="NEW",
        officeId="ALY",
        officeId4="KALY",
        phenomena=phenomena,
        significance=significance,
        eventTrackingNumber=1,
        beginTimestamp=datetime(2023, 7, 13, 19, 15, 0, tzinfo=UTC),
        endTimestamp=datetime(2023, 7, 13, 20, 0, 0, tzinfo=UTC),
        year=2023,
    )


def demonstrate_topic_structure():
    """Demonstrate the MQTT topic structure with various product examples."""
    print("🌪️  NWWS MQTT Topic Structure Examples")
    print("=" * 50)

    # Create MQTT output for topic generation
    config = MQTTOutputConfig(
        broker="localhost",
        topic_prefix="nwws",
        topic_pattern="{prefix}/{cccc}/{product_type}/{awipsid}/{product_id}",
    )
    mqtt_output = MQTTOutput("example", config=config)

    # Sample products with different characteristics
    examples = [
        {
            "name": "Tornado Warning (VTEC)",
            "product": create_sample_product(
                cccc="KTBW",
                awipsid="TORALY",
                product_id="202307131915-KTBW-WFUS51-TORALY",
                vtec_records=[create_vtec("TO", "W")],
                subject="URGENT - TORNADO WARNING",
            ),
            "description": "Tornado warning with VTEC TO.W",
        },
        {
            "name": "Severe Thunderstorm Watch (VTEC)",
            "product": create_sample_product(
                cccc="KBOX",
                awipsid="SVSBOX",
                product_id="202307132000-KBOX-WWUS41-SVSBOX",
                vtec_records=[create_vtec("SV", "A")],
                subject="SEVERE THUNDERSTORM WATCH",
            ),
            "description": "Severe thunderstorm watch with VTEC SV.A",
        },
        {
            "name": "Flash Flood Warning (VTEC)",
            "product": create_sample_product(
                cccc="KPHI",
                awipsid="FFWPHI",
                product_id="202307131800-KPHI-WFUS51-FFWPHI",
                vtec_records=[create_vtec("FF", "W")],
                subject="FLASH FLOOD WARNING",
            ),
            "description": "Flash flood warning with VTEC FF.W",
        },
        {
            "name": "Area Forecast Discussion (No VTEC)",
            "product": create_sample_product(
                cccc="KDMX",
                awipsid="AFDDMX",
                product_id="202307131830-KDMX-FXUS63-AFDDMX",
                subject="AREA FORECAST DISCUSSION",
            ),
            "description": "Area forecast discussion, no VTEC (uses AWIPS prefix 'AFD')",
        },
        {
            "name": "Zone Forecast Product (No VTEC)",
            "product": create_sample_product(
                cccc="KALY",
                awipsid="ZFPALY",
                product_id="202307131700-KALY-FXUS61-ZFPALY",
                subject="ZONE FORECAST PRODUCT",
            ),
            "description": "Zone forecast product, no VTEC (uses AWIPS prefix 'ZFP')",
        },
        {
            "name": "Short Term Forecast (No VTEC)",
            "product": create_sample_product(
                cccc="KPHI",
                awipsid="NOWPHI",
                product_id="202307132200-KPHI-FXUS61-NOWPHI",
                subject="SHORT TERM FORECAST",
            ),
            "description": "Short term forecast, no VTEC (uses AWIPS prefix 'NOW')",
        },
    ]

    print("\n📊 Product Topic Examples:")
    print("-" * 30)

    for example in examples:
        topic = mqtt_output._build_topic(example["product"])
        product_type = mqtt_output._get_product_type_indicator(example["product"])

        print(f"\n{example['name']}:")
        print(f"  Description: {example['description']}")
        print(f"  Product Type: {product_type}")
        print(f"  Topic: {topic}")

    print("\n\n🎯 Subscription Pattern Examples:")
    print("-" * 35)

    subscription_examples = [
        ("All products from Tampa Bay (KTBW)", "nwws/KTBW/#"),
        ("All tornado warnings from any station", "nwws/+/TO.W/#"),
        ("All warnings from Tampa Bay", "nwws/KTBW/+.W/#"),
        ("All watches from any station", "nwws/+/+.A/#"),
        ("All forecast discussions from any station", "nwws/+/AFD/#"),
        ("All severe thunderstorm products from Boston", "nwws/KBOX/SV.+/#"),
        ("Specific product type from Albany", "nwws/KALY/TO.W/TORALY/#"),
        ("All flood-related products from any station", "nwws/+/FL.+/# nwws/+/FF.+/#"),
    ]

    for description, pattern in subscription_examples:
        print(f"  {description}:")
        print(f"    {pattern}")
        print()


def demonstrate_custom_patterns():
    """Demonstrate custom topic patterns."""
    print("\n🔧 Custom Topic Pattern Examples:")
    print("-" * 35)

    custom_patterns = [
        {
            "name": "Product-First Pattern",
            "pattern": "{prefix}/{product_type}/{cccc}/{awipsid}/{product_id}",
            "description": "Groups by product type first for type-based filtering",
        },
        {
            "name": "Simplified Pattern",
            "pattern": "{prefix}/{cccc}/{product_type}/{product_id}",
            "description": "Omits AWIPS ID for cleaner structure",
        },
        {
            "name": "Regional Pattern",
            "pattern": "weather/{cccc}/{product_type}/{awipsid}",
            "description": "Custom prefix with regional organization",
        },
    ]

    for pattern_info in custom_patterns:
        print(f"\n{pattern_info['name']}:")
        print(f"  Pattern: {pattern_info['pattern']}")
        print(f"  Description: {pattern_info['description']}")

        # Create MQTT output with custom pattern
        config = MQTTOutputConfig(
            broker="localhost",
            topic_prefix="nwws",
            topic_pattern=pattern_info["pattern"],
        )
        mqtt_output = MQTTOutput("example", config=config)

        # Show example with tornado warning
        sample_product = create_sample_product(
            cccc="KTBW",
            awipsid="TORALY",
            product_id="202307131915-KTBW-WFUS51-TORALY",
            vtec_records=[create_vtec("TO", "W")],
        )

        topic = mqtt_output._build_topic(sample_product)
        print(f"  Example: {topic}")


def demonstrate_filtering_scenarios():
    """Demonstrate real-world filtering scenarios."""
    print("\n🌦️  Real-World Filtering Scenarios:")
    print("-" * 40)

    scenarios = [
        {
            "name": "Emergency Manager",
            "description": "Wants all warnings for their county (covered by KTBW)",
            "subscriptions": ["nwws/KTBW/+.W/#"],
            "rationale": "Subscribes to all warnings (.W) from Tampa Bay office",
        },
        {
            "name": "Storm Chaser",
            "description": "Wants tornado and severe thunderstorm warnings nationwide",
            "subscriptions": ["nwws/+/TO.W/#", "nwws/+/SV.W/#"],
            "rationale": "Subscribes to specific phenomena types across all offices",
        },
        {
            "name": "Weather Enthusiast",
            "description": "Wants all products from their local office (KALY)",
            "subscriptions": ["nwws/KALY/#"],
            "rationale": "Single subscription gets all product types from Albany",
        },
        {
            "name": "Flood Monitoring System",
            "description": "Wants all flood-related warnings and advisories",
            "subscriptions": ["nwws/+/FL.W/#", "nwws/+/FL.Y/#", "nwws/+/FF.W/#"],
            "rationale": "Subscribes to flood warnings, advisories, and flash flood warnings",
        },
        {
            "name": "Aviation Weather Service",
            "description": "Wants forecasts and discussions from multiple offices",
            "subscriptions": ["nwws/+/AFD/#", "nwws/+/ZFP/#", "nwws/+/NOW/#"],
            "rationale": "Gets forecast products needed for flight planning",
        },
        {
            "name": "Regional Coordinator",
            "description": "Monitors watches across multiple offices in their region",
            "subscriptions": ["nwws/KALY/+.A/#", "nwws/KBOX/+.A/#", "nwws/KBGM/+.A/#"],
            "rationale": "Gets all watch types from offices in their coordination area",
        },
    ]

    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        print(f"  Use Case: {scenario['description']}")
        print("  Subscriptions:")
        for sub in scenario["subscriptions"]:
            print(f"    - {sub}")
        print(f"  Rationale: {scenario['rationale']}")


def main():
    """Run the demonstration."""
    demonstrate_topic_structure()
    demonstrate_custom_patterns()
    demonstrate_filtering_scenarios()

    print("\n\n✅ Summary:")
    print("-" * 10)
    print("The MQTT topic structure enables:")
    print("  • Station-based filtering (by CCCC)")
    print("  • Product type filtering (by VTEC codes or AWIPS prefixes)")
    print("  • Flexible subscription patterns with wildcards")
    print("  • No hardcoded lookups - uses pyIEM fields directly")
    print("  • Configurable patterns for different use cases")
    print("\nFor more details, see docs/mqtt_topic_structure.md")


if __name__ == "__main__":
    main()
