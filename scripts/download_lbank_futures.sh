#!/bin/bash

################################################################################
# Script: download_lbank_futures.sh
# Description: Downloads LBank Futures market data and saves it to a JSON file
# Usage: ./download_lbank_futures.sh
################################################################################

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly OUTPUT_DIR="${PROJECT_ROOT}/state"
readonly OUTPUT_FILE="${OUTPUT_DIR}/lbank_futures_data.json"
readonly LBANK_API_URL="https://www.lbkex.net/v2/supplement/ticker/24hr.do"
readonly TEMP_FILE="${OUTPUT_DIR}/lbank_futures_data.tmp"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Logging function with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Error handling function
error_exit() {
    log "ERROR: $1" >&2
    exit 1
}

# Main download function
download_lbank_data() {
    log "Starting LBank Futures data download..."
    log "API URL: $LBANK_API_URL"
    
    # Download data with curl using --fail to handle HTTP errors
    # --silent: Suppress progress meter
    # --show-error: Show errors even in silent mode
    # --fail: Fail silently on HTTP errors (4xx, 5xx)
    # --location: Follow redirects
    # --max-time: Maximum time allowed for the operation
    if ! curl --silent --show-error --fail --location --max-time 30 \
         --output "$TEMP_FILE" "$LBANK_API_URL"; then
        error_exit "Failed to download data from LBank API. Check your connection and try again."
    fi
    
    log "Download successful"
    
    # Verify the downloaded file is valid JSON
    if ! python3 -m json.tool "$TEMP_FILE" > /dev/null 2>&1; then
        rm -f "$TEMP_FILE"
        error_exit "Downloaded data is not valid JSON"
    fi
    
    log "JSON validation successful"
    
    # Move temp file to final location
    mv "$TEMP_FILE" "$OUTPUT_FILE"
    
    log "Data saved to: $OUTPUT_FILE"
    log "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
    
    return 0
}

# Cleanup function for temp files
cleanup() {
    if [ -f "$TEMP_FILE" ]; then
        log "Cleaning up temporary file..."
        rm -f "$TEMP_FILE"
    fi
}

# Set up trap to cleanup on exit
trap cleanup EXIT

# Main execution
main() {
    log "=== LBank Futures Data Download Script ==="
    
    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        error_exit "curl is not installed. Please install curl and try again."
    fi
    
    # Check if python3 is available for JSON validation
    if ! command -v python3 &> /dev/null; then
        error_exit "python3 is not installed. Please install python3 and try again."
    fi
    
    # Download the data
    download_lbank_data
    
    log "=== Download complete ==="
    exit 0
}

# Run main function
main "$@"
