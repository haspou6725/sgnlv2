from .rest_client import RESTClient

async def funding_oi(symbol: str):
    rc = RESTClient("https://fapi.binance.com")
    try:
        fund = await rc.get("/fapi/v1/premiumIndex", params={"symbol": symbol})
        oi = await rc.get("/futures/data/openInterestHist", params={"symbol": symbol, "period":"5m", "limit": 1})
        await rc.close()
        return fund, oi
    except Exception:
        await rc.close()
        raise
