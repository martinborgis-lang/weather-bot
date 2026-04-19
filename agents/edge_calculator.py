import asyncio
import json
import logging
import os
from datetime import datetime
from typing import List
from shared.models import WeatherMarket, WeatherForecast, TradeSignal, TemperatureRange
from shared.cache import cache

# Constantes de trading
EDGE_MINIMUM = 0.20              # 20 points minimum
CONVICTION_MIN_MODELS = 3
MAX_ENTRY_PRICE = 0.30           # pour BUY YES
MIN_EXIT_PRICE_NO = 0.45         # pour BUY NO
MIN_LIQUIDITY = 10000
BANKROLL_USDC = 250.0            # configurable via .env plus tard
MAX_POSITION_PCT = 0.02          # 2% du bankroll max par trade
MAX_POSITION_USDC = 10.0         # plafond absolu

# Intervalle de calcul
EDGE_CALCULATOR_INTERVAL = 300   # 5 min

logger = logging.getLogger(__name__)


def calculate_edge(market: WeatherMarket, forecast: WeatherForecast) -> List[TradeSignal]:
    """
    Calcule les opportunités d'edge pour un marché donné.

    Args:
        market: Marché météo Polymarket
        forecast: Prédiction météo correspondante

    Returns:
        Liste des signaux de trading détectés
    """
    signals = []

    # Vérifications préalables
    if market.liquidity_usdc < MIN_LIQUIDITY:
        logger.debug(f"Marché {market.title} ignoré: liquidité insuffisante ({market.liquidity_usdc:.0f} < {MIN_LIQUIDITY})")
        return signals

    for temp_range in market.ranges:
        model_prob = forecast.probabilities_by_range.get(temp_range.label, 0.0)
        market_prob = temp_range.current_price  # prix = probabilité implicite

        # Pattern 1: BUY YES (marché sous-évalue la probabilité)
        edge_yes = model_prob - market_prob
        if edge_yes > EDGE_MINIMUM and temp_range.current_price < MAX_ENTRY_PRICE:
            if forecast.models_agreement_count >= CONVICTION_MIN_MODELS:
                # Calcul du sizing Kelly prudent (quart-Kelly)
                odds = (1 / temp_range.current_price) - 1 if temp_range.current_price > 0 else 0
                kelly_fraction = (edge_yes / odds) * 0.25 if odds > 0 else 0

                size = min(
                    BANKROLL_USDC * MAX_POSITION_PCT,
                    BANKROLL_USDC * kelly_fraction,
                    MAX_POSITION_USDC
                )

                if size >= 1.0:
                    conviction = min(1.0, forecast.models_agreement_count / 5.0)

                    signal = TradeSignal(
                        market=market,
                        temperature_range=temp_range,
                        side="YES",
                        model_probability=model_prob,
                        market_implied_probability=market_prob,
                        edge_points=edge_yes,
                        conviction_score=conviction,
                        recommended_size_usdc=size,
                        reason=f"Modèles prédisent {model_prob:.1%} vs marché {market_prob:.1%} pour {temp_range.label}"
                    )
                    signals.append(signal)
                    logger.debug(f"Signal YES détecté: {market.title} {temp_range.label} | Edge +{edge_yes:.1%} | Size ${size:.1f}")

        # Pattern 2: BUY NO (marché sur-évalue la probabilité)
        no_price = 1.0 - temp_range.current_price
        model_prob_no = 1.0 - model_prob
        market_prob_no = no_price

        edge_no = model_prob_no - market_prob_no
        if edge_no > EDGE_MINIMUM and no_price > MIN_EXIT_PRICE_NO:
            if forecast.models_agreement_count >= CONVICTION_MIN_MODELS:
                # Calcul du sizing Kelly pour NO
                odds_no = (1 / no_price) - 1 if no_price > 0 else 0
                kelly_fraction_no = (edge_no / odds_no) * 0.25 if odds_no > 0 else 0

                size_no = min(
                    BANKROLL_USDC * MAX_POSITION_PCT,
                    BANKROLL_USDC * kelly_fraction_no,
                    MAX_POSITION_USDC
                )

                if size_no >= 1.0:
                    conviction = min(1.0, forecast.models_agreement_count / 5.0)

                    signal = TradeSignal(
                        market=market,
                        temperature_range=temp_range,
                        side="NO",
                        model_probability=model_prob_no,
                        market_implied_probability=market_prob_no,
                        edge_points=edge_no,
                        conviction_score=conviction,
                        recommended_size_usdc=size_no,
                        reason=f"Modèles prédisent PAS {temp_range.label}: {model_prob_no:.1%} vs marché {market_prob_no:.1%}"
                    )
                    signals.append(signal)
                    logger.debug(f"Signal NO détecté: {market.title} {temp_range.label} | Edge +{edge_no:.1%} | Size ${size_no:.1f}")

    return signals


def deduplicate_signals(signals: List[TradeSignal]) -> List[TradeSignal]:
    """
    Filtre les signaux dupliqués (même marché + même range).
    Garde le signal avec le meilleur edge.
    """
    seen = {}

    for signal in signals:
        key = (signal.market.condition_id, signal.temperature_range.label, signal.side)

        if key not in seen or signal.edge_points > seen[key].edge_points:
            seen[key] = signal

    return list(seen.values())


async def save_signals_to_file(signals: List[TradeSignal]):
    """Sauvegarde les signaux de trading dans un fichier JSON"""
    try:
        data_dir = os.getenv("DATA_DIR", "./data")
        os.makedirs(data_dir, exist_ok=True)
        signals_file = os.path.join(data_dir, "signals.json")

        # Charger les signaux existants
        existing_signals = []
        if os.path.exists(signals_file):
            try:
                with open(signals_file, 'r', encoding='utf-8') as f:
                    existing_signals = json.load(f)
            except:
                existing_signals = []

        # Convertir les nouveaux signaux en dict
        timestamp = datetime.now().isoformat()
        for signal in signals:
            # Extract city from market title
            city = "Unknown"
            if hasattr(signal.market, 'title') and signal.market.title:
                import re
                city_match = re.search(r'in\s+([A-Z][a-z]+)', signal.market.title)
                if city_match:
                    city = city_match.group(1)

            signal_dict = {
                'timestamp': timestamp,
                'condition_id': signal.market.condition_id,
                'token_id': getattr(signal.temperature_range, 'token_id', signal.temperature_range.label),
                'city': city,
                'market_title': signal.market.title,
                'temperature_label': signal.temperature_range.label,
                'action': f"BUY_{signal.side}",
                'side': signal.side,
                'edge_value': signal.edge_points,
                'model_probability': signal.model_probability,
                'market_price': signal.market_implied_probability,
                'bid_ask_spread': getattr(signal.market, 'bid_ask_spread', 0.01),
                'confidence': signal.conviction_score,
                'kelly_size_usdc': signal.recommended_size_usdc,
                'kelly_fraction': signal.recommended_size_usdc / BANKROLL_USDC if BANKROLL_USDC > 0 else 0,
                'reason': signal.reason
            }
            existing_signals.append(signal_dict)

        # Garder seulement les 500 derniers signaux pour éviter un fichier trop gros
        if len(existing_signals) > 500:
            existing_signals = existing_signals[-500:]

        # Sauvegarder avec gestion des datetime
        with open(signals_file, 'w', encoding='utf-8') as f:
            json.dump(existing_signals, f, indent=2, ensure_ascii=False, default=str)

        logger.debug(f"💾 {len(signals)} nouveaux signaux sauvegardés dans {signals_file}")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la sauvegarde des signaux: {e}")


async def run_edge_loop():
    """
    Boucle principale de l'Edge Calculator.
    Analyse les marchés et prédictions pour détecter des opportunités de trading.
    """
    logger.info("Edge Calculator démarré")

    while True:
        try:
            # Récupération des données depuis le cache
            weather_markets = await cache.get('weather_markets', [])
            forecasts = await cache.get('forecasts', {})

            if not weather_markets:
                logger.debug("Aucun marché météo disponible")
                await asyncio.sleep(EDGE_CALCULATOR_INTERVAL)
                continue

            if not forecasts:
                logger.debug("Aucune prédiction météo disponible")
                await asyncio.sleep(EDGE_CALCULATOR_INTERVAL)
                continue

            # Calcul des signaux pour chaque marché ayant une prédiction
            all_signals = []

            for market in weather_markets:
                if market.condition_id in forecasts:
                    forecast = forecasts[market.condition_id]
                    market_signals = calculate_edge(market, forecast)
                    all_signals.extend(market_signals)

            # Déduplication des signaux
            unique_signals = deduplicate_signals(all_signals)

            # Sauvegarde dans le cache
            await cache.set('trade_signals', unique_signals)

            # Sauvegarde dans le fichier JSON pour le dashboard
            if unique_signals:
                await save_signals_to_file(unique_signals)

            # Logging des résultats
            logger.info(f"Edge Calculator: {len(unique_signals)} opportunités détectées")

            for signal in unique_signals:
                logger.info(
                    f"Signal: {signal.market.title} | "
                    f"{signal.side} {signal.temperature_range.label} | "
                    f"Edge +{signal.edge_points:.1%} | "
                    f"Size ${signal.recommended_size_usdc:.1f}"
                )

            # Attendre avant la prochaine analyse
            await asyncio.sleep(EDGE_CALCULATOR_INTERVAL)

        except Exception as e:
            logger.error(f"Erreur dans Edge Calculator: {e}", exc_info=True)
            await asyncio.sleep(60)  # Attendre 1 minute en cas d'erreur


if __name__ == "__main__":
    # Configuration du logging pour les tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Lancement de la boucle
    asyncio.run(run_edge_loop())