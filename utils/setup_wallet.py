"""
Script d'initialisation du wallet pour Polymarket CLOB trading.

Ce script aide à:
1. Créer un nouveau wallet Ethereum (ou utiliser existant)
2. Générer les clés API nécessaires pour py-clob-client
3. Vérifier la configuration et les balances
4. Mettre à jour le .env automatiquement

Usage:
    python utils/setup_wallet.py --generate-new    # Créer nouveau wallet
    python utils/setup_wallet.py --use-existing    # Utiliser wallet existant
    python utils/setup_wallet.py --check           # Vérifier config actuelle
"""

import sys
import io

# Force UTF-8 sur Windows pour éviter les UnicodeEncodeError cp1252
if sys.platform == "win32":
    # sys.stdout non wrappé pour scripts interactifs : conflit avec argparse
    # sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    # sys.stderr non wrappé : conflit avec argparse / logging stderr handlers
    # Les émojis dans stderr peuvent être moches mais le script fonctionne
    pass

import argparse
import os
import logging
from pathlib import Path
from eth_account import Account
from web3 import Web3

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
ENV_FILE = Path(".env")
POLYGON_RPC = "https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY"
CLOB_HOST_MAINNET = "https://clob.polymarket.com"
CLOB_HOST_TESTNET = "https://clob-staging.polymarket.com"
CHAIN_ID_POLYGON = 137
USDC_CONTRACT_POLYGON = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"  # USDC.e sur Polygon


def generate_new_wallet():
    """Génère un nouveau wallet Ethereum avec clé privée et adresse"""
    try:
        logger.info("🔑 Génération d'un nouveau wallet Ethereum...")

        # Créer un nouveau compte
        account = Account.create()
        private_key = account.key.hex()
        address = account.address

        logger.info(f"✅ Nouveau wallet créé:")
        logger.info(f"   Adresse: {address}")
        logger.info(f"   Clé privée: {private_key}")

        logger.warning("⚠️  IMPORTANT: Sauvegardez cette clé privée en sécurité!")
        logger.warning("⚠️  Ne partagez JAMAIS votre clé privée!")

        return private_key, address

    except Exception as e:
        logger.error(f"❌ Erreur génération wallet: {e}")
        return None, None


def get_existing_wallet():
    """Récupère les infos d'un wallet existant depuis une clé privée"""
    try:
        print("\n" + "="*50)
        print("CONFIGURATION WALLET EXISTANT")
        print("="*50)

        while True:
            private_key = input("Entrez votre clé privée (0x...): ").strip()

            if not private_key:
                logger.error("❌ Clé privée requise")
                continue

            if not private_key.startswith('0x'):
                private_key = '0x' + private_key

            try:
                # Valider la clé privée
                account = Account.from_key(private_key)
                address = account.address

                logger.info(f"✅ Wallet validé:")
                logger.info(f"   Adresse: {address}")

                return private_key, address

            except Exception as e:
                logger.error(f"❌ Clé privée invalide: {e}")
                retry = input("Réessayer? (y/n): ").strip().lower()
                if retry != 'y':
                    return None, None

    except KeyboardInterrupt:
        logger.info("\n⏹️ Arrêt par l'utilisateur")
        return None, None


def check_wallet_balance(address: str, rpc_url: str = None):
    """Vérifie les balances MATIC et USDC d'un wallet"""
    try:
        if not rpc_url:
            logger.warning("⚠️ RPC URL non configurée, skip vérification balance")
            return

        logger.info(f"💰 Vérification balances pour {address}...")

        # Connexion Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            logger.error("❌ Connexion Web3 échouée")
            return

        # Balance MATIC
        balance_wei = w3.eth.get_balance(address)
        balance_matic = w3.from_wei(balance_wei, 'ether')

        logger.info(f"   MATIC: {balance_matic:.4f}")

        # Balance USDC (nécessite ABI mais on fait simple)
        logger.info(f"   USDC: Vérifiez manuellement sur Polygonscan")
        logger.info(f"   Contract USDC.e: {USDC_CONTRACT_POLYGON}")

        # Recommandations
        if balance_matic < 0.1:
            logger.warning("⚠️ Balance MATIC faible (<0.1) - ajoutez des MATIC pour les gas fees")
        else:
            logger.info("✅ Balance MATIC suffisante pour les gas fees")

    except Exception as e:
        logger.error(f"❌ Erreur vérification balance: {e}")


def update_env_file(private_key: str, address: str):
    """Met à jour le fichier .env avec les nouvelles configurations"""
    try:
        logger.info("📝 Mise à jour du fichier .env...")

        # Lire le .env existant
        env_content = []
        if ENV_FILE.exists():
            with open(ENV_FILE, 'r') as f:
                env_content = f.readlines()

        # Variables à ajouter/mettre à jour
        new_vars = {
            'CLOB_PRIVATE_KEY': private_key,
            'CLOB_HOST': CLOB_HOST_MAINNET,
            'CLOB_CHAIN_ID': str(CHAIN_ID_POLYGON),
            'WALLET_ADDRESS': address,
        }

        # Mettre à jour ou ajouter les variables
        updated_vars = set()
        for i, line in enumerate(env_content):
            if '=' in line and not line.strip().startswith('#'):
                var_name = line.split('=')[0].strip()
                if var_name in new_vars:
                    env_content[i] = f"{var_name}={new_vars[var_name]}\n"
                    updated_vars.add(var_name)

        # Ajouter les nouvelles variables
        for var_name, value in new_vars.items():
            if var_name not in updated_vars:
                env_content.append(f"{var_name}={value}\n")

        # Sauvegarder
        with open(ENV_FILE, 'w') as f:
            f.writelines(env_content)

        logger.info("✅ Fichier .env mis à jour avec succès")

        # Afficher les variables ajoutées
        logger.info("Variables CLOB ajoutées:")
        for var_name, value in new_vars.items():
            if var_name == 'CLOB_PRIVATE_KEY':
                logger.info(f"   {var_name}={value[:10]}...{value[-4:]}")
            else:
                logger.info(f"   {var_name}={value}")

    except Exception as e:
        logger.error(f"❌ Erreur mise à jour .env: {e}")


def check_current_config():
    """Vérifie la configuration actuelle du wallet"""
    try:
        logger.info("🔍 Vérification configuration actuelle...")

        if not ENV_FILE.exists():
            logger.error("❌ Fichier .env introuvable")
            return

        # Lire les variables d'environnement
        with open(ENV_FILE, 'r') as f:
            env_vars = {}
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value

        # Vérifier les variables CLOB
        clob_vars = ['CLOB_PRIVATE_KEY', 'CLOB_HOST', 'CLOB_CHAIN_ID', 'WALLET_ADDRESS']

        logger.info("Configuration CLOB:")
        all_present = True

        for var in clob_vars:
            if var in env_vars:
                value = env_vars[var]
                if var == 'CLOB_PRIVATE_KEY' and value:
                    logger.info(f"   ✅ {var}: {value[:10]}...{value[-4:]}")
                else:
                    logger.info(f"   ✅ {var}: {value}")
            else:
                logger.error(f"   ❌ {var}: NON CONFIGURÉ")
                all_present = False

        if all_present:
            logger.info("✅ Configuration CLOB complète")

            # Test de validation du wallet
            private_key = env_vars.get('CLOB_PRIVATE_KEY')
            if private_key:
                try:
                    account = Account.from_key(private_key)
                    logger.info(f"✅ Wallet validé: {account.address}")

                    # Vérifier balance si RPC disponible
                    polygon_rpc = env_vars.get('POLYGON_RPC_URL')
                    if polygon_rpc:
                        check_wallet_balance(account.address, polygon_rpc)

                except Exception as e:
                    logger.error(f"❌ Wallet invalide: {e}")
        else:
            logger.error("❌ Configuration CLOB incomplète - utilisez --generate-new ou --use-existing")

    except Exception as e:
        logger.error(f"❌ Erreur vérification config: {e}")


def main():
    """Fonction principale avec arguments CLI"""
    parser = argparse.ArgumentParser(description="Setup wallet pour Polymarket CLOB trading")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--generate-new', action='store_true', help="Générer un nouveau wallet")
    group.add_argument('--use-existing', action='store_true', help="Utiliser un wallet existant")
    group.add_argument('--check', action='store_true', help="Vérifier la configuration actuelle")

    args = parser.parse_args()

    print("\n" + "="*60)
    print("🏛️ POLYMARKET CLOB WALLET SETUP")
    print("="*60)

    try:
        if args.check:
            check_current_config()

        elif args.generate_new:
            logger.warning("⚠️  ATTENTION: Un nouveau wallet sera créé")
            logger.warning("⚠️  Vous devrez y transférer des MATIC (gas) et USDC.e (trading)")

            confirm = input("\nContinuer? (y/N): ").strip().lower()
            if confirm != 'y':
                logger.info("⏹️ Arrêt par l'utilisateur")
                return

            private_key, address = generate_new_wallet()
            if private_key and address:
                update_env_file(private_key, address)

                logger.info("\n" + "="*50)
                logger.info("✅ SETUP TERMINÉ")
                logger.info("="*50)
                logger.info("Prochaines étapes:")
                logger.info("1. Transférez des MATIC vers cette adresse (pour gas fees)")
                logger.info("2. Transférez des USDC.e vers cette adresse (pour trading)")
                logger.info("3. Lancez: python utils/setup_approvals.py")
                logger.info("4. Testez: python test_clob_single_order.py")

        elif args.use_existing:
            private_key, address = get_existing_wallet()
            if private_key and address:
                update_env_file(private_key, address)

                logger.info("\n" + "="*50)
                logger.info("✅ SETUP TERMINÉ")
                logger.info("="*50)
                logger.info("Prochaines étapes:")
                logger.info("1. Vérifiez vos balances MATIC et USDC.e")
                logger.info("2. Lancez: python utils/setup_approvals.py")
                logger.info("3. Testez: python test_clob_single_order.py")

    except KeyboardInterrupt:
        logger.info("\n⏹️ Arrêt par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")


if __name__ == "__main__":
    main()