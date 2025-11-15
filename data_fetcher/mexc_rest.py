from .rest_client import RESTClient

async def funding(symbol: str):
    rc = RESTClient("https://contract.mexc.com")
    data = await rc.get("/api/v1/contract/funding/prevFundingRate", params={"symbol": symbol})
    await rc.close()
    return data
