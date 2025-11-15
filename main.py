import asyncio, os
from orchestrator.engine import Orchestrator

async def main():
    o = Orchestrator()
    await o.run()

if __name__ == "__main__":
    asyncio.run(main())
