"""
tp_monitor.py — Take Profit Monitor pour Weather Trading Bot Polymarket

Surveille le PNL global du portfolio et ferme toutes les positions
quand le seuil de TP est atteint (+10% par défaut).

Usage:
    python tp_monitor.py

Variables d'environnement:
    WALLET_ADDRESS         (required)
    TP_THRESHOLD_PCT       (default: 10.0)
    TP_CHECK_INTERVAL_SEC  (default: 30)
    TP_DRY_RUN             (default: false)
"""

import asyncio
import logging
import os
import sys
import httpx
from datetime import datetime
from dotenv import load_dotenv

from shared.clob_client import get_clob_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tp_monitor")

# Config
load_dotenv()
WALLET = os.getenv("WALLET_ADDRESS")
TP_THRESHOLD = float(os.getenv("TP_THRESHOLD_PCT", "10.0"))
INTERVAL = int(os.getenv("TP_CHECK_INTERVAL_SEC", "30"))
DRY_RUN = os.getenv("TP_DRY_RUN", "false").lower() == "true"

DATA_API_URL = f"https://data-api.polymarket.com/positions?user={WALLET}"
CLOB_TICK_SIZE_URL = "https://clob.polymarket.com/tick-size?token_id={token_id}"

if not WALLET:
    logger.error("❌ WALLET_ADDRESS manquant dans .env")
    sys.exit(1)


async def fetch_positions(client: httpx.AsyncClient) -> list:
    """Récupère les positions ouvertes via Data API."""
    try:
        response = await client.get(DATA_API_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.warning(f"⚠️ Erreur fetch positions: {e}")
        return []


async def fetch_tick_size(client: httpx.AsyncClient, token_id: str) -> str:
    """Récupère le tick_size d'un token via CLOB API. Fallback "0.01" si erreur."""
    try:
        url = CLOB_TICK_SIZE_URL.format(token_id=token_id)
        response = await client.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        ts = data.get("minimum_tick_size", "0.01")
        return str(ts)
    except Exception as e:
        logger.warning(f"⚠️ Tick size fallback pour {token_id[:16]}...: {e}")
        return "0.01"


def calc_portfolio_pnl(positions: list) -> tuple[float, float, float, float]:
    """Calcule le PNL global du portfolio.

    Returns:
        (total_invested, total_current, pnl_usdc, pnl_pct)
    """
    if not positions:
        return 0.0, 0.0, 0.0, 0.0

    total_invested = sum(p.get("initialValue", 0) for p in positions)
    total_current = sum(p.get("currentValue", 0) for p in positions)
    pnl = total_current - total_invested
    pnl_pct = (pnl / total_invested * 100) if total_invested > 0 else 0.0

    return total_invested, total_current, pnl, pnl_pct


async def close_all_positions(positions: list, http_client: httpx.AsyncClient) -> int:
    """Vend toutes les positions ouvertes.

    Returns:
        Nombre de fermetures réussies
    """
    if not positions:
        logger.info("Aucune position à fermer")
        return 0

    logger.info(f"🚀 Début fermeture de {len(positions)} positions")

    if DRY_RUN:
        logger.info("[DRY RUN] Simulation des ventes — aucun ordre réel envoyé")

    clob = None
    if not DRY_RUN:
        clob = get_clob_client()

    success_count = 0
    estimated_usdc = 0.0

    for pos in positions:
        token_id = pos.get("asset")
        shares = pos.get("size", 0)
        neg_risk = pos.get("negativeRisk", True)
        title = pos.get("title", "Unknown")
        outcome = pos.get("outcome", "?")
        current_value = pos.get("currentValue", 0)

        if shares <= 0:
            logger.warning(f"⚠️ Skip {title[:40]} ({outcome}): shares <= 0")
            continue

        # Récupère tick_size
        tick_size = await fetch_tick_size(http_client, token_id)

        if DRY_RUN:
            logger.info(
                f"[DRY RUN] Aurait vendu {shares:.2f} shares de '{title[:40]}' "
                f"({outcome}) | valeur estimée ${current_value:.2f}"
            )
            success_count += 1
            estimated_usdc += current_value
            continue

        # Vente réelle
        try:
            response = clob.post_sell_market_order(
                token_id=token_id,
                shares=shares,
                neg_risk=neg_risk,
                tick_size=tick_size
            )
            order_id = response.get("orderID", "?")
            logger.info(
                f"✅ Vendu {shares:.2f} shares de '{title[:40]}' ({outcome}) "
                f"→ order_id={order_id[:16]}..."
            )
            success_count += 1
            estimated_usdc += current_value
        except Exception as e:
            logger.error(
                f"❌ Échec vente de '{title[:40]}' ({outcome}, {shares:.2f} shares): {e}"
            )

        # Petit délai pour éviter rate limit (50ms entre ordres)
        await asyncio.sleep(0.05)

    logger.info(
        f"🏁 Fermeture terminée : {success_count}/{len(positions)} positions vendues "
        f"| USDC reçu estimé: ${estimated_usdc:.2f}"
    )
    return success_count


async def main_loop():
    """Boucle principale du TP Monitor."""
    logger.info("=" * 70)
    logger.info(
        f"🤖 TP Monitor démarré | Wallet: {WALLET[:10]}... | "
        f"Threshold: +{TP_THRESHOLD}% | Interval: {INTERVAL}s | DRY_RUN: {DRY_RUN}"
    )
    logger.info("=" * 70)

    async with httpx.AsyncClient() as http_client:
        cycle = 0
        while True:
            cycle += 1
            try:
                positions = await fetch_positions(http_client)

                if not positions:
                    if cycle % 10 == 1:  # Log seulement tous les 10 cycles si vide
                        logger.info("💤 Aucune position ouverte, en attente...")
                    await asyncio.sleep(INTERVAL)
                    continue

                invested, current, pnl, pnl_pct = calc_portfolio_pnl(positions)

                logger.info(
                    f"📊 PNL: ${pnl:+.2f} ({pnl_pct:+.2f}%) | "
                    f"Positions: {len(positions)} | "
                    f"Invested: ${invested:.2f} | Current: ${current:.2f}"
                )

                # Check si on a atteint le TP
                if pnl_pct >= TP_THRESHOLD:
                    logger.info("=" * 70)
                    logger.info(
                        f"🚀 TAKE PROFIT TRIGGERED ! PNL atteint {pnl_pct:+.2f}% "
                        f"(seuil +{TP_THRESHOLD}%) — fermeture des {len(positions)} positions"
                    )
                    logger.info("=" * 70)

                    await close_all_positions(positions, http_client)

                    logger.info("💼 TP Monitor terminé. Bonne journée !")
                    return

                await asyncio.sleep(INTERVAL)
            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle: {e}", exc_info=True)
                await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("🛑 TP Monitor arrêté manuellement")
        sys.exit(0)