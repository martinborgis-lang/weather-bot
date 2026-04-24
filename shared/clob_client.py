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
from decimal import Decimal, ROUND_DOWN

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
                signature_type=2  # EOA signature (standard wallet)
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

            logger.info(f"📊 CLOB ORDER: {side} {quantity:.4f} tokens @ ${price:.4f} = ${size_usdc:.2f}")

            # Créer l'ordre avec le bon SDK pattern (2 étapes)
            from py_clob_client.clob_types import OrderArgs, OrderType
            from py_clob_client.order_builder.constants import BUY

            # Étape 1: Créer et signer l'ordre localement
            order_args = OrderArgs(
                price=price,
                size=quantity,
                side=BUY,
                token_id=token_id,
            )
            signed_order = self.client.create_order(order_args)

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
                result['executed_price'] = price
                result['executed_quantity'] = quantity
                result['token_id'] = token_id

                return result
            else:
                error_msg = result.get('errorMsg', 'Ordre rejeté sans détails') if result else 'Aucune réponse'
                logger.error(f"❌ Ordre rejeté: {error_msg}")
                logger.error(f"Raw response: {result}")
                return None

        except Exception as e:
            logger.error(f"❌ Erreur post_market_order: {e}")
            return None

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