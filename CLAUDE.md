# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Bot
- **Start the main trading bot**: `python main.py`
- **Install dependencies**: `pip install -r requirements.txt`
- **Run API server**: `python api.py`

### Testing and Development Scripts
- **Test single order execution**: `python test_clob_single_order.py`
- **Test edge calculation**: `python test_edge.py`
- **Test weather forecasting**: `python test_forecaster.py`
- **Test market scanning**: `python test_scanner.py`
- **Reset bot state**: `python reset_bot_state.py`

### Configuration Setup
- **Setup wallet credentials**: `python setup_credentials.py`
- **Create new wallet**: `python create_new_wallet.py`

## Architecture Overview

This is a **Weather Trading Bot for Polymarket** that automatically trades weather prediction markets by:

1. **Scanning** weather temperature markets on Polymarket
2. **Forecasting** weather using Open-Meteo ensemble API data
3. **Calculating** trading edges by comparing model predictions vs market prices
4. **Executing** trades when profitable opportunities are found
5. **Managing** open positions with automated profit-taking

### Core Agent Architecture

The bot uses an **agent-based architecture** with specialized components:

#### `/agents/` - Core Trading Agents
- **`market_scanner.py`** - Scans Polymarket for active daily temperature events
- **`weather_forecaster.py`** - Fetches ensemble weather predictions from Open-Meteo API
- **`edge_calculator.py`** - Calculates statistical edges by comparing forecasts vs market prices
- **`trade_executor.py`** - Executes trades via Polymarket CLOB API
- **`position_manager.py`** - Monitors and manages open positions

#### `/shared/` - Common Infrastructure
- **`models.py`** - Core data structures (WeatherMarket, TemperatureRange, TradeSignal, etc.)
- **`cities.py`** - Mapping of supported cities to GPS coordinates
- **`cache.py`** - Simple in-memory cache for data sharing between agents
- **`clob_client.py`** - Polymarket CLOB API client wrapper

#### Main Bot Loop (`main.py`)
- **Trading Cycle** (15min intervals): scan markets → fetch forecasts → calculate edges → execute trades
- **Position Cycle** (5min intervals): update position prices and P&L
- **HTTP Sessions**: Manages persistent connections for all agents
- **Status Tracking**: Writes bot status to JSON for monitoring

### Key Data Flow

1. **MarketScanner** discovers active weather temperature markets via Polymarket Events API
2. **WeatherForecaster** fetches ensemble predictions for each city using Open-Meteo API
3. **EdgeCalculator** compares statistical model probabilities vs implied market probabilities
4. **TradeExecutor** places orders when edge exceeds minimum threshold (default 25%)
5. **PositionManager** monitors open positions and executes profit-taking at 2x or 50% gains

### Configuration

The bot is configured via environment variables (see `.env.example`):

- **Trading**: `BANKROLL_USDC`, `MAX_POSITION_USDC`, `EDGE_MINIMUM`, `DRY_RUN`
- **API**: `CLOB_PRIVATE_KEY`, `POLYGON_RPC_URL` for blockchain interactions
- **Data**: `DATA_DIR` for storing positions, logs, and cache files

### Special Features

- **Rate Limiting**: Respects Open-Meteo API limits with intelligent caching
- **Multi-Unit Support**: Handles both Celsius and Fahrenheit temperature markets
- **Dry Run Mode**: Full simulation mode for testing without real trades
- **Session Management**: Proper HTTP session lifecycle management
- **Error Recovery**: Robust error handling with retry logic

### File Structure Notes

- Test files (`test_*.py`) demonstrate usage patterns for each component
- Utils directory contains wallet setup and approval management
- Data directory stores positions, forecasts, and logs (created at runtime)
- Weather-dashboard contains a separate Node.js monitoring interface