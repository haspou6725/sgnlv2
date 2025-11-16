#!/usr/bin/env python3
"""
Script: process_watchlist.py
Description: Processes LBank Futures data, calculates scores for symbols,
             and updates a watchlist with the top 120 symbols based on criteria.
Usage: python3 process_watchlist.py
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Any


# ============================================================================
# Configuration
# ============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
STATE_DIR = os.path.join(PROJECT_ROOT, "state")
INPUT_FILE = os.path.join(STATE_DIR, "lbank_futures_data.json")
OUTPUT_FILE = os.path.join(STATE_DIR, "watchlist.txt")  # Configurable output location

# Ranking criteria weights
WEIGHT_VOLUME = 0.3
WEIGHT_TURNOVER = 0.3
WEIGHT_PRICE_CHANGE = 0.2
WEIGHT_TRADES = 0.2

# Top symbols to highlight in console
TOP_HIGHLIGHT_COUNT = 10
WATCHLIST_SIZE = 120


# ============================================================================
# Logging Utilities
# ============================================================================
def log(message: str, level: str = "INFO") -> None:
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def log_error(message: str) -> None:
    """Log an error message."""
    log(message, level="ERROR")


def log_warning(message: str) -> None:
    """Log a warning message."""
    log(message, level="WARNING")


# ============================================================================
# Data Loading and Validation
# ============================================================================
def load_json_data(filepath: str) -> Dict[str, Any]:
    """
    Load JSON data from file with proper error handling.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        Dictionary containing the parsed JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
        Exception: For other unexpected errors
    """
    log(f"Loading data from: {filepath}")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        log(f"Successfully loaded JSON data")
        return data
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in file {filepath}: {e.msg}",
            e.doc,
            e.pos
        )
    except Exception as e:
        raise Exception(f"Unexpected error loading {filepath}: {str(e)}")


def validate_numeric_field(value: Any, field_name: str) -> float:
    """
    Validate and convert a field to float.
    
    Args:
        value: Value to validate
        field_name: Name of the field (for error messages)
        
    Returns:
        Float value, or 0.0 if invalid
    """
    if value is None:
        return 0.0
    
    try:
        # Handle string representations
        if isinstance(value, str):
            value = value.strip()
            if not value or value == 'null' or value == 'None':
                return 0.0
        
        result = float(value)
        
        # Check for NaN or infinity
        if result != result or result == float('inf') or result == float('-inf'):
            log_warning(f"Invalid numeric value for {field_name}: {value}")
            return 0.0
            
        return result
    except (ValueError, TypeError) as e:
        log_warning(f"Cannot convert {field_name}={value} to float: {e}")
        return 0.0


def extract_symbols_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract and validate symbol data from the API response.
    
    Args:
        data: Raw API response data
        
    Returns:
        List of symbol dictionaries with validated data
    """
    log("Extracting symbol data...")
    
    # Validate that 'data' field exists and is a list
    if 'data' not in data:
        raise ValueError("API response missing 'data' field")
    
    symbols_data = data['data']
    
    if not isinstance(symbols_data, list):
        raise TypeError(
            f"Expected 'data' field to be a list, got {type(symbols_data).__name__}"
        )
    
    log(f"Found {len(symbols_data)} symbols in data")
    
    # Validate and normalize each symbol's data
    validated_symbols = []
    for idx, symbol_data in enumerate(symbols_data):
        if not isinstance(symbol_data, dict):
            log_warning(f"Skipping symbol at index {idx}: not a dictionary")
            continue
        
        # Validate required fields
        symbol_name = symbol_data.get('symbol', f'UNKNOWN_{idx}')
        
        # Validate numeric fields
        validated_symbol = {
            'symbol': symbol_name,
            'volume': validate_numeric_field(symbol_data.get('volume'), 'volume'),
            'turnover': validate_numeric_field(symbol_data.get('turnover'), 'turnover'),
            'price_change_percent': validate_numeric_field(
                symbol_data.get('change', symbol_data.get('priceChangePercent')),
                'price_change_percent'
            ),
            'trades': validate_numeric_field(symbol_data.get('trades', 0), 'trades'),
            'last_price': validate_numeric_field(symbol_data.get('lastPrice'), 'last_price'),
        }
        
        validated_symbols.append(validated_symbol)
    
    log(f"Successfully validated {len(validated_symbols)} symbols")
    return validated_symbols


# ============================================================================
# Ranking Logic
# ============================================================================
def calculate_score(symbol_data: Dict[str, Any]) -> float:
    """
    Calculate a composite score for a symbol based on multiple criteria.
    
    Score is calculated as a weighted combination of:
    - Volume (30%)
    - Turnover (30%)
    - Price change percentage (20%)
    - Number of trades (20%)
    
    Args:
        symbol_data: Dictionary containing symbol metrics
        
    Returns:
        Composite score as a float
    """
    volume = symbol_data['volume']
    turnover = symbol_data['turnover']
    price_change = abs(symbol_data['price_change_percent'])  # Use absolute value
    trades = symbol_data['trades']
    
    # Calculate weighted score
    score = (
        WEIGHT_VOLUME * volume +
        WEIGHT_TURNOVER * turnover +
        WEIGHT_PRICE_CHANGE * price_change +
        WEIGHT_TRADES * trades
    )
    
    return score


def rank_symbols(symbols_data: List[Dict[str, Any]]) -> List[Tuple[str, float, Dict[str, Any]]]:
    """
    Rank symbols by their calculated scores.
    
    Args:
        symbols_data: List of symbol dictionaries
        
    Returns:
        List of tuples (symbol_name, score, symbol_data) sorted by score descending
    """
    log("Calculating scores for symbols...")
    
    ranked = []
    for symbol_data in symbols_data:
        score = calculate_score(symbol_data)
        ranked.append((symbol_data['symbol'], score, symbol_data))
    
    # Sort by score descending
    ranked.sort(key=lambda x: x[1], reverse=True)
    
    log(f"Ranked {len(ranked)} symbols")
    return ranked


# ============================================================================
# Output and Display
# ============================================================================
def save_watchlist(ranked_symbols: List[Tuple[str, float, Dict[str, Any]]], 
                   output_path: str, 
                   top_n: int = WATCHLIST_SIZE) -> None:
    """
    Save the top N symbols to the watchlist file.
    
    Args:
        ranked_symbols: List of ranked symbols
        output_path: Path to save the watchlist
        top_n: Number of top symbols to save
    """
    log(f"Saving top {top_n} symbols to watchlist: {output_path}")
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    
    # Take top N symbols
    top_symbols = ranked_symbols[:top_n]
    
    # Write to file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# LBank Futures Watchlist - Top {top_n} Symbols\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"#\n")
            
            for rank, (symbol, score, data) in enumerate(top_symbols, 1):
                f.write(f"{symbol}\n")
        
        log(f"Successfully saved {len(top_symbols)} symbols to watchlist")
    except Exception as e:
        log_error(f"Failed to save watchlist: {str(e)}")
        raise


def display_top_symbols(ranked_symbols: List[Tuple[str, float, Dict[str, Any]]], 
                        highlight_count: int = TOP_HIGHLIGHT_COUNT) -> None:
    """
    Display the top symbols in the console with highlighting.
    
    Args:
        ranked_symbols: List of ranked symbols
        highlight_count: Number of top symbols to highlight
    """
    log(f"\n{'='*80}")
    log(f"TOP {highlight_count} SYMBOLS (Highlighted)")
    log(f"{'='*80}\n")
    
    # ANSI color codes for highlighting
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    
    for rank, (symbol, score, data) in enumerate(ranked_symbols[:highlight_count], 1):
        # Highlight top 10 with colors
        if rank <= 10:
            color = GREEN if rank <= 5 else YELLOW
            prefix = f"{color}{BOLD}★ "
            suffix = RESET
        else:
            prefix = "  "
            suffix = ""
        
        print(f"{prefix}#{rank:3d} {symbol:20s} Score: {score:15.2f} | "
              f"Vol: {data['volume']:12.2f} | "
              f"Turnover: {data['turnover']:12.2f} | "
              f"Change: {data['price_change_percent']:6.2f}%{suffix}")
    
    print(f"\n{'='*80}\n")


# ============================================================================
# Main Execution
# ============================================================================
def main() -> int:
    """
    Main execution function.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        log("="*80)
        log("LBank Futures Watchlist Processor")
        log("="*80)
        
        # Load data
        raw_data = load_json_data(INPUT_FILE)
        
        # Extract and validate symbol data
        symbols_data = extract_symbols_data(raw_data)
        
        if not symbols_data:
            log_warning("No symbols found in data")
            return 1
        
        # Rank symbols
        ranked_symbols = rank_symbols(symbols_data)
        
        # Display top symbols
        display_top_symbols(ranked_symbols, highlight_count=TOP_HIGHLIGHT_COUNT)
        
        # Save watchlist
        save_watchlist(ranked_symbols, OUTPUT_FILE, top_n=WATCHLIST_SIZE)
        
        log("="*80)
        log(f"Processing complete! Watchlist saved to: {OUTPUT_FILE}")
        log("="*80)
        
        return 0
        
    except FileNotFoundError as e:
        log_error(str(e))
        log_error("Please run download_lbank_futures.sh first")
        return 1
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        log_error(f"Data validation error: {str(e)}")
        return 1
    except Exception as e:
        log_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
