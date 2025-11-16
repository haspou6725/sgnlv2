#!/bin/bash

################################################################################
# Script: run_watchlist_update.sh
# Description: Convenience wrapper that downloads data and generates watchlist
# Usage: ./run_watchlist_update.sh
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== LBank Futures Watchlist Update ==="
echo "Started at: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Step 1: Download data
echo "Step 1: Downloading LBank Futures data..."
if ! "${SCRIPT_DIR}/download_lbank_futures.sh"; then
    echo "ERROR: Data download failed. Aborting."
    exit 1
fi
echo ""

# Step 2: Process and generate watchlist
echo "Step 2: Processing data and generating watchlist..."
if ! python3 "${SCRIPT_DIR}/process_watchlist.py"; then
    echo "ERROR: Watchlist generation failed. Aborting."
    exit 1
fi
echo ""

echo "=== Watchlist Update Complete ==="
echo "Completed at: $(date '+%Y-%m-%d %H:%M:%S')"
exit 0
