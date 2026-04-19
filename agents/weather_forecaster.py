import asyncio
import aiohttp
import logging
import math
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from shared.models import WeatherMarket, WeatherForecast, TemperatureRange
from shared.cache import cache

# Configuration
FORECASTER_INTERVAL = 300  # 5 min
RATE_LIMIT_DELAY = 1.2  # 1.2s entre appels API (plus conservateur)
RETRY_DELAY = 60
CACHE_TTL_SECONDS = 1800  # 30 min
RETRY_AFTER_429 = 10  # 10s d'attente après 429

# Import des coordonnées partagées
from shared.cities import CITY_COORDINATES

# Cache en mémoire pour les prévisions
_forecast_cache: Dict[str, Tuple[List[float], float]] = {}

# Semaphore pour rate limiting
_api_semaphore = asyncio.Semaphore(1)

logger = logging.getLogger(__name__)

def _get_cache_key(lat: float, lon: float, target_date: datetime) -> str:
    """Génère une clé de cache pour les prévisions"""
    return f"{lat:.4f}_{lon:.4f}_{target_date.strftime('%Y-%m-%d')}"

def _is_cache_valid(fetched_at: float) -> bool:
    """Vérifie si le cache est encore valide (< 30 min)"""
    return time.time() - fetched_at < CACHE_TTL_SECONDS

async def fetch_ensemble_forecast(lat: float, lon: float, target_date: datetime) -> List[float]:
    """
    Récupère les prévisions ensemble de Open-Meteo pour une position et date données.
    Inclut cache en mémoire et rate limiting.

    Args:
        lat: Latitude de la ville
        lon: Longitude de la ville
        target_date: Date cible pour les prévisions

    Returns:
        List[float]: Liste des prédictions de température max des différents modèles/membres
    """
    cache_key = _get_cache_key(lat, lon, target_date)

    # Vérifier le cache d'abord
    if cache_key in _forecast_cache:
        predictions, fetched_at = _forecast_cache[cache_key]
        if _is_cache_valid(fetched_at):
            logger.info(f"Cache hit pour {cache_key}: {len(predictions)} prédictions")
            return predictions
        else:
            # Cache expiré, on le supprime
            del _forecast_cache[cache_key]

    # Rate limiting avec semaphore
    async with _api_semaphore:
        return await _fetch_ensemble_forecast_impl(lat, lon, target_date, cache_key)

async def _fetch_ensemble_forecast_impl(lat: float, lon: float, target_date: datetime, cache_key: str) -> List[float]:
    """Implémentation interne avec retry logic"""
    url = "https://ensemble-api.open-meteo.com/v1/ensemble"
    params = {
        'latitude': lat,
        'longitude': lon,
        'daily': 'temperature_2m_max',
        'timezone': 'auto',
        'forecast_days': 7,
        'models': 'ecmwf_ifs025,gfs_seamless,icon_seamless'
    }

    # Premier essai
    predictions = await _try_fetch(url, params, target_date)

    if predictions is None:
        # Rate limit retry après 10s
        logger.warning(f"Rate limit 429, attente {RETRY_AFTER_429}s avant retry...")
        await asyncio.sleep(RETRY_AFTER_429)
        predictions = await _try_fetch(url, params, target_date)

        if predictions is None:
            logger.error("Échec définitif après retry 429")
            return []

    # Rate limiting entre les appels
    await asyncio.sleep(RATE_LIMIT_DELAY)

    # Stocker en cache
    if predictions:
        _forecast_cache[cache_key] = (predictions, time.time())
        logger.info(f"Cache stocké pour {cache_key}: {len(predictions)} prédictions")

    return predictions

async def _try_fetch(url: str, params: dict, target_date: datetime) -> Optional[List[float]]:
    """Tentative d'appel API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 429:
                    logger.warning("Rate limit 429 détecté")
                    return None

                if response.status != 200:
                    logger.error(f"Open-Meteo API error: {response.status}")
                    return []

                data = await response.json()

                # Trouver l'index du jour cible dans les prévisions
                forecast_dates = data.get('daily', {}).get('time', [])
                target_date_str = target_date.strftime('%Y-%m-%d')

                if target_date_str not in forecast_dates:
                    logger.warning(f"Date cible {target_date_str} non trouvée dans les prévisions")
                    return []

                target_index = forecast_dates.index(target_date_str)

                # Extraire les prédictions pour tous les modèles/membres
                predictions = []
                daily_data = data.get('daily', {})

                # Open-Meteo Ensemble API renvoie les membres comme "temperature_2m_max_memberXX"
                for key, values in daily_data.items():
                    if key.startswith("temperature_2m_max") and isinstance(values, list):
                        if target_index < len(values) and values[target_index] is not None:
                            predictions.append(float(values[target_index]))

                logger.info(f"API fetch: {len(predictions)} prédictions pour {target_date_str}")
                return predictions

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des prévisions: {e}")
        return []

def calculate_probabilities(predictions: List[float], ranges: List[TemperatureRange], unit: str = "C") -> Dict[str, float]:
    """
    Calcule les probabilités pour chaque range de température basé sur les prédictions ensemble.
    Gère automatiquement la conversion Celsius/Fahrenheit.

    Args:
        predictions: Liste des prédictions de température (toujours en Celsius de Open-Meteo)
        ranges: Liste des ranges de température du marché
        unit: "C" pour Celsius, "F" pour Fahrenheit

    Returns:
        Dict[str, float]: Probabilités par range {"17°C": 0.74, "52-53°F": 0.28, ...}
    """
    if not predictions:
        return {}

    probabilities = {}
    total_members = len(predictions)

    # Convertir les prédictions en Fahrenheit si nécessaire
    if unit == "F":
        predictions_converted = [(pred * 9/5 + 32) for pred in predictions]
    else:
        predictions_converted = predictions

    # Calculer les probabilités pour chaque range
    for range_obj in ranges:
        count = 0
        label = range_obj.label.lower()

        # Analyser le type de range depuis le label
        if "or below" in label:
            # "69°F or below" → count(pred <= 69.999) pour couvrir tout l'intervalle
            import re
            temp_match = re.search(r'(\d+)°?[cf]?\s+or\s+below', label)
            if temp_match:
                threshold = float(temp_match.group(1)) + 0.999  # Inclure toute la plage
                for pred in predictions_converted:
                    if pred <= threshold:
                        count += 1

        elif "or higher" in label or "or above" in label:
            # "64°F or higher" → count(pred >= 64)
            import re
            temp_match = re.search(r'(\d+)°?[cf]?\s+or\s+(higher|above)', label)
            if temp_match:
                threshold = float(temp_match.group(1))
                for pred in predictions_converted:
                    if pred >= threshold:
                        count += 1

        elif "-" in label and not "below" in label and not "higher" in label:
            # "64-65°F" → count(64 <= pred <= 65.999)
            import re
            range_match = re.search(r'(\d+)-(\d+)°?[cf]?', label)
            if range_match:
                min_temp = float(range_match.group(1))
                max_temp = float(range_match.group(2)) + 0.999  # Inclure tout l'intervalle
                for pred in predictions_converted:
                    if min_temp <= pred <= max_temp:
                        count += 1

        else:
            # "17°C" seul → count(17 <= pred <= 17.999)
            import re
            temp_match = re.search(r'(\d+)°?[cf]?$', label)
            if temp_match:
                temp = float(temp_match.group(1))
                for pred in predictions_converted:
                    if temp <= pred <= temp + 0.999:  # Inclure tout le degré
                        count += 1

        probability = count / total_members
        probabilities[range_obj.label] = probability

    return probabilities

def detect_model_agreement(predictions: List[float]) -> int:
    """
    Détecte le niveau d'accord entre les modèles en groupant par degré entier.
    Fonctionne indépendamment de l'unité (toujours en Celsius).

    Args:
        predictions: Liste des prédictions de température (en Celsius)

    Returns:
        int: Nombre de membres dans le range le plus représenté si >= 25% du total
    """
    if not predictions:
        return 0

    # Grouper par degré entier (toujours en Celsius)
    temp_counts = {}
    for pred in predictions:
        temp_int = int(math.floor(pred))
        temp_counts[temp_int] = temp_counts.get(temp_int, 0) + 1

    # Trouver le range le plus représenté
    max_count = max(temp_counts.values())
    total_members = len(predictions)

    # Vérifier si >= 25% des membres sont d'accord (seuil plus réaliste pour météo)
    # Avec ~100-120 membres, ça donne un minimum de 25-30 modèles d'accord
    if max_count / total_members >= 0.25:
        return max_count

    return 0

async def run_forecaster_loop():
    """
    Boucle principale du Weather Forecaster Agent.
    Récupère les prévisions pour tous les marchés weather actifs.
    """
    logger.info("Démarrage du Weather Forecaster Agent")

    while True:
        try:
            # Récupérer les marchés weather actifs
            weather_markets = await cache.get('weather_markets', [])

            if not weather_markets:
                logger.info("Aucun marché weather actif trouvé")
                await asyncio.sleep(FORECASTER_INTERVAL)
                continue

            forecasts = {}
            processed_count = 0

            for market in weather_markets:
                try:
                    # Vérifier si la ville est supportée
                    if market.city not in CITY_COORDINATES:
                        logger.warning(f"Ville non supportée: {market.city}")
                        continue

                    coords = CITY_COORDINATES[market.city]

                    # Récupérer les prévisions ensemble
                    predictions = await fetch_ensemble_forecast(
                        coords['lat'],
                        coords['lon'],
                        market.target_date
                    )

                    if not predictions:
                        logger.warning(f"Aucune prévision obtenue pour {market.city}")
                        continue

                    # Calculer les probabilités avec gestion de l'unité
                    probabilities = calculate_probabilities(predictions, market.ranges, market.unit)

                    # Détecter l'accord entre modèles
                    agreement_count = detect_model_agreement(predictions)

                    # Créer l'objet WeatherForecast
                    forecast = WeatherForecast(
                        city=market.city,
                        target_date=market.target_date,
                        models_agreement_count=agreement_count,
                        ensemble_members_count=len(predictions),
                        probabilities_by_range=probabilities,
                        raw_predictions=predictions
                    )

                    forecasts[market.condition_id] = forecast
                    processed_count += 1

                    # Rate limiting entre les appels
                    await asyncio.sleep(RATE_LIMIT_DELAY)

                except Exception as e:
                    logger.error(f"Erreur lors du traitement du marché {market.condition_id}: {e}")
                    continue

            # Stocker les prévisions dans le cache
            await cache.set('forecasts', forecasts)

            logger.info(f"Forecaster: {processed_count}/{len(weather_markets)} marchés ont reçu un forecast ensemble")

        except Exception as e:
            logger.error(f"Erreur dans la boucle forecaster: {e}")
            await asyncio.sleep(RETRY_DELAY)
            continue

        # Attendre avant le prochain cycle
        await asyncio.sleep(FORECASTER_INTERVAL)

if __name__ == "__main__":
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Lancer la boucle principale
    asyncio.run(run_forecaster_loop())