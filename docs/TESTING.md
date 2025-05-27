# Testing Framework Documentation

This document describes the testing framework and test suite for the nwws2mqtt project.

## Framework Overview

The project uses **pytest** as the primary testing framework with the following additional tools:

- **pytest-cov**: Code coverage reporting
- **pytest-mock**: Enhanced mocking capabilities  
- **pytest-asyncio**: Async test support
- **pytest-xdist**: Parallel test execution

## Test Organization

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py             # Global test configuration and fixtures
└── messaging/              # Message bus and messaging tests
    ├── __init__.py
    ├── test_message_bus.py  # Message bus functionality tests
    └── test_topics.py       # Topic definitions tests
```

## Test Categories

### Unit Tests
- Test individual components in isolation
- Use mocking for external dependencies
- Fast execution
- Run with: `pytest tests/ -m "not integration"`

### Integration Tests
- Test component interactions
- Use real pubsub functionality
- More comprehensive but slower
- Run with: `pytest tests/ -m integration`

## Message Bus Test Coverage

The message bus tests cover:

### 1. Message Dataclasses
- **ProductMessage**: Weather product data containers
- **StatsConnectionMessage**: Connection statistics events
- **StatsMessageProcessingMessage**: Message processing statistics
- **StatsHandlerMessage**: Handler statistics events

### 2. MessageBus Functionality
- **Publishing**: Message publication with error handling
- **Subscribing**: Topic subscription with error handling
- **Unsubscribing**: Topic unsubscription
- **Subscriber Management**: Getting topic subscribers

### 3. Integration Testing
- **End-to-End Messaging**: Real publish/subscribe workflows
- **Multiple Subscribers**: Multiple listeners per topic
- **Topic Isolation**: Different message signatures per topic
- **Dataclass Integration**: Publishing structured message objects

## Test Configuration

### pytest.ini Configuration
```toml
[tool.pytest.ini_options]
minversion = "8.0"
addopts = [
    "--strict-markers",
    "--strict-config", 
    "--cov=app",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-report=xml",
    "--cov-fail-under=80",
]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests", 
    "unit: marks tests as unit tests",
]
```

### Coverage Configuration
- **Target Coverage**: 80% minimum
- **Source**: `app` package
- **Reports**: Terminal, HTML, and XML formats
- **Exclusions**: Test files, cache directories, magic methods

## Running Tests

### Basic Commands

```bash
# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=app

# Run specific test file
uv run pytest tests/messaging/test_message_bus.py

# Run with verbose output
uv run pytest tests/ -v

# Run only unit tests
uv run pytest tests/ -m "not integration"

# Run only integration tests  
uv run pytest tests/ -m integration

# Run with coverage threshold enforcement
uv run pytest tests/ --cov=app --cov-fail-under=80
```

### Test Runner Script

Use the provided `run_tests.sh` script for common testing scenarios:

```bash
# Make executable (first time only)
chmod +x run_tests.sh

# Run the test suite
./run_tests.sh
```

## Test Fixtures

### Global Fixtures (conftest.py)

- **`reset_pubsub`**: Automatically cleans up pubsub state between tests
- **`mock_logger`**: Mocked logger for testing log outputs
- **`sample_product_message`**: Sample ProductMessage for testing
- **`sample_stats_message`**: Sample statistics message for testing
- **`sample_handler_message`**: Sample handler message for testing
- **`mock_listener`**: Mock listener function with proper `__name__` attribute

## Pubsub Testing Considerations

The pypubsub library has specific requirements for testing:

1. **Message Signatures**: Listener functions must have argument signatures that match the published message parameters
2. **Topic Isolation**: Each topic can only have one message signature across all tests
3. **Type Annotations**: Avoid type annotations in listener functions as pypubsub doesn't support them
4. **State Cleanup**: Use the `reset_pubsub` fixture to clean up listeners between tests

## Best Practices

### Test Naming
- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

### Test Organization
- Group related tests in classes
- Use descriptive test names
- One assertion per logical concept
- Arrange-Act-Assert pattern

### Mocking
- Mock external dependencies
- Use `pytest-mock` for enhanced mocking
- Mock at the interface boundary
- Verify mock interactions

### Error Testing
- Test both success and failure paths
- Test exception handling
- Verify error messages and logging

## Coverage Reports

### HTML Report
Generated in `htmlcov/` directory:
```bash
uv run pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

### Terminal Report  
```bash
uv run pytest tests/ --cov=app --cov-report=term-missing
```

### XML Report (for CI/CD)
```bash
uv run pytest tests/ --cov=app --cov-report=xml
```

## Continuous Integration

The test configuration is designed to work with CI/CD pipelines:

- **Coverage Enforcement**: Fails if coverage drops below 80%
- **Multiple Report Formats**: XML for CI tools, HTML for developers
- **Parallel Execution**: Use `pytest-xdist` for faster CI runs
- **Strict Configuration**: Fails on unknown markers or configuration errors

## Adding New Tests

### For New Message Types
1. Add test class in `tests/messaging/test_message_bus.py`
2. Test dataclass creation and validation
3. Test integration with MessageBus
4. Use unique topic names to avoid conflicts

### For New Components
1. Create new test file in appropriate subdirectory
2. Add component-specific fixtures in local `conftest.py`
3. Follow existing patterns for unit and integration tests
4. Update this documentation

## Troubleshooting

### Common Issues

1. **pubsub Topic Conflicts**: Use different topics for different message signatures
2. **Mock Attribute Errors**: Ensure mock objects have required attributes (e.g., `__name__`)
3. **Coverage Issues**: Check exclusion patterns and source paths
4. **Async Test Issues**: Use `pytest-asyncio` markers and fixtures

### Debug Mode
```bash
# Run with extra debug information
uv run pytest tests/ -v -s --tb=long

# Run single test with debugging
uv run pytest tests/messaging/test_message_bus.py::TestMessageBus::test_publish_success -v -s
```
