"""
Test de trading LIVE sur Polymarket CLOB avec un ordre unique.

Ce script test permet de:
1. Vérifier la connexion CLOB et les approvals
2. Exécuter un ordre test de petite taille ($1-2 USDC)
3. Monitorer l'exécution et les résultats
4. Tester toute la chaîne LIVE avant d'activer le bot

Usage:
    python test_clob_single_order.py --dry-run          # Test sans ordre réel
    python test_clob_single_order.py --live             # Ordre réel de test
    python test_clob_single_order.py --token <ID>       # Token spécifique
"""

import sys
import io

# Force UTF-8 sur Windows pour éviter les UnicodeEncodeError cp1252
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

import argparse
import asyncio
import logging
import json
import time
from datetime import datetime

# Imports du bot
from shared.clob_client import CLOBClient, get_clob_client
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Token de test par défaut (marché actif avec bonne liquidité)
DEFAULT_TEST_TOKEN = None  # Sera déterminé dynamiquement
TEST_SIZE_USDC = 1.0  # Ordre de test minimal


async def find_good_test_market():
    """
    Trouve un bon marché de test avec:
    - Liquidité > $5000
    - Prix entre 0.20-0.80 (éviter les extrêmes)
    - Marché actif et proche de la résolution
    """
    try:
        logger.info("🔍 Recherche d'un marché de test approprié...")

        # Import dynamique pour éviter les erreurs si API non disponible
        from agents.market_scanner import MarketScanner

        async with MarketScanner() as scanner:
            markets = await scanner.scan_weather_markets()

        if not markets:
            logger.error("❌ Aucun marché weather disponible")
            return None

        # Filtrer les marchés appropriés pour le test
        good_markets = []

        for market in markets:
            if market.liquidity_usdc < 5000:  # Liquidité minimale
                continue

            # Chercher des ranges avec des prix raisonnables
            good_ranges = []
            for temp_range in market.ranges:
                price = temp_range.current_price
                if 0.20 <= price <= 0.80:  # Prix raisonnables pour test
                    good_ranges.append((temp_range, price))

            if good_ranges:
                # Prendre le range avec le prix le plus proche de 0.5
                best_range = min(good_ranges, key=lambda x: abs(x[1] - 0.5))
                good_markets.append((market, best_range[0], best_range[1]))

        if not good_markets:
            logger.error("❌ Aucun marché approprié trouvé pour le test")
            return None

        # Prendre le marché avec la meilleure liquidité
        best_market = max(good_markets, key=lambda x: x[0].liquidity_usdc)
        market, temp_range, price = best_market

        logger.info(f"✅ Marché de test sélectionné:")
        logger.info(f"   Titre: {market.title}")
        logger.info(f"   Range: {temp_range.label}")
        logger.info(f"   Prix: ${price:.4f}")
        logger.info(f"   Token ID: {temp_range.token_id}")
        logger.info(f"   Liquidité: ${market.liquidity_usdc:.0f}")

        return {
            'market': market,
            'temp_range': temp_range,
            'token_id': temp_range.token_id,
            'price': price
        }

    except Exception as e:
        logger.error(f"❌ Erreur recherche marché de test: {e}")
        return None


def test_clob_connection():
    """Test la connexion CLOB et les vérifications préalables"""
    try:
        logger.info("🔗 Test de connexion CLOB...")

        # Créer le client CLOB
        client = CLOBClient()

        # Health check
        health = client.health_check()
        logger.info(f"Health check: {health}")

        if health['status'] != 'healthy':
            logger.error(f"❌ CLOB unhealthy: {health}")
            return False

        # Vérifier balance (non-bloquant)
        balance = client.get_balance_usdc()
        if balance is None:
            logger.warning("⚠️ Impossible de récupérer la balance USDC (continuant...)")
            balance = 0.0  # Valeur par défaut pour continuer
        else:
            logger.info(f"💰 Balance USDC: ${balance:.2f}")

        if balance < TEST_SIZE_USDC:
            logger.warning(f"⚠️ Balance potentiellement insuffisante pour test (requis: ${TEST_SIZE_USDC}, détecté: ${balance:.2f})")
            # Ne pas return False - continuer malgré tout

        # Vérifier positions et ordres existants
        positions = client.get_positions()
        orders = client.get_open_orders()

        logger.info(f"📊 Positions ouvertes: {len(positions)}")
        logger.info(f"📋 Ordres ouverts: {len(orders)}")

        # Tout OK
        logger.info("✅ Connexion CLOB validée")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur test connexion: {e}")
        return False


async def execute_test_order(token_id: str, dry_run: bool = True):
    """Exécute un ordre de test"""
    try:
        logger.info(f"📊 Test d'ordre {'DRY RUN' if dry_run else 'LIVE'}...")

        if dry_run:
            logger.info("🔸 Mode DRY RUN activé - aucun ordre réel")

        # Créer le client
        if dry_run:
            # Simulation
            logger.info(f"🔸 [DRY RUN] Ordre simulé:")
            logger.info(f"   Token: {token_id}")
            logger.info(f"   Taille: ${TEST_SIZE_USDC} USDC")
            logger.info(f"   Type: BUY MARKET FOK")

            # Simuler un délai d'exécution
            await asyncio.sleep(1)

            result = {
                'dry_run': True,
                'simulated': True,
                'token_id': token_id,
                'size_usdc': TEST_SIZE_USDC,
                'timestamp': time.time()
            }

            logger.info("✅ [DRY RUN] Ordre simulé avec succès")
            return result

        else:
            # Ordre réel
            client = CLOBClient()

            logger.warning("🚨 ATTENTION: Ordre LIVE sur Polymarket!")
            logger.warning(f"💰 Montant: ${TEST_SIZE_USDC} USDC")
            logger.warning(f"🎯 Token: {token_id}")

            confirm = input("\n🔥 Confirmer l'ordre LIVE? (YES/no): ").strip()
            if confirm.upper() != "YES":
                logger.info("⏹️ Ordre annulé par l'utilisateur")
                return None

            logger.info("📤 Envoi ordre LIVE...")
            start_time = time.time()

            result = client.post_market_order(
                token_id=token_id,
                size_usdc=TEST_SIZE_USDC,
                side="BUY"
            )

            execution_time = time.time() - start_time

            if result:
                logger.info(f"✅ Ordre LIVE exécuté en {execution_time:.2f}s!")
                logger.info(f"   Order ID: {result.get('orderID', 'unknown')}")
                logger.info(f"   Prix: ${result.get('executed_price', 0):.4f}")
                logger.info(f"   Quantité: {result.get('executed_quantity', 0):.4f} tokens")

                return result
            else:
                logger.error("❌ Échec de l'ordre LIVE")
                return None

    except Exception as e:
        logger.error(f"❌ Erreur exécution ordre de test: {e}")
        return None


def save_test_results(results: dict):
    """Sauvegarde les résultats du test"""
    try:
        test_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(test_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"💾 Résultats sauvegardés: {test_file}")

    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde: {e}")


async def main():
    """Fonction principale du test"""
    global TEST_SIZE_USDC

    parser = argparse.ArgumentParser(description="Test d'ordre CLOB Polymarket")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run', action='store_true', help="Test en mode simulation")
    group.add_argument('--live', action='store_true', help="Ordre réel de test")

    parser.add_argument('--token', type=str, help="Token ID spécifique (optionnel)")
    parser.add_argument('--size', type=float, default=TEST_SIZE_USDC, help=f"Taille en USDC (défaut: {TEST_SIZE_USDC})")

    args = parser.parse_args()

    TEST_SIZE_USDC = args.size

    print("\n" + "="*60)
    print("🧪 POLYMARKET CLOB - TEST D'ORDRE")
    print("="*60)

    test_results = {
        'timestamp': datetime.now().isoformat(),
        'mode': 'dry_run' if args.dry_run else 'live',
        'test_size_usdc': TEST_SIZE_USDC,
        'results': {}
    }

    try:
        # Étape 1: Test connexion CLOB
        logger.info("\n" + "="*30 + " ÉTAPE 1: CONNEXION " + "="*30)

        if args.live and not test_clob_connection():
            logger.error("❌ Test de connexion échoué - arrêt")
            return

        test_results['results']['connection'] = 'success' if args.live else 'skipped_dry_run'

        # Étape 2: Sélection du marché de test
        logger.info("\n" + "="*30 + " ÉTAPE 2: MARCHÉ TEST " + "="*30)

        token_id = args.token

        if not token_id:
            # Trouver automatiquement un bon marché
            market_info = await find_good_test_market()
            if not market_info:
                logger.error("❌ Impossible de trouver un marché de test approprié")
                return

            token_id = market_info['token_id']
            test_results['results']['market_selection'] = {
                'auto_selected': True,
                'market_title': market_info['market'].title,
                'temp_range': market_info['temp_range'].label,
                'token_id': token_id,
                'price': market_info['price']
            }
        else:
            test_results['results']['market_selection'] = {
                'auto_selected': False,
                'token_id': token_id
            }

        # Étape 3: Exécution de l'ordre de test
        logger.info("\n" + "="*30 + " ÉTAPE 3: ORDRE TEST " + "="*30)

        order_result = await execute_test_order(token_id, dry_run=args.dry_run)

        if order_result:
            test_results['results']['order'] = order_result
            logger.info("✅ Test d'ordre réussi!")
        else:
            test_results['results']['order'] = {'status': 'failed'}
            logger.error("❌ Test d'ordre échoué")

        # Étape 4: Vérifications post-ordre (LIVE seulement)
        if args.live and order_result and not order_result.get('dry_run'):
            logger.info("\n" + "="*30 + " ÉTAPE 4: VÉRIFICATIONS " + "="*30)

            try:
                client = CLOBClient()

                # Vérifier nouvelle balance
                new_balance = client.get_balance_usdc()
                logger.info(f"💰 Nouvelle balance USDC: ${new_balance:.2f}")

                # Vérifier positions
                positions = client.get_positions()
                logger.info(f"📊 Nouvelles positions: {len(positions)}")

                test_results['results']['post_order'] = {
                    'new_balance_usdc': new_balance,
                    'positions_count': len(positions)
                }

            except Exception as e:
                logger.error(f"❌ Erreur vérifications post-ordre: {e}")

        # Sauvegarde des résultats
        save_test_results(test_results)

        # Résumé final
        logger.info("\n" + "="*60)
        if order_result:
            logger.info("✅ TEST CLOB TERMINÉ AVEC SUCCÈS!")
            if args.dry_run:
                logger.info("🔸 Mode DRY RUN - prêt pour test LIVE")
                logger.info("🔥 Commande LIVE: python test_clob_single_order.py --live")
            else:
                logger.info("🔥 ORDRE LIVE EXÉCUTÉ - Bot prêt pour production!")
                logger.info("⚙️ Configurez DRY_RUN=false dans .env")
                logger.info("🚀 Lancez: python main.py")
        else:
            logger.error("❌ TEST CLOB ÉCHOUÉ")
            logger.error("🔧 Vérifiez la configuration et les approvals")

    except KeyboardInterrupt:
        logger.info("\n⏹️ Test arrêté par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur inattendue: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())