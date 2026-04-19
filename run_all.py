#!/usr/bin/env python3
"""
Orchestrateur pour lancer le bot météo et le dashboard Streamlit en parallèle
"""

import asyncio
import subprocess
import sys
import os
import logging
from main import main as bot_main

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def run_dashboard():
    """Lance l'application Streamlit dashboard"""
    port = os.getenv("PORT", "8080")

    logger.info(f"🎨 Démarrage du dashboard Streamlit sur le port {port}")

    # Créer le répertoire data s'il n'existe pas
    data_dir = os.getenv("DATA_DIR", "./data")
    os.makedirs(data_dir, exist_ok=True)

    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
            "--server.port", port,
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--logger.level", "warning",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        logger.info("✅ Dashboard Streamlit démarré avec succès")

        # Lire les logs en continu
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            logger.info(f"Streamlit: {line.decode().strip()}")

        await process.wait()

    except Exception as e:
        logger.error(f"❌ Erreur dashboard: {e}")
        raise

async def run_bot():
    """Lance le bot météo"""
    logger.info("🤖 Démarrage du bot météo")

    try:
        await bot_main()
    except Exception as e:
        logger.error(f"❌ Erreur bot: {e}")
        raise

async def run_all():
    """Lance le bot et le dashboard en parallèle"""
    logger.info("🚀 Démarrage de l'application complète Weather Bot + Dashboard")

    try:
        # Lancer les deux processus en parallèle
        await asyncio.gather(
            run_bot(),
            run_dashboard(),
            return_exceptions=True
        )
    except KeyboardInterrupt:
        logger.info("⏹️ Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur générale: {e}")
        raise

if __name__ == "__main__":
    # Vérifier les variables d'environnement importantes
    data_dir = os.getenv("DATA_DIR", "./data")
    logger.info(f"📁 Répertoire de données: {data_dir}")

    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    logger.info(f"🔄 Mode: {'DRY_RUN' if dry_run else 'LIVE TRADING'}")

    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        logger.info("👋 Application arrêtée proprement")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Échec du démarrage: {e}")
        sys.exit(1)