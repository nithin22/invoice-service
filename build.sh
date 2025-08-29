#!/usr/bin/env bash
# Fail on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers with dependencies
python -m playwright install --with-deps chromium

# Create cache directory for Playwright
mkdir -p /opt/render/.cache/ms-playwright

# Set environment variable for Playwright
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright