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

  // Bot Control (future endpoints to be added to FastAPI)
  async startBot(): Promise<{ success: boolean; message: string }> {
    // TODO: Add to FastAPI backend
    return Promise.resolve({ success: true, message: "Bot start command sent" })
  }

  async stopBot(): Promise<{ success: boolean; message: string }> {
    // TODO: Add to FastAPI backend
    return Promise.resolve({ success: true, message: "Bot stop command sent" })
  }

  async pauseBot(): Promise<{ success: boolean; message: string }> {
    // TODO: Add to FastAPI backend
    return Promise.resolve({ success: true, message: "Bot pause command sent" })
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
} as const