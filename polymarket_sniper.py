"""
Polymarket On-Chain Sniper POC

Écoute les créations de nouveaux marchés Polymarket sur Polygon.
Mesure la latence de détection pour évaluer l'intérêt d'un trading on-chain.
"""

import sys
import io

# Force UTF-8 sur Windows pour éviter les UnicodeEncodeError cp1252
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    # sys.stderr non wrappé : conflit avec argparse / logging stderr handlers
    # Les émojis dans stderr peuvent être moches mais le script fonctionne

import asyncio
import csv
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
from web3 import AsyncWeb3
from web3.providers.persistent import WebSocketProvider
from web3.middleware import ExtraDataToPOAMiddleware
from eth_utils import keccak

load_dotenv()

# Configuration
POLYGON_WSS_URL = os.getenv(
    "POLYGON_WSS_URL",
    "wss://polygon.publicnode.com"
)
CONDITIONAL_TOKENS_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
# Adresses des oracles Polymarket connus
POLYMARKET_ORACLES = {
    "0x6a9d222616c90fca5754cd1333cfd9b7fb6a4f74": "UMA CTF Adapter V2",
    "0x71392e133063cc0d16f40e1f9b60227404bc03f7": "UMA CTF Adapter V1",
    "0xcb1822859cef82cd2eb4e6276c7916e692995130": "UMA Binary Adapter V1",
    "0xd91e80cf2e7be2e162c6513ced06f1dd0da35296": "MOOV2 Adapter (managed)",  # Détecté dans les logs
}
GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CSV_PATH = Path("data/sniper_detections.csv")

# Event signature hashée (keccak256) : ConditionPreparation(bytes32,address,bytes32,uint256)
# Calculer dynamiquement pour éviter les erreurs
CONDITION_PREPARATION_TOPIC = "0x" + keccak(text="ConditionPreparation(bytes32,address,bytes32,uint256)").hex()

# ABI minimal du contrat ConditionalTokens (juste l'event qui nous intéresse)
CONDITIONAL_TOKENS_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "conditionId", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "oracle", "type": "address"},
            {"indexed": True, "internalType": "bytes32", "name": "questionId", "type": "bytes32"},
            {"indexed": False, "internalType": "uint256", "name": "outcomeSlotCount", "type": "uint256"}
        ],
        "name": "ConditionPreparation",
        "type": "event"
    }
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# Sémaphore pour limiter la concurrence des appels Gamma API (éviter surcharge)
gamma_semaphore = asyncio.Semaphore(10)  # max 10 appels Gamma en parallèle


def parse_weather_slug(slug: str) -> tuple:
    """Extract city and date from weather event slug"""
    import re

    # Pattern: daily-temperature-berlin-2026-04-25
    match = re.search(r'daily-temperature-(.+)-(\d{4}-\d{2}-\d{2})', slug)
    if match:
        city = match.group(1).replace('-', ' ').title()
        date = match.group(2)
        return city, date
    return "Unknown", None


def extract_range_from_outcome(outcome_text: str) -> str:
    """Extract temperature range from outcome text"""
    import re

    # Examples: "13°C or below", "14°C", "19°C", "20°C or above"
    match = re.search(r'(\d+°C(?:\s+or\s+(?:below|above))?)', outcome_text)
    if match:
        return match.group(1)
    return outcome_text


def is_weather_market(question: str, slug: str) -> bool:
    """Check if this is a weather market"""
    weather_keywords = ['temperature', 'daily-temperature', '°C', 'celsius', 'fahrenheit']
    text_to_check = f"{question or ''} {slug or ''}".lower()
    return any(keyword in text_to_check for keyword in weather_keywords)


async def enrich_weather_event(slug: str, session: aiohttp.ClientSession) -> dict:
    """Get complete weather event with all ranges"""
    try:
        url = f"{GAMMA_API_BASE}/events?slug={slug}"
        async with session.get(url, timeout=10) as resp:
            if resp.status != 200:
                return None

            data = await resp.json()
            if not data:
                return None

            event = data[0]

            ranges = []
            for market in event.get("markets", []):
                outcome_prices = market.get("outcomePrices", [0, 0])
                ranges.append({
                    "condition_id": market["conditionId"],
                    "clob_token_ids": market.get("clobTokenIds", []),
                    "label": extract_range_from_outcome(market["outcomeText"]),
                    "yes_price": float(outcome_prices[0]) if len(outcome_prices) > 0 else 0,
                    "no_price": float(outcome_prices[1]) if len(outcome_prices) > 1 else 0,
                    "volume": float(market.get("volume", 0)),
                    "liquidity": float(market.get("liquidity", 0)),
                })

            # Extract city and date from slug
            city, target_date = parse_weather_slug(event["slug"])

            return {
                "city": city,
                "target_date": target_date,
                "event_slug": event["slug"],
                "end_date": event.get("endDate"),
                "ranges": ranges,
                "total_liquidity": sum(r["liquidity"] for r in ranges),
                "ranges_count": len(ranges)
            }

    except Exception as e:
        logger.debug(f"Error enriching weather event {slug}: {e}")
        return None


async def enrich_via_gamma(condition_id: str, session: aiohttp.ClientSession, max_retries: int = 6):  # 6*5s = 30s au lieu de 2min
    """
    Interroge Gamma API pour enrichir le market.
    Retry toutes les 5s pendant 2 min max.
    """
    url = f"{GAMMA_API_BASE}/markets?condition_ids={condition_id}"
    started_at = time.time()

    for attempt in range(max_retries):
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and len(data) > 0:
                        elapsed_ms = int((time.time() - started_at) * 1000)
                        market = data[0]

                        # Extraire les tags de façon sécurisée
                        tags = []
                        events = market.get('events', [])
                        if events and len(events) > 0:
                            event_tags = events[0].get('tags', [])
                            tags = [t.get('slug', 'unknown') for t in event_tags[:3]]

                        question = market.get('question', 'N/A')
                        slug = market.get('slug', 'N/A')
                        is_weather = is_weather_market(question, slug)

                        logger.info(
                            f"  📊 Gamma enrich ({elapsed_ms}ms after detect):\n"
                            f"     Question: {question[:100]}\n"
                            f"     Slug: {slug[:50]}\n"
                            f"     Tags: {tags}\n"
                            f"     Volume: ${market.get('volume', 0):,.0f}\n"
                            f"     Liquidity: ${market.get('liquidity', 0):,.0f}\n"
                            f"     Weather Market: {is_weather}"
                        )

                        result = {
                            "gamma_delay_ms": elapsed_ms,
                            "question": question,
                            "slug": slug,
                            "volume": market.get("volume", 0),
                            "liquidity": market.get("liquidity", 0),
                            "tags": ",".join(tags) if tags else None,
                            "is_weather_market": is_weather,
                            "gamma_confirmed": True
                        }

                        # Si c'est un marché météo, enrichir avec tous les ranges
                        if is_weather and slug != 'N/A':
                            weather_data = await enrich_weather_event(slug, session)
                            if weather_data:
                                result.update(weather_data)

                        return result
        except Exception as e:
            logger.debug(f"  Gamma attempt {attempt+1} error: {e}")

        await asyncio.sleep(5)

    logger.warning(f"  ⚠️  Gamma never returned market for {condition_id[:10]}... after 30s")
    return None


def write_csv_row(row: dict):
    """Append une ligne au CSV, crée le fichier + header si absent."""
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "detected_at_utc", "block_number", "block_ts_utc",
            "detection_latency_ms", "condition_id", "question_id",
            "oracle", "oracle_name", "is_polymarket", "gamma_delay_ms",
            "question", "slug", "volume", "liquidity", "tags",
            "is_weather_market", "city", "target_date", "total_liquidity",
            "ranges_count", "gamma_confirmed"
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


async def handle_event(event_log, w3, gamma_session):
    """Traite un event ConditionPreparation."""
    try:
        detected_ms = int(time.time() * 1000)

        # Créer le contrat pour décoder
        contract = w3.eth.contract(
            address=CONDITIONAL_TOKENS_ADDRESS,
            abi=CONDITIONAL_TOKENS_ABI
        )

        # Décoder l'event log
        decoded_event = contract.events.ConditionPreparation().process_log(event_log)
        args = decoded_event["args"]

        condition_id = "0x" + args["conditionId"].hex()
        question_id = "0x" + args["questionId"].hex()
        oracle = args["oracle"].lower()
        block_number = event_log["blockNumber"]

        # Récupérer le timestamp du bloc
        block = await w3.eth.get_block(block_number)
        block_ts = block["timestamp"]
        block_ts_ms = block_ts * 1000

        latency_ms = detected_ms - block_ts_ms
        is_polymarket_oracle = oracle in POLYMARKET_ORACLES
        oracle_name = POLYMARKET_ORACLES.get(oracle, "Unknown")

        emoji = "🎯" if is_polymarket_oracle else "📡"
        logger.info(
            f"\n{emoji} CONDITION PREPARATION EVENT\n"
            f"  condition_id : {condition_id}\n"
            f"  question_id  : {question_id}\n"
            f"  oracle       : {oracle}\n"
            f"  oracle_name  : {oracle_name}\n"
            f"  known_oracle : {is_polymarket_oracle}\n"
            f"  block        : {block_number}\n"
            f"  block_ts_utc : {datetime.fromtimestamp(block_ts, timezone.utc).isoformat()}\n"
            f"  detected_ts  : {datetime.fromtimestamp(detected_ms/1000, timezone.utc).isoformat()}\n"
            f"  latency      : {latency_ms}ms"
        )

        # Enrichissement Gamma avec semaphore (tenter même si oracle inconnu)
        async with gamma_semaphore:
            gamma_data = await enrich_via_gamma(condition_id, gamma_session)

        # Déterminer la classification Polymarket finale
        if is_polymarket_oracle and gamma_data:
            polymarket_status = "Confirmed Polymarket (oracle match)"
        elif not is_polymarket_oracle and gamma_data:
            polymarket_status = "Confirmed Polymarket (Gamma only)"
            logger.warning(f"  ⚠️  NEW POLYMARKET ORACLE DETECTED: {oracle} - Add to POLYMARKET_ORACLES!")
        elif is_polymarket_oracle and not gamma_data:
            polymarket_status = "Known oracle (Gamma timeout)"
        else:
            polymarket_status = "Not Polymarket"

        is_polymarket_final = gamma_data is not None
        logger.info(f"  📊 Classification: {polymarket_status}")

        # Log enrichi pour les marchés météo
        # Log enrichi pour les marchés météo
        if gamma_data and gamma_data.get("is_weather_market"):
            ranges = gamma_data.get("ranges", [])
            logger.info(
                f"\n🌡️  POLYMARKET WEATHER MARKET DETECTED\n"
                f"  Detection latency     : {latency_ms}ms\n"
                f"  Gamma indexing delay  : {gamma_data.get('gamma_delay_ms', 0)}ms\n"
                f"  City                  : {gamma_data.get('city', 'Unknown')}\n"
                f"  Target date           : {gamma_data.get('target_date', 'Unknown')}\n"
                f"  Ranges available      : {gamma_data.get('ranges_count', 0)}\n"
                f"  Total liquidity       : ${gamma_data.get('total_liquidity', 0):,.0f}"
            )

            if ranges and len(ranges) <= 15:  # Éviter un log trop long
                logger.info("  Price distribution:")
                for r in sorted(ranges, key=lambda x: float(x.get('label', '0°C').replace('°C', '').replace(' or below', '').replace(' or above', '').split()[0])):
                    yes_price = r.get('yes_price', 0)
                    no_price = r.get('no_price', 0)
                    if yes_price > 0.5:
                        main_side = f"YES @ {yes_price:.1%}"
                    else:
                        main_side = f"NO @ {no_price:.1%}"
                    logger.info(f"    {r.get('label', 'N/A'):15} : {main_side}")

        # CSV avec tous les nouveaux champs
        csv_row = {
            "detected_at_utc": datetime.fromtimestamp(detected_ms/1000, timezone.utc).isoformat(),
            "block_number": block_number,
            "block_ts_utc": datetime.fromtimestamp(block_ts, timezone.utc).isoformat(),
            "detection_latency_ms": latency_ms,
            "condition_id": condition_id,
            "question_id": question_id,
            "oracle": oracle,
            "oracle_name": oracle_name,
            "is_polymarket": is_polymarket_final,
            "gamma_delay_ms": gamma_data.get("gamma_delay_ms") if gamma_data else None,
            "question": gamma_data.get("question") if gamma_data else None,
            "slug": gamma_data.get("slug") if gamma_data else None,
            "volume": gamma_data.get("volume") if gamma_data else None,
            "liquidity": gamma_data.get("liquidity") if gamma_data else None,
            "tags": gamma_data.get("tags") if gamma_data else None,
            "is_weather_market": gamma_data.get("is_weather_market", False) if gamma_data else False,
            "city": gamma_data.get("city") if gamma_data else None,
            "target_date": gamma_data.get("target_date") if gamma_data else None,
            "total_liquidity": gamma_data.get("total_liquidity") if gamma_data else None,
            "ranges_count": gamma_data.get("ranges_count") if gamma_data else None,
            "gamma_confirmed": gamma_data is not None,
        }

        write_csv_row(csv_row)

    except Exception as e:
        logger.error(f"Erreur dans handle_event: {e}", exc_info=True)


async def main():
    logger.info("=" * 70)
    logger.info("🎯 Polymarket On-Chain Sniper POC")
    logger.info("=" * 70)
    logger.info(f"RPC WebSocket : {POLYGON_WSS_URL}")
    logger.info(f"Contract      : {CONDITIONAL_TOKENS_ADDRESS} (ConditionalTokens)")
    logger.info(f"Event         : ConditionPreparation")
    logger.info(f"Computed topic: {CONDITION_PREPARATION_TOPIC}")
    logger.info(f"CSV output    : {CSV_PATH}")
    logger.info("=" * 70)

    # Vérification critique du topic
    expected_topic = "0xab3760c3bd4bbe6b90a3d2dbf97cefdafea8a6fddab1a0bb6885ea2ad3062a0b"
    if CONDITION_PREPARATION_TOPIC.lower() != expected_topic.lower():
        logger.warning(f"⚠️  Topic différent attendu! Utilisation du calculé: {CONDITION_PREPARATION_TOPIC}")
    else:
        logger.info("✅ Topic hash vérifié")

    async with aiohttp.ClientSession() as gamma_session:
        retry_count = 0
        max_retries = 5

        while retry_count < max_retries:
            try:
                logger.info(f"🔌 Connexion WebSocket (tentative {retry_count + 1}/{max_retries})...")

                w3 = AsyncWeb3(WebSocketProvider(POLYGON_WSS_URL))
                await w3.provider.connect()

                # Test connection
                latest_block = await w3.eth.get_block_number()
                logger.info(f"✅ Connecté! Latest block: {latest_block}")

                # Inject POA middleware for Polygon compatibility
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                logger.info("✅ POA middleware injected for Polygon compatibility")

                # Subscribe aux logs du contrat ConditionalTokens
                filter_params = {
                    "address": CONDITIONAL_TOKENS_ADDRESS,
                    "topics": [CONDITION_PREPARATION_TOPIC]
                }

                logger.info(f"📡 Création du filtre: {filter_params}")
                subscription_id = await w3.eth.subscribe("logs", filter_params)
                logger.info(f"✅ Subscribed to logs (subscription_id={subscription_id})")
                logger.info("⏳ En attente de nouveaux markets...\n")

                async for message in w3.socket.process_subscriptions():
                    try:
                        if "result" in message:
                            raw_log = message["result"]
                            # Traiter l'event en parallèle (ne bloque pas la queue WebSocket)
                            asyncio.create_task(handle_event(raw_log, w3, gamma_session))
                        else:
                            logger.debug(f"Message sans result: {message}")
                    except Exception as e:
                        logger.error(f"Erreur traitement event: {e}", exc_info=True)

            except Exception as e:
                retry_count += 1
                logger.error(f"❌ WebSocket error (tentative {retry_count}): {e}")
                if retry_count < max_retries:
                    wait_time = 5 * retry_count
                    logger.info(f"⏳ Attente {wait_time}s avant reconnection...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("🚫 Nombre maximum de tentatives atteint")
                    break
            finally:
                try:
                    if 'w3' in locals():
                        await w3.provider.disconnect()
                except:
                    pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Arrêt du sniper")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)