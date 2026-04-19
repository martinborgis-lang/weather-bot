#!/usr/bin/env python3
"""
Test de debug pour valider le calcul des probabilités Celsius/Fahrenheit
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from agents.weather_forecaster import calculate_probabilities, detect_model_agreement, fetch_ensemble_forecast
from shared.models import TemperatureRange, WeatherMarket, WeatherForecast
from shared.cities import CITY_COORDINATES

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def analyze_range_type(label: str) -> tuple:
    """Analyse un label de range et retourne son type et ses paramètres"""
    label_lower = label.lower()

    if "or below" in label_lower:
        temp_match = re.search(r'(\d+)°?[cf]?\s+or\s+below', label_lower)
        if temp_match:
            threshold = float(temp_match.group(1))
            return ("or_below", threshold, None)

    elif "or higher" in label_lower or "or above" in label_lower:
        temp_match = re.search(r'(\d+)°?[cf]?\s+or\s+(higher|above)', label_lower)
        if temp_match:
            threshold = float(temp_match.group(1))
            return ("or_higher", threshold, None)

    elif "-" in label_lower and not "below" in label_lower and not "higher" in label_lower:
        range_match = re.search(r'(\d+)-(\d+)°?[cf]?', label_lower)
        if range_match:
            min_temp = float(range_match.group(1))
            max_temp = float(range_match.group(2))
            return ("range", min_temp, max_temp)

    else:
        temp_match = re.search(r'(\d+)°?[cf]?$', label_lower)
        if temp_match:
            temp = float(temp_match.group(1))
            return ("exact", temp, None)

    return ("unknown", None, None)

def debug_probability_calculation(predictions: list, ranges: list, unit: str, market_name: str):
    """Debug détaillé du calcul des probabilités"""
    logger.info(f"\n🔍 DEBUG MARCHÉ: {market_name}")
    logger.info(f"Unité: {unit}")
    logger.info(f"Prédictions brutes (Celsius): {predictions[:5]}... ({len(predictions)} total)")

    # Convertir les prédictions si nécessaire
    if unit == "F":
        predictions_converted = [(pred * 9/5 + 32) for pred in predictions]
        logger.info(f"Prédictions converties (Fahrenheit): {predictions_converted[:5]}...")
    else:
        predictions_converted = predictions

    logger.info(f"Min converti: {min(predictions_converted):.1f}°{unit}")
    logger.info(f"Max converti: {max(predictions_converted):.1f}°{unit}")
    logger.info(f"Moyenne: {sum(predictions_converted)/len(predictions_converted):.1f}°{unit}")

    # Analyser chaque range
    total_members = len(predictions)
    probabilities = {}
    total_probability = 0

    logger.info(f"\n📊 ANALYSE PAR RANGE:")

    for range_obj in ranges:
        label = range_obj.label
        range_type, param1, param2 = analyze_range_type(label)

        count = 0
        condition_desc = ""

        if range_type == "or_below":
            threshold = param1 + 0.999
            condition_desc = f"pred <= {threshold:.1f}"
            for pred in predictions_converted:
                if pred <= threshold:
                    count += 1

        elif range_type == "or_higher":
            condition_desc = f"pred >= {param1}"
            for pred in predictions_converted:
                if pred >= param1:
                    count += 1

        elif range_type == "range":
            max_threshold = param2 + 0.999
            condition_desc = f"{param1} <= pred <= {max_threshold:.1f}"
            for pred in predictions_converted:
                if param1 <= pred <= max_threshold:
                    count += 1

        elif range_type == "exact":
            max_threshold = param1 + 0.999
            condition_desc = f"{param1} <= pred <= {max_threshold:.1f}"
            for pred in predictions_converted:
                if param1 <= pred <= max_threshold:
                    count += 1

        probability = count / total_members
        probabilities[label] = probability
        total_probability += probability

        logger.info(f"  {label:15} | Type: {range_type:10} | Condition: {condition_desc:20} | Count: {count:3}/{total_members} | Prob: {probability:.3f}")

    logger.info(f"\n✅ RÉSULTATS:")
    logger.info(f"Somme des probabilités: {total_probability:.6f}")
    logger.info(f"Doit être ≈ 1.0: {'✅ OUI' if abs(total_probability - 1.0) < 0.001 else '❌ NON'}")

    return probabilities

async def test_probabilities_debug():
    """Test principal de debug des probabilités"""
    logger.info("🐛 TEST DEBUG CALCUL PROBABILITÉS")
    logger.info("=" * 60)

    try:
        # Test 1: Marché Celsius (London)
        logger.info("\n🇬🇧 TEST 1: MARCHÉ CELSIUS (London)")

        # Récupérer vraies prédictions pour London
        coords = CITY_COORDINATES["London"]
        target_date = datetime.now() + timedelta(days=2)
        london_predictions = await fetch_ensemble_forecast(
            coords['lat'], coords['lon'], target_date
        )

        if london_predictions:
            # Simuler des ranges London en Celsius
            london_ranges = [
                TemperatureRange("12°C or below", 0.0, 12.0, "token_12", 0.10),
                TemperatureRange("13°C", 13.0, 13.999, "token_13", 0.20),
                TemperatureRange("14°C", 14.0, 14.999, "token_14", 0.30),
                TemperatureRange("15°C", 15.0, 15.999, "token_15", 0.25),
                TemperatureRange("16°C or higher", 16.0, 99.0, "token_16", 0.15)
            ]

            london_probs = debug_probability_calculation(
                london_predictions, london_ranges, "C", "London (Celsius)"
            )

            # Test agreement
            agreement = detect_model_agreement(london_predictions)
            logger.info(f"Model agreement: {agreement}/{len(london_predictions)} membres ({agreement/len(london_predictions)*100:.1f}%)")

        # Test 2: Marché Fahrenheit (NYC)
        logger.info("\n🇺🇸 TEST 2: MARCHÉ FAHRENHEIT (NYC)")

        # Récupérer vraies prédictions pour NYC
        coords = CITY_COORDINATES["NYC"]
        nyc_predictions = await fetch_ensemble_forecast(
            coords['lat'], coords['lon'], target_date
        )

        if nyc_predictions:
            # Simuler des ranges NYC en Fahrenheit
            nyc_ranges = [
                TemperatureRange("50°F or below", 0.0, 50.0, "token_50", 0.10),
                TemperatureRange("51-52°F", 51.0, 52.999, "token_51", 0.20),
                TemperatureRange("53-54°F", 53.0, 54.999, "token_53", 0.35),
                TemperatureRange("55-56°F", 55.0, 56.999, "token_55", 0.25),
                TemperatureRange("57°F or higher", 57.0, 99.0, "token_57", 0.10)
            ]

            nyc_probs = debug_probability_calculation(
                nyc_predictions, nyc_ranges, "F", "NYC (Fahrenheit)"
            )

            # Test agreement
            agreement = detect_model_agreement(nyc_predictions)
            logger.info(f"Model agreement: {agreement}/{len(nyc_predictions)} membres ({agreement/len(nyc_predictions)*100:.1f}%)")

        # Test 3: Marché avec ranges problématiques
        logger.info("\n🧪 TEST 3: RANGES PROBLÉMATIQUES")

        # Utiliser NYC mais avec ranges extrêmes pour tester les edge cases
        if nyc_predictions:
            problem_ranges = [
                TemperatureRange("30°F or below", 0.0, 30.0, "token_30", 0.05),  # Devrait être ~0%
                TemperatureRange("31-40°F", 31.0, 40.999, "token_31", 0.10),
                TemperatureRange("41-50°F", 41.0, 50.999, "token_41", 0.25),
                TemperatureRange("51-60°F", 51.0, 60.999, "token_51", 0.40),
                TemperatureRange("61°F or higher", 61.0, 99.0, "token_61", 0.20)  # Devrait être élevé
            ]

            problem_probs = debug_probability_calculation(
                nyc_predictions, problem_ranges, "F", "NYC (Ranges problématiques)"
            )

        logger.info(f"\n🎉 TEST DEBUG TERMINÉ AVEC SUCCÈS!")

    except Exception as e:
        logger.error(f"❌ Erreur lors du test debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_probabilities_debug())
