"use client"

import { cn } from "@/lib/utils"
import React, { useState } from "react"
import {
  Play,
  Pause,
  Square,
  RefreshCw,
  Settings,
  AlertTriangle,
  DollarSign,
  TrendingUp,
  Activity,
  Zap
} from "lucide-react"
import { Button } from "./button"
import { Card, CardContent, CardHeader, CardTitle } from "./card"

interface BotStatus {
  isRunning: boolean
  status: "active" | "paused" | "stopped" | "error"
  uptime: string
  lastAction: string
  totalTrades: number
  successRate: number
  currentExposure: number
  availableBalance: number
}

interface BotControlsProps {
  className?: string
  onStart?: () => void
  onPause?: () => void
  onStop?: () => void
  onRestart?: () => void
  onSettings?: () => void
}

export function BotControls({
  className,
  onStart,
  onPause,
  onStop,
  onRestart,
  onSettings
}: BotControlsProps) {
  const [botStatus, setBotStatus] = useState<BotStatus>({
    isRunning: true,
    status: "active",
    uptime: "2h 34m 15s",
    lastAction: "Executed trade: Paris 18°C YES",
    totalTrades: 47,
    successRate: 68.3,
    currentExposure: 2450,
    availableBalance: 37550
  })

  const [isUpdating, setIsUpdating] = useState(false)

  const handleStart = () => {
    setIsUpdating(true)
    setBotStatus(prev => ({ ...prev, isRunning: true, status: "active" }))
    setTimeout(() => {
      setIsUpdating(false)
      onStart?.()
    }, 1000)
  }

  const handlePause = () => {
    setIsUpdating(true)
    setBotStatus(prev => ({ ...prev, isRunning: false, status: "paused" }))
    setTimeout(() => {
      setIsUpdating(false)
      onPause?.()
    }, 1000)
  }

  const handleStop = () => {
    setIsUpdating(true)
    setBotStatus(prev => ({ ...prev, isRunning: false, status: "stopped" }))
    setTimeout(() => {
      setIsUpdating(false)
      onStop?.()
    }, 1000)
  }

  const handleRestart = () => {
    setIsUpdating(true)
    setBotStatus(prev => ({ ...prev, status: "active" }))
    setTimeout(() => {
      setBotStatus(prev => ({ ...prev, isRunning: true }))
      setIsUpdating(false)
      onRestart?.()
    }, 1500)
  }

  const getStatusColor = (status: BotStatus["status"]) => {
    switch (status) {
      case "active":
        return "text-success"
      case "paused":
        return "text-warning"
      case "stopped":
        return "text-muted-foreground"
      case "error":
        return "text-destructive"
      default:
        return "text-muted-foreground"
    }
  }

  const getStatusIcon = (status: BotStatus["status"]) => {
    switch (status) {
      case "active":
        return <Activity className="h-4 w-4 animate-pulse" />
      case "paused":
        return <Pause className="h-4 w-4" />
      case "stopped":
        return <Square className="h-4 w-4" />
      case "error":
        return <AlertTriangle className="h-4 w-4" />
      default:
        return <Square className="h-4 w-4" />
    }
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* Main Status Card */}
      <Card className="relative overflow-hidden neon-border">
        <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent pointer-events-none" />

        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={cn(
                "w-3 h-3 rounded-full",
                botStatus.status === "active" ? "bg-success animate-pulse" :
                botStatus.status === "paused" ? "bg-warning" :
                botStatus.status === "error" ? "bg-destructive" :
                "bg-muted"
              )} />
              <span className="neon-glow">Weather Trading Bot</span>
              {isUpdating && <RefreshCw className="h-4 w-4 animate-spin text-accent" />}
            </div>
            <div className={cn("flex items-center gap-2", getStatusColor(botStatus.status))}>
              {getStatusIcon(botStatus.status)}
              <span className="text-sm font-mono uppercase tracking-wider">
                {botStatus.status}
              </span>
            </div>
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Control Buttons */}
          <div className="flex items-center gap-3">
            {!botStatus.isRunning ? (
              <Button
                onClick={handleStart}
                disabled={isUpdating}
                variant="neon"
                size="sm"
                className="flex items-center gap-2"
              >
                <Play className="h-4 w-4" />
                Start Bot
              </Button>
            ) : (
              <Button
                onClick={handlePause}
                disabled={isUpdating}
                variant="outline"
                size="sm"
                className="flex items-center gap-2"
              >
                <Pause className="h-4 w-4" />
                Pause
              </Button>
            )}

            <Button
              onClick={handleStop}
              disabled={isUpdating}
              variant="destructive"
              size="sm"
              className="flex items-center gap-2"
            >
              <Square className="h-4 w-4" />
              Stop
            </Button>

            <Button
              onClick={handleRestart}
              disabled={isUpdating}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <RefreshCw className={cn("h-4 w-4", isUpdating && "animate-spin")} />
              Restart
            </Button>

            <div className="flex-1" />

            <Button
              onClick={onSettings}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <Settings className="h-4 w-4" />
              Settings
            </Button>
          </div>

          {/* Status Info */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground uppercase tracking-wider">Uptime</div>
              <div className="font-mono text-foreground">{botStatus.uptime}</div>
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground uppercase tracking-wider">Total Trades</div>
              <div className="font-mono text-foreground">{botStatus.totalTrades}</div>
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground uppercase tracking-wider">Success Rate</div>
              <div className="font-mono text-success">{botStatus.successRate}%</div>
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground uppercase tracking-wider">Last Action</div>
              <div className="font-mono text-xs text-foreground truncate">{botStatus.lastAction}</div>
            </div>
          </div>

          {/* Financial Status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-accent/20">
            <div className="flex items-center gap-3 p-3 bg-accent/5 rounded-lg">
              <div className="w-10 h-10 bg-success/20 rounded-full flex items-center justify-center">
                <TrendingUp className="h-5 w-5 text-success" />
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Current Exposure</div>
                <div className="text-lg font-mono font-bold">${botStatus.currentExposure.toLocaleString()}</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-accent/5 rounded-lg">
              <div className="w-10 h-10 bg-accent/20 rounded-full flex items-center justify-center">
                <DollarSign className="h-5 w-5 text-accent" />
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Available Balance</div>
                <div className="text-lg font-mono font-bold">${botStatus.availableBalance.toLocaleString()}</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="hover:neon-border transition-all duration-300 cursor-pointer">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-warning/20 rounded-full flex items-center justify-center">
                <AlertTriangle className="h-4 w-4 text-warning" />
              </div>
              <div>
                <div className="text-sm font-medium">Emergency Stop</div>
                <div className="text-xs text-muted-foreground">Halt all trading activity</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:neon-border transition-all duration-300 cursor-pointer">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-accent/20 rounded-full flex items-center justify-center">
                <Zap className="h-4 w-4 text-accent" />
              </div>
              <div>
                <div className="text-sm font-medium">Force Refresh</div>
                <div className="text-xs text-muted-foreground">Update market data</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:neon-border transition-all duration-300 cursor-pointer">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-success/20 rounded-full flex items-center justify-center">
                <Settings className="h-4 w-4 text-success" />
              </div>
              <div>
                <div className="text-sm font-medium">Auto Settings</div>
                <div className="text-xs text-muted-foreground">Optimize parameters</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// Compact bot controls for dashboard widgets
export function BotControlsWidget({ className }: { className?: string }) {
  const [isRunning, setIsRunning] = useState(true)
  const [isUpdating, setIsUpdating] = useState(false)

  const handleToggle = () => {
    setIsUpdating(true)
    setTimeout(() => {
      setIsRunning(!isRunning)
      setIsUpdating(false)
    }, 1000)
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={cn(
            "w-2 h-2 rounded-full",
            isRunning ? "bg-success animate-pulse" : "bg-muted"
          )} />
          <span className="text-sm font-medium">
            {isRunning ? "Active" : "Stopped"}
          </span>
        </div>
        <Button
          onClick={handleToggle}
          disabled={isUpdating}
          variant={isRunning ? "outline" : "neon"}
          size="sm"
          className="text-xs px-2 py-1"
        >
          {isUpdating ? (
            <RefreshCw className="h-3 w-3 animate-spin" />
          ) : isRunning ? (
            <>
              <Pause className="h-3 w-3 mr-1" />
              Pause
            </>
          ) : (
            <>
              <Play className="h-3 w-3 mr-1" />
              Start
            </>
          )}
        </Button>
      </div>

      <div className="space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Uptime:</span>
          <span className="font-mono">2h 34m</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Trades:</span>
          <span className="font-mono">47</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Success:</span>
          <span className="font-mono text-success">68.3%</span>
        </div>
      </div>
    </div>
  )
}