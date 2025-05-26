ARG PYTHON_VERSION=3.13

# Builder stage
FROM python:${PYTHON_VERSION}-slim as builder

# Install UV
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency definition files
COPY pyproject.toml uv.lock ./

# Install dependencies using UV
RUN uv pip install --system --no-cache --requirement pyproject.toml

# Copy application code
COPY nwws_oi_ingest.py output_handlers.py ./

# NWWS-OI Configuration
ENV NWWS_USERNAME=your_username_here
ENV NWWS_PASSWORD=your_password_here
ENV NWWS_SERVER=nwws-oi.weather.gov
ENV NWWS_PORT=5222

# Logging Configuration
ENV LOG_LEVEL=INFO
# ENV LOG_FILE=/path/to/log/file.log

# Output Configuration
# Comma-separated list of output handlers: console, mqtt
ENV OUTPUT_HANDLERS=console
# ENV OUTPUT_HANDLERS=mqtt

# MQTT Configuration (only needed if mqtt is in OUTPUT_HANDLERS)
# ENV MQTT_BROKER=your.mqtt.broker.com
# ENV MQTT_PORT=1883
# ENV MQTT_USERNAME=mqtt_user
# ENV MQTT_PASSWORD=mqtt_password
# ENV MQTT_TOPIC_PREFIX=nwws
# ENV MQTT_QOS=1
# ENV MQTT_RETAIN=true
# ENV MQTT_CLIENT_ID=nwws-oi-client

# Command to run the application
CMD ["python", "nwws_oi_ingest.py"]
