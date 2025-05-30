# Pipeline Examples

This directory contains examples demonstrating how to use the pipeline package.

## Examples

### 1. Simple Pipeline Example (`simple_pipeline_example.py`)

Demonstrates basic pipeline functionality with custom components:

- Custom event types
- Custom filters, transformers, and outputs
- Basic pipeline setup and event processing
- Statistics collection

```bash
python simple_pipeline_example.py
```

### 2. Configuration-based Pipeline Example (`config_pipeline_example.py`)

Shows how to use configuration files and programmatic configuration:

- Loading pipelines from YAML configuration
- Creating pipelines from configuration dictionaries
- Using built-in components
- Error handling strategies

```bash
python config_pipeline_example.py
```

### 3. Configuration File (`pipeline_config.yaml`)

Example YAML configuration file demonstrating:

- Filter configuration (attribute and regex filters)
- Transformer configuration
- Output configuration (log and file outputs)
- Error handling settings
- Statistics enablement

## Running the Examples

From the project root directory:

```bash
cd examples/
python simple_pipeline_example.py
python config_pipeline_example.py
```

## Requirements

The examples require the pipeline package to be available. They automatically add the `src/` directory to the Python path.

Optional dependencies for full functionality:
- `aiofiles` - For file output functionality
- `aiohttp` - For HTTP output functionality
- `pyyaml` - For YAML configuration file support

Install optional dependencies:
```bash
pip install aiofiles aiohttp pyyaml
```

## Example Output

The simple pipeline example will show:
- Event processing with filtering
- Transformation of event data
- Output to console
- Pipeline statistics

The configuration example will demonstrate:
- Loading from configuration files
- Programmatic configuration creation
- Event processing with built-in components
- Error handling and statistics