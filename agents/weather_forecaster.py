import asyncio
import aiohttp
import json
import logging
import math
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from shared.models import WeatherMarket, WeatherForecast, TemperatureRange
from shared.cache import cache

# Configuration avec API commerciale
FORECASTER_INTERVAL = 300  # 5 min
RATE_LIMIT_DELAY = 0.2  # 0.2s entre appels API (API commerciale)
RETRY_DELAY = 60
CACHE_TTL_SECONDS = 900  # 15 min (réduit grâce à l'API commerciale)
RETRY_AFTER_429 = 5  # 5s d'attente après 429 (rare maintenant)
MAX_RETRIES_429 = 2  # Maximum 2 tentatives par ville

# Limites quotidiennes API commerciale
DAILY_API_LIMIT = 28800  # ~1M/mois = 33k/jour, on prend 80% = 28.8k
API_ALERT_THRESHOLD = 0.8  # Alerte à 80% du quota

# Import des coordonnées partagées
from shared.cities import CITY_COORDINATES

# Cache en mémoire pour les prévisions
_forecast_cache: Dict[str, Tuple[List[float], float]] = {}

# Semaphore pour rate limiting (3 appels concurrents avec API commerciale)
_api_semaphore = asyncio.Semaphore(3)

# Compteur d'appels API quotidien
_daily_api_calls = 0
_last_reset_date = datetime.now().date()

logger = logging.getLogger(__name__)

def _get_cache_key(lat: float, lon: float, target_date: datetime) -> str:
    """Génère une clé de cache pour les prévisions"""
    return f"{lat:.4f}_{lon:.4f}_{target_date.strftime('%Y-%m-%d')}"

def _is_cache_valid(fetched_at: float, target_date: datetime) -> bool:
    """Vérifie si le cache est encore valide (15 min avec API commerciale)"""
    now = time.time()
    age_seconds = now - fetched_at
    return age_seconds < CACHE_TTL_SECONDS

def _get_cache_info(cache_key: str, target_date: datetime) -> dict:
    """Retourne les infos du cache pour logs"""
    if cache_key not in _forecast_cache:
        return {"status": "MISS", "age_min": None, "expires_min": None}

    predictions, fetched_at = _forecast_cache[cache_key]
    now = time.time()
    age_seconds = now - fetched_at
    expires_seconds = CACHE_TTL_SECONDS - age_seconds

    return {
        "status": "HIT" if expires_seconds > 0 else "EXPIRED",
        "age_min": age_seconds / 60,
        "expires_min": max(0, expires_seconds / 60)
    }

def _reset_daily_counter():
    """Reset le compteur quotidien si nécessaire"""
    global _daily_api_calls, _last_reset_date

    today = datetime.now().date()
    if today != _last_reset_date:
        _daily_api_calls = 0
        _last_reset_date = today
        logger.info(f"🔄 Reset compteur API quotidien: {today}")

def _increment_api_counter():
    """Incrémente le compteur d'appels API"""
    global _daily_api_calls

    _reset_daily_counter()
    _daily_api_calls += 1

    # Alerte si on approche de la limite
    if _daily_api_calls / DAILY_API_LIMIT >= API_ALERT_THRESHOLD:
        remaining = DAILY_API_LIMIT - _daily_api_calls
        logger.warning(f"⚠️ Quota API: {_daily_api_calls}/{DAILY_API_LIMIT} ({_daily_api_calls/DAILY_API_LIMIT:.1%}) - {remaining} appels restants")

def _get_api_usage_info() -> dict:
    """Retourne les stats d'utilisation API"""
    _reset_daily_counter()

    usage_pct = _daily_api_calls / DAILY_API_LIMIT if DAILY_API_LIMIT > 0 else 0
    remaining = max(0, DAILY_API_LIMIT - _daily_api_calls)

    return {
        "calls_today": _daily_api_calls,
        "daily_limit": DAILY_API_LIMIT,
        "usage_percent": usage_pct,
        "remaining": remaining
    }

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

    # Récupérer infos cache pour logs
    cache_info = _get_cache_info(cache_key, target_date)

    # Vérifier le cache d'abord avec logs explicites
    if cache_key in _forecast_cache:
        predictions, fetched_at = _forecast_cache[cache_key]
        if _is_cache_valid(fetched_at, target_date):
            logger.info(f"Cache HIT: {cache_key} (expire dans {cache_info['expires_min']:.1f}min)")
            return predictions
        else:
            # Cache expiré, on le supprime
            logger.info(f"Cache EXPIRED: {cache_key} (âgé de {cache_info['age_min']:.1f}min)")
            del _forecast_cache[cache_key]

    logger.info(f"Cache MISS → API fetch: {cache_key}")

    # Rate limiting avec semaphore
    async with _api_semaphore:
        return await _fetch_ensemble_forecast_impl(lat, lon, target_date, cache_key)

async def _fetch_ensemble_forecast_impl(lat: float, lon: float, target_date: datetime, cache_key: str) -> List[float]:
    """Implémentation interne simplifiée avec API commerciale"""

    url = "https://customer-api.open-meteo.com/v1/ensemble"
    params = {
        'latitude': lat,
        'longitude': lon,
        'daily': 'temperature_2m_max',
        'timezone': 'auto',
        'forecast_days': 7,
        'models': 'ecmwf_ifs025,gfs_seamless,icon_seamless'
    }

    # Ajouter clé API commerciale
    api_key = os.getenv("OPENMETEO_API_KEY")
    if api_key:
        params['apikey'] = api_key
    else:
        logger.warning("OPENMETEO_API_KEY manquante - utilisation API gratuite limitée")

    # Tentatives simples (rare d'avoir des erreurs avec l'API commerciale)
    predictions = None
    for attempt in range(MAX_RETRIES_429):
        predictions = await _try_fetch(url, params, target_date)

        if predictions is not None:
            break
        elif attempt < MAX_RETRIES_429 - 1:
            logger.warning(f"Erreur API (tentative {attempt + 1}/{MAX_RETRIES_429}), retry dans {RETRY_AFTER_429}s...")
            await asyncio.sleep(RETRY_AFTER_429)

    if predictions is None:
        logger.error(f"Échec définitif après {MAX_RETRIES_429} tentatives pour {cache_key}")
        return []

    # Rate limiting léger entre les appels
    await asyncio.sleep(RATE_LIMIT_DELAY)

    # Stocker en cache
    if predictions:
        _forecast_cache[cache_key] = (predictions, time.time())
        logger.debug(f"Cache stocké pour {cache_key}: {len(predictions)} prédictions")

    return predictions

async def _try_fetch(url: str, params: dict, target_date: datetime) -> Optional[List[float]]:
    """Tentative d'appel API avec compteur d'usage"""
    try:
        # Incrémenter le compteur d'appels API
        _increment_api_counter()

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 429:
                    logger.warning("Rate limit 429 détecté (rare avec API commerciale)")
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

                logger.debug(f"API fetch: {len(predictions)} prédictions pour {target_date_str}")
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

async def save_forecast_to_log(forecast: WeatherForecast, market: WeatherMarket):
    """Sauvegarde un forecast dans le log JSON"""
    try:
        data_dir = os.getenv("DATA_DIR", "./data")
        os.makedirs(data_dir, exist_ok=True)
        log_file = os.path.join(data_dir, "forecast_log.json")

        # Charger le log existant
        existing_log = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing_log = json.load(f)
            except:
                existing_log = []

        # Créer l'entrée de log
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'condition_id': market.condition_id,
            'city': forecast.city,
            'target_date': forecast.target_date.isoformat(),
            'ensemble_members_count': forecast.ensemble_members_count,
            'models_agreement_count': forecast.models_agreement_count,
            'agreement_percentage': (forecast.models_agreement_count / forecast.ensemble_members_count * 100) if forecast.ensemble_members_count > 0 else 0,
            'probabilities_by_range': forecast.probabilities_by_range,
            'market_title': getattr(market, 'title', 'Unknown'),
            'unit': getattr(market, 'unit', 'C'),
            'raw_predictions_sample': forecast.raw_predictions[:10] if forecast.raw_predictions else [],  # Échantillon des prédictions
            'min_prediction': min(forecast.raw_predictions) if forecast.raw_predictions else None,
            'max_prediction': max(forecast.raw_predictions) if forecast.raw_predictions else None,
            'avg_prediction': sum(forecast.raw_predictions) / len(forecast.raw_predictions) if forecast.raw_predictions else None
        }

        existing_log.append(log_entry)

        # Garder seulement les 1000 derniers forecasts pour éviter un fichier trop gros
        if len(existing_log) > 1000:
            existing_log = existing_log[-1000:]

        # Sauvegarder avec gestion des datetime
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(existing_log, f, indent=2, ensure_ascii=False, default=str)

        logger.debug(f"💾 Forecast sauvegardé: {forecast.city} {forecast.target_date.strftime('%Y-%m-%d')} - {forecast.ensemble_members_count} membres")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la sauvegarde du forecast: {e}")


async def run_forecaster_loop():
    """
    Boucle principale du Weather Forecaster Agent avec cycle intelligent.
    Récupère les prévisions seulement pour les villes dont le cache est expiré.
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

            # Status de l'API au début du cycle
            api_usage = _get_api_usage_info()

            # Filtrer les villes qui ont besoin d'un forecast (cache expiré ou absent)
            cities_to_fetch = []
            cities_in_cache = 0

            for market in weather_markets:
                if market.city not in CITY_COORDINATES:
                    continue

                coords = CITY_COORDINATES[market.city]
                cache_key = _get_cache_key(coords['lat'], coords['lon'], market.target_date)
                cache_info = _get_cache_info(cache_key, market.target_date)

                if cache_info["status"] == "HIT":
                    cities_in_cache += 1
                else:
                    cities_to_fetch.append(market)

            logger.info(f"Forecaster: {len(cities_to_fetch)} cities to fetch, "
                       f"API calls today: {api_usage['calls_today']}/{api_usage['daily_limit']} "
                       f"({api_usage['usage_percent']:.1%})")

            forecasts = {}
            processed_count = 0
            cache_hits = 0

            for market in weather_markets:
                try:
                    # Vérifier si la ville est supportée
                    if market.city not in CITY_COORDINATES:
                        logger.warning(f"Ville non supportée: {market.city}")
                        continue

                    coords = CITY_COORDINATES[market.city]

                    # Récupérer les prévisions ensemble (avec cache intelligent)
                    predictions = await fetch_ensemble_forecast(
                        coords['lat'],
                        coords['lon'],
                        market.target_date
                    )

                    if not predictions:
                        logger.warning(f"Aucune prévision obtenue pour {market.city}")
                        continue

                    # Compter cache hits vs fetches
                    cache_key = _get_cache_key(coords['lat'], coords['lon'], market.target_date)
                    if cache_key in _forecast_cache:
                        cache_hits += 1

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

                    # Sauvegarder le forecast dans le log JSON pour le dashboard
                    await save_forecast_to_log(forecast, market)

                except Exception as e:
                    logger.error(f"Erreur lors du traitement du marché {market.condition_id}: {e}")
                    continue

            # Stocker les prévisions dans le cache
            await cache.set('forecasts', forecasts)

            # Statistiques finales avec ratio cache hit/miss
            api_fetches = processed_count - cache_hits
            cache_ratio = cache_hits / processed_count if processed_count > 0 else 0

            logger.info(f"Forecaster: {processed_count}/{len(weather_markets)} marchés traités | "
                       f"Cache ratio: {cache_hits}/{processed_count} ({cache_ratio:.1%}) | "
                       f"API fetches: {api_fetches}")

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