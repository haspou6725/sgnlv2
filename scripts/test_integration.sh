#!/bin/bash

################################################################################
# Integration Test Script for LBank Futures Data Processing
# Tests the full workflow: download → process → verify
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STATE_DIR="${PROJECT_ROOT}/state"

echo "=== LBank Futures Integration Test ==="
echo "Test started at: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Test 1: Verify scripts exist
echo "Test 1: Checking script files..."
if [[ ! -f "${SCRIPT_DIR}/download_lbank_futures.sh" ]]; then
    echo "FAIL: download_lbank_futures.sh not found"
    exit 1
fi
if [[ ! -f "${SCRIPT_DIR}/process_watchlist.py" ]]; then
    echo "FAIL: process_watchlist.py not found"
    exit 1
fi
echo "PASS: Script files exist"
echo ""

# Test 2: Verify scripts are executable
echo "Test 2: Checking script permissions..."
if [[ ! -x "${SCRIPT_DIR}/download_lbank_futures.sh" ]]; then
    echo "FAIL: download_lbank_futures.sh is not executable"
    exit 1
fi
if [[ ! -x "${SCRIPT_DIR}/process_watchlist.py" ]]; then
    echo "FAIL: process_watchlist.py is not executable"
    exit 1
fi
echo "PASS: Scripts are executable"
echo ""

# Test 3: Create test data with edge cases
echo "Test 3: Creating test data with edge cases..."
cat > "${STATE_DIR}/lbank_futures_data.json" << 'EOF'
{
  "result": true,
  "data": [
    {
      "symbol": "btc_usdt",
      "volume": 1500000.50,
      "turnover": 45000000.75,
      "change": 2.5,
      "trades": 15000,
      "lastPrice": 30000.00
    },
    {
      "symbol": "eth_usdt",
      "volume": "850000.25",
      "turnover": "25000000.50",
      "change": "1.8",
      "trades": "12000",
      "lastPrice": "2000.00"
    },
    {
      "symbol": "invalid_symbol",
      "volume": null,
      "turnover": null,
      "change": null,
      "trades": null,
      "lastPrice": null
    },
    {
      "symbol": "empty_strings",
      "volume": "",
      "turnover": "",
      "change": "",
      "trades": "",
      "lastPrice": ""
    },
    {
      "symbol": "negative_change",
      "volume": 100000,
      "turnover": 5000000,
      "change": -5.2,
      "trades": 3000,
      "lastPrice": 50.0
    }
  ]
}
EOF
echo "PASS: Test data created"
echo ""

# Test 4: Run Python processor
echo "Test 4: Running Python watchlist processor..."
if ! python3 "${SCRIPT_DIR}/process_watchlist.py"; then
    echo "FAIL: Python processor failed"
    exit 1
fi
echo "PASS: Python processor completed"
echo ""

# Test 5: Verify output file
echo "Test 5: Verifying output file..."
WATCHLIST_FILE="${STATE_DIR}/watchlist.txt"
if [[ ! -f "$WATCHLIST_FILE" ]]; then
    echo "FAIL: Watchlist file not created"
    exit 1
fi

# Check that file has content
if [[ ! -s "$WATCHLIST_FILE" ]]; then
    echo "FAIL: Watchlist file is empty"
    exit 1
fi

# Verify symbols are in the file
if ! grep -q "btc_usdt" "$WATCHLIST_FILE"; then
    echo "FAIL: btc_usdt not found in watchlist"
    exit 1
fi

echo "PASS: Watchlist file created with expected content"
echo ""

# Test 6: Verify Python script handles missing file gracefully
echo "Test 6: Testing error handling (missing file)..."
mv "${STATE_DIR}/lbank_futures_data.json" "${STATE_DIR}/lbank_futures_data.json.backup"
if python3 "${SCRIPT_DIR}/process_watchlist.py" 2>/dev/null; then
    echo "FAIL: Script should fail with missing input file"
    mv "${STATE_DIR}/lbank_futures_data.json.backup" "${STATE_DIR}/lbank_futures_data.json"
    exit 1
fi
mv "${STATE_DIR}/lbank_futures_data.json.backup" "${STATE_DIR}/lbank_futures_data.json"
echo "PASS: Script handles missing file correctly"
echo ""

# Test 7: Verify Python script handles invalid JSON gracefully
echo "Test 7: Testing error handling (invalid JSON)..."
echo "{ invalid json" > "${STATE_DIR}/lbank_futures_data.json.backup"
mv "${STATE_DIR}/lbank_futures_data.json" "${STATE_DIR}/lbank_futures_data.json.bak"
mv "${STATE_DIR}/lbank_futures_data.json.backup" "${STATE_DIR}/lbank_futures_data.json"
if python3 "${SCRIPT_DIR}/process_watchlist.py" 2>/dev/null; then
    echo "FAIL: Script should fail with invalid JSON"
    mv "${STATE_DIR}/lbank_futures_data.json.bak" "${STATE_DIR}/lbank_futures_data.json"
    exit 1
fi
mv "${STATE_DIR}/lbank_futures_data.json.bak" "${STATE_DIR}/lbank_futures_data.json"
echo "PASS: Script handles invalid JSON correctly"
echo ""

echo "=== All Integration Tests Passed ==="
echo "Test completed at: $(date '+%Y-%m-%d %H:%M:%S')"
exit 0
