#!/usr/bin/env python3
"""
Test du chaînage Scanner → Forecaster après les corrections.
"""

import asyncio
import logging
from agents.market_scanner import MarketScanner
from agents.weather_forecaster import run_forecaster_cycle
from agents.edge_calculator import run_edge_cycle
from shared.cache import cache

# Configuration du logging avec plus de détails
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_chain():
    """Test complet du chaînage Scanner → Forecaster → Edge Calculator"""
    logger.info("=== TEST DU CHAÎNAGE SCANNER → FORECASTER → EDGE CALCULATOR ===")

    try:
        # 1. Scanner
        async with MarketScanner() as scanner:
            markets = await scanner.scan_weather_markets()
            logger.info(f"✅ Scanner: {len(markets)} marchés récupérés")

            if not markets:
                logger.error("❌ Aucun marché trouvé par le scanner")
                return

            # Afficher quelques exemples
            for i, market in enumerate(markets[:3]):
                logger.debug(f"Marché {i+1}: {market.city} - {market.title[:50]}...")

        # 2. Forecaster avec marchés explicites
        logger.info("--- Forecaster avec marchés passés explicitement ---")
        await run_forecaster_cycle(markets=markets)

        # Vérifier le cache des forecasts
        forecasts = await cache.get('forecasts', {})
        logger.info(f"✅ Forecaster: {len(forecasts)} prévisions stockées dans le cache")

        if not forecasts:
            logger.error("❌ Aucune prévision trouvée dans le cache après le forecaster")
            return

        # 3. Edge Calculator avec marchés et forecasts explicites
        logger.info("--- Edge Calculator avec données passées explicitement ---")
        await run_edge_cycle(markets=markets, forecasts=forecasts)

        # Vérifier les signaux
        signals = await cache.get('trade_signals', [])
        logger.info(f"✅ Edge Calculator: {len(signals)} signaux générés")

        # Résumé final
        logger.info("=== RÉSUMÉ DU TEST ===")
        logger.info(f"Scanner: {len(markets)} marchés")
        logger.info(f"Forecaster: {len(forecasts)} prévisions")
        logger.info(f"Edge Calculator: {len(signals)} signaux")

        if len(markets) > 0 and len(forecasts) > 0:
            logger.info("✅ Chaînage Scanner → Forecaster → Edge Calculator réussi!")
        else:
            logger.error("❌ Problème dans le chaînage")

    except Exception as e:
        logger.error(f"❌ Erreur dans le test: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_chain())