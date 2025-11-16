# LBank Futures Data Processing Scripts

This directory contains scripts for downloading and processing LBank Futures market data to generate a watchlist of top-performing symbols.

## Overview

The workflow consists of two main scripts:

1. **download_lbank_futures.sh** - Downloads market data from the LBank API
2. **process_watchlist.py** - Processes the data and generates a ranked watchlist

## Scripts

### download_lbank_futures.sh

Downloads LBank Futures 24-hour ticker data and saves it to `state/lbank_futures_data.json`.

**Features:**
- Proper error handling with `curl --fail`
- JSON validation before saving
- Timestamped logging
- Graceful error messages
- Automatic cleanup of temporary files

**Usage:**
```bash
./scripts/download_lbank_futures.sh
```

**Requirements:**
- `curl` command-line tool
- `python3` for JSON validation
- Internet connectivity to LBank API

### process_watchlist.py

Processes the downloaded data, calculates scores for symbols based on multiple criteria, and generates a watchlist of the top 120 symbols.

**Features:**
- Robust error handling for file loading and JSON parsing
- Numeric field validation (handles null, empty, invalid values)
- Modularized ranking logic
- Configurable output location
- Timestamped logging
- Highlights top 10 symbols in terminal output
- Uses `os.path.join` for cross-platform path handling

**Scoring Criteria:**
Symbols are scored based on a weighted combination of:
- Volume (30%)
- Turnover (30%)
- Price Change Percentage (20%)
- Number of Trades (20%)

**Usage:**
```bash
./scripts/process_watchlist.py
```

**Configuration:**
Edit the following constants at the top of the script to customize:
- `OUTPUT_FILE` - Output file location (default: `state/watchlist.txt`)
- `WEIGHT_VOLUME`, `WEIGHT_TURNOVER`, `WEIGHT_PRICE_CHANGE`, `WEIGHT_TRADES` - Scoring weights
- `TOP_HIGHLIGHT_COUNT` - Number of top symbols to highlight (default: 10)
- `WATCHLIST_SIZE` - Number of symbols in watchlist (default: 120)

**Output:**
- Console: Displays top 10 symbols with color highlighting
- File: `state/watchlist.txt` containing top 120 symbols

## Complete Workflow

Run the complete workflow:

```bash
# Download data
./scripts/download_lbank_futures.sh

# Process and generate watchlist
./scripts/process_watchlist.py
```

## Testing

### Unit Tests

Run unit tests with:
```bash
python3 -m unittest tests.test_watchlist -v
```

### Integration Tests

Run integration tests with:
```bash
./scripts/test_integration.sh
```

The integration test suite validates:
- Script file existence and permissions
- Processing with edge cases (null values, empty strings, mixed types)
- Output file generation
- Error handling (missing files, invalid JSON)

## Error Handling

Both scripts implement comprehensive error handling:

### Bash Script Errors:
- Missing dependencies (`curl`, `python3`)
- Network/API connection failures
- Invalid JSON responses
- File system errors

### Python Script Errors:
- Missing input files
- Invalid JSON format
- Type validation errors
- Missing or invalid data fields

All errors are logged with timestamps and descriptive messages.

## File Structure

```
scripts/
├── download_lbank_futures.sh   # Data download script
├── process_watchlist.py        # Data processing script
├── test_integration.sh         # Integration tests
└── README_SCRIPTS.md          # This file

state/
├── lbank_futures_data.json    # Downloaded market data (generated)
└── watchlist.txt              # Top 120 symbols (generated)

tests/
└── test_watchlist.py          # Unit tests
```

## Best Practices Implemented

### Bash Script:
✅ Proper shebang and script header
✅ `set -euo pipefail` for strict error handling
✅ Readonly configuration variables
✅ Timestamped logging function
✅ `curl --fail` for HTTP error handling
✅ Trap for cleanup on exit
✅ Comprehensive comments

### Python Script:
✅ Type hints for function parameters
✅ Docstrings for all functions
✅ `os.path.join` for path construction
✅ Validation of data types and numeric fields
✅ Modularized logic (separate functions for each task)
✅ Configurable parameters at top of file
✅ Timestamped logging
✅ Graceful error handling with descriptive messages
✅ ANSI color codes for terminal highlighting

## Troubleshooting

### "Failed to download data from LBank API"
- Check internet connection
- Verify LBank API is accessible
- Check firewall/proxy settings

### "Data file not found"
- Run `download_lbank_futures.sh` first
- Check that `state/` directory exists

### "Invalid JSON in file"
- Re-run download script
- Check API response format hasn't changed

### "Expected 'data' field to be a list"
- API response format may have changed
- Check the raw JSON file manually

## License

Part of the SGNLV2 project.
