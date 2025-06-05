#!/usr/bin/env python3
"""Health check script for NWWS2MQTT Docker container.

This script performs comprehensive health checks on the NWWS2MQTT service
to ensure it's running properly within the Docker container.
"""

import json
import socket
import sys
import time
import urllib.error
import urllib.request
from typing import Any, cast


def check_http_endpoint(url: str, timeout: int = 10) -> tuple[bool, str]:
    """Check if HTTP endpoint is responding.

    Args:
        url: The URL to check
        timeout: Request timeout in seconds

    Returns:
        Tuple of (success, message)

    """
    try:
        req = urllib.request.Request(url)  # noqa: S310
        req.add_header("User-Agent", "NWWS2MQTT-HealthCheck/1.0")

        with urllib.request.urlopen(req, timeout=timeout) as response:  # noqa: S310
            if response.status == 200:
                return True, f"HTTP endpoint {url} is healthy"
            return False, f"HTTP endpoint {url} returned status {response.status}"

    except urllib.error.HTTPError as e:
        return False, f"HTTP error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"URL error: {e.reason}"
    except TimeoutError:
        return False, f"Timeout connecting to {url}"
    except Exception as e:  # noqa: BLE001
        return False, f"Unexpected error: {e}"


def check_health_endpoint() -> tuple[bool, str]:  # noqa: PLR0911
    """Check the dedicated health endpoint.

    Returns:
        Tuple of (success, message)

    """
    url = "http://localhost:8080/api/v1/health"

    try:
        req = urllib.request.Request(url)  # noqa: S310
        req.add_header("User-Agent", "NWWS2MQTT-HealthCheck/1.0")

        with urllib.request.urlopen(req, timeout=10) as response:  # noqa: S310
            if response.status != 200:
                return False, f"Health endpoint returned status {response.status}"

            # Try to parse JSON response
            try:
                data: Any = json.loads(response.read().decode("utf-8"))
                if isinstance(data, dict):
                    data_dict = cast("dict[str, Any]", data)
                    status = data_dict.get("status", "unknown")
                    if status in {"healthy", "ok"}:
                        return True, "Health endpoint reports service is healthy"
                    return False, f"Health endpoint reports status: {status}"
            except json.JSONDecodeError:
                # If it's not JSON, but we got a 200, consider it healthy
                return True, "Health endpoint is responding"

            return True, "Health endpoint responded with valid data"

    except urllib.error.HTTPError as e:
        return False, f"Health endpoint HTTP error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"Health endpoint URL error: {e.reason}"
    except TimeoutError:
        return False, "Timeout connecting to health endpoint"
    except Exception as e:  # noqa: BLE001
        return False, f"Health endpoint check failed: {e}"


def check_metrics_endpoint() -> tuple[bool, str]:
    """Check if metrics endpoint is responding.

    Returns:
        Tuple of (success, message)

    """
    return check_http_endpoint("http://localhost:8080/metrics")


def check_port_listening(port: int, host: str = "localhost") -> tuple[bool, str]:
    """Check if a port is listening.

    Args:
        port: Port number to check
        host: Host to check (default: localhost)

    Returns:
        Tuple of (success, message)

    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            return True, f"Port {port} is listening"

    except Exception as e:  # noqa: BLE001
        return False, f"Error checking port {port}: {e}"

    return False, f"Port {port} is not listening"


def run_health_checks() -> dict[str, Any]:
    """Run all health checks and return results.

    Returns:
        Dictionary with check results

    """
    checks = {
        "health_endpoint": check_health_endpoint(),
        "metrics_endpoint": check_metrics_endpoint(),
        "port_8080": check_port_listening(8080),
    }

    # Calculate overall health
    all_passed = all(result[0] for result in checks.values())

    return {
        "overall_health": all_passed,
        "checks": {
            name: {"passed": result[0], "message": result[1]} for name, result in checks.items()
        },
        "timestamp": time.time(),
    }


def main() -> int:
    """Run health check and return exit code.

    Returns:
        Exit code (0 for healthy, 1 for unhealthy)

    """
    try:
        results = run_health_checks()

        if results["overall_health"]:
            print("✅ NWWS2MQTT container is healthy")  # noqa: T201
            for check_name, check_result in results["checks"].items():
                print(f"  ✅ {check_name}: {check_result['message']}")  # noqa: T201
            return 0

        print("❌ NWWS2MQTT container is unhealthy")  # noqa: T201
        for check_name, check_result in results["checks"].items():
            status = "✅" if check_result["passed"] else "❌"
            print(f"  {status} {check_name}: {check_result['message']}")  # noqa: T201

    except Exception as e:  # noqa: BLE001
        print(f"❌ Health check failed with error: {e}")  # noqa: T201

    return 1


if __name__ == "__main__":
    sys.exit(main())
