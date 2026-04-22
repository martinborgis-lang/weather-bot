// API Response Types matching the existing FastAPI backend

export interface Position {
  market_condition_id: string
  market_title: string
  temperature_label: string
  side: "YES" | "NO"
  entry_price: number
  current_price: number
  size_usdc: number
  size_tokens: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  opened_at: string
  transaction_hash?: string
  resolution_datetime?: string
  time_to_resolution?: string
  resolution_status?: "pending" | "resolved" | "unknown"
}

export interface Trade {
  timestamp: string
  condition_id: string
  token_id: string
  city: string
  market_title: string
  temperature_label: string
  side: "YES" | "NO"
  entry_price: number
  size_usdc: number
  size_tokens: number
  opened_at: string
  transaction_hash?: string
  dry_run: boolean
  order_id?: string
  target_date?: string
  exit_price?: number
  final_pnl?: number
  closed_at?: string
  exit_reason?: string
}

export interface Signal {
  timestamp: string
  condition_id: string
  token_id: string
  city: string
  market_title: string
  temperature_label: string
  action: string
  side: "YES" | "NO"
  edge_value: number
  model_probability: number
  market_price: number
  bid_ask_spread: number
  confidence: number
  kelly_size_usdc: number
  kelly_fraction: number
  reason: string
}

export interface Stats {
  total_trades: number
  open_positions: number
  total_exposure: number
  bankroll: number
  dry_run: boolean
}

export interface BotStatus {
  status: "running" | "stopped" | "error"
  last_cycle?: string
  next_cycle?: string
  uptime?: string
}

// UI Component Types
export interface MetricCard {
  title: string
  value: string | number
  change?: number
  changeType?: "positive" | "negative" | "neutral"
  icon?: React.ComponentType
  trend?: number[]
}

export interface City {
  name: string
  lat: number
  lng: number
  active_markets: number
  total_volume: number
}