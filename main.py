import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

from agents.market_scanner import MarketScanner
# TODO: Importer les fonctions de cycle simple quand elles seront créées
# from agents.weather_forecaster import run_forecaster_cycle
# from agents.edge_calculator import run_edge_cycle
from agents.trade_executor import TradeExecutor
from agents.position_manager import PositionManager
from config import Config
from shared.cache import cache

# Logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('main')


class WeatherBot:
    def __init__(self):
        self.scanner = MarketScanner()
        self.trade_executor = TradeExecutor()
        self.position_manager = PositionManager()

        # Sessions HTTP initialisées dans start()
        self.scanner_session = None

        self.last_forecast_ts = None
        self.forecast_interval = 3600  # 1h
        self.trading_interval = 900    # 15min
        self.position_interval = 300   # 5min

        self.last_trading = 0
        self.last_position = 0

    async def trading_cycle(self):
        """Cycle complet : scan → forecast → edges → trades"""
        logger.info("=" * 60)
        logger.info(f"🔄 CYCLE TRADING - {datetime.now().isoformat()}")
        logger.info("=" * 60)

        try:
            # 1. Scanner marchés Polymarket
            markets = await self.scanner.scan_weather_markets()
            logger.info(f"✅ Scanner: {len(markets)} marchés weather")

            if not markets:
                logger.warning("Aucun marché, skip cycle")
                return

            # 2. Forecasts Open-Meteo (1x par heure)
            now = asyncio.get_event_loop().time()
            if self.last_forecast_ts is None or (now - self.last_forecast_ts > self.forecast_interval):
                logger.info("🌤️ Fetch forecasts Open-Meteo (premier cycle ou cache expiré)")
                # TODO: Créer un cycle simple pour forecaster
                self.last_forecast_ts = now
            else:
                remaining = self.forecast_interval - (now - self.last_forecast_ts)
                logger.info(f"⏭️ Forecasts en cache (refresh dans {remaining/60:.0f}min)")

            # 3. Calcul des edges
            # TODO: Créer un cycle simple pour edge calculator
            signals = await cache.get('trade_signals', [])
            logger.info(f"✅ Edge Calculator: {len(signals)} signaux détectés")

            # 4. Exécution des trades
            if signals:
                await self.trade_executor.process_trade_signals()
            else:
                logger.info("Aucun signal à exécuter")

        except Exception as e:
            logger.error(f"❌ Erreur cycle trading: {e}", exc_info=True)

    async def position_cycle(self):
        """Gestion des positions ouvertes"""
        try:
            await self.position_manager.update_position_prices()
        except Exception as e:
            logger.error(f"❌ Erreur position cycle: {e}", exc_info=True)

    async def start_sessions(self):
        """Initialise toutes les sessions HTTP des agents"""
        logger.info("🔌 Initialisation des sessions HTTP...")

        # MarketScanner : utilise async context manager
        self.scanner_session = await self.scanner.__aenter__()

        # PositionManager : utilise méthode start() mais sans la boucle
        self.position_manager.session = await self._create_session()
        await self.position_manager.load_positions_from_file()

        # TradeExecutor : initialise le client CLOB
        await self.trade_executor._initialize_clob_client()

        logger.info("✅ Sessions HTTP initialisées")

    async def _create_session(self):
        """Crée une session aiohttp avec timeout"""
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=30)
        return aiohttp.ClientSession(timeout=timeout)

    async def stop_sessions(self):
        """Ferme proprement toutes les sessions HTTP"""
        logger.info("🔌 Fermeture des sessions HTTP...")

        # MarketScanner
        if self.scanner_session:
            await self.scanner.__aexit__(None, None, None)

        # PositionManager
        if self.position_manager.session:
            await self.position_manager.session.close()

        # TradeExecutor
        await self.trade_executor.stop()

        logger.info("✅ Sessions fermées")

    async def run(self):
        logger.info("=" * 60)
        logger.info("🚀 WEATHER TRADING BOT POLYMARKET")
        logger.info("=" * 60)
        logger.info(f"📁 Data: {Config.DATA_DIR}")
        logger.info(f"💰 Bankroll: ${Config.BANKROLL_USDC}")
        logger.info(f"💵 Position: ${Config.MIN_POSITION_USDC}-${Config.MAX_POSITION_USDC}")
        logger.info(f"🎯 Edge min: {Config.EDGE_MINIMUM:.0%}")
        logger.info(f"📊 Max positions: {Config.MAX_POSITIONS_COUNT}")
        logger.info(f"🔄 Mode: {'LIVE TRADING' if not Config.DRY_RUN else 'DRY_RUN'}")
        logger.info("=" * 60)

        try:
            # Initialiser les sessions HTTP
            await self.start_sessions()

            while True:
                try:
                    now = asyncio.get_event_loop().time()

                    # Trading cycle toutes les 15 min
                    if now - self.last_trading >= self.trading_interval:
                        await self.trading_cycle()
                        self.last_trading = now

                    # Position management toutes les 5 min
                    if now - self.last_position >= self.position_interval:
                        await self.position_cycle()
                        self.last_position = now

                    await asyncio.sleep(30)  # check toutes les 30s

                except KeyboardInterrupt:
                    logger.info("🛑 Arrêt du bot demandé")
                    break
                except Exception as e:
                    logger.error(f"❌ Erreur boucle principale: {e}", exc_info=True)
                    await asyncio.sleep(60)  # wait before retry

        finally:
            # Fermer les sessions proprement
            await self.stop_sessions()


if __name__ == "__main__":
    bot = WeatherBot()
    asyncio.run(bot.run())