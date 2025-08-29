#!/usr/bin/env bash
# Fail on error
set -o errexit

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Installing Playwright browsers..."
# Install browsers without specifying a custom path initially
python -m playwright install chromium

echo "Verifying browser installation..."
python -m playwright install-deps chromium

echo "Build completed successfully"