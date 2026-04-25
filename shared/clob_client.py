import sys
import io

# Force UTF-8 sur Windows pour éviter les UnicodeEncodeError cp1252
if sys.platform == "win32":
    # sys.stdout non wrappé pour modules importés : conflit lors de l'import
    # sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    # sys.stderr non wrappé : conflit avec argparse / logging stderr handlers
    # Les émojis dans stderr peuvent être moches mais le script fonctionne
    pass

import logging
import time
import aiohttp
import json
from typing import Dict, Optional
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds
from config import Config

# Imports pour web3 direct calls
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)


class CLOBClient:
    """
    Wrapper autour de py-clob-client pour faciliter les trades Polymarket.

    Fonctionnalités:
    - Post des ordres market (BUY seulement, HOLD-TO-RESOLUTION)
    - Gestion des erreurs et retry automatique
    - Logging détaillé pour debugging
    - Respect des limites de sizing du bot
    """

    def __init__(self):
        """Initialise le client CLOB avec la config du .env"""
        try:
            self.client = ClobClient(
                host=Config.CLOB_HOST,
                key=Config.CLOB_PRIVATE_KEY,
                chain_id=int(Config.CLOB_CHAIN_ID),
                signature_type=0  # EOA signature (standard wallet)
            )

            # Charger les credentials API depuis .env
            import os
            from dotenv import load_dotenv
            load_dotenv()

            api_key = os.getenv("CLOB_API_KEY")
            api_secret = os.getenv("CLOB_API_SECRET")
            api_passphrase = os.getenv("CLOB_API_PASSPHRASE")

            if api_key and api_secret and api_passphrase:
                self.client.set_api_creds(ApiCreds(
                    api_key=api_key,
                    api_secret=api_secret,
                    api_passphrase=api_passphrase,
                ))
                logger.info("✅ API credentials loaded")
            else:
                logger.warning(
                    "⚠️ API credentials missing - only public endpoints available. "
                    "Run: python utils/setup_wallet.py --use-existing"
                )

            # Test de connexion
            self._test_connection()

            logger.info(f"✅ CLOB Client initialisé: {Config.CLOB_HOST} (chain {Config.CLOB_CHAIN_ID})")

        except Exception as e:
            logger.error(f"❌ Erreur initialisation CLOB client: {e}")
            raise

    def _test_connection(self):
        """Test basique de connexion à l'API CLOB"""
        try:
            # Test simple: récupérer le statut du serveur
            response = self.client.get_sampling_simplified_markets()
            logger.debug(f"Test connexion CLOB OK: {len(response) if response else 0} marchés")
        except Exception as e:
            logger.error(f"Test connexion CLOB failed: {e}")
            raise

    def _has_api_creds(self) -> bool:
        """Vérifie si les credentials API sont configurés"""
        return bool(Config.CLOB_PRIVATE_KEY and Config.CLOB_PRIVATE_KEY.strip())

    def get_order_book(self, token_id: str) -> Optional[Dict]:
        """Récupère l'order book pour un token donné"""
        try:
            return self.client.get_order_book(token_id=token_id)
        except Exception as e:
            logger.error(f"Erreur get_order_book pour {token_id}: {e}")
            return None

    def get_best_prices(self, token_id: str) -> dict | None:
        """
        Récupère les meilleurs prix (bid/ask) depuis le carnet d'ordres.

        Returns:
            dict avec 'best_bid' et 'best_ask' en float, ou None si erreur
        """
        try:
            book = self.client.get_order_book(token_id)

            # OrderBookSummary est un objet, pas un dict
            bids = book.bids if hasattr(book, 'bids') else []
            asks = book.asks if hasattr(book, 'asks') else []

            if not asks:
                logger.warning(f"Pas d'asks pour {token_id[:10]}...")
                return None

            # Les asks sont triés par prix croissant (le plus bas = meilleur ask)
            # S'il y a doute, prendre le min
            best_ask = min(float(a.price) for a in asks)
            best_bid = max(float(b.price) for b in bids) if bids else 0.0

            return {
                "best_bid": best_bid,
                "best_ask": best_ask,
                "mid_price": (best_bid + best_ask) / 2 if best_bid > 0 else best_ask,
            }
        except Exception as e:
            logger.error(f"Erreur get_best_prices pour {token_id[:10]}...: {e}")
            return None

    def _is_neg_risk_market(self, token_id: str) -> bool:
        """
        Check if a market is neg-risk via multiple methods.

        Daily-temperature weather markets are typically neg-risk type.
        Fallback: assume True for weather markets if API detection fails.
        """
        try:
            import requests

            # Method 1: Try the direct neg-risk API endpoint
            url = f"https://clob.polymarket.com/neg-risk?token_id={token_id}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                is_neg_risk = bool(data.get("neg_risk", False))
                logger.debug(f"API confirmed neg-risk={is_neg_risk} for {token_id[:10]}...")
                return is_neg_risk

            # Method 2: Try via order book or market data API
            # (This could be extended if we find other endpoints)

            # Method 3: Fallback assumption for weather markets
            # Since user stated all daily-temperature markets are neg-risk
            logger.info(f"Could not confirm via API, assuming neg-risk=True for weather market {token_id[:10]}...")
            return True

        except Exception as e:
            logger.warning(f"Neg-risk detection failed for {token_id[:10]}...: {e}")
            # Conservative fallback: assume neg-risk=True for weather markets
            # Better to sign with wrong domain and get rejected than miss the trade
            logger.info("Fallback: assuming neg-risk=True for safety")
            return True

    def _get_tick_size(self, token_id: str) -> float:
        """Récupère le minimum_tick_size du marché via API Polymarket."""
        try:
            import requests
            url = f"https://clob.polymarket.com/tick-size?token_id={token_id}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                tick_size = float(data.get("minimum_tick_size", 0.01))
                logger.debug(f"API returned tick_size={tick_size} for {token_id[:10]}...")
                return tick_size
            else:
                logger.debug(f"Tick-size API returned {response.status_code} for {token_id[:10]}...")
                return 0.01  # Default fallback
        except Exception as e:
            logger.warning(f"Could not fetch tick_size for {token_id[:10]}...: {e}")
            return 0.01  # Conservative fallback

    def _normalize_tick_size(self, ts: float) -> str:
        """Convertit un float tick_size vers le string Literal attendu par le SDK."""
        # Mapping float → Literal string attendu par le SDK py-clob-client
        TICK_SIZE_MAP = {
            0.1: "0.1",
            0.01: "0.01",
            0.001: "0.001",
            0.0001: "0.0001",
        }

        # Arrondir à 4 décimales pour éviter problèmes float
        ts_rounded = round(ts, 4)
        if ts_rounded in TICK_SIZE_MAP:
            return TICK_SIZE_MAP[ts_rounded]

        # Fallback: trouver le plus proche
        closest = min(TICK_SIZE_MAP.keys(), key=lambda k: abs(k - ts_rounded))
        logger.warning(f"tick_size {ts} non standard, fallback sur {TICK_SIZE_MAP[closest]}")
        return TICK_SIZE_MAP[closest]

    def post_market_order(self, token_id: str, size_usdc: float, side: str = "BUY") -> Optional[Dict]:
        """
        Poste un ordre market pour acheter des tokens YES/NO.

        Args:
            token_id: ID du token à trader (string hexadécimal)
            size_usdc: Montant en USDC à investir
            side: "BUY" seulement (HOLD-TO-RESOLUTION strategy)

        Returns:
            dict: Résultat de l'ordre avec order_id, execution details, etc.
            None: Si erreur
        """
        try:
            # Validation des paramètres
            if side != "BUY":
                raise ValueError("Seuls les ordres BUY sont supportés (HOLD-TO-RESOLUTION)")

            if size_usdc < Config.MIN_POSITION_USDC:
                raise ValueError(f"Taille minimum: ${Config.MIN_POSITION_USDC}")

            if size_usdc > Config.MAX_POSITION_USDC:
                raise ValueError(f"Taille maximum: ${Config.MAX_POSITION_USDC}")

            # Récupérer les prix actuels pour calculer la quantité
            prices = self.get_best_prices(token_id)
            if not prices or not prices.get("best_ask"):
                raise ValueError(f"Impossible de récupérer le prix pour {token_id}")

            # Calculer la quantité de tokens à acheter
            # On utilise le ask price (prix de vente) pour notre achat
            price = prices["best_ask"]
            quantity = size_usdc / price

            # Arrondir à 4 décimales (standard Polymarket)
            quantity_decimal = Decimal(str(quantity)).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
            quantity = float(quantity_decimal)

            # Détecter neg-risk et récupérer tick_size (important pour signature EIP-712)
            neg_risk = self._is_neg_risk_market(token_id)
            tick_size_float = self._get_tick_size(token_id)
            tick_size_str = self._normalize_tick_size(tick_size_float)
            logger.info(f"📊 Market neg-risk: {neg_risk} | tick_size: {tick_size_str}")

            # ARRONDIR le prix au tick_size pour cohérence avec signature EIP-712
            # Par ex: prix 0.4723 avec tick 0.01 → 0.47 ; avec tick 0.001 → 0.472
            price_decimal = Decimal(str(price))
            tick_decimal = Decimal(str(tick_size_float))  # Utiliser la valeur float pour le calcul
            price_rounded = float((price_decimal / tick_decimal).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * tick_decimal)

            # Recalculer size tokens avec le prix arrondi
            size_tokens = size_usdc / price_rounded
            size_tokens_decimal = Decimal(str(size_tokens)).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
            size_tokens = float(size_tokens_decimal)

            # Arrondir amount USDC à 2 décimales (limite maker amount)
            amount_usdc_rounded = round(size_usdc, 2)

            logger.info(f"📊 Market neg-risk: {neg_risk} | tick_size: {tick_size_str}")
            logger.info(f"📊 CLOB MARKET ORDER: BUY ${amount_usdc_rounded} USDC @ ~${price_rounded}")

            # Créer l'ordre avec le bon SDK pattern (MarketOrderArgs pour market orders)
            from py_clob_client.clob_types import OrderArgs, MarketOrderArgs, OrderType, PartialCreateOrderOptions
            from py_clob_client.order_builder.constants import BUY

            # MarketOrderArgs (pas OrderArgs !) pour un vrai market order
            market_order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount_usdc_rounded,  # USDC à dépenser, 2 décimales max
                side=BUY,
                price=price_rounded,          # prix indicatif arrondi au tick_size
            )

            # IMPORTANT : passer LES DEUX options (neg_risk ET tick_size) pour signature correcte
            options = PartialCreateOrderOptions(
                neg_risk=neg_risk,
                tick_size=tick_size_str,  # STRING Literal, attendu par le SDK
            )

            # create_market_order (pas create_order !)
            signed_order = self.client.create_market_order(market_order_args, options=options)

            # Étape 2: Poster l'ordre signé (FOK = Fill-Or-Kill market order)
            start_time = time.time()
            result = self.client.post_order(signed_order, OrderType.FOK)
            execution_time = time.time() - start_time

            if result and result.get('success', False):
                logger.info(f"✅ Ordre exécuté en {execution_time:.2f}s: {result.get('orderID', 'unknown')}")

                # Enrichir le résultat avec nos métadonnées
                result['executed_at'] = time.time()
                result['execution_time_seconds'] = execution_time
                result['requested_size_usdc'] = size_usdc
                result['executed_amount_usdc'] = amount_usdc_rounded  # Montant USDC arrondi
                result['executed_price'] = price_rounded  # Prix arrondi au tick_size
                result['estimated_quantity'] = size_tokens  # Quantité estimée (market order)
                result['token_id'] = token_id
                result['neg_risk'] = neg_risk
                result['tick_size'] = tick_size_str
                result['order_type'] = 'MARKET'  # Indiquer que c'est un market order

                return result
            else:
                error_msg = result.get('errorMsg', 'Ordre rejeté sans détails') if result else 'Aucune réponse'
                logger.error(f"❌ Ordre rejeté: {error_msg}")
                logger.error(f"Raw response: {result}")
                return None

        except Exception as e:
            logger.error(f"❌ Erreur post_market_order: {e}")
            return None

    def post_sell_market_order(
        self,
        token_id: str,
        shares: float,
        neg_risk: bool = True,
        tick_size: str = "0.01"
    ) -> dict:
        """
        Vend des shares sur le CLOB en market order FAK.

        Args:
            token_id: ID du token à vendre (YES ou NO)
            shares: Nombre de shares à vendre (sera arrondi à 2 décimales)
            neg_risk: True si le market est neg-risk (défaut True pour markets température)
            tick_size: Tick size du market (défaut "0.01")

        Returns:
            dict avec la réponse CLOB (incluant order_id si succès)

        Raises:
            Exception si l'ordre échoue
        """
        try:
            from py_clob_client.clob_types import MarketOrderArgs, OrderType, PartialCreateOrderOptions
            from py_clob_client.order_builder.constants import SELL

            shares_rounded = round(shares, 2)
            if shares_rounded <= 0:
                raise ValueError(f"Shares à vendre doit être > 0, reçu {shares_rounded}")

            logger.info(
                f"📤 CLOB SELL: {shares_rounded} shares de {token_id[:20]}... "
                f"(neg_risk={neg_risk}, tick={tick_size})"
            )

            market_order = MarketOrderArgs(
                token_id=token_id,
                amount=shares_rounded,
                side=SELL,
                order_type=OrderType.FAK
            )

            options = PartialCreateOrderOptions(
                neg_risk=neg_risk,
                tick_size=tick_size
            )

            start_time = time.time()
            signed_order = self.client.create_market_order(market_order, options=options)
            response = self.client.post_order(signed_order, OrderType.FAK)
            elapsed = time.time() - start_time

            if response and response.get("success"):
                order_id = response.get("orderID", "?")
                logger.info(f"✅ SELL exécuté en {elapsed:.2f}s: {order_id}")

                # Enrichir le résultat avec nos métadonnées
                response['executed_at'] = time.time()
                response['execution_time_seconds'] = elapsed
                response['executed_shares'] = shares_rounded
                response['token_id'] = token_id
                response['neg_risk'] = neg_risk
                response['tick_size'] = tick_size
                response['order_type'] = 'MARKET_SELL'

                return response
            else:
                logger.error(f"❌ SELL échoué: {response}")
                raise Exception(f"SELL order failed: {response}")

        except Exception as e:
            logger.error(f"❌ Erreur post_sell_market_order: {e}")
            raise

    def get_balance_usdc(self) -> Optional[float]:
        """Récupère le solde USDC disponible via appel direct web3"""
        try:
            # Configuration web3 pour Polygon
            w3 = Web3(Web3.HTTPProvider("https://polygon-mainnet.g.alchemy.com/v2/demo"))
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if not w3.is_connected():
                logger.error("Impossible de se connecter à Polygon")
                return None

            # Adresse du contrat USDC.e sur Polygon
            usdc_address = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"

            # ABI minimal pour balanceOf
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function"
                }
            ]

            # Récupérer l'adresse wallet depuis la clé privée
            from eth_account import Account
            account = Account.from_key(Config.CLOB_PRIVATE_KEY)
            wallet_address = account.address

            # Contrat USDC
            usdc_contract = w3.eth.contract(address=usdc_address, abi=erc20_abi)

            # Récupérer le solde en wei
            balance_wei = usdc_contract.functions.balanceOf(wallet_address).call()

            # Récupérer les décimales (USDC = 6 décimales)
            decimals = usdc_contract.functions.decimals().call()

            # Convertir en float
            balance_usdc = balance_wei / (10 ** decimals)

            logger.debug(f"Balance USDC via web3: {balance_usdc:.2f}")
            return balance_usdc

        except Exception as e:
            logger.error(f"Erreur get_balance_usdc via web3: {e}")
            return None

    def get_open_orders(self) -> list:
        """Récupère les ordres ouverts via SDK avec validation credentials"""
        try:
            if not self._has_api_creds():
                logger.warning("Pas de credentials API - impossible de récupérer les ordres")
                return []

            # Utilise la vraie méthode du SDK
            orders = self.client.get_orders() or []
            logger.debug(f"Ordres ouverts via SDK: {len(orders)}")
            return orders

        except Exception as e:
            logger.error(f"Erreur get_open_orders: {e}")
            return []

    def get_positions(self) -> list:
        """Récupère les positions ouvertes via Polymarket Data API"""
        try:
            # Récupérer l'adresse wallet depuis la clé privée
            from eth_account import Account
            account = Account.from_key(Config.CLOB_PRIVATE_KEY)
            wallet_address = account.address.lower()

            # URL de l'API Polymarket Data
            url = f"https://data-api.polymarket.com/positions?user={wallet_address}"

            import requests
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            positions_data = response.json()

            # Filtrer les positions avec une valeur > 0
            active_positions = []
            for pos in positions_data:
                size = float(pos.get('size', 0))
                if size > 0:
                    active_positions.append(pos)

            logger.debug(f"Positions actives via Data API: {len(active_positions)}")
            return active_positions

        except Exception as e:
            logger.error(f"Erreur get_positions via Data API: {e}")
            return []

    def cancel_all_orders(self) -> bool:
        """Annule tous les ordres ouverts (KILL SWITCH)"""
        try:
            orders = self.get_open_orders()
            if not orders:
                logger.info("Aucun ordre à annuler")
                return True

            success_count = 0
            for order in orders:
                order_id = order.get('orderID', order.get('id'))
                if order_id:
                    try:
                        result = self.client.cancel_order(order_id)
                        if result:
                            success_count += 1
                    except Exception as e:
                        logger.error(f"Erreur annulation ordre {order_id}: {e}")

            logger.info(f"🛑 KILL SWITCH: {success_count}/{len(orders)} ordres annulés")
            return success_count == len(orders)

        except Exception as e:
            logger.error(f"Erreur cancel_all_orders: {e}")
            return False

    def health_check(self) -> Dict[str, any]:
        """Vérification de santé du client CLOB"""
        try:
            start_time = time.time()

            # Tests basiques
            balance = self.get_balance_usdc()
            orders = self.get_open_orders()
            positions = self.get_positions()

            response_time = time.time() - start_time

            return {
                'status': 'healthy',
                'response_time_seconds': round(response_time, 3),
                'balance_usdc': balance,
                'open_orders_count': len(orders) if orders else 0,
                'positions_count': len(positions) if positions else 0,
                'timestamp': time.time()
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }


# Instance globale pour usage dans le bot
clob_client = None

def get_clob_client() -> CLOBClient:
    """Factory pour récupérer l'instance CLOB client (singleton pattern)"""
    global clob_client

    if clob_client is None:
        if Config.DRY_RUN:
            logger.info("🔸 Mode DRY_RUN: pas d'initialisation CLOB client")
            return None

        logger.info("Initialisation CLOB client...")
        clob_client = CLOBClient()

    return clob_client


if __name__ == "__main__":
    # Test rapide du client CLOB
    logging.basicConfig(level=logging.INFO)

    try:
        client = CLOBClient()
        health = client.health_check()
        print(f"Health check: {health}")

        balance = client.get_balance_usdc()
        print(f"Balance USDC: ${balance}")

    except Exception as e:
        print(f"Erreur test: {e}")