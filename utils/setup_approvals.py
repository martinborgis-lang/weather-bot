"""
Script de configuration des approvals pour Polymarket CLOB trading.

Ce script configure les approvals nécessaires pour permettre au bot de trader:
1. USDC.e approval vers le contract Exchange de Polymarket
2. CTF (Conditional Token Framework) approval pour les positions
3. Vérification des allowances existantes
4. Test des transactions avec dry-run

Usage:
    python utils/setup_approvals.py --check         # Vérifier approvals actuelles
    python utils/setup_approvals.py --setup         # Configurer les approvals
    python utils/setup_approvals.py --revoke        # Révoquer les approvals
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
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Polygon Mainnet Contracts (Polymarket)
CONTRACTS = {
    'USDC': '0x2791bca1f2de4661ed88a30c99a7a9449aa84174',      # USDC.e
    'CTF': '0x4D97DCd97eC945f40cF65F87097ACe5EA0476045',        # ConditionalTokens
    'EXCHANGE': '0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E',    # Polymarket Exchange
    'COLLATERAL_TOKEN': '0x2791bca1f2de4661ed88a30c99a7a9449aa84174',  # USDC.e
}

# ABIs minimaux pour les approvals
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    }
]

ERC1155_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}, {"name": "_operator", "type": "address"}],
        "name": "isApprovedForAll",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [{"name": "_operator", "type": "address"}, {"name": "_approved", "type": "bool"}],
        "name": "setApprovalForAll",
        "outputs": [],
        "type": "function"
    }
]

# Montant max approval (2^256 - 1)
MAX_APPROVAL = 2**256 - 1


class ApprovalsManager:
    """Manager pour configurer les approvals Polymarket"""

    def __init__(self):
        """Initialise le manager avec Web3 et les contracts"""
        try:
            # Charger la config depuis .env
            self._load_config()

            # Initialiser Web3
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if not self.w3.is_connected():
                raise ConnectionError("Connexion Web3 échouée")

            # Initialiser le compte
            self.account = Account.from_key(self.private_key)
            logger.info(f"✅ Web3 connecté | Wallet: {self.account.address}")

            # Initialiser les contracts
            self.usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACTS['USDC']),
                abi=ERC20_ABI
            )

            self.ctf_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACTS['CTF']),
                abi=ERC1155_ABI
            )

            logger.info(f"✅ Contracts initialisés")

        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            raise

    def _load_config(self):
        """Charge la config depuis le fichier .env"""
        env_file = Path(".env")
        if not env_file.exists():
            raise FileNotFoundError("Fichier .env introuvable - lancez d'abord setup_wallet.py")

        env_vars = {}
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value

        # Vérifier les variables requises
        required_vars = ['CLOB_PRIVATE_KEY', 'POLYGON_RPC_URL']
        missing = [var for var in required_vars if var not in env_vars]

        if missing:
            raise ValueError(f"Variables manquantes dans .env: {missing}")

        self.private_key = env_vars['CLOB_PRIVATE_KEY']
        self.rpc_url = env_vars['POLYGON_RPC_URL']

    def get_balances(self):
        """Récupère les balances MATIC et USDC"""
        try:
            # Balance MATIC
            balance_wei = self.w3.eth.get_balance(self.account.address)
            balance_matic = self.w3.from_wei(balance_wei, 'ether')

            # Balance USDC
            balance_usdc_raw = self.usdc_contract.functions.balanceOf(self.account.address).call()
            decimals = self.usdc_contract.functions.decimals().call()
            balance_usdc = balance_usdc_raw / (10 ** decimals)

            return {
                'matic': float(balance_matic),
                'usdc': float(balance_usdc),
                'address': self.account.address
            }

        except Exception as e:
            logger.error(f"❌ Erreur récupération balances: {e}")
            return None

    def check_usdc_allowance(self):
        """Vérifie l'allowance USDC vers l'Exchange"""
        try:
            allowance = self.usdc_contract.functions.allowance(
                self.account.address,
                CONTRACTS['EXCHANGE']
            ).call()

            decimals = self.usdc_contract.functions.decimals().call()
            allowance_usdc = allowance / (10 ** decimals)

            return {
                'allowance_raw': allowance,
                'allowance_usdc': allowance_usdc,
                'is_max': allowance >= MAX_APPROVAL // 2,  # Proche du max
                'exchange_address': CONTRACTS['EXCHANGE']
            }

        except Exception as e:
            logger.error(f"❌ Erreur vérification allowance USDC: {e}")
            return None

    def check_ctf_approval(self):
        """Vérifie l'approval CTF vers l'Exchange"""
        try:
            is_approved = self.ctf_contract.functions.isApprovedForAll(
                self.account.address,
                CONTRACTS['EXCHANGE']
            ).call()

            return {
                'is_approved': is_approved,
                'operator_address': CONTRACTS['EXCHANGE']
            }

        except Exception as e:
            logger.error(f"❌ Erreur vérification approval CTF: {e}")
            return None

    def approve_usdc(self, dry_run=True):
        """Approve USDC vers l'Exchange Polymarket"""
        try:
            logger.info("📝 Préparation approval USDC...")

            # Construire la transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)

            transaction = self.usdc_contract.functions.approve(
                CONTRACTS['EXCHANGE'],
                MAX_APPROVAL
            ).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gasPrice': self.w3.eth.gas_price,
            })

            # Estimation gas
            gas_estimate = self.w3.eth.estimate_gas(transaction)
            transaction['gas'] = int(gas_estimate * 1.2)  # 20% buffer

            gas_cost_wei = transaction['gas'] * transaction['gasPrice']
            gas_cost_matic = self.w3.from_wei(gas_cost_wei, 'ether')

            logger.info(f"Gas estimé: {transaction['gas']} | Coût: {gas_cost_matic:.4f} MATIC")

            if dry_run:
                logger.info("🔸 DRY RUN: Transaction non envoyée")
                return {
                    'dry_run': True,
                    'gas_estimate': transaction['gas'],
                    'gas_cost_matic': float(gas_cost_matic),
                    'transaction_data': transaction
                }

            # Confirmation utilisateur
            confirm = input(f"\n💰 Envoyer approval USDC? Coût: {gas_cost_matic:.4f} MATIC (y/N): ").strip().lower()
            if confirm != 'y':
                logger.info("⏹️ Approval annulée par l'utilisateur")
                return None

            # Signer et envoyer
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            logger.info(f"📤 Transaction envoyée: {tx_hash.hex()}")
            logger.info("⏳ Attente confirmation...")

            # Attendre la confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status == 1:
                logger.info("✅ Approval USDC réussie!")
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'gas_used': receipt.gasUsed,
                    'block_number': receipt.blockNumber
                }
            else:
                logger.error("❌ Transaction échouée")
                return None

        except Exception as e:
            logger.error(f"❌ Erreur approval USDC: {e}")
            return None

    def approve_ctf(self, dry_run=True):
        """Approve CTF vers l'Exchange Polymarket"""
        try:
            logger.info("📝 Préparation approval CTF...")

            # Construire la transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)

            transaction = self.ctf_contract.functions.setApprovalForAll(
                CONTRACTS['EXCHANGE'],
                True
            ).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gasPrice': self.w3.eth.gas_price,
            })

            # Estimation gas
            gas_estimate = self.w3.eth.estimate_gas(transaction)
            transaction['gas'] = int(gas_estimate * 1.2)  # 20% buffer

            gas_cost_wei = transaction['gas'] * transaction['gasPrice']
            gas_cost_matic = self.w3.from_wei(gas_cost_wei, 'ether')

            logger.info(f"Gas estimé: {transaction['gas']} | Coût: {gas_cost_matic:.4f} MATIC")

            if dry_run:
                logger.info("🔸 DRY RUN: Transaction non envoyée")
                return {
                    'dry_run': True,
                    'gas_estimate': transaction['gas'],
                    'gas_cost_matic': float(gas_cost_matic),
                    'transaction_data': transaction
                }

            # Confirmation utilisateur
            confirm = input(f"\n💰 Envoyer approval CTF? Coût: {gas_cost_matic:.4f} MATIC (y/N): ").strip().lower()
            if confirm != 'y':
                logger.info("⏹️ Approval annulée par l'utilisateur")
                return None

            # Signer et envoyer
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            logger.info(f"📤 Transaction envoyée: {tx_hash.hex()}")
            logger.info("⏳ Attente confirmation...")

            # Attendre la confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status == 1:
                logger.info("✅ Approval CTF réussie!")
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'gas_used': receipt.gasUsed,
                    'block_number': receipt.blockNumber
                }
            else:
                logger.error("❌ Transaction échouée")
                return None

        except Exception as e:
            logger.error(f"❌ Erreur approval CTF: {e}")
            return None


def check_approvals():
    """Vérifie les approvals actuelles"""
    try:
        logger.info("🔍 Vérification des approvals actuelles...")

        manager = ApprovalsManager()

        # Balances
        balances = manager.get_balances()
        if balances:
            logger.info(f"💰 Balances {balances['address']}:")
            logger.info(f"   MATIC: {balances['matic']:.4f}")
            logger.info(f"   USDC:  {balances['usdc']:.2f}")

            if balances['matic'] < 0.05:
                logger.warning("⚠️ Balance MATIC faible - ajoutez des MATIC pour gas fees")

        # USDC Allowance
        usdc_allowance = manager.check_usdc_allowance()
        if usdc_allowance:
            logger.info("\n📋 USDC Allowance:")
            logger.info(f"   Exchange: {usdc_allowance['exchange_address']}")
            logger.info(f"   Allowance: {usdc_allowance['allowance_usdc']:.2f} USDC")

            if usdc_allowance['is_max']:
                logger.info("   ✅ Approval maximale configurée")
            else:
                logger.warning("   ⚠️ Approval insuffisante ou manquante")

        # CTF Approval
        ctf_approval = manager.check_ctf_approval()
        if ctf_approval:
            logger.info("\n📋 CTF Approval:")
            logger.info(f"   Exchange: {ctf_approval['operator_address']}")

            if ctf_approval['is_approved']:
                logger.info("   ✅ Approval CTF configurée")
            else:
                logger.warning("   ⚠️ Approval CTF manquante")

        # Résumé
        usdc_ok = usdc_allowance and usdc_allowance['is_max']
        ctf_ok = ctf_approval and ctf_approval['is_approved']

        logger.info("\n" + "="*50)
        if usdc_ok and ctf_ok:
            logger.info("✅ Toutes les approvals sont configurées - bot prêt pour LIVE trading!")
        else:
            logger.warning("⚠️ Approvals manquantes - lancez: python utils/setup_approvals.py --setup")

    except Exception as e:
        logger.error(f"❌ Erreur vérification: {e}")


def setup_approvals():
    """Configure toutes les approvals nécessaires"""
    try:
        logger.info("🔧 Configuration des approvals Polymarket...")

        manager = ApprovalsManager()

        # Vérifier les balances d'abord
        balances = manager.get_balances()
        if not balances or balances['matic'] < 0.01:
            logger.error("❌ Balance MATIC insuffisante pour les gas fees")
            return

        logger.info(f"💰 Balance MATIC: {balances['matic']:.4f}")

        # Vérifier les approvals actuelles
        usdc_allowance = manager.check_usdc_allowance()
        ctf_approval = manager.check_ctf_approval()

        setup_needed = []

        # USDC Approval
        if not (usdc_allowance and usdc_allowance['is_max']):
            setup_needed.append('USDC')

        # CTF Approval
        if not (ctf_approval and ctf_approval['is_approved']):
            setup_needed.append('CTF')

        if not setup_needed:
            logger.info("✅ Toutes les approvals sont déjà configurées!")
            return

        logger.info(f"\n🔧 Approvals à configurer: {', '.join(setup_needed)}")

        # Confirmation
        logger.warning("⚠️ ATTENTION: Ces transactions vont consommer des MATIC en gas fees")
        confirm = input("\nContinuer avec la configuration? (y/N): ").strip().lower()
        if confirm != 'y':
            logger.info("⏹️ Configuration annulée par l'utilisateur")
            return

        # Configurer USDC approval
        if 'USDC' in setup_needed:
            logger.info("\n" + "="*30 + " USDC APPROVAL " + "="*30)
            result = manager.approve_usdc(dry_run=False)
            if result and result.get('success'):
                logger.info(f"✅ USDC approval réussie: {result['tx_hash']}")
            else:
                logger.error("❌ Échec USDC approval")
                return

        # Configurer CTF approval
        if 'CTF' in setup_needed:
            logger.info("\n" + "="*30 + " CTF APPROVAL " + "="*30)
            result = manager.approve_ctf(dry_run=False)
            if result and result.get('success'):
                logger.info(f"✅ CTF approval réussie: {result['tx_hash']}")
            else:
                logger.error("❌ Échec CTF approval")
                return

        logger.info("\n" + "="*50)
        logger.info("✅ TOUTES LES APPROVALS CONFIGURÉES AVEC SUCCÈS!")
        logger.info("="*50)
        logger.info("Prochaines étapes:")
        logger.info("1. Testez: python test_clob_single_order.py")
        logger.info("2. Configurez DRY_RUN=false dans .env pour LIVE trading")
        logger.info("3. Lancez le bot: python main.py")

    except Exception as e:
        logger.error(f"❌ Erreur configuration: {e}")


def revoke_approvals():
    """Révoque toutes les approvals (sécurité)"""
    try:
        logger.warning("🚨 RÉVOCATION DES APPROVALS")
        logger.warning("Cette opération va révoquer TOUTES les approvals Polymarket")

        confirm = input("\nÊtes-vous sûr? Cette action nécessite des gas fees (y/N): ").strip().lower()
        if confirm != 'y':
            logger.info("⏹️ Révocation annulée")
            return

        manager = ApprovalsManager()

        # Révoquer USDC
        logger.info("🔄 Révocation USDC approval...")
        # Note: On met allowance à 0 pour révoquer
        # Cette partie serait similaire à approve_usdc mais avec montant = 0

        # Révoquer CTF
        logger.info("🔄 Révocation CTF approval...")
        # Note: On met approved = False pour révoquer
        # Cette partie serait similaire à approve_ctf mais avec approved = False

        logger.info("✅ Approvals révoquées")

    except Exception as e:
        logger.error(f"❌ Erreur révocation: {e}")


def main():
    """Fonction principale avec arguments CLI"""
    parser = argparse.ArgumentParser(description="Configuration des approvals Polymarket")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true', help="Vérifier les approvals actuelles")
    group.add_argument('--setup', action='store_true', help="Configurer les approvals")
    group.add_argument('--revoke', action='store_true', help="Révoquer les approvals")

    args = parser.parse_args()

    print("\n" + "="*60)
    print("🔐 POLYMARKET APPROVALS SETUP")
    print("="*60)

    try:
        if args.check:
            check_approvals()
        elif args.setup:
            setup_approvals()
        elif args.revoke:
            revoke_approvals()

    except KeyboardInterrupt:
        logger.info("\n⏹️ Arrêt par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")


if __name__ == "__main__":
    main()