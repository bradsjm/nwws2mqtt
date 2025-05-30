# NWWS2MQTT Tests

This directory contains pytest tests for the NWWS2MQTT pipeline components.

## Test Structure

```
tests/
├── transformers/           # Tests for transformer components
│   └── test_noaa_port_transformer.py
├── filters/               # Tests for filter components
│   └── test_test_msg_filter.py
├── pipeline/              # Tests for core pipeline components
├── outputs/               # Tests for output components
├── conftest.py           # Shared test fixtures
└── test_integration_transformers_filters.py  # Integration tests
```

## Running Tests

### Run All Tests
```bash
python -m pytest src/tests/ -v
```

### Run Specific Test Categories

#### Transformer Tests
```bash
python -m pytest src/tests/transformers/ -v
```

#### Filter Tests
```bash
python -m pytest src/tests/filters/ -v
```

#### Integration Tests
```bash
python -m pytest src/tests/test_integration_transformers_filters.py -v
```

### Run Single Test File
```bash
python -m pytest src/tests/transformers/test_noaa_port_transformer.py -v
```

### Run Single Test Method
```bash
python -m pytest src/tests/transformers/test_noaa_port_transformer.py::TestNoaaPortTransformer::test_init_default_id -v
```

## Test Coverage

### NoaaPortTransformer Tests
- Initialization with default and custom IDs
- Transformation of NoaaPortEventData to TextProductEventData
- Pass-through behavior for non-NoaaPortEventData events
- Error handling for parser and conversion exceptions
- Metadata preservation during transformation

### TestMessageFilter Tests
- Initialization with default and custom IDs
- Rejection of test messages (TSTMSG) - case insensitive
- Allow normal messages to pass through
- Handle events without awipsid attribute
- Handle edge cases (None, empty string, non-string awipsid)
- Exact match only (partial matches are allowed)

### Integration Tests
- Filter and transformer working together in pipeline sequence
- Mixed event processing (normal and test messages)
- Complete pipeline simulation

## Test Fixtures

Common fixtures are defined in `conftest.py`:
- `event_metadata`: Basic pipeline event metadata
- `pipeline_event`: Basic pipeline event
- Various mock components for testing

## Test Dependencies

- `pytest`: Test framework
- `pytest-mock`: Mocking utilities
- `pytest-asyncio`: Async test support
- `unittest.mock`: Python standard library mocking

## Writing New Tests

When adding new tests:

1. Follow the existing naming convention: `test_<component_name>.py`
2. Use descriptive test method names: `test_<what_it_tests>`
3. Group related tests in test classes
4. Use fixtures for common setup
5. Mock external dependencies
6. Test both success and error conditions
7. Keep tests simple and focused on single functionality

## Test Guidelines

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test components working together
- **Mock External Dependencies**: Use mocks for external libraries (pyiem, etc.)
- **Focus on Critical Paths**: Test the most important functionality first
- **Edge Cases**: Test error conditions and edge cases
- **Clear Assertions**: Use descriptive assertion messages