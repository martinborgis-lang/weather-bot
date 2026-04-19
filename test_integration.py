#!/usr/bin/env python3
"""
Test d'intégration du Weather Trading Bot
Simule un cycle complet avec des données mockées
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from shared.models import WeatherMarket, TemperatureRange, WeatherForecast, TradeSignal, OpenPosition
from shared.cache import cache
from agents.market_scanner import MarketScanner
from agents.weather_forecaster import calculate_probabilities, detect_model_agreement
from agents.edge_calculator import calculate_edge
from agents.trade_executor import TradeExecutor

# Configuration du logging pour les tests
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegrationTest:
    """Suite de tests d'intégration"""

    def __init__(self):
        self.test_results = {}

    def create_mock_event_data(self):
        """Crée des données d'événements simulées (nouvelle structure Events API)"""
        return [
            {
                'title': 'Highest temperature in London on April 22?',
                'slug': 'london-temp-april-22',
                'liquidity': 25000.0,
                'volume': 50000.0,
                'endDate': (datetime.now() + timedelta(days=2)).isoformat() + 'Z',
                'markets': [
                    {
                        'conditionId': 'mock_condition_16',
                        'groupItemTitle': '16°C',
                        'clobTokenIds': '["token_16_yes", "token_16_no"]',
                        'outcomePrices': '["0.15", "0.85"]'
                    },
                    {
                        'conditionId': 'mock_condition_17',
                        'groupItemTitle': '17°C',
                        'clobTokenIds': '["token_17_yes", "token_17_no"]',
                        'outcomePrices': '["0.25", "0.75"]'
                    },
                    {
                        'conditionId': 'mock_condition_18',
                        'groupItemTitle': '18°C',
                        'clobTokenIds': '["token_18_yes", "token_18_no"]',
                        'outcomePrices': '["0.40", "0.60"]'
                    },
                    {
                        'conditionId': 'mock_condition_19',
                        'groupItemTitle': '19°C',
                        'clobTokenIds': '["token_19_yes", "token_19_no"]',
                        'outcomePrices': '["0.20", "0.80"]'
                    },
                    {
                        'conditionId': 'mock_condition_20',
                        'groupItemTitle': '20°C',
                        'clobTokenIds': '["token_20_yes", "token_20_no"]',
                        'outcomePrices': '["0.10", "0.90"]'
                    }
                ]
            },
            {
                'title': 'Highest temperature in NYC on April 23?',
                'slug': 'nyc-temp-april-23',
                'liquidity': 30000.0,
                'volume': 60000.0,
                'endDate': (datetime.now() + timedelta(days=3)).isoformat() + 'Z',
                'markets': [
                    {
                        'conditionId': 'mock_condition_70',
                        'groupItemTitle': '70°F',
                        'clobTokenIds': '["token_70_yes", "token_70_no"]',
                        'outcomePrices': '["0.15", "0.85"]'
                    },
                    {
                        'conditionId': 'mock_condition_71',
                        'groupItemTitle': '71°F',
                        'clobTokenIds': '["token_71_yes", "token_71_no"]',
                        'outcomePrices': '["0.30", "0.70"]'
                    },
                    {
                        'conditionId': 'mock_condition_72',
                        'groupItemTitle': '72°F',
                        'clobTokenIds': '["token_72_yes", "token_72_no"]',
                        'outcomePrices': '["0.35", "0.65"]'
                    },
                    {
                        'conditionId': 'mock_condition_73',
                        'groupItemTitle': '73°F',
                        'clobTokenIds': '["token_73_yes", "token_73_no"]',
                        'outcomePrices': '["0.20", "0.80"]'
                    }
                ]
            }
        ]

    def create_mock_weather_data(self):
        """Crée des prédictions météo simulées"""
        return {
            'daily': {
                'time': [(datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')],
                'temperature_2m_max': [
                    # Ensemble de prédictions favorisant 18°C pour London
                    [18.1, 18.2, 17.9, 18.3, 18.0, 18.1, 17.8, 18.2, 18.0, 18.1,
                     18.3, 18.0, 17.9, 18.1, 18.2, 18.0, 18.1, 18.3, 17.8, 18.0,
                     17.9, 18.2, 18.1, 18.0, 18.3, 18.1, 17.8, 18.0, 18.2, 18.1,
                     18.0, 18.1, 17.9, 18.2, 18.3, 18.0, 18.1, 17.8, 18.0, 18.2,
                     18.1, 18.0, 18.3, 17.9, 18.1, 18.0, 18.2, 17.8, 18.1, 18.0]
                ]
            }
        }

    async def test_market_scanner(self):
        """Test du Market Scanner"""
        logger.info("🔍 Test Market Scanner...")

        try:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=self.create_mock_event_data())

            with patch('aiohttp.ClientSession.get') as mock_get:
                mock_get.return_value.__aenter__.return_value = mock_response

                async with MarketScanner() as scanner:
                    markets = await scanner.scan_weather_markets()

                    # Vérifications
                    assert len(markets) == 2, f"Attendu 2 marchés, trouvé {len(markets)}"
                    assert markets[0].city == "London"
                    assert markets[1].city == "NYC"
                    assert len(markets[0].ranges) == 5

                    # Stocker dans le cache
                    await cache.set('weather_markets', markets)

                    self.test_results['market_scanner'] = 'PASSED'
                    logger.info("✅ Market Scanner: PASSED")

        except Exception as e:
            self.test_results['market_scanner'] = f'FAILED: {e}'
            logger.error(f"❌ Market Scanner: FAILED - {e}")

    async def test_weather_forecaster(self):
        """Test du Weather Forecaster"""
        logger.info("🌤️  Test Weather Forecaster...")

        try:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=self.create_mock_weather_data())

            with patch('aiohttp.ClientSession.get') as mock_get:
                mock_get.return_value.__aenter__.return_value = mock_response

                # Récupérer les marchés
                markets = await cache.get('weather_markets', [])
                assert len(markets) > 0, "Aucun marché disponible"

                # Simuler les prédictions
                predictions = [18.1, 18.2, 17.9, 18.3, 18.0] * 10  # 50 prédictions autour de 18°C

                # Test calcul des probabilités
                market = markets[0]  # London
                probabilities = calculate_probabilities(predictions, market.ranges, market.unit)

                # Test détection accord modèles
                agreement = detect_model_agreement(predictions)

                # Créer forecast
                forecast = WeatherForecast(
                    city=market.city,
                    target_date=market.target_date,
                    models_agreement_count=agreement,
                    ensemble_members_count=len(predictions),
                    probabilities_by_range=probabilities,
                    raw_predictions=predictions
                )

                # Stocker dans le cache
                forecasts = {market.condition_id: forecast}
                await cache.set('forecasts', forecasts)

                # Vérifications
                assert "18°C" in probabilities, "Label 18°C manquante dans les probabilités"
                assert probabilities["18°C"] > 0.7, f"Probabilité 18°C trop faible: {probabilities['18°C']}"
                assert agreement >= 40, f"Accord modèles trop faible: {agreement}"

                self.test_results['weather_forecaster'] = 'PASSED'
                logger.info("✅ Weather Forecaster: PASSED")

        except Exception as e:
            self.test_results['weather_forecaster'] = f'FAILED: {e}'
            logger.error(f"❌ Weather Forecaster: FAILED - {e}")

    async def test_edge_calculator(self):
        """Test de l'Edge Calculator"""
        logger.info("🎯 Test Edge Calculator...")

        try:
            # Récupérer données du cache
            markets = await cache.get('weather_markets', [])
            forecasts = await cache.get('forecasts', {})

            assert len(markets) > 0 and len(forecasts) > 0, "Données manquantes"

            market = markets[0]  # London
            forecast = forecasts[market.condition_id]

            # Simuler des prix de marché sous-évaluant 18°C
            for i, range_obj in enumerate(market.ranges):
                if range_obj.label == '18°C':
                    range_obj.current_price = 0.25  # Prix marché: 25%
                else:
                    range_obj.current_price = 0.15  # Autres: 15%

            # Calculer les edges
            signals = calculate_edge(market, forecast)

            # Stocker dans le cache
            await cache.set('trade_signals', signals)

            # Vérifications
            assert len(signals) > 0, "Aucun signal généré"

            signal_18c = next((s for s in signals if s.temperature_range.label == '18°C'), None)
            assert signal_18c is not None, "Signal pour 18°C non trouvé"
            assert signal_18c.edge_points > 0.2, f"Edge trop faible: {signal_18c.edge_points}"
            assert signal_18c.side == "YES", f"Côté incorrect: {signal_18c.side}"

            self.test_results['edge_calculator'] = 'PASSED'
            logger.info("✅ Edge Calculator: PASSED")

        except Exception as e:
            self.test_results['edge_calculator'] = f'FAILED: {e}'
            logger.error(f"❌ Edge Calculator: FAILED - {e}")

    async def test_trade_executor(self):
        """Test du Trade Executor"""
        logger.info("💼 Test Trade Executor...")

        try:
            # Forcer DRY_RUN pour le test
            import os
            os.environ['DRY_RUN'] = 'true'

            # Récupérer les signaux
            signals = await cache.get('trade_signals', [])
            assert len(signals) > 0, "Aucun signal disponible"

            # Tester l'exécuteur
            executor = TradeExecutor()
            await executor._initialize_clob_client()

            # Exécuter un signal
            signal = signals[0]
            success = await executor.execute_signal(signal)

            # Vérifications
            assert success, "Exécution du signal échouée"

            # Vérifier les positions créées
            positions = await cache.get('open_positions', [])
            assert len(positions) > 0, "Aucune position créée"

            position = positions[0]
            assert position.market_condition_id == signal.market.condition_id
            assert position.side == signal.side
            assert position.size_usdc == signal.recommended_size_usdc

            self.test_results['trade_executor'] = 'PASSED'
            logger.info("✅ Trade Executor: PASSED")

        except Exception as e:
            self.test_results['trade_executor'] = f'FAILED: {e}'
            logger.error(f"❌ Trade Executor: FAILED - {e}")

    async def test_position_manager(self):
        """Test du Position Manager"""
        logger.info("📊 Test Position Manager...")

        try:
            # Mock de l'API prix
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={'price': 0.30})

            with patch('aiohttp.ClientSession.get') as mock_get:
                mock_get.return_value.__aenter__.return_value = mock_response

                from agents.position_manager import PositionManager

                pm = PositionManager()
                pm.session = MagicMock()
                pm.session.get = mock_get

                # Test mise à jour des prix
                await pm.update_position_prices()

                # Vérifier que les positions ont été mises à jour
                positions = await cache.get('open_positions', [])
                if positions:
                    position = positions[0]
                    assert position.current_price == 0.30, "Prix non mis à jour"

                self.test_results['position_manager'] = 'PASSED'
                logger.info("✅ Position Manager: PASSED")

        except Exception as e:
            self.test_results['position_manager'] = f'FAILED: {e}'
            logger.error(f"❌ Position Manager: FAILED - {e}")

    async def run_all_tests(self):
        """Lance tous les tests d'intégration"""
        logger.info("🧪 DÉBUT DES TESTS D'INTÉGRATION")
        logger.info("=" * 50)

        # Nettoyer le cache
        await cache.set('weather_markets', [])
        await cache.set('forecasts', {})
        await cache.set('trade_signals', [])
        await cache.set('open_positions', [])

        # Exécuter les tests dans l'ordre
        await self.test_market_scanner()
        await self.test_weather_forecaster()
        await self.test_edge_calculator()
        await self.test_trade_executor()
        await self.test_position_manager()

        # Résumé des résultats
        self.print_results()

    def print_results(self):
        """Affiche le résumé des tests"""
        logger.info("\n" + "=" * 50)
        logger.info("📋 RÉSULTATS DES TESTS D'INTÉGRATION")
        logger.info("=" * 50)

        passed = 0
        failed = 0

        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result == "PASSED" else f"❌ FAILED ({result})"
            logger.info(f"{test_name:20} : {status}")

            if result == "PASSED":
                passed += 1
            else:
                failed += 1

        logger.info("-" * 50)
        logger.info(f"Total: {passed + failed} | Réussis: {passed} | Échecs: {failed}")

        if failed == 0:
            logger.info("🎉 TOUS LES TESTS ONT RÉUSSI !")
            return True
        else:
            logger.error(f"💥 {failed} TEST(S) ONT ÉCHOUÉ")
            return False

async def main():
    """Point d'entrée des tests"""
    test_suite = IntegrationTest()
    success = await test_suite.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    result = asyncio.run(main())
    sys.exit(result)