import asyncio
import aiohttp
import json

async def main():
    # Events daily-temperature
    url = "https://gamma-api.polymarket.com/events"
    params = {"active": "true", "closed": "false", "limit": 50, "tag_slug": "daily-temperature"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            events = await resp.json()
    
    print(f"=== {len(events)} events daily-temperature ===\n")
    
    for e in events[:3]:
        print(f"📍 {e.get('title')}")
        print(f"   slug: {e.get('slug')}")
        print(f"   endDate: {e.get('endDate')}")
        print(f"   volume: {e.get('volume')}")
        print(f"   liquidity: {e.get('liquidity')}")
        print(f"   markets: {len(e.get('markets', []))}")
        
        # Inspect 1er market
        if e.get('markets'):
            m = e['markets'][0]
            print(f"\n   1er market de l'event :")
            print(f"   question: {m.get('question')}")
            print(f"   outcome: {m.get('groupItemTitle') or m.get('outcomes')}")
            print(f"   clobTokenIds: {m.get('clobTokenIds')}")
            print(f"   outcomePrices: {m.get('outcomePrices')}")
        print("\n")

asyncio.run(main())