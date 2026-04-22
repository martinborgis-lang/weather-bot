"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader, CardTitle } from "./card"
import { TrendSparkline } from "@/components/charts/sparkline"

interface MetricCardProps {
  title: string
  value: string | number
  change?: number
  changeType?: "positive" | "negative" | "neutral"
  icon?: React.ComponentType<{ className?: string }>
  trend?: number[]
  className?: string
  animated?: boolean
}

export function MetricCard({
  title,
  value,
  change,
  changeType = "neutral",
  icon: Icon,
  trend,
  className,
  animated = true,
  ...props
}: MetricCardProps) {
  const [displayValue, setDisplayValue] = React.useState(0)
  const numericValue = typeof value === 'string' ? parseFloat(value.replace(/[^\d.-]/g, '')) : value

  // Animate number counting up
  React.useEffect(() => {
    if (!animated || typeof numericValue !== 'number') return

    const start = 0
    const end = numericValue
    const duration = 1000 // 1 second
    const increment = end / (duration / 16) // 60fps

    let current = start
    const timer = setInterval(() => {
      current += increment
      if (current >= end) {
        setDisplayValue(end)
        clearInterval(timer)
      } else {
        setDisplayValue(current)
      }
    }, 16)

    return () => clearInterval(timer)
  }, [numericValue, animated])

  const changeColor = {
    positive: "text-success",
    negative: "text-destructive",
    neutral: "text-muted-foreground",
  }[changeType]

  const changeSymbol = changeType === "positive" ? "+" : changeType === "negative" ? "-" : ""

  return (
    <Card
      className={cn(
        "relative overflow-hidden transition-all duration-300",
        animated && "hover:scale-105 hover:neon-border",
        className
      )}
      {...props}
    >
      {/* Cyberpunk background effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent pointer-events-none" />

      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {Icon && (
          <Icon className="h-4 w-4 text-accent" />
        )}
      </CardHeader>

      <CardContent>
        <div className="text-2xl font-bold font-mono">
          {animated && typeof numericValue === 'number' ? (
            <span className="tabular-nums">
              {typeof value === 'string'
                ? value.replace(/[\d.-]+/, displayValue.toLocaleString())
                : displayValue.toLocaleString()
              }
            </span>
          ) : (
            <span className="neon-glow">{value}</span>
          )}
        </div>

        {change !== undefined && (
          <p className={cn("text-xs flex items-center gap-1", changeColor)}>
            <span>{changeSymbol}{Math.abs(change)}%</span>
            <span className="text-muted-foreground">from last period</span>
          </p>
        )}

        {/* Enhanced sparkline */}
        {trend && trend.length > 0 && (
          <div className="mt-2 h-8 w-full">
            <TrendSparkline
              data={trend}
              width={200}
              height={32}
              strokeWidth={1.5}
              animated={animated}
              gradient={true}
              showTrend={true}
              className="w-full"
            />
          </div>
        )}
      </CardContent>
    </Card>
  )
}