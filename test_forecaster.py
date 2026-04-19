#!/usr/bin/env python3
"""
Test du Weather Forecaster avec l'API Ensemble Open-Meteo
"""

import asyncio
import logging
from datetime import datetime, timedelta
from agents.weather_forecaster import fetch_ensemble_forecast, calculate_probabilities, detect_model_agreement
from shared.cities import CITY_COORDINATES
from shared.models import TemperatureRange

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_forecaster():
    """Test du forecaster avec la vraie API Open-Meteo Ensemble"""
    logger.info("🌤️  Test du Weather Forecaster avec API Ensemble")
    logger.info("=" * 60)

    try:
        # Test avec Londres
        city = "London"
        coords = CITY_COORDINATES[city]
        target_date = datetime.now() + timedelta(days=2)

        logger.info(f"Test pour {city} le {target_date.strftime('%Y-%m-%d')}")
        logger.info(f"Coordonnées: {coords['lat']}, {coords['lon']}")

        # Récupérer les prédictions ensemble
        predictions = await fetch_ensemble_forecast(
            coords['lat'],
            coords['lon'],
            target_date
        )

        logger.info(f"\n📊 RÉSULTATS:")
        logger.info(f"Nombre de prédictions: {len(predictions)}")

        if not predictions:
            logger.error("❌ Aucune prédiction récupérée!")
            logger.info("Vérifiez:")
            logger.info("- La connexion Internet")
            logger.info("- L'API Open-Meteo Ensemble")
            logger.info("- La date cible (dans les 7 prochains jours)")
            return

        logger.info(f"Températures prédites: {predictions[:10]}..." if len(predictions) > 10 else f"Températures prédites: {predictions}")
        logger.info(f"Min: {min(predictions):.1f}°C | Max: {max(predictions):.1f}°C | Moyenne: {sum(predictions)/len(predictions):.1f}°C")

        # Test de calcul des probabilités
        logger.info(f"\n🎯 TEST CALCUL PROBABILITÉS:")

        # Créer des ranges de test autour de la moyenne
        avg_temp = sum(predictions) / len(predictions)
        ranges = []
        for temp in range(int(avg_temp) - 2, int(avg_temp) + 4):
            ranges.append(TemperatureRange(
                label=f"{temp}°C",
                min_temp=float(temp),
                max_temp=float(temp) + 0.999,
                token_id=f"test_token_{temp}",
                current_price=0.15
            ))

        probabilities = calculate_probabilities(predictions, ranges, "C")  # Test en Celsius
        logger.info(f"Probabilités calculées:")
        for label, prob in sorted(probabilities.items()):
            logger.info(f"  {label}: {prob:.3f} ({prob*100:.1f}%)")

        # Test de détection d'accord
        agreement = detect_model_agreement(predictions)
        logger.info(f"\n🤝 ACCORD ENTRE MODÈLES:")
        logger.info(f"Nombre de membres d'accord: {agreement}")
        logger.info(f"Seuil minimum (25%): {len(predictions) * 0.25:.1f}")
        logger.info(f"Accord suffisant: {'✅ OUI' if agreement >= len(predictions) * 0.25 else '❌ NON'}")

        # Test avec plusieurs villes
        logger.info(f"\n🌍 TEST MULTI-VILLES:")
        test_cities = ["NYC", "Paris", "Tokyo"]

        for test_city in test_cities:
            if test_city in CITY_COORDINATES:
                coords = CITY_COORDINATES[test_city]
                predictions = await fetch_ensemble_forecast(
                    coords['lat'],
                    coords['lon'],
                    target_date
                )
                logger.info(f"{test_city:10}: {len(predictions):3d} prédictions | "
                           f"Moyenne: {sum(predictions)/len(predictions):5.1f}°C" if predictions
                           else f"{test_city:10}: ÉCHEC")

                # Small delay between API calls
                await asyncio.sleep(1)

        logger.info(f"\n✅ Test terminé avec succès!")
        logger.info(f"Le Weather Forecaster fonctionne correctement avec l'API Ensemble.")

    except Exception as e:
        logger.error(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_forecaster())
