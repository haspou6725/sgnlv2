"""
Tests for the LBank watchlist processing scripts.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, mock_open
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import process_watchlist


class TestProcessWatchlist(unittest.TestCase):
    """Test cases for the process_watchlist.py script."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_data = {
            "result": True,
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
                    "volume": 850000.25,
                    "turnover": 25000000.50,
                    "change": 1.8,
                    "trades": 12000,
                    "lastPrice": 2000.00
                }
            ]
        }
        
    def test_validate_numeric_field_valid_number(self):
        """Test numeric field validation with valid numbers."""
        self.assertEqual(process_watchlist.validate_numeric_field(100.5, "test"), 100.5)
        self.assertEqual(process_watchlist.validate_numeric_field("100.5", "test"), 100.5)
        self.assertEqual(process_watchlist.validate_numeric_field(0, "test"), 0.0)
        
    def test_validate_numeric_field_invalid_input(self):
        """Test numeric field validation with invalid input."""
        self.assertEqual(process_watchlist.validate_numeric_field(None, "test"), 0.0)
        self.assertEqual(process_watchlist.validate_numeric_field("", "test"), 0.0)
        self.assertEqual(process_watchlist.validate_numeric_field("null", "test"), 0.0)
        self.assertEqual(process_watchlist.validate_numeric_field("invalid", "test"), 0.0)
        
    def test_validate_numeric_field_special_values(self):
        """Test numeric field validation with special float values."""
        self.assertEqual(process_watchlist.validate_numeric_field(float('inf'), "test"), 0.0)
        self.assertEqual(process_watchlist.validate_numeric_field(float('-inf'), "test"), 0.0)
        self.assertEqual(process_watchlist.validate_numeric_field(float('nan'), "test"), 0.0)
        
    def test_extract_symbols_data_valid(self):
        """Test symbol data extraction with valid data."""
        symbols = process_watchlist.extract_symbols_data(self.test_data)
        self.assertEqual(len(symbols), 2)
        self.assertEqual(symbols[0]['symbol'], 'btc_usdt')
        self.assertEqual(symbols[0]['volume'], 1500000.50)
        
    def test_extract_symbols_data_missing_data_field(self):
        """Test symbol data extraction with missing data field."""
        with self.assertRaises(ValueError):
            process_watchlist.extract_symbols_data({})
            
    def test_extract_symbols_data_invalid_type(self):
        """Test symbol data extraction when data field is not a list."""
        with self.assertRaises(TypeError):
            process_watchlist.extract_symbols_data({"data": "not a list"})
            
    def test_calculate_score(self):
        """Test score calculation."""
        symbol_data = {
            'symbol': 'test_usdt',
            'volume': 1000.0,
            'turnover': 5000.0,
            'price_change_percent': 2.5,
            'trades': 100.0,
            'last_price': 50.0
        }
        score = process_watchlist.calculate_score(symbol_data)
        # Score = 0.3*1000 + 0.3*5000 + 0.2*2.5 + 0.2*100 = 300 + 1500 + 0.5 + 20 = 1820.5
        self.assertAlmostEqual(score, 1820.5, places=2)
        
    def test_rank_symbols(self):
        """Test symbol ranking."""
        symbols_data = process_watchlist.extract_symbols_data(self.test_data)
        ranked = process_watchlist.rank_symbols(symbols_data)
        
        self.assertEqual(len(ranked), 2)
        # BTC should be ranked first due to higher volume and turnover
        self.assertEqual(ranked[0][0], 'btc_usdt')
        # Scores should be in descending order
        self.assertGreater(ranked[0][1], ranked[1][1])
        
    def test_load_json_data_file_not_found(self):
        """Test loading JSON data when file doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            process_watchlist.load_json_data("/nonexistent/file.json")
            
    def test_save_watchlist(self):
        """Test saving watchlist to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_watchlist.txt")
            
            ranked_symbols = [
                ("btc_usdt", 1000.0, {"symbol": "btc_usdt"}),
                ("eth_usdt", 800.0, {"symbol": "eth_usdt"}),
            ]
            
            process_watchlist.save_watchlist(ranked_symbols, output_file, top_n=2)
            
            # Verify file was created
            self.assertTrue(os.path.exists(output_file))
            
            # Verify content
            with open(output_file, 'r') as f:
                lines = f.readlines()
                
            # Should have header and symbols
            self.assertIn("btc_usdt", ''.join(lines))
            self.assertIn("eth_usdt", ''.join(lines))


class TestBashScriptIntegration(unittest.TestCase):
    """Integration tests for the Bash download script."""
    
    def test_bash_script_exists(self):
        """Test that the bash script exists and is executable."""
        script_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'scripts', 
            'download_lbank_futures.sh'
        )
        self.assertTrue(os.path.exists(script_path))
        self.assertTrue(os.access(script_path, os.X_OK))
        
    def test_bash_script_has_proper_shebang(self):
        """Test that the bash script has proper shebang."""
        script_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'scripts', 
            'download_lbank_futures.sh'
        )
        with open(script_path, 'r') as f:
            first_line = f.readline()
        self.assertTrue(first_line.startswith('#!/bin/bash'))


if __name__ == '__main__':
    unittest.main()
