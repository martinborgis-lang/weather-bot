#!/usr/bin/env python3
"""
Weather Trading Bot - Main Orchestration
Lance tous les agents en parallèle pour le trading météo sur Polymarket
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime

# Imports des agents
from agents.market_scanner import run_scanner_loop
from agents.weather_forecaster import run_forecaster_loop
from agents.edge_calculator import run_edge_loop
from agents.trade_executor import TradeExecutor
from agents.position_manager import start_position_manager

# Configuration
logger = logging.getLogger(__name__)

class WeatherTradingBot:
    """Orchestrateur principal du bot de trading météo"""

    def __init__(self):
        self.running = True
        self.tasks = []

    async def start_all_agents(self):
        """Lance tous les agents en parallèle"""
        logger.info("🚀 Démarrage du Weather Trading Bot")
        logger.info(f"📅 Heure de démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # Créer les tâches pour chaque agent
            tasks = [
                asyncio.create_task(run_scanner_loop(), name="MarketScanner"),
                asyncio.create_task(run_forecaster_loop(), name="WeatherForecaster"),
                asyncio.create_task(run_edge_loop(), name="EdgeCalculator"),
                asyncio.create_task(self.run_trade_executor(), name="TradeExecutor"),
                asyncio.create_task(start_position_manager(), name="PositionManager")
            ]

            self.tasks = tasks

            # Log de démarrage de chaque agent
            for task in tasks:
                logger.info(f"📡 Agent {task.get_name()} démarré")

            # Attendre que tous les agents tournent
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage des agents: {e}")
            await self.stop()

    async def run_trade_executor(self):
        """Lance l'exécuteur de trades"""
        executor = TradeExecutor()
        await executor.run_executor_loop()

    async def stop(self):
        """Arrête proprement tous les agents"""
        logger.info("🛑 Arrêt du Weather Trading Bot demandé")
        self.running = False

        # Annuler toutes les tâches
        for task in self.tasks:
            if not task.done():
                task.cancel()
                logger.info(f"⏹️  Agent {task.get_name()} arrêté")

        # Attendre que toutes les tâches se terminent
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info("✅ Tous les agents arrêtés proprement")

# Instance globale du bot
bot = WeatherTradingBot()

def setup_logging():
    """Configure le système de logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Réduire le niveau de log pour aiohttp
    logging.getLogger('aiohttp').setLevel(logging.WARNING)

    logger.info("📝 Système de logging configuré")

def handle_shutdown(signum, frame):
    """Gestionnaire de signaux pour arrêt propre"""
    logger.info(f"🔔 Signal {signum} reçu, arrêt du bot...")
    asyncio.create_task(bot.stop())

async def main():
    """Point d'entrée principal"""
    # Configuration du logging
    setup_logging()

    # Configuration des signaux pour arrêt propre
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("=" * 50)
    logger.info("🌤️  WEATHER TRADING BOT POLYMARKET")
    logger.info("=" * 50)

    try:
        # Démarrer tous les agents
        await bot.start_all_agents()

    except KeyboardInterrupt:
        logger.info("⌨️  Interruption clavier détectée")
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
    finally:
        await bot.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot arrêté par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        sys.exit(1)