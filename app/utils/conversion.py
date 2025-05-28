"""Conversion utilities."""

import json

from loguru import logger

from app.models.product import TextProductModel


def product_to_json(text_product: TextProductModel) -> str | None:
    """Convert a product model to JSON format for storage or transmission.

    Args:
        text_product: The product model instance to convert.

    Returns:
        str: JSON representation of the product model.

    """
    try:
        model_json = json.dumps(
            text_product.model_dump(mode="json", by_alias=True, exclude_defaults=True),
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, RecursionError) as e:
        logger.error(
            "Failed to serialize product",
            product_id=text_product.product_id,
            error=str(e),
        )
        return None
    return model_json
