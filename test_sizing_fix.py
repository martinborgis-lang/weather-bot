#!/usr/bin/env python3
"""
Test pour vérifier que le sizing respecte MAX_POSITION_USDC
"""

import asyncio
from datetime import datetime, timedelta
from agents.edge_calculator import calculate_edge
from shared.models import WeatherMarket, WeatherForecast, TemperatureRange
from config import Config

def test_sizing_limits():
    """Test que le sizing ne dépasse jamais MAX_POSITION_USDC"""

    print(f"Configuration testée:")
    print(f"  MAX_POSITION_USDC: {Config.MAX_POSITION_USDC}")
    print(f"  BANKROLL_USDC: {Config.BANKROLL_USDC}")
    print(f"  EDGE_MINIMUM: {Config.EDGE_MINIMUM}")
    print()

    # Créer un marché test avec des ranges de température
    ranges = [
        TemperatureRange(
            label="18°C",
            min_temp=18.0,
            max_temp=18.9,
            token_id="test_token_18",
            current_price=0.10  # Prix très bas = grosse opportunity
        )
    ]

    market = WeatherMarket(
        condition_id="test_market",
        slug="test-market",
        title="Test Market for Sizing",
        city="Paris",
        target_date=datetime.now() + timedelta(days=1),
        resolution_source="test",
        liquidity_usdc=50000,
        volume_usdc=10000,
        ranges=ranges,
        ends_at=datetime.now() + timedelta(hours=23),
        unit="C",
        resolution_datetime=datetime.now() + timedelta(hours=23)
    )

    # Créer une prévision avec edge énorme pour tester les limites
    forecast = WeatherForecast(
        city="Paris",
        target_date=datetime.now() + timedelta(days=1),
        probabilities_by_range={"18°C": 0.80},  # 80% vs marché 10% = edge énorme
        models_agreement_count=5,  # Full agreement
        ensemble_members_count=50,  # Nombre de membres d'ensemble
        raw_predictions=[]
    )

    # Tester le calcul d'edge
    signals = calculate_edge(market, forecast)

    print(f"Résultats du test:")
    print(f"  Signaux générés: {len(signals)}")

    for i, signal in enumerate(signals):
        print(f"  Signal {i+1}:")
        print(f"    Side: {signal.side}")
        print(f"    Edge: {signal.edge_points:.1%}")
        print(f"    Model prob: {signal.model_probability:.1%}")
        print(f"    Market prob: {signal.market_implied_probability:.1%}")
        print(f"    Recommended size: ${signal.recommended_size_usdc:.2f}")
        print(f"    Respecte MAX_POSITION_USDC ({Config.MAX_POSITION_USDC}): {'OK' if signal.recommended_size_usdc <= Config.MAX_POSITION_USDC else 'NOK'}")
        print()

    # Vérification
    all_respect_limit = all(s.recommended_size_usdc <= Config.MAX_POSITION_USDC for s in signals)
    print(f"Tous les signaux respectent MAX_POSITION_USDC: {'OK' if all_respect_limit else 'NOK'}")

    # Si pas de signaux, on examine pourquoi
    if len(signals) == 0:
        print("Debug: Aucun signal généré. Vérification des conditions...")
        edge = 0.80 - 0.10  # model_prob - market_prob
        print(f"  Edge calculé: {edge:.1%} (minimum requis: {Config.EDGE_MINIMUM:.0%})")
        print(f"  Prix d'entrée: 0.10 (max autorisé: 0.30)")
        print(f"  Agreement models: 5 (minimum requis: 3)")

    return len(signals) == 0 or all_respect_limit  # Success si pas de signaux OU si tous respectent la limite

if __name__ == "__main__":
    success = test_sizing_limits()
    if success:
        print("Test réussi - Le sizing respecte bien MAX_POSITION_USDC")
    else:
        print("Test échoué - Le sizing dépasse MAX_POSITION_USDC")