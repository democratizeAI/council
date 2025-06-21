import asyncio
from phoenix_auto_welder import PhoenixAutoWelder

async def main():
    welder = PhoenixAutoWelder()
    # Weld every minute
    while True:
        await welder.auto_weld_all_services()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main()) 