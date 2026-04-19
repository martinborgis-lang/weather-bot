from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class TemperatureRange:
    """Un range de température d'un marché (ex: '17°C' signifie [17.0, 17.9])"""
    label: str              # "17°C"
    min_temp: float         # 17.0
    max_temp: float         # 17.999
    token_id: str           # CLOB token_id YES
    current_price: float    # prix actuel du token YES

@dataclass
class WeatherMarket:
    """Un marché météo Polymarket"""
    condition_id: str
    slug: str
    title: str              # "Highest temperature in London on April 22?"
    city: str               # "London"
    target_date: datetime   # date de la mesure
    resolution_source: str  # "Wunderground EGLC"
    liquidity_usdc: float
    volume_usdc: float
    ranges: list[TemperatureRange]
    ends_at: datetime
    unit: str               # "C" ou "F" - détecté depuis les labels des ranges

@dataclass
class WeatherForecast:
    """Prévision météo pour une ville/date donnée"""
    city: str
    target_date: datetime
    models_agreement_count: int      # nb de modèles principaux alignés
    ensemble_members_count: int       # nb de membres ECMWF utilisés
    probabilities_by_range: dict[str, float]  # {"17°C": 0.74, "52-53°F": 0.28, ...}
    raw_predictions: list[float]     # températures prédites brutes (toujours en Celsius)

@dataclass
class TradeSignal:
    """Signal d'entrée détecté par l'edge calculator"""
    market: WeatherMarket
    temperature_range: TemperatureRange
    side: str                        # "YES" ou "NO"
    model_probability: float         # 0.74
    market_implied_probability: float # 0.25
    edge_points: float               # 0.49 (49 points)
    conviction_score: float          # 0.0-1.0
    recommended_size_usdc: float
    reason: str                      # description textuelle

@dataclass
class OpenPosition:
    """Position ouverte trackée"""
    market_condition_id: str
    market_title: str
    temperature_label: str
    side: str
    entry_price: float
    current_price: float
    size_usdc: float
    size_tokens: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    opened_at: datetime
    transaction_hash: Optional[str]  # None si DRY_RUN
    partial_sold: bool = False  # Track si 50% déjà vendus pour take profit