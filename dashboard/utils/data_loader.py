"""
Utilitaires pour charger les données du bot météo depuis les fichiers JSON
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import streamlit as st
import pandas as pd

# Configuration
DATA_DIR = os.getenv("DATA_DIR", "./data")

@st.cache_data(ttl=30)  # Cache pendant 30 secondes
def load_positions() -> List[Dict[str, Any]]:
    """Charge les positions ouvertes"""
    file_path = os.path.join(DATA_DIR, "positions.json")

    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        st.error(f"Erreur chargement positions: {e}")
        return []

@st.cache_data(ttl=30)
def load_signals(limit: int = 200) -> List[Dict[str, Any]]:
    """Charge les signaux récents"""
    file_path = os.path.join(DATA_DIR, "signals.json")

    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            signals = data if isinstance(data, list) else []
            return signals[-limit:] if len(signals) > limit else signals
    except Exception as e:
        st.error(f"Erreur chargement signaux: {e}")
        return []

@st.cache_data(ttl=30)
def load_trade_history() -> List[Dict[str, Any]]:
    """Charge l'historique des trades"""
    file_path = os.path.join(DATA_DIR, "trade_history.json")

    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        st.error(f"Erreur chargement historique: {e}")
        return []

@st.cache_data(ttl=30)
def load_forecast_log() -> List[Dict[str, Any]]:
    """Charge le log des forecasts"""
    file_path = os.path.join(DATA_DIR, "forecast_log.json")

    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        st.error(f"Erreur chargement forecast log: {e}")
        return []

@st.cache_data(ttl=30)
def get_bot_status() -> str:
    """Détermine le status du bot basé sur l'activité récente"""
    positions_file = os.path.join(DATA_DIR, "positions.json")

    if not os.path.exists(positions_file):
        return "stopped"

    try:
        # Vérifier la dernière modification du fichier positions
        mtime = os.path.getmtime(positions_file)
        now = time.time()

        # Si modifié il y a moins de 10 minutes, considéré comme actif
        if now - mtime < 600:  # 10 minutes
            return "running"
        else:
            return "stopped"
    except Exception:
        return "unknown"

@st.cache_data(ttl=30)
def calculate_pnl_metrics() -> Dict[str, float]:
    """Calcule les métriques de PnL"""
    trade_history = load_trade_history()
    positions = load_positions()

    metrics = {
        "total_pnl": 0.0,
        "pnl_24h": 0.0,
        "win_rate": 0.0,
        "total_trades": 0,
        "bankroll": float(os.getenv("BANKROLL_USDC", "250.0"))
    }

    if not trade_history:
        return metrics

    # Calculer PnL total des trades fermés
    closed_trades = [t for t in trade_history if t.get("final_pnl") is not None]

    if closed_trades:
        metrics["total_pnl"] = sum(t["final_pnl"] for t in closed_trades)
        metrics["total_trades"] = len(closed_trades)

        # Win rate
        winning_trades = [t for t in closed_trades if t["final_pnl"] > 0]
        metrics["win_rate"] = len(winning_trades) / len(closed_trades)

    # PnL 24h
    now = datetime.now()
    yesterday = now - timedelta(hours=24)

    recent_trades = [
        t for t in closed_trades
        if t.get("timestamp") and datetime.fromisoformat(t["timestamp"].replace('Z', '')) >= yesterday
    ]

    if recent_trades:
        metrics["pnl_24h"] = sum(t["final_pnl"] for t in recent_trades)

    # Ajouter PnL non réalisé des positions ouvertes
    if positions:
        unrealized_pnl = 0.0
        for pos in positions:
            if "current_price" in pos and "entry_price" in pos and "size_usdc" in pos:
                price_change = pos["current_price"] - pos["entry_price"]
                if pos.get("side") == "NO":
                    price_change = -price_change
                unrealized_pnl += price_change * pos["size_usdc"]

        metrics["unrealized_pnl"] = unrealized_pnl

    return metrics

@st.cache_data(ttl=30)
def get_latest_activity() -> Dict[str, Any]:
    """Récupère la dernière activité du bot"""
    signals = load_signals(limit=50)
    trades = load_trade_history()

    activity = {
        "latest_signal": None,
        "latest_trade": None,
        "signals_24h": 0
    }

    # Dernier signal
    if signals:
        activity["latest_signal"] = signals[-1]

    # Dernier trade
    if trades:
        activity["latest_trade"] = trades[-1]

    # Signaux 24h
    now = datetime.now()
    yesterday = now - timedelta(hours=24)

    recent_signals = [
        s for s in signals
        if s.get("timestamp") and datetime.fromisoformat(s["timestamp"].replace('Z', '')) >= yesterday
    ]

    activity["signals_24h"] = len(recent_signals)

    return activity

def format_currency(amount: float) -> str:
    """Formate un montant en devise avec couleur"""
    return f"${amount:,.2f}"

def format_percentage(pct: float) -> str:
    """Formate un pourcentage avec couleur"""
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"

def format_timestamp(timestamp: str) -> str:
    """Formate un timestamp en heure locale Paris"""
    if not timestamp:
        return "N/A"

    try:
        # Parse le timestamp ISO
        dt = datetime.fromisoformat(timestamp.replace('Z', ''))

        # Convertir en heure locale (approximation)
        local_dt = dt + timedelta(hours=1)  # UTC+1 pour Paris

        return local_dt.strftime("%d/%m %H:%M")
    except Exception:
        return timestamp

def get_city_flag(city: str) -> str:
    """Retourne le drapeau emoji correspondant à une ville"""
    city_flags = {
        "London": "🇬🇧",
        "Paris": "🇫🇷",
        "NYC": "🇺🇸",
        "New York": "🇺🇸",
        "Tokyo": "🇯🇵",
        "Shanghai": "🇨🇳",
        "Beijing": "🇨🇳",
        "Hong Kong": "🇭🇰",
        "Seoul": "🇰🇷",
        "Sydney": "🇦🇺",
        "Toronto": "🇨🇦",
        "Berlin": "🇩🇪",
        "Munich": "🇩🇪",
        "Amsterdam": "🇳🇱",
        "Stockholm": "🇸🇪",
        "Oslo": "🇳🇴",
        "Helsinki": "🇫🇮",
        "Moscow": "🇷🇺",
        "Warsaw": "🇵🇱",
        "Madrid": "🇪🇸",
        "Milan": "🇮🇹",
        "Istanbul": "🇹🇷",
        "Tel Aviv": "🇮🇱",
        "Dubai": "🇦🇪",
        "Singapore": "🇸🇬",
        "Mumbai": "🇮🇳",
        "Bangkok": "🇹🇭",
        "Jakarta": "🇮🇩",
        "Manila": "🇵🇭",
        "Taipei": "🇹🇼",
        "Kuala Lumpur": "🇲🇾",
        "Mexico City": "🇲🇽",
        "Sao Paulo": "🇧🇷",
        "Buenos Aires": "🇦🇷",
        "Lima": "🇵🇪",
        "Santiago": "🇨🇱",
        "Bogota": "🇨🇴",
        "Lagos": "🇳🇬",
        "Cairo": "🇪🇬",
        "Cape Town": "🇿🇦",
        "Nairobi": "🇰🇪"
    }

    return city_flags.get(city, "🌍")