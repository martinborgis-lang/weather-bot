"""
Position Manager Agent - Gestion des positions ouvertes
Mise à jour des prix, détection des conditions de sortie, clôture des positions.
"""

import asyncio
import aiohttp
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List
from shared.models import OpenPosition
from shared.cache import cache

# Configuration des constantes
TAKE_PROFIT_PARTIAL_PCT = 0.40    # +40% → vendre 50%
TIME_BEFORE_RESOLUTION_HOLD = 7200  # 2h avant fin, freeze (en secondes)
POSITION_MANAGER_INTERVAL = 300  # 5 min entre chaque cycle
SUMMARY_INTERVAL = 1800  # 30 min pour le résumé

logger = logging.getLogger(__name__)

# Lock pour thread-safety lors des modifications de positions
position_lock = asyncio.Lock()

class PositionManager:
    def __init__(self):
        self.session = None
        self.last_summary_time = datetime.now()
        self.positions_file = "positions.json"

    async def start(self):
        """Démarre le gestionnaire de positions"""
        logger.info("🎯 Position Manager démarré")

        # Charger les positions existantes
        await self.load_positions_from_file()

        # Créer session HTTP
        self.session = aiohttp.ClientSession()

        # Lancer la boucle de gestion
        await self.run_position_loop()

    async def load_positions_from_file(self):
        """Charge les positions depuis le fichier JSON"""
        if os.path.exists(self.positions_file):
            try:
                with open(self.positions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Convertir les dict en objets OpenPosition
                positions = []
                for pos_data in data:
                    # Convertir datetime string vers datetime object
                    pos_data['opened_at'] = datetime.fromisoformat(pos_data['opened_at'])
                    # Ajouter partial_sold si absent (rétrocompatibilité)
                    if 'partial_sold' not in pos_data:
                        pos_data['partial_sold'] = False
                    positions.append(OpenPosition(**pos_data))

                await cache.set('open_positions', positions)
                logger.info(f"📂 {len(positions)} positions chargées depuis {self.positions_file}")

            except Exception as e:
                logger.error(f"❌ Erreur lors du chargement des positions: {e}")
                await cache.set('open_positions', [])
        else:
            await cache.set('open_positions', [])
            logger.info("📂 Aucun fichier de positions existant, démarrage à vide")

    async def save_positions_to_file(self):
        """Sauvegarde les positions dans le fichier JSON"""
        try:
            positions_data = []
            positions = await cache.get('open_positions', [])
            for pos in positions:
                pos_dict = {
                    'market_condition_id': pos.market_condition_id,
                    'market_title': pos.market_title,
                    'temperature_label': pos.temperature_label,
                    'side': pos.side,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'size_usdc': pos.size_usdc,
                    'size_tokens': pos.size_tokens,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'unrealized_pnl_pct': pos.unrealized_pnl_pct,
                    'opened_at': pos.opened_at.isoformat(),
                    'transaction_hash': pos.transaction_hash,
                    'partial_sold': pos.partial_sold
                }
                positions_data.append(pos_dict)

            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(positions_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde des positions: {e}")

    async def get_current_price(self, token_id: str) -> float:
        """Récupère le prix actuel d'un token via l'API Polymarket"""
        try:
            url = "https://clob.polymarket.com/price"
            params = {
                'token_id': token_id,
                'side': 'BUY'
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data.get('price', 0))
                else:
                    logger.warning(f"⚠️ Erreur API prix pour {token_id}: {response.status}")
                    return 0.0

        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération du prix pour {token_id}: {e}")
            return 0.0

    async def update_position_prices(self):
        """Met à jour les prix actuels de toutes les positions ouvertes"""
        positions = await cache.get('open_positions', [])

        if not positions:
            return

        logger.debug(f"🔄 Mise à jour des prix pour {len(positions)} positions")

        async with position_lock:
            for position in positions:
                # Récupérer le token_id depuis le market
                # Note: Il faudra adapter selon la structure réelle de vos données
                # Pour l'instant, on utilise market_condition_id comme token_id
                current_price = await self.get_current_price(position.market_condition_id)

                if current_price > 0:
                    # Mettre à jour le prix
                    position.current_price = current_price

                    # Recalculer les PnL
                    if position.side == "YES":
                        price_diff = current_price - position.entry_price
                    else:  # NO
                        price_diff = position.entry_price - current_price

                    position.unrealized_pnl = price_diff * position.size_tokens

                    # PnL en pourcentage
                    if position.size_usdc > 0:
                        position.unrealized_pnl_pct = (position.unrealized_pnl / position.size_usdc) * 100
                    else:
                        position.unrealized_pnl_pct = 0.0

    async def check_exit_conditions(self):
        """Vérifie les conditions de sortie pour toutes les positions"""
        positions = await cache.get('open_positions', [])
        current_time = datetime.now()

        for position in positions:
            # Calculer le temps avant résolution (approximatif)
            # Note: Il faudra récupérer la vraie date de résolution du marché
            # Pour l'instant, on utilise opened_at + 24h comme exemple
            estimated_resolution = position.opened_at + timedelta(days=1)
            time_to_resolution = (estimated_resolution - current_time).total_seconds()

            # Condition 1: Take profit partiel
            if (position.unrealized_pnl_pct >= TAKE_PROFIT_PARTIAL_PCT * 100 and
                not position.partial_sold):

                logger.info(f"🎯 Take profit partiel atteint sur {position.market_title} "
                           f"({position.temperature_label}) - PnL: +{position.unrealized_pnl_pct:.1f}%")

                # En DRY_RUN : simuler la vente
                dry_run = await cache.get('dry_run', True)
                if dry_run:
                    logger.info(f"🔸 [DRY_RUN] Simulation vente 50% de {position.size_tokens/2:.2f} tokens")
                else:
                    # En réel : créer un ordre de vente
                    await self.execute_partial_sell(position)

                # Marquer comme partiellement vendu
                async with position_lock:
                    position.partial_sold = True

            # Condition 2: Gel avant résolution
            if time_to_resolution <= TIME_BEFORE_RESOLUTION_HOLD and time_to_resolution > 0:
                logger.info(f"🔒 Position {position.market_title} ({position.temperature_label}) "
                           f"gelée jusqu'à résolution (dans {time_to_resolution/3600:.1f}h)")
                # Note: Ici on pourrait ajouter un flag "frozen" à la position

    async def execute_partial_sell(self, position: OpenPosition):
        """Exécute la vente partielle d'une position (50%)"""
        # Cette fonction devra être intégrée avec le trade executor
        # Pour l'instant, on log seulement
        tokens_to_sell = position.size_tokens * 0.5
        logger.info(f"🔸 [RÉEL] Création ordre SELL pour {tokens_to_sell:.2f} tokens "
                   f"sur {position.market_title} ({position.temperature_label})")

        # TODO: Intégrer avec trade_executor.py pour créer l'ordre réel
        # await trade_executor.place_sell_order(position, tokens_to_sell)

    async def log_summary(self):
        """Log un résumé des positions toutes les 30 minutes"""
        positions = await cache.get('open_positions', [])

        if not positions:
            logger.info("📊 Aucune position ouverte")
            return

        total_invested = sum(pos.size_usdc for pos in positions)
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
        avg_pnl_pct = total_unrealized_pnl / total_invested * 100 if total_invested > 0 else 0

        logger.info(f"📊 Positions ouvertes: {len(positions)} | "
                   f"Total investi: ${total_invested:.2f} | "
                   f"PnL non réalisé: {total_unrealized_pnl:+.2f}$ ({avg_pnl_pct:+.1f}%)")

        # Détail par position
        for pos in positions:
            status = "🔸PARTIAL" if pos.partial_sold else "🔵FULL"
            logger.info(f"  {status} {pos.market_title} ({pos.temperature_label}) {pos.side}: "
                       f"{pos.unrealized_pnl:+.2f}$ ({pos.unrealized_pnl_pct:+.1f}%)")

    async def run_position_loop(self):
        """Boucle principale de gestion des positions"""
        logger.info(f"🔄 Boucle de gestion démarrée (intervalle: {POSITION_MANAGER_INTERVAL}s)")

        while True:
            try:
                # Mise à jour des prix
                await self.update_position_prices()

                # Vérification des conditions de sortie
                await self.check_exit_conditions()

                # Sauvegarde
                await self.save_positions_to_file()

                # Résumé périodique
                current_time = datetime.now()
                if (current_time - self.last_summary_time).total_seconds() >= SUMMARY_INTERVAL:
                    await self.log_summary()
                    self.last_summary_time = current_time

                # Attendre le prochain cycle
                await asyncio.sleep(POSITION_MANAGER_INTERVAL)

            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle de position management: {e}")
                await asyncio.sleep(60)  # Attendre 1 min en cas d'erreur

    async def stop(self):
        """Arrête le gestionnaire de positions"""
        if self.session:
            await self.session.close()
        logger.info("⛔ Position Manager arrêté")

# Instance globale
position_manager = PositionManager()

async def start_position_manager():
    """Point d'entrée pour démarrer le gestionnaire de positions"""
    await position_manager.start()

if __name__ == "__main__":
    # Test en standalone
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_position_manager())