import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import List
from shared.models import TradeSignal, OpenPosition
from shared.cache import cache
from config import Config

# Constantes
EXECUTOR_INTERVAL = 300  # 5 min

# Configuration du logger
logger = logging.getLogger(__name__)

def get_position_size(pos):
    """Retourne size_usdc qu'il s'agisse d'un dict ou d'un objet OpenPosition"""
    if isinstance(pos, dict):
        return pos.get('size_usdc', 0)
    return getattr(pos, 'size_usdc', 0)

def get_position_field(pos, field, default=None):
    """Helper générique pour accéder à un champ"""
    if isinstance(pos, dict):
        return pos.get(field, default)
    return getattr(pos, field, default)

# Placeholder pour ClobClient - À adapter selon la vraie librairie
class MockClobClient:
    def __init__(self, api_key, secret, passphrase, private_key):
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        self.private_key = private_key
        self.dry_run = os.environ.get('DRY_RUN', 'true').lower() == 'true'

        logger.info(f"ClobClient initialisé - DRY_RUN: {self.dry_run}")

    def create_and_post_order(self, token_id, price, size, side, order_type):
        """Crée et poste un ordre sur CLOB"""
        if self.dry_run:
            # Mock implementation pour DRY_RUN
            logger.info(f"[DRY RUN] Ordre simulé: {side} {size} tokens à {price} USDC")
            return {
                "success": True,
                "orderId": f"mock_order_{datetime.now().strftime('%H%M%S')}",
                "hash": f"0xmockhash{datetime.now().strftime('%H%M%S')}"
            }
        else:
            # TODO: Implémenter la vraie librairie CLOB ici
            # Exemple d'appel réel (à adapter):
            # return self.client.create_and_post_order(
            #     token_id=token_id,
            #     price=price,
            #     size=size,
            #     side=side,
            #     order_type=order_type
            # )
            raise NotImplementedError("Vraie implémentation CLOB API à implémenter")

class TradeExecutor:
    """Exécute les signaux de trade via la CLOB API Polymarket"""

    def __init__(self):
        self.clob_client = None
        self.running = False

        # Chargement des credentials depuis .env
        self.api_key = os.environ.get('CLOB_API_KEY')
        self.secret = os.environ.get('CLOB_SECRET')
        self.passphrase = os.environ.get('CLOB_PASSPHRASE')
        self.private_key = os.environ.get('CLOB_PRIVATE_KEY')

        # Configuration DRY_RUN
        self.dry_run = os.environ.get('DRY_RUN', 'true').lower() == 'true'

        logger.info(f"TradeExecutor initialisé - DRY_RUN: {self.dry_run}")

        # Setup data directory
        self.data_dir = os.getenv("DATA_DIR", "./data")
        os.makedirs(self.data_dir, exist_ok=True)

    async def save_trade_to_history(self, trade_record: dict):
        """Sauvegarde un trade dans l'historique JSON"""
        try:
            history_file = os.path.join(self.data_dir, "trade_history.json")

            # Charger l'historique existant
            existing_history = []
            if os.path.exists(history_file):
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        existing_history = json.load(f)
                except:
                    existing_history = []

            # Extraire la ville du titre du marché
            city = "Unknown"
            signal = trade_record['signal']
            if hasattr(signal.market, 'title') and signal.market.title:
                city_match = re.search(r'in\s+([A-Z][a-z]+)', signal.market.title)
                if city_match:
                    city = city_match.group(1)

            # Créer l'entrée d'historique
            history_entry = {
                'timestamp': trade_record['execution_time'].isoformat(),
                'condition_id': signal.market.condition_id,
                'token_id': getattr(signal.temperature_range, 'token_id', signal.temperature_range.label),
                'city': city,
                'market_title': signal.market.title,
                'temperature_label': signal.temperature_range.label,
                'side': signal.side,
                'entry_price': signal.temperature_range.current_price,
                'size_usdc': signal.recommended_size_usdc,
                'size_tokens': trade_record['position'].size_tokens,
                'opened_at': trade_record['execution_time'].isoformat(),
                'transaction_hash': trade_record['position'].transaction_hash,
                'dry_run': trade_record['dry_run'],
                'order_id': trade_record['order_result'].get('orderId'),
                'target_date': getattr(signal.market, 'target_date', None),
                # Fields that will be filled when trade is closed
                'exit_price': None,
                'final_pnl': None,
                'closed_at': None,
                'exit_reason': None
            }

            existing_history.append(history_entry)

            # Garder seulement les 1000 derniers trades pour éviter un fichier trop gros
            if len(existing_history) > 1000:
                existing_history = existing_history[-1000:]

            # Sauvegarder avec gestion des datetime
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(existing_history, f, indent=2, ensure_ascii=False, default=str)

            logger.debug(f"💾 Trade sauvegardé dans l'historique: {city} {signal.side} {signal.recommended_size_usdc:.0f} USDC")

        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde de l'historique: {e}")

    async def _initialize_clob_client(self):
        """Initialise le client CLOB avec les credentials"""
        if not all([self.api_key, self.secret, self.passphrase, self.private_key]):
            if not self.dry_run:
                raise ValueError("Credentials CLOB manquants dans .env")
            else:
                logger.warning("Credentials CLOB manquants - mode DRY_RUN uniquement")

        self.clob_client = MockClobClient(
            api_key=self.api_key,
            secret=self.secret,
            passphrase=self.passphrase,
            private_key=self.private_key
        )

    async def _check_existing_position(self, signal: TradeSignal) -> bool:
        """Vérifie si une position est déjà ouverte sur le même marché/range"""
        open_positions = await cache.get('open_positions', [])

        for position in open_positions:
            market_id = get_position_field(position, 'market_condition_id')
            temp_label = get_position_field(position, 'temperature_label')
            if (market_id == signal.market.condition_id and
                temp_label == signal.temperature_range.label):
                logger.info(f"Position existante trouvée: {signal.market.title} - {signal.temperature_range.label}")
                return True

        return False

    async def _check_capital_available(self, signal_size: float) -> bool:
        """Vérifie si le capital est suffisant pour exécuter le signal"""
        open_positions = await cache.get('open_positions', [])
        total_exposure = sum(get_position_size(pos) for pos in open_positions)
        available = Config.BANKROLL_USDC - total_exposure

        if signal_size > available:
            logger.warning(f"Signal skippé - capital insuffisant: besoin ${signal_size:.2f}, disponible ${available:.2f}")
            return False

        logger.debug(f"Capital OK: besoin ${signal_size:.2f}, disponible ${available:.2f} (exposition: ${total_exposure:.2f}/${Config.BANKROLL_USDC})")
        return True

    async def _is_duplicate_position(self, signal: TradeSignal) -> bool:
        """Vérifie qu'on n'a pas déjà la même position ouverte"""
        open_positions = await cache.get('open_positions', [])

        for pos in open_positions:
            market_id = get_position_field(pos, 'market_condition_id')
            temp_label = get_position_field(pos, 'temperature_label')
            side = get_position_field(pos, 'side')

            if (market_id == signal.market.condition_id and
                temp_label == signal.temperature_range.label and
                side == signal.side):
                return True

        return False

    async def execute_signal(self, signal: TradeSignal) -> bool:
        """Exécute un signal de trade avec vérifications complètes

        Returns:
            bool: True si le trade a été exécuté avec succès, False sinon
        """
        try:
            # Extraire ville du titre pour les logs
            city = "Unknown"
            if hasattr(signal.market, 'title') and signal.market.title:
                city_match = re.search(r'in\s+([A-Z][a-z]+)', signal.market.title)
                if city_match:
                    city = city_match.group(1)

            # Log du signal reçu
            logger.info(f"Signal REÇU: {city} {signal.temperature_range.label} {signal.side} "
                       f"edge={signal.edge_points:.1%} size=${signal.recommended_size_usdc:.2f}")

            # Vérification 1: Capital disponible
            if not await self._check_capital_available(signal.recommended_size_usdc):
                logger.info(f"→ SKIP (capital insuffisant)")
                return False

            # Vérification 2: Position dupliquée
            if await self._is_duplicate_position(signal):
                logger.info(f"→ SKIP (position déjà ouverte): {signal.market.title} {signal.temperature_range.label} {signal.side}")
                return False

            # Vérification 3: Position existante (ancienne méthode)
            if await self._check_existing_position(signal):
                logger.info(f"→ SKIP (position existante détectée)")
                return False

            logger.info(f"→ EXÉCUTION confirmée pour {city} {signal.temperature_range.label} {signal.side}")

            # Calcul de la taille en tokens
            size_tokens = signal.recommended_size_usdc / signal.temperature_range.current_price

            if self.dry_run:
                # Mode simulation
                logger.info(f"[DRY RUN] Exécution: {signal.side} {size_tokens:.4f} tokens "
                           f"({signal.recommended_size_usdc:.2f} USDC) sur {signal.market.title} - "
                           f"{signal.temperature_range.label} à {signal.temperature_range.current_price:.4f}")

                # Création d'un ordre simulé
                order_result = {
                    "success": True,
                    "orderId": f"dry_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "hash": None
                }
                transaction_hash = None
            else:
                # Mode réel - appel CLOB API
                logger.info(f"Exécution RÉELLE: {signal.side} {size_tokens:.4f} tokens "
                           f"({signal.recommended_size_usdc:.2f} USDC) sur {signal.market.title} - "
                           f"{signal.temperature_range.label}")

                order_result = self.clob_client.create_and_post_order(
                    token_id=signal.temperature_range.token_id,
                    price=signal.temperature_range.current_price,
                    size=size_tokens,
                    side='BUY',  # Toujours BUY car on trade les tokens YES
                    order_type='FOK'
                )

                if not order_result.get("success"):
                    logger.error(f"Échec de l'ordre CLOB: {order_result}")
                    return False

                transaction_hash = order_result.get("hash")
                logger.info(f"Trade exécuté: tx_hash={transaction_hash}, order_id={order_result.get('orderId')}")

            # Création de la position ouverte
            open_position = OpenPosition(
                market_condition_id=signal.market.condition_id,
                market_title=signal.market.title,
                temperature_label=signal.temperature_range.label,
                side=signal.side,
                entry_price=signal.temperature_range.current_price,
                current_price=signal.temperature_range.current_price,
                size_usdc=signal.recommended_size_usdc,
                size_tokens=size_tokens,
                unrealized_pnl=0.0,
                unrealized_pnl_pct=0.0,
                opened_at=datetime.now(),
                transaction_hash=transaction_hash,
                resolution_datetime=signal.resolution_datetime
            )

            # Ajout à la liste des positions ouvertes
            open_positions = await cache.get('open_positions', [])
            open_positions.append(open_position)
            await cache.set('open_positions', open_positions)

            # Ajout à la liste des trades exécutés
            executed_trades = await cache.get('executed_trades', [])
            trade_record = {
                "signal": signal,
                "execution_time": datetime.now(),
                "order_result": order_result,
                "position": open_position,
                "dry_run": self.dry_run
            }
            executed_trades.append(trade_record)
            await cache.set('executed_trades', executed_trades)

            # Sauvegarder dans l'historique JSON pour le dashboard
            await self.save_trade_to_history(trade_record)

            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'exécution du signal: {e}", exc_info=True)
            return False

    async def process_trade_signals(self):
        """Traite tous les signaux de trade en attente"""
        try:
            # Récupération des signaux
            trade_signals = await cache.get('trade_signals', [])

            if not trade_signals:
                logger.debug("Aucun signal de trade à traiter")
                return

            # Calcul exposition actuelle
            open_positions = await cache.get('open_positions', [])
            total_exposure = sum(get_position_size(pos) for pos in open_positions)

            logger.info(f"=== Cycle Trade Executor: {len(trade_signals)} signaux, exposition actuelle ${total_exposure:.2f}/${Config.BANKROLL_USDC} ===")

            successful_executions = 0

            for signal in trade_signals:
                # L'exécution de chaque signal inclut maintenant toutes les vérifications
                if await self.execute_signal(signal):
                    successful_executions += 1

            # Vidage du cache des signaux après traitement
            await cache.set('trade_signals', [])

            logger.info(f"=== Traitement terminé: {successful_executions}/{len(trade_signals)} signaux exécutés ===")

        except Exception as e:
            logger.error(f"Erreur lors du traitement des signaux: {e}", exc_info=True)

    async def run_executor_loop(self):
        """Boucle principale d'exécution des trades"""
        logger.info(f"Démarrage du Trade Executor - Intervalle: {EXECUTOR_INTERVAL}s")

        # Initialisation du client CLOB
        await self._initialize_clob_client()

        self.running = True

        while self.running:
            try:
                await self.process_trade_signals()

                # Attente avant le prochain cycle
                await asyncio.sleep(EXECUTOR_INTERVAL)

            except asyncio.CancelledError:
                logger.info("Executor loop annulée")
                break
            except Exception as e:
                logger.error(f"Erreur dans la boucle executor: {e}", exc_info=True)
                # Attente plus courte en cas d'erreur pour retry
                await asyncio.sleep(60)

    async def stop(self):
        """Arrête la boucle d'exécution"""
        logger.info("Arrêt du Trade Executor")
        self.running = False

async def main():
    """Point d'entrée pour tester l'executor"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    executor = TradeExecutor()

    try:
        await executor.run_executor_loop()
    except KeyboardInterrupt:
        await executor.stop()
        logger.info("Executor arrêté par l'utilisateur")

if __name__ == "__main__":
    asyncio.run(main())