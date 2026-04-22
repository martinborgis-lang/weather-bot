"use client"

import { cn } from "@/lib/utils"
import React, { useEffect, useRef, useState } from "react"
import { Terminal as TerminalIcon, Maximize2, Minimize2, X } from "lucide-react"

interface TerminalLog {
  id: string
  timestamp: Date
  level: "info" | "warn" | "error" | "success"
  message: string
  component?: string
}

interface TerminalProps {
  className?: string
  logs?: TerminalLog[]
  title?: string
  height?: string
  autoScroll?: boolean
}

export function Terminal({
  className,
  logs = [],
  title = "Weather Bot Terminal",
  height = "h-96",
  autoScroll = true
}: TerminalProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [terminalLogs, setTerminalLogs] = useState<TerminalLog[]>(logs)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Demo logs for demonstration
  const demoLogs: TerminalLog[] = [
    {
      id: "1",
      timestamp: new Date(Date.now() - 300000),
      level: "info",
      message: "Weather bot initialized successfully",
      component: "SYSTEM"
    },
    {
      id: "2",
      timestamp: new Date(Date.now() - 240000),
      level: "info",
      message: "Scanning 97 weather markets across 8 cities",
      component: "SCANNER"
    },
    {
      id: "3",
      timestamp: new Date(Date.now() - 180000),
      level: "success",
      message: "Found profitable opportunity: Paris 18°C - Edge: 12.4%",
      component: "ANALYZER"
    },
    {
      id: "4",
      timestamp: new Date(Date.now() - 120000),
      level: "info",
      message: "Executing trade: YES Paris 18°C - Size: $45.00",
      component: "EXECUTOR"
    },
    {
      id: "5",
      timestamp: new Date(Date.now() - 90000),
      level: "success",
      message: "Trade executed successfully - TX: 0xabc123...",
      component: "EXECUTOR"
    },
    {
      id: "6",
      timestamp: new Date(Date.now() - 60000),
      level: "warn",
      message: "High volatility detected in London markets",
      component: "MONITOR"
    },
    {
      id: "7",
      timestamp: new Date(Date.now() - 30000),
      level: "info",
      message: "Portfolio rebalancing: Current exposure $2,450 (12% of bankroll)",
      component: "PORTFOLIO"
    },
    {
      id: "8",
      timestamp: new Date(Date.now() - 10000),
      level: "error",
      message: "Failed to fetch weather data for Tokyo - Retrying...",
      component: "WEATHER"
    },
    {
      id: "9",
      timestamp: new Date(Date.now() - 5000),
      level: "success",
      message: "Weather data recovered - Tokyo 25°C confirmed",
      component: "WEATHER"
    },
    {
      id: "10",
      timestamp: new Date(),
      level: "info",
      message: "Monitoring active positions... All systems operational",
      component: "SYSTEM"
    }
  ]

  useEffect(() => {
    if (logs.length === 0) {
      setTerminalLogs(demoLogs)
    } else {
      setTerminalLogs(logs)
    }
  }, [logs])

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [terminalLogs, autoScroll])

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    })
  }

  const getLevelColor = (level: TerminalLog["level"]) => {
    switch (level) {
      case "success":
        return "text-success"
      case "warn":
        return "text-warning"
      case "error":
        return "text-destructive"
      default:
        return "text-foreground"
    }
  }

  const getLevelPrefix = (level: TerminalLog["level"]) => {
    switch (level) {
      case "success":
        return "✓"
      case "warn":
        return "⚠"
      case "error":
        return "✗"
      default:
        return "•"
    }
  }

  return (
    <div
      className={cn(
        "bg-surface/95 border border-accent/30 rounded-lg overflow-hidden neon-border",
        isExpanded ? "fixed inset-4 z-50" : height,
        className
      )}
    >
      {/* Terminal Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-accent/20 bg-accent/5">
        <div className="flex items-center gap-2">
          <TerminalIcon className="h-4 w-4 text-accent" />
          <span className="text-sm font-mono font-medium">{title}</span>
          <div className="flex gap-1 ml-2">
            <div className="w-2 h-2 rounded-full bg-destructive animate-pulse"></div>
            <div className="w-2 h-2 rounded-full bg-warning"></div>
            <div className="w-2 h-2 rounded-full bg-success"></div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-accent/20 rounded text-muted-foreground hover:text-foreground transition-colors"
          >
            {isExpanded ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </button>
          {isExpanded && (
            <button
              onClick={() => setIsExpanded(false)}
              className="p-1 hover:bg-destructive/20 rounded text-muted-foreground hover:text-destructive transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Terminal Content */}
      <div
        ref={scrollRef}
        className={cn(
          "overflow-y-auto bg-surface/50 font-mono text-xs leading-relaxed",
          isExpanded ? "flex-1" : "h-full"
        )}
      >
        <div className="p-4 space-y-1">
          {terminalLogs.map((log) => (
            <div key={log.id} className="flex items-start gap-3 group hover:bg-accent/5 px-2 -mx-2 rounded">
              <span className="text-muted-foreground/70 shrink-0 w-16">
                {formatTimestamp(log.timestamp)}
              </span>
              <span className={cn("shrink-0 w-4", getLevelColor(log.level))}>
                {getLevelPrefix(log.level)}
              </span>
              {log.component && (
                <span className="text-accent/80 shrink-0 w-20 uppercase">
                  [{log.component}]
                </span>
              )}
              <span className={cn("flex-1", getLevelColor(log.level))}>
                {log.message}
              </span>
            </div>
          ))}
        </div>

        {/* Terminal Cursor */}
        <div className="px-4 pb-2">
          <div className="flex items-center gap-2 text-accent">
            <span>$</span>
            <div className="w-2 h-4 bg-accent animate-pulse"></div>
          </div>
        </div>
      </div>

      {/* Scanlines Effect */}
      <div
        className="absolute inset-0 pointer-events-none opacity-10"
        style={{
          backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(34, 197, 94, 0.1) 2px, rgba(34, 197, 94, 0.1) 4px)",
        }}
      />
    </div>
  )
}

// Smaller terminal widget for dashboard cards
export function TerminalWidget({
  className,
  maxLines = 5
}: {
  className?: string
  maxLines?: number
}) {
  const recentLogs: TerminalLog[] = [
    {
      id: "recent-1",
      timestamp: new Date(Date.now() - 30000),
      level: "success",
      message: "Trade executed: +$45 Paris 18°C"
    },
    {
      id: "recent-2",
      timestamp: new Date(Date.now() - 15000),
      level: "info",
      message: "Scanning new markets..."
    },
    {
      id: "recent-3",
      timestamp: new Date(Date.now() - 5000),
      level: "warn",
      message: "High volatility: London"
    },
    {
      id: "recent-4",
      timestamp: new Date(),
      level: "info",
      message: "All systems operational"
    }
  ]

  return (
    <div className={cn("space-y-1", className)}>
      {recentLogs.slice(0, maxLines).map((log) => (
        <div key={log.id} className="flex items-center gap-2 text-xs font-mono">
          <span className="text-muted-foreground/50 w-12 shrink-0">
            {log.timestamp.toLocaleTimeString("en-US", {
              hour12: false,
              minute: "2-digit",
              second: "2-digit"
            })}
          </span>
          <span className={cn("w-3 shrink-0", {
            "text-success": log.level === "success",
            "text-warning": log.level === "warn",
            "text-destructive": log.level === "error",
            "text-muted-foreground": log.level === "info"
          })}>
            {log.level === "success" ? "✓" : log.level === "warn" ? "⚠" : log.level === "error" ? "✗" : "•"}
          </span>
          <span className={cn("flex-1 truncate", {
            "text-success": log.level === "success",
            "text-warning": log.level === "warn",
            "text-destructive": log.level === "error",
            "text-foreground": log.level === "info"
          })}>
            {log.message}
          </span>
        </div>
      ))}
    </div>
  )
}