#!/bin/bash
# TechDaily Digest Generator - Manual Run Script

cd "$(dirname "$0")/src"

echo "========================================"
echo "  TechDaily Digest Generator"
echo "========================================"
echo ""

# Run with default settings (24h, max 5 articles)
python3 generate_digest.py --hours 24 --max 5

echo ""
echo "Done! Open frontend/index.html to view"
