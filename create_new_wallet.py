"""
Script ultra-simple : génère un nouveau wallet Polygon + API creds Polymarket.
Affiche les variables à copier dans .env. Ne modifie RIEN automatiquement.

Usage: python create_new_wallet.py
"""
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

from eth_account import Account
from py_clob_client.client import ClobClient

# Activer la génération HD (nécessaire depuis eth-account 0.6+)
Account.enable_unaudited_hdwallet_features()

print("=" * 70)
print("GENERATION NOUVEAU WALLET POLYMARKET")
print("=" * 70)
print()

# 1. Generer un nouveau wallet
print("[1/2] Generation du wallet...")
acct = Account.create()
private_key = acct.key.hex()
if not private_key.startswith("0x"):
    private_key = "0x" + private_key
address = acct.address
print(f"    OK - Adresse: {address}")
print()

# 2. Generer les API credentials Polymarket
print("[2/2] Generation API credentials Polymarket...")
try:
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=private_key,
        chain_id=137,
    )
    creds = client.create_or_derive_api_creds()
    api_key = creds.api_key
    api_secret = creds.api_secret
    api_passphrase = creds.api_passphrase
    print(f"    OK - API creds generes")
except Exception as e:
    print(f"    ERREUR: {e}")
    print()
    print("Les API creds n'ont pas pu etre generes.")
    print("Tu peux quand meme utiliser le wallet, mais il faudra")
    print("relancer la generation des API creds une fois les fonds envoyes.")
    api_key = ""
    api_secret = ""
    api_passphrase = ""

print()
print("=" * 70)
print("COPIER CES LIGNES DANS TON .env")
print("=" * 70)
print()
print(f"CLOB_PRIVATE_KEY={private_key}")
print(f"WALLET_ADDRESS={address}")
print(f"CLOB_FUNDER_ADDRESS={address}")
print(f"CLOB_HOST=https://clob.polymarket.com")
print(f"CLOB_CHAIN_ID=137")
print(f"CLOB_API_KEY={api_key}")
print(f"CLOB_API_SECRET={api_secret}")
print(f"CLOB_API_PASSPHRASE={api_passphrase}")
print()
print("=" * 70)
print("PROCHAINES ETAPES")
print("=" * 70)
print()
print(f"1. Copie les 8 lignes ci-dessus dans ton .env")
print(f"   (remplace les anciennes valeurs si elles existent)")
print()
print(f"2. Envoie des fonds a cette adresse :")
print(f"   {address}")
print(f"   - 58 USDC.e (contrat 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174)")
print(f"   - 2 POL (native token)")
print()
print(f"3. Verifie sur PolygonScan :")
print(f"   https://polygonscan.com/address/{address}")
print()
print(f"4. Puis lance :")
print(f"   python utils/setup_approvals.py --setup")
print()
print("=" * 70)
print("IMPORTANT")
print("=" * 70)
print("- Sauvegarde ta PRIVATE_KEY dans un password manager (Bitwarden, 1Password)")
print("- NE PARTAGE JAMAIS la PRIVATE_KEY avec personne")
print("- NE FAIS PAS de commit de ton .env")
print("=" * 70)