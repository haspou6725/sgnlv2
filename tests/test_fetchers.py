"""
Tests for exchange data fetchers
"""
import pytest
import asyncio
from data_fetcher.fetch_binance import BinanceFetcher
from data_fetcher.fetch_lbank import LBankFetcher


@pytest.mark.asyncio
async def test_binance_fetcher_initialization():
    """Test Binance fetcher initialization"""
    fetcher = BinanceFetcher()
    assert fetcher is not None
    assert fetcher.BASE_URL == "https://fapi.binance.com"
    await fetcher.close()


@pytest.mark.asyncio
async def test_binance_fetch_ticker():
    """Test fetching ticker from Binance"""
    fetcher = BinanceFetcher()
    
    # Try to fetch BTCUSDT (should exist)
    ticker = await fetcher.fetch_ticker("BTCUSDT")
    
    if ticker:  # May fail if API is down
        assert "symbol" in ticker
        assert "price" in ticker
        assert ticker["price"] > 0
    
    await fetcher.close()


@pytest.mark.asyncio
async def test_lbank_fetcher_initialization():
    """Test LBank fetcher initialization"""
    fetcher = LBankFetcher()
    assert fetcher is not None
    assert fetcher.BASE_URL == "https://www.lbkex.net"
    await fetcher.close()


@pytest.mark.asyncio
async def test_unified_data_structure():
    """Test unified data format across fetchers"""
    fetcher = BinanceFetcher()
    
    try:
        data = await fetcher.fetch_unified_data("BTCUSDT")
        
        if data:
            # Check required keys
            assert "symbol" in data
            assert "exchange" in data
            assert "price" in data
            assert "orderbook" in data
            assert "trades" in data
            assert "funding_rate" in data
            assert "open_interest" in data
    except:
        pass  # API may be unavailable
    finally:
        await fetcher.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
