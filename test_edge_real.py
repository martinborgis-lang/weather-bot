import asyncio
import logging
from agents.market_scanner import scan_weather_markets
from agents.weather_forecaster import fetch_ensemble_forecast, calculate_probabilities, detect_model_agreement
from shared.models import WeatherForecast
from shared.cache import cache
from shared.cities import CITY_COORDINATES

logging.basicConfig(level=logging.WARNING)

async def main():
    print("=== 1. Scanner markets ===\n")
    markets = await scan_weather_markets()
    print(f"✅ {len(markets)} marchés\n")
    await cache.set('weather_markets', markets)
    
    print("=== 2. Fetching forecasts (avec rate limit) ===\n")
    forecasts = {}
    for i, market in enumerate(markets):
        coords = CITY_COORDINATES.get(market.city)
        if not coords:
            continue
        try:
            predictions = await fetch_ensemble_forecast(coords['lat'], coords['lon'], market.target_date)
            if not predictions:
                continue
            probs = calculate_probabilities(predictions, market.ranges, unit=market.unit)
            agreement = detect_model_agreement(predictions)
            forecasts[market.condition_id] = WeatherForecast(
                city=market.city,
                target_date=market.target_date,
                models_agreement_count=agreement,
                ensemble_members_count=len(predictions),
                probabilities_by_range=probs,
                raw_predictions=predictions
            )
            print(f"  [{i+1}/{len(markets)}] {market.city} {market.target_date.date()} OK")
        except Exception as e:
            print(f"  [{i+1}/{len(markets)}] {market.city}: {e}")
    
    print(f"\n✅ {len(forecasts)} forecasts\n")
    await cache.set('forecasts', forecasts)
    
    print("=== 3. Analyse des edges ===\n")
    
    all_opportunities = []
    for market in markets:
        forecast = forecasts.get(market.condition_id)
        if not forecast:
            continue
        
        for r in market.ranges:
            model_p = forecast.probabilities_by_range.get(r.label, 0.0)
            market_p = r.current_price
            edge = model_p - market_p
            
            if abs(edge) >= 0.15:
                all_opportunities.append({
                    'market_title': market.title,
                    'city': market.city,
                    'date': market.target_date.date(),
                    'range': r.label,
                    'market_p': market_p,
                    'model_p': model_p,
                    'edge': edge,
                    'agreement': forecast.models_agreement_count,
                    'side': 'YES' if edge > 0 else 'NO',
                    'liquidity': market.liquidity_usdc,
                })
    
    all_opportunities.sort(key=lambda x: abs(x['edge']), reverse=True)
    
    print(f"🎯 {len(all_opportunities)} opportunités détectées (edge >= 15 points)\n")
    print(f"{'Ville':<14} {'Date':<12} {'Range':<18} {'Marché':>8} {'Modèles':>8} {'Edge':>8} {'Side':>5} {'Agree':>6} {'Liq':>10}")
    print("-" * 110)
    for opp in all_opportunities[:30]:
        print(f"{opp['city']:<14} {str(opp['date']):<12} {opp['range']:<18} {opp['market_p']:>7.0%} {opp['model_p']:>7.0%} {opp['edge']:>+7.0%} {opp['side']:>5} {opp['agreement']:>6} ${opp['liquidity']:>8.0f}")

asyncio.run(main())