#!/usr/bin/env bash
# Fail on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install --with-deps chromium
