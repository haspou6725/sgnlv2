from .rest_client import RESTClient

async def oi(symbol: str):
    rc = RESTClient("https://api.bybit.com")
    data = await rc.get("/v5/market/open-interest", params={"category":"linear","symbol":symbol,"intervalTime":"5min"})
    await rc.close()
    return data
