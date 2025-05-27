#!/usr/bin/env bash

# Test runner script for nwws2mqtt project

echo "Running messaging tests..."
uv run pytest ../tests/messaging/ -v --cov=app.messaging --cov-report=term-missing --cov-report=html

echo ""
echo "Running all tests..."
uv run pytest ../tests/ -v --cov=app --cov-report=term-missing --cov-report=html

echo ""
echo "Running tests with coverage check..."
uv run pytest ../tests/ --cov=app --cov-fail-under=80 --cov-report=term-missing

echo ""
echo "Running only unit tests..."
uv run pytest ../tests/ -m "not integration" -v

echo ""
echo "Running only integration tests..."
uv run pytest ../tests/ -m integration -v

echo ""
echo "Test run completed!"
