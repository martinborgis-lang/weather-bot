import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

from agents.market_scanner import MarketScanner
from agents.weather_forecaster import run_forecaster_cycle
from agents.edge_calculator import run_edge_cycle
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

# Status tracking
BOT_STATUS_FILE = Path("data/bot_status.json")
PAUSE_FILE = Path("data/.pause")
FORCE_CYCLE_FILE = Path("data/.force_cycle")
START_TIME = datetime.now()


def write_status(last_cycle_at=None, next_scan_at=None, errors_24h=0):
    """Écrit l'état courant du bot dans un fichier lisible par l'API"""
    try:
        status = {
            "running": True,
            "last_cycle_at": last_cycle_at.isoformat() if last_cycle_at else None,
            "uptime_seconds": int((datetime.now() - START_TIME).total_seconds()),
            "next_scan_at": next_scan_at.isoformat() if next_scan_at else None,
            "dry_run": Config.DRY_RUN,
            "errors_24h": errors_24h,
            "bankroll_usdc": Config.BANKROLL_USDC,
            "max_position_usdc": Config.MAX_POSITION_USDC,
            "edge_minimum": Config.EDGE_MINIMUM,
        }
        BOT_STATUS_FILE.parent.mkdir(exist_ok=True)
        BOT_STATUS_FILE.write_text(json.dumps(status, indent=2))
    except Exception as e:
        logger.error(f"Error writing bot status: {e}")


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
            logger.debug(f"Marchés détaillés: {[f'{m.city} ({m.condition_id[:8]})' for m in markets[:5]]}")

            if not markets:
                logger.warning("Aucun marché, skip cycle")
                return

            # 2. Forecasts Open-Meteo (1x par heure)
            now = asyncio.get_event_loop().time()
            if self.last_forecast_ts is None or (now - self.last_forecast_ts > self.forecast_interval):
                logger.info("🌤️ Début fetch forecasts Open-Meteo (premier cycle ou cache expiré)")
                await run_forecaster_cycle(markets=markets)
                self.last_forecast_ts = now
                logger.info("✅ Fin fetch forecasts Open-Meteo")
            else:
                remaining = self.forecast_interval - (now - self.last_forecast_ts)
                logger.info(f"⏭️ Forecasts en cache (refresh dans {remaining/60:.0f}min)")

            # 3. Calcul des edges (récupérer les forecasts du cache)
            forecasts = await cache.get('forecasts', {})
            logger.debug(f"Forecasts récupérés du cache: {len(forecasts)} villes")
            await run_edge_cycle(markets=markets, forecasts=forecasts)
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

            # Écrire le statut initial
            write_status()
            logger.info("✅ Bot status initialized")

            while True:
                try:
                    # Check si pause
                    if PAUSE_FILE.exists():
                        logger.info("⏸️  Bot en pause (data/.pause existe), skip cycle")
                        await asyncio.sleep(60)
                        continue

                    # Check si force cycle
                    force = FORCE_CYCLE_FILE.exists()
                    if force:
                        logger.info("⚡ Force cycle demandé, exécution immédiate")
                        FORCE_CYCLE_FILE.unlink()

                    now = asyncio.get_event_loop().time()
                    cycle_executed = False

                    # Trading cycle toutes les 15 min (ou si force)
                    if force or now - self.last_trading >= self.trading_interval:
                        await self.trading_cycle()
                        self.last_trading = now
                        cycle_executed = True

                    # Position management toutes les 5 min
                    if now - self.last_position >= self.position_interval:
                        await self.position_cycle()
                        self.last_position = now

                    # Mettre à jour le statut après les cycles
                    if cycle_executed:
                        next_scan = datetime.now() + timedelta(seconds=self.trading_interval)
                        write_status(last_cycle_at=datetime.now(), next_scan_at=next_scan)

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