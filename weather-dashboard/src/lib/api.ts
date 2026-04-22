import { Position, Trade, Signal, Stats } from './types'

// Configuration de base de l'API
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiClient {
  private baseURL: string

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
  }

  private async request<T>(endpoint: string): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error)
      throw error
    }
  }

  // Health check
  async getHealth(): Promise<{ status: string; data_dir: string }> {
    return this.request('/health')
  }

  // Positions
  async getPositions(): Promise<Position[]> {
    return this.request('/positions')
  }

  async getPositionsDetailed(): Promise<Position[]> {
    return this.request('/positions-detailed')
  }

  // Trades
  async getTrades(): Promise<Trade[]> {
    return this.request('/trades')
  }

  // Signals
  async getSignals(): Promise<Signal[]> {
    return this.request('/signals')
  }

  // Stats
  async getStats(): Promise<Stats> {
    return this.request('/stats')
  }

  // Bot Status and Control
  async getBotStatus(): Promise<BotStatus> {
    return this.request('/api/bot/status')
  }

  async getMarkets(): Promise<Market[]> {
    return this.request('/api/markets')
  }

  async getForecasts(): Promise<Forecast[]> {
    return this.request('/api/forecasts')
  }

  async pauseBot(): Promise<{ status: string; timestamp: string }> {
    const response = await fetch(`${this.baseURL}/api/bot/pause`, { method: 'POST' })
    return response.json()
  }

  async resumeBot(): Promise<{ status: string; timestamp: string }> {
    const response = await fetch(`${this.baseURL}/api/bot/resume`, { method: 'POST' })
    return response.json()
  }

  async forceCycle(): Promise<{ status: string; timestamp: string }> {
    const response = await fetch(`${this.baseURL}/api/bot/force-cycle`, { method: 'POST' })
    return response.json()
  }
}

// Singleton instance
export const apiClient = new ApiClient()

// React Query hooks helpers
export const queryKeys = {
  health: ['health'],
  positions: ['positions'],
  positionsDetailed: ['positions', 'detailed'],
  trades: ['trades'],
  signals: ['signals'],
  stats: ['stats'],
  botStatus: ['bot', 'status'],
  markets: ['markets'],
  forecasts: ['forecasts'],
} as const

// New interfaces for the API
export interface BotStatus {
  running: boolean;
  last_cycle_at: string | null;
  uptime_seconds: number;
  next_scan_at: string | null;
  dry_run: boolean;
  errors_24h: number;
  paused: boolean;
  bankroll_usdc: number;
  max_position_usdc: number;
  edge_minimum: number;
}

export interface Market {
  id: string;
  condition_id?: string;
  slug: string;
  title: string;
  city: string;
  target_date: string;
  resolution_source: string;
  liquidity_usdc: number;
  volume_usdc: number;
  ranges: Array<{
    min: number;
    max: number;
    tokens: Array<{
      token_id: string;
      outcome: string;
      price: number;
    }>;
  }>;
  ends_at: string;
  unit: string;
  resolution_datetime?: string;
}

export interface Forecast {
  city: string;
  target_date: string;
  members: number[];
  mean: number;
  timestamp: string;
}