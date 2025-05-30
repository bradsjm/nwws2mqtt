# Tests for Utils Package

## Overview

This directory contains pytest tests for the `nwws.utils` package, focusing on converter functions that transform pyiem objects to Pydantic models.

## Test Files

### `test_converters.py`

Comprehensive tests for the `converters.py` module covering all critical converter functions:

#### Test Coverage

- **`convert_ugc_to_model`**: Tests UGC (Universal Geographic Code) object conversion
  - Basic attribute mapping
  - Missing attributes with defaults
  - Empty collections handling

- **`convert_vtec_to_model`**: Tests VTEC (Valid Time Event Code) object conversion
  - Complete VTEC data conversion
  - Missing attributes with proper defaults

- **`convert_hvtec_to_model`**: Tests HVTEC (Hydrologic VTEC) object conversion
  - Basic HVTEC attributes
  - NWSLI handling (both object and string formats)
  - Missing attributes and null values

- **`convert_text_product_segment_to_model`**: Tests segment conversion
  - Complex segment with multiple nested objects
  - Empty collections and missing attributes
  - All weather-related tags and metadata

- **`convert_text_product_to_model`**: Tests complete product conversion
  - Full product with all attributes
  - Missing required fields for product ID generation
  - Method exceptions and missing methods
  - Channel handling with missing AFOS

#### Test Strategy

- **Minimal Functionality**: Tests focus on critical conversion paths only
- **Mock Objects**: Uses `unittest.mock.MagicMock` and custom classes for isolation
- **Edge Cases**: Covers missing attributes, null values, and exception handling
- **Data Validation**: Ensures Pydantic models are created correctly with proper types

#### Running Tests

```bash
# Run all converter tests
python -m pytest src/tests/utils/test_converters.py -v

# Run specific test class
python -m pytest src/tests/utils/test_converters.py::TestConvertUGCToModel -v

# Run with coverage (note: coverage may be limited due to mocked dependencies)
python -m pytest src/tests/utils/test_converters.py --cov=src/nwws/utils/converters
```

## Test Design Principles

1. **Simple and Focused**: Each test validates one specific aspect of conversion
2. **Isolation**: Uses mocks to avoid external dependencies
3. **Comprehensive Edge Cases**: Tests both success and failure scenarios
4. **Type Safety**: Validates Pydantic model creation and attribute access
5. **Maintainable**: Clear test names and organized into logical test classes

## Future Enhancements

- Add integration tests with real pyiem objects
- Performance benchmarking for large data sets
- Additional edge cases for malformed input data
- Property-based testing with hypothesis for broader coverage