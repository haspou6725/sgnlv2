from .rest_client import RESTClient

async def funding(symbol: str):
    rc = RESTClient("https://api.lbkex.com")
    data = await rc.get("/v2/funding_rate.do", params={"symbol": symbol})
    await rc.close()
    return data
