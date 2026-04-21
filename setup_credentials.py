import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

load_dotenv()

def main():
    private_key = os.getenv("CLOB_PRIVATE_KEY")
    
    if not private_key:
        print("❌ Error: CLOB_PRIVATE_KEY not found in .env file")
        print("Please add your private key to the .env file and try again.")
        return
    
    if not private_key.startswith("0x"):
        print("❌ Error: Private key should start with '0x'")
        return
    
    # Masquer la clé pour affichage
    masked = f"{private_key[:10]}...{private_key[-4:]}"
    print(f"🔑 Setting up Polymarket API credentials...")
    print(f"   Private key: {masked} (hidden for security)")
    print(f"🔄 Generating API credentials...")
    
    try:
        client = ClobClient(
            host="https://clob.polymarket.com",
            chain_id=POLYGON,
            key=private_key,
        )
        
        creds = client.create_or_derive_api_creds()
        
        print(f"✅ API credentials generated successfully!")
        print(f"📋 Copy these values to your .env file:")
        print(f"=" * 50)
        print(f"CLOB_API_KEY={creds.api_key}")
        print(f"CLOB_SECRET={creds.api_secret}")
        print(f"CLOB_PASSPHRASE={creds.api_passphrase}")
        print(f"=" * 50)
        print(f"⚠️  Important: Keep these credentials secure and never share them!")
        print(f"   These credentials are tied to your wallet and can be used to trade.")
        
    except Exception as e:
        print(f"❌ Error generating credentials: {e}")
        print(f"Possible issues:")
        print(f"- Invalid private key format")
        print(f"- Network connection problem")
        print(f"- Polymarket API temporarily unavailable")

if __name__ == "__main__":
    main()