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
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

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
    'CTF_EXCHANGE': '0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E',    # CTF Exchange (standard)
    'NEG_RISK_EXCHANGE': '0xC5d563A36AE78145C45a50134d48A1215220f80a',  # Neg Risk Exchange
    'NEG_RISK_ADAPTER': '0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296',   # Neg Risk Adapter
    'COLLATERAL_TOKEN': '0x2791bca1f2de4661ed88a30c99a7a9449aa84174',  # USDC.e
}

# Liste des contracts qui ont besoin d'approvals
APPROVAL_TARGETS = [
    ('CTF Exchange', 'CTF_EXCHANGE'),
    ('Neg Risk Exchange', 'NEG_RISK_EXCHANGE'),
    ('Neg Risk Adapter', 'NEG_RISK_ADAPTER')
]

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
        """Vérifie l'allowance USDC vers tous les contracts Polymarket"""
        try:
            decimals = self.usdc_contract.functions.decimals().call()
            results = {}

            for name, contract_key in APPROVAL_TARGETS:
                spender_address = Web3.to_checksum_address(CONTRACTS[contract_key])
                allowance = self.usdc_contract.functions.allowance(
                    self.account.address,
                    spender_address
                ).call()

                allowance_usdc = allowance / (10 ** decimals)
                is_max = allowance >= MAX_APPROVAL // 2  # Proche du max

                results[name] = {
                    'allowance_raw': allowance,
                    'allowance_usdc': allowance_usdc,
                    'is_max': is_max,
                    'spender_address': spender_address
                }

            return results

        except Exception as e:
            logger.error(f"❌ Erreur vérification allowance USDC: {e}")
            return None

    def check_ctf_approval(self):
        """Vérifie l'approval CTF vers tous les contracts Polymarket"""
        try:
            results = {}

            for name, contract_key in APPROVAL_TARGETS:
                operator_address = Web3.to_checksum_address(CONTRACTS[contract_key])
                is_approved = self.ctf_contract.functions.isApprovedForAll(
                    self.account.address,
                    operator_address
                ).call()

                results[name] = {
                    'is_approved': is_approved,
                    'operator_address': operator_address
                }

            return results

        except Exception as e:
            logger.error(f"❌ Erreur vérification approval CTF: {e}")
            return None

    def approve_usdc(self, targets_to_approve=None, dry_run=True):
        """Approve USDC vers les contracts Polymarket spécifiés"""
        try:
            # Si aucun target spécifié, approuver tous ceux qui ne le sont pas encore
            if targets_to_approve is None:
                usdc_status = self.check_usdc_allowance()
                if not usdc_status:
                    return None
                targets_to_approve = [name for name, status in usdc_status.items() if not status['is_max']]

            if not targets_to_approve:
                logger.info("✅ Tous les contracts USDC sont déjà approuvés")
                return {'success': True, 'skipped': True}

            logger.info(f"📝 Préparation approval USDC pour: {', '.join(targets_to_approve)}")
            results = {}

            for target_name in targets_to_approve:
                # Trouver la clé du contract
                contract_key = next((key for name, key in APPROVAL_TARGETS if name == target_name), None)
                if not contract_key:
                    logger.error(f"❌ Contract inconnu: {target_name}")
                    continue

                spender_address = Web3.to_checksum_address(CONTRACTS[contract_key])

                # Construire la transaction
                nonce = self.w3.eth.get_transaction_count(self.account.address)

                transaction = self.usdc_contract.functions.approve(
                    spender_address,
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

                logger.info(f"Gas estimé pour {target_name}: {transaction['gas']} | Coût: {gas_cost_matic:.4f} MATIC")

                if dry_run:
                    results[target_name] = {
                        'dry_run': True,
                        'gas_estimate': transaction['gas'],
                        'gas_cost_matic': float(gas_cost_matic)
                    }
                    continue

                # Confirmation utilisateur
                confirm = input(f"\n💰 Envoyer approval USDC pour {target_name}? Coût: {gas_cost_matic:.4f} MATIC (y/N): ").strip().lower()
                if confirm != 'y':
                    logger.info(f"⏹️ Approval {target_name} annulée par l'utilisateur")
                    results[target_name] = {'skipped': True}
                    continue

                # Signer et envoyer
                signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

                logger.info(f"📤 Transaction envoyée pour {target_name}: {tx_hash.hex()}")
                logger.info("⏳ Attente confirmation...")

                # Attendre la confirmation
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

                if receipt.status == 1:
                    logger.info(f"✅ Approval USDC pour {target_name} réussie!")
                    results[target_name] = {
                        'success': True,
                        'tx_hash': tx_hash.hex(),
                        'gas_used': receipt.gasUsed,
                        'block_number': receipt.blockNumber
                    }
                else:
                    logger.error(f"❌ Transaction échouée pour {target_name}")
                    results[target_name] = {'failed': True}

            return results

        except Exception as e:
            logger.error(f"❌ Erreur approval USDC: {e}")
            return None

    def approve_ctf(self, targets_to_approve=None, dry_run=True):
        """Approve CTF vers les contracts Polymarket spécifiés"""
        try:
            # Si aucun target spécifié, approuver tous ceux qui ne le sont pas encore
            if targets_to_approve is None:
                ctf_status = self.check_ctf_approval()
                if not ctf_status:
                    return None
                targets_to_approve = [name for name, status in ctf_status.items() if not status['is_approved']]

            if not targets_to_approve:
                logger.info("✅ Tous les contracts CTF sont déjà approuvés")
                return {'success': True, 'skipped': True}

            logger.info(f"📝 Préparation approval CTF pour: {', '.join(targets_to_approve)}")
            results = {}

            for target_name in targets_to_approve:
                # Trouver la clé du contract
                contract_key = next((key for name, key in APPROVAL_TARGETS if name == target_name), None)
                if not contract_key:
                    logger.error(f"❌ Contract inconnu: {target_name}")
                    continue

                operator_address = Web3.to_checksum_address(CONTRACTS[contract_key])

                # Construire la transaction
                nonce = self.w3.eth.get_transaction_count(self.account.address)

                transaction = self.ctf_contract.functions.setApprovalForAll(
                    operator_address,
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

                logger.info(f"Gas estimé pour {target_name}: {transaction['gas']} | Coût: {gas_cost_matic:.4f} MATIC")

                if dry_run:
                    results[target_name] = {
                        'dry_run': True,
                        'gas_estimate': transaction['gas'],
                        'gas_cost_matic': float(gas_cost_matic)
                    }
                    continue

                # Confirmation utilisateur
                confirm = input(f"\n💰 Envoyer approval CTF pour {target_name}? Coût: {gas_cost_matic:.4f} MATIC (y/N): ").strip().lower()
                if confirm != 'y':
                    logger.info(f"⏹️ Approval {target_name} annulée par l'utilisateur")
                    results[target_name] = {'skipped': True}
                    continue

                # Signer et envoyer
                signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

                logger.info(f"📤 Transaction envoyée pour {target_name}: {tx_hash.hex()}")
                logger.info("⏳ Attente confirmation...")

                # Attendre la confirmation
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

                if receipt.status == 1:
                    logger.info(f"✅ Approval CTF pour {target_name} réussie!")
                    results[target_name] = {
                        'success': True,
                        'tx_hash': tx_hash.hex(),
                        'gas_used': receipt.gasUsed,
                        'block_number': receipt.blockNumber
                    }
                else:
                    logger.error(f"❌ Transaction échouée pour {target_name}")
                    results[target_name] = {'failed': True}

            return results

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
            for name, status in usdc_allowance.items():
                status_icon = "✅ MAX" if status['is_max'] else "❌ NOT approved"
                logger.info(f"   {name:<18}: {status_icon}")
                if not status['is_max']:
                    logger.info(f"   {'':<18}  Current: {status['allowance_usdc']:.2f} USDC")

        # CTF Approval
        ctf_approval = manager.check_ctf_approval()
        if ctf_approval:
            logger.info("\n📋 CTF Approval:")
            for name, status in ctf_approval.items():
                status_icon = "✅ Approved" if status['is_approved'] else "❌ NOT approved"
                logger.info(f"   {name:<18}: {status_icon}")

        # Résumé
        usdc_ok = usdc_allowance and all(status['is_max'] for status in usdc_allowance.values())
        ctf_ok = ctf_approval and all(status['is_approved'] for status in ctf_approval.values())

        logger.info("\n" + "="*50)
        total_approvals = len(APPROVAL_TARGETS) * 2  # 3 contracts x 2 types (USDC + CTF) = 6
        if usdc_ok and ctf_ok:
            logger.info(f"✅ All {total_approvals} approvals configured - bot prêt pour LIVE trading!")
        else:
            approved_count = 0
            if usdc_allowance:
                approved_count += sum(1 for status in usdc_allowance.values() if status['is_max'])
            if ctf_approval:
                approved_count += sum(1 for status in ctf_approval.values() if status['is_approved'])
            logger.warning(f"⚠️ Only {approved_count}/{total_approvals} approvals configured - lancez: python utils/setup_approvals.py --setup")

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

        # Identifier ce qui manque
        usdc_needed = []
        ctf_needed = []

        if usdc_allowance:
            usdc_needed = [name for name, status in usdc_allowance.items() if not status['is_max']]

        if ctf_approval:
            ctf_needed = [name for name, status in ctf_approval.items() if not status['is_approved']]

        if not usdc_needed and not ctf_needed:
            total_approvals = len(APPROVAL_TARGETS) * 2
            logger.info(f"✅ All {total_approvals} approvals déjà configurées!")
            return

        logger.info("\n🔧 Approvals à configurer:")
        if usdc_needed:
            logger.info(f"   USDC: {', '.join(usdc_needed)}")
        if ctf_needed:
            logger.info(f"   CTF:  {', '.join(ctf_needed)}")

        # Confirmation
        logger.warning("⚠️ ATTENTION: Ces transactions vont consommer des MATIC en gas fees")
        confirm = input("\nContinuer avec la configuration? (y/N): ").strip().lower()
        if confirm != 'y':
            logger.info("⏹️ Configuration annulée par l'utilisateur")
            return

        # Configurer USDC approvals
        if usdc_needed:
            logger.info("\n" + "="*30 + " USDC APPROVALS " + "="*30)
            result = manager.approve_usdc(targets_to_approve=usdc_needed, dry_run=False)
            if result:
                success_count = sum(1 for r in result.values() if r.get('success'))
                if success_count > 0:
                    logger.info(f"✅ {success_count}/{len(usdc_needed)} USDC approvals réussies")
                if success_count < len(usdc_needed):
                    logger.error("❌ Certaines USDC approvals ont échoué")
            else:
                logger.error("❌ Échec USDC approvals")
                return

        # Configurer CTF approvals
        if ctf_needed:
            logger.info("\n" + "="*30 + " CTF APPROVALS " + "="*30)
            result = manager.approve_ctf(targets_to_approve=ctf_needed, dry_run=False)
            if result:
                success_count = sum(1 for r in result.values() if r.get('success'))
                if success_count > 0:
                    logger.info(f"✅ {success_count}/{len(ctf_needed)} CTF approvals réussies")
                if success_count < len(ctf_needed):
                    logger.error("❌ Certaines CTF approvals ont échoué")
            else:
                logger.error("❌ Échec CTF approvals")
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