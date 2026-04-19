import asyncio
import logging
from agents.market_scanner import scan_weather_markets

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    markets = await scan_weather_markets()
    print(f"\n=== {len(markets)} marchés retenus ===\n")
    for m in markets[:5]:
        print(f"📍 {m.title}")
        print(f"   City: {m.city} | Date: {m.target_date}")
        print(f"   Liquidity: ${m.liquidity_usdc:.0f} | Volume: ${m.volume_usdc:.0f}")
        print(f"   Ranges: {[r.label for r in m.ranges]}")
        print()

asyncio.run(main())