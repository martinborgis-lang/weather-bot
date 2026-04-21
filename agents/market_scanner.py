import asyncio
import aiohttp
import re
import json
import logging
from datetime import datetime, timedelta
from typing import List
from shared.models import WeatherMarket, TemperatureRange
from shared.cache import cache

# Constantes
EVENT_LIQUIDITY_MIN = 10000
SCANNER_INTERVAL = 900  # 15 min
RETRY_DELAY = 60
MIN_TIME_BEFORE_END = 7200  # 2h minimum avant la fin

# Configuration du logger
logger = logging.getLogger(__name__)

# Import des villes supportées
from shared.cities import CITY_COORDINATES
SUPPORTED_CITIES = set(CITY_COORDINATES.keys())

class MarketScanner:
    """Scanner pour détecter les events météo actifs sur Polymarket"""

    def __init__(self):
        self.session: aiohttp.ClientSession = None
        self.running = False

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _parse_event_title(self, title: str) -> tuple[str, datetime]:
        """Parse le titre pour extraire la ville et la date

        Exemple: 'Highest temperature in London on April 22?' -> ('London', datetime(2026, 4, 22))
        """
        pattern = r'Highest temperature in ([\w\s]+?) on (\w+ \d+)'
        match = re.search(pattern, title)

        if not match:
            raise ValueError(f"Titre ne matche pas le pattern: {title}")

        city = match.group(1).strip()
        date_str = match.group(2)  # "April 22"

        # Vérifier que la ville est supportée
        if city not in SUPPORTED_CITIES:
            raise ValueError(f"Ville non supportée: {city}")

        # Parse la date en utilisant l'année courante ou suivante
        current_year = datetime.now().year
        try:
            target_date = datetime.strptime(f"{date_str} {current_year}", "%B %d %Y")
            # Si la date est déjà passée cette année, essayer l'année suivante
            if target_date.date() < datetime.now().date():
                target_date = datetime.strptime(f"{date_str} {current_year + 1}", "%B %d %Y")
        except ValueError:
            # Si échec, essayer avec l'année suivante
            target_date = datetime.strptime(f"{date_str} {current_year + 1}", "%B %d %Y")

        return city, target_date

    def _parse_temperature_from_label(self, label: str) -> tuple[float, float]:
        """Parse un label de température en min/max

        Exemples:
        - "13°C or below" → (0, 13)
        - "14°C" → (14, 14.999)
        - "20°C or above" → (20, 99)
        - "19°C or higher" → (19, 99)
        - "70°F" → (21.1, 22.1) (converti en Celsius)
        - "47°F or below" → (0, 8.3)
        """
        # Détecter si c'est en Fahrenheit ou Celsius
        is_fahrenheit = '°F' in label or 'F' in label

        # Extraire le(s) nombre(s)
        if is_fahrenheit:
            # Patterns Fahrenheit: "70°F", "47°F or below", "48-49°F"
            if '-' in label:
                # Range comme "48-49°F"
                temp_match = re.search(r'(\d+)-(\d+)°?F', label)
                if temp_match:
                    temp_min_f = float(temp_match.group(1))
                    temp_max_f = float(temp_match.group(2))
                    # Convertir en Celsius
                    temp_min_c = (temp_min_f - 32) * 5/9
                    temp_max_c = (temp_max_f - 32) * 5/9
                    return temp_min_c, temp_max_c + 0.999
            else:
                # Simple comme "70°F"
                temp_match = re.search(r'(\d+)°?F', label)
                if temp_match:
                    temp_f = float(temp_match.group(1))
                    temp_c = (temp_f - 32) * 5/9

                    if "or below" in label.lower():
                        return 0.0, temp_c
                    elif "or above" in label.lower() or "or higher" in label.lower():
                        return temp_c, 99.0
                    else:
                        # Température exacte
                        return temp_c, temp_c + 0.999
        else:
            # Celsius
            temp_match = re.search(r'(\d+)°?C?', label)
            if not temp_match:
                raise ValueError(f"Impossible de parser la température depuis: {label}")

            temp = float(temp_match.group(1))

            if "or below" in label.lower():
                return 0.0, temp
            elif "or above" in label.lower() or "or higher" in label.lower():
                return temp, 99.0
            else:
                # Température exacte
                return temp, temp + 0.999

        raise ValueError(f"Pattern de température non reconnu: {label}")

    def _parse_temperature_range(self, market: dict) -> TemperatureRange:
        """Parse un sub-market en TemperatureRange"""
        label = market.get('groupItemTitle', '')

        # Parse les températures min/max
        min_temp, max_temp = self._parse_temperature_from_label(label)

        # Parse clobTokenIds (JSON string)
        clob_token_ids_str = market.get('clobTokenIds', '[]')
        try:
            clob_token_ids = json.loads(clob_token_ids_str)
            if not clob_token_ids:
                raise ValueError("Pas de clobTokenIds")
            token_id = clob_token_ids[0]  # Token YES
        except (json.JSONDecodeError, IndexError) as e:
            raise ValueError(f"Erreur parsing clobTokenIds: {e}")

        # Parse outcomePrices (JSON string)
        outcome_prices_str = market.get('outcomePrices', '["0", "1"]')
        try:
            outcome_prices = json.loads(outcome_prices_str)
            current_price = float(outcome_prices[0])  # Prix YES
        except (json.JSONDecodeError, IndexError, ValueError) as e:
            raise ValueError(f"Erreur parsing outcomePrices: {e}")

        # Skip si prix extrêmes (déjà résolu)
        if current_price <= 0.001 or current_price >= 0.999:
            raise ValueError(f"Prix extrême détecté: {current_price}")

        return TemperatureRange(
            label=label,
            min_temp=min_temp,
            max_temp=max_temp,
            token_id=token_id,
            current_price=current_price
        )

    def _is_valid_event(self, event_data: dict) -> bool:
        """Vérifie si un event respecte nos critères de filtrage"""
        try:
            # Vérification du titre et parsing
            title = event_data.get('title', '')
            city, target_date = self._parse_event_title(title)

            # Vérification date dans le futur et dans les 7 prochains jours
            now = datetime.now()
            max_date = now + timedelta(days=7)
            min_end_time = now + timedelta(seconds=MIN_TIME_BEFORE_END)

            if target_date.date() < now.date() or target_date.date() > max_date.date():
                return False

            # Vérification endDate
            end_date_str = event_data.get('endDate')
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    if end_date.replace(tzinfo=None) < min_end_time:
                        return False
                except Exception:
                    return False

            # Vérification liquidité au niveau event
            liquidity = float(event_data.get('liquidity', 0))
            if liquidity < EVENT_LIQUIDITY_MIN:
                return False

            # Vérification qu'il y a des sub-markets
            markets = event_data.get('markets', [])
            if len(markets) < 3:  # Au moins 3 ranges de température
                return False

            return True

        except Exception as e:
            logger.warning(f"Erreur validation event: {e}")
            return False

    def _parse_event(self, event_data: dict) -> WeatherMarket:
        """Parse un event depuis l'API en WeatherMarket"""
        title = event_data['title']
        city, target_date = self._parse_event_title(title)

        # Parse la date de fin
        end_date_str = event_data.get('endDate')
        if end_date_str:
            try:
                ends_at = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                ends_at = ends_at.replace(tzinfo=None)  # Remove timezone for consistency
            except Exception:
                ends_at = target_date + timedelta(days=1)
        else:
            ends_at = target_date + timedelta(days=1)

        # Parse les ranges de température depuis les sub-markets
        ranges = []
        markets = event_data.get('markets', [])

        for market in markets:
            try:
                temp_range = self._parse_temperature_range(market)
                ranges.append(temp_range)
            except ValueError as e:
                logger.warning(f"Erreur parsing range {market.get('groupItemTitle', 'unknown')}: {e}")
                continue

        if not ranges:
            raise ValueError(f"Aucun range valide trouvé pour event: {title}")

        # Détecter l'unité depuis les labels
        unit = "C"  # Par défaut Celsius
        for temp_range in ranges:
            if '°F' in temp_range.label or 'F' in temp_range.label:
                unit = "F"
                break

        # Utiliser le conditionId du premier market comme identifiant principal
        condition_id = markets[0].get('conditionId', event_data.get('slug', 'unknown'))

        # Parse resolution datetime depuis endDate
        resolution_datetime = None
        end_date_str = event_data.get('endDate')
        if end_date_str:
            try:
                resolution_datetime = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                resolution_datetime = resolution_datetime.replace(tzinfo=None)  # Remove timezone for consistency
            except Exception as e:
                logger.warning(f"Impossible de parser endDate {end_date_str}: {e}")

        return WeatherMarket(
            condition_id=condition_id,
            slug=event_data.get('slug', ''),
            title=title,
            city=city,
            target_date=target_date,
            resolution_source="",  # Pas fourni dans l'API events
            liquidity_usdc=float(event_data.get('liquidity', 0)),
            volume_usdc=float(event_data.get('volume', 0)),
            ranges=ranges,
            ends_at=ends_at,
            unit=unit,
            resolution_datetime=resolution_datetime
        )

    async def scan_weather_markets(self) -> List[WeatherMarket]:
        """Scan les events météo actifs sur Polymarket"""
        if not self.session:
            raise RuntimeError("Session HTTP non initialisée")

        url = "https://gamma-api.polymarket.com/events"
        params = {
            'active': 'true',
            'closed': 'false',
            'limit': 500,
            'tag_slug': 'daily-temperature'
        }

        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                events_data = await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"Erreur HTTP lors du scan: {e}")
            raise

        # Assurer que events_data est une liste
        if not isinstance(events_data, list):
            logger.error(f"Format de réponse inattendu: {type(events_data)}")
            return []

        logger.info(f"Scanner: {len(events_data)} events daily-temperature trouvés")

        valid_markets = []
        city_counts = {}

        for event_data in events_data:
            try:
                # Filtre d'abord selon nos critères
                if not self._is_valid_event(event_data):
                    continue

                # Parse l'event
                market = self._parse_event(event_data)
                valid_markets.append(market)

                # Compter par ville pour le log
                city = market.city
                city_counts[city] = city_counts.get(city, 0) + 1

                logger.info(f"Retenu: {market.title} | Liq: ${market.liquidity_usdc:.0f} | Ranges: {len(market.ranges)}")

            except Exception as e:
                logger.warning(f"Erreur parsing event {event_data.get('title', 'unknown')}: {e}")
                continue

        # Log de synthèse
        logger.info(f"Scanner: {len(events_data)} events trouvés, {len(valid_markets)} retenus après filtrage")
        if city_counts:
            cities_summary = ", ".join([f"{city}({count})" for city, count in city_counts.items()])
            logger.info(f"Scanner: Villes retenues: {cities_summary}")

        return valid_markets

    async def run_scanner_loop(self):
        """Lance la boucle principale du scanner"""
        self.running = True
        logger.info("Démarrage du Market Scanner (Events API)")

        while self.running:
            try:
                # Scan des markets
                markets = await self.scan_weather_markets()

                # Mise à jour du cache
                await cache.set('weather_markets', markets)

                logger.info(f"Cache mis à jour avec {len(markets)} marchés weather")

                # Attendre avant le prochain cycle
                await asyncio.sleep(SCANNER_INTERVAL)

            except Exception as e:
                logger.error(f"Erreur dans le scanner loop: {e}")
                logger.info(f"Retry dans {RETRY_DELAY}s")
                await asyncio.sleep(RETRY_DELAY)

    def stop(self):
        """Arrête la boucle du scanner"""
        self.running = False
        logger.info("Arrêt du Market Scanner demandé")


# Fonctions utilitaires pour usage externe
async def scan_weather_markets() -> List[WeatherMarket]:
    """Fonction utilitaire pour scanner les marchés une seule fois"""
    async with MarketScanner() as scanner:
        return await scanner.scan_weather_markets()


async def run_scanner_loop():
    """Fonction utilitaire pour lancer la boucle du scanner"""
    async with MarketScanner() as scanner:
        await scanner.run_scanner_loop()


if __name__ == "__main__":
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Lancement du scanner
    asyncio.run(run_scanner_loop())