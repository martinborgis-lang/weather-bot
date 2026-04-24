#!/usr/bin/env python3
"""
Configuration centralisée du Weather Trading Bot
"""

import os
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

class Config:
    """Configuration centralisée"""

    # Trading
    DRY_RUN = os.getenv('DRY_RUN', 'true').lower() == 'true'
    BANKROLL_USDC = float(os.getenv('BANKROLL_USDC', '40.0'))
    MAX_POSITION_USDC = float(os.getenv('MAX_POSITION_USDC', '2.0'))
    MIN_POSITION_USDC = float(os.getenv('MIN_POSITION_USDC', '1.0'))
    EDGE_MINIMUM = float(os.getenv('EDGE_MINIMUM', '0.25'))
    MAX_POSITIONS_COUNT = int(os.getenv('MAX_POSITIONS_COUNT', '15'))
    COPY_RATIO = float(os.getenv('COPY_RATIO', '0.05'))

    # Data
    DATA_DIR = os.getenv('DATA_DIR', './data')

    # CLOB API (Polymarket)
    CLOB_PRIVATE_KEY = os.getenv('CLOB_PRIVATE_KEY')
    CLOB_HOST = os.getenv('CLOB_HOST', 'https://clob.polymarket.com')
    CLOB_CHAIN_ID = os.getenv('CLOB_CHAIN_ID', '137')  # Polygon mainnet
    WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')

    # API RPC
    POLYGON_RPC_URL = os.getenv('POLYGON_RPC_URL')

    # Legacy CLOB configs (deprecated)
    CLOB_API_KEY = os.getenv('CLOB_API_KEY')
    CLOB_SECRET = os.getenv('CLOB_SECRET')
    CLOB_PASSPHRASE = os.getenv('CLOB_PASSPHRASE')

    # Notifications
    NOTIFY_SLACK = os.getenv('NOTIFY_SLACK', 'false').lower() == 'true'
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
    NOTIFY_ON_TRADE_COPIED = os.getenv('NOTIFY_ON_TRADE_COPIED', 'true').lower() == 'true'
    NOTIFY_ON_POSITION_UPDATE = os.getenv('NOTIFY_ON_POSITION_UPDATE', 'true').lower() == 'true'
    NOTIFY_ON_BOT_STARTED = os.getenv('NOTIFY_ON_BOT_STARTED', 'true').lower() == 'true'