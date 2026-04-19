#!/usr/bin/env python3
"""
Test du nouveau Market Scanner v2 (Events API)
"""

import asyncio
import logging
from agents.market_scanner import scan_weather_markets

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_scanner():
    """Test du scanner avec la vraie API Events"""
    logger.info("🔍 Test du Market Scanner V2 (Events API)")
    logger.info("=" * 60)

    try:
        # Scanner les marchés
        markets = await scan_weather_markets()

        logger.info(f"\n📊 RÉSULTATS DU SCAN:")
        logger.info(f"Total marchés trouvés: {len(markets)}")

        if not markets:
            logger.info("❌ Aucun marché météo actif trouvé")
            logger.info("Ceci peut être normal si:")
            logger.info("- Pas d'events daily-temperature en cours")
            logger.info("- Tous les events ont une liquidité < 10000 USDC")
            logger.info("- Tous les events se terminent dans < 2h")
            return

        # Afficher les 10 premiers marchés
        logger.info(f"\n🏆 TOP {min(10, len(markets))} MARCHÉS:")
        logger.info("-" * 60)

        for i, market in enumerate(markets[:10], 1):
            logger.info(f"{i:2d}. {market.title}")
            logger.info(f"    Ville: {market.city}")
            logger.info(f"    Date: {market.target_date.strftime('%Y-%m-%d')}")
            logger.info(f"    Liquidité: ${market.liquidity_usdc:,.0f}")
            logger.info(f"    Volume: ${market.volume_usdc:,.0f}")
            logger.info(f"    Ranges: {len(market.ranges)}")
            logger.info(f"    Fin: {market.ends_at.strftime('%Y-%m-%d %H:%M')}")

            # Afficher quelques ranges
            logger.info("    Ranges de température:")
            for j, temp_range in enumerate(market.ranges[:5]):
                logger.info(f"      {j+1}. {temp_range.label:<15} | "
                           f"Prix: {temp_range.current_price:.3f} | "
                           f"Token: {temp_range.token_id[:12]}...")

            if len(market.ranges) > 5:
                logger.info(f"      ... et {len(market.ranges) - 5} autres ranges")

            logger.info("")

        if len(markets) > 10:
            logger.info(f"... et {len(markets) - 10} autres marchés")

        # Statistiques par ville
        cities = {}
        total_liquidity = 0
        total_volume = 0

        for market in markets:
            cities[market.city] = cities.get(market.city, 0) + 1
            total_liquidity += market.liquidity_usdc
            total_volume += market.volume_usdc

        logger.info(f"\n📈 STATISTIQUES:")
        logger.info(f"Liquidité totale: ${total_liquidity:,.0f}")
        logger.info(f"Volume total: ${total_volume:,.0f}")
        logger.info(f"Répartition par ville:")
        for city, count in sorted(cities.items()):
            logger.info(f"  {city}: {count} marché(s)")

        # Test de parsing des ranges
        logger.info(f"\n🧪 TEST PARSING DES RANGES:")
        sample_market = markets[0]
        logger.info(f"Marché: {sample_market.title}")
        for temp_range in sample_market.ranges:
            logger.info(f"  {temp_range.label:<20} → "
                       f"[{temp_range.min_temp:5.1f}, {temp_range.max_temp:5.1f}] | "
                       f"Prix: {temp_range.current_price:.3f}")

        logger.info(f"\n✅ Test terminé avec succès!")
        logger.info(f"Le nouveau scanner fonctionne correctement avec l'API Events.")

    except Exception as e:
        logger.error(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scanner())