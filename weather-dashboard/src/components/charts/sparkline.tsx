"use client"

import { cn } from "@/lib/utils"
import React, { useEffect, useRef, useState } from "react"

interface SparklineProps {
  data: number[]
  className?: string
  width?: number
  height?: number
  strokeWidth?: number
  color?: string
  fillColor?: string
  animated?: boolean
  showDots?: boolean
  gradient?: boolean
}

export function Sparkline({
  data,
  className,
  width = 200,
  height = 60,
  strokeWidth = 2,
  color = "#22C55E", // accent color
  fillColor = "#22C55E20",
  animated = false,
  showDots = false,
  gradient = true
}: SparklineProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [animatedData, setAnimatedData] = useState<number[]>(animated ? Array(data.length).fill(data[0] || 0) : data)

  useEffect(() => {
    if (animated) {
      const timer = setTimeout(() => {
        setAnimatedData(data)
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [data, animated])

  const currentData = animated ? animatedData : data

  if (!currentData || currentData.length < 2) {
    return (
      <div className={cn("flex items-center justify-center bg-accent/5 rounded", className)} style={{ width, height }}>
        <span className="text-xs text-muted-foreground">No data</span>
      </div>
    )
  }

  // Filter out NaN and invalid values
  const validData = currentData.filter(value =>
    typeof value === 'number' && !isNaN(value) && isFinite(value)
  )

  if (validData.length < 2) {
    return (
      <div className={cn("flex items-center justify-center bg-accent/5 rounded", className)} style={{ width, height }}>
        <span className="text-xs text-muted-foreground">Invalid data</span>
      </div>
    )
  }

  const min = Math.min(...validData)
  const max = Math.max(...validData)
  const range = max - min || 1

  // Create path points with validation
  const points = validData.map((value, index) => {
    const x = (index / (validData.length - 1)) * width
    const y = height - ((value - min) / range) * height

    // Additional NaN guard
    return {
      x: isNaN(x) ? 0 : x,
      y: isNaN(y) ? height / 2 : y,
      value
    }
  })

  const pathD = points.reduce((path, point, index) => {
    if (index === 0) {
      return `M ${point.x} ${point.y}`
    }
    return `${path} L ${point.x} ${point.y}`
  }, "")

  // Create area path
  const areaD = `${pathD} L ${width} ${height} L 0 ${height} Z`

  const [gradientId] = useState(() => `sparkline-gradient-${Math.random().toString(36).substr(2, 9)}`)

  return (
    <div className={cn("relative", className)}>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="overflow-visible"
      >
        {gradient && (
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={color} stopOpacity="0.3" />
              <stop offset="100%" stopColor={color} stopOpacity="0.05" />
            </linearGradient>
          </defs>
        )}

        {/* Fill area */}
        {gradient && (
          <path
            d={areaD}
            fill={`url(#${gradientId})`}
            className={animated ? "transition-all duration-1000 ease-out" : ""}
          />
        )}

        {/* Sparkline path */}
        <path
          d={pathD}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          className={cn(
            "drop-shadow-sm",
            animated ? "transition-all duration-1000 ease-out" : ""
          )}
        />

        {/* Data points */}
        {showDots && points.map((point, index) => (
          <circle
            key={index}
            cx={point.x}
            cy={point.y}
            r={strokeWidth}
            fill={color}
            className={cn(
              "drop-shadow-sm",
              animated ? "transition-all duration-1000 ease-out" : ""
            )}
            style={{
              animationDelay: animated ? `${index * 50}ms` : undefined
            }}
          />
        ))}

        {/* Glow effect */}
        <path
          d={pathD}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth * 3}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.3"
          filter="blur(2px)"
          className={animated ? "transition-all duration-1000 ease-out" : ""}
        />
      </svg>
    </div>
  )
}

// Real-time updating sparkline with data streaming
export function RealtimeSparkline({
  initialData = [],
  updateInterval = 2000,
  maxDataPoints = 20,
  ...sparklineProps
}: {
  initialData?: number[]
  updateInterval?: number
  maxDataPoints?: number
} & Omit<SparklineProps, 'data'>) {
  const [data, setData] = useState<number[]>(initialData)

  useEffect(() => {
    const interval = setInterval(() => {
      setData(prev => {
        const newValue = prev.length > 0
          ? prev[prev.length - 1] + (Math.random() - 0.5) * 10
          : Math.random() * 100

        const newData = [...prev, newValue]
        return newData.slice(-maxDataPoints)
      })
    }, updateInterval)

    return () => clearInterval(interval)
  }, [updateInterval, maxDataPoints])

  return <Sparkline data={data} animated {...sparklineProps} />
}

// Sparkline with trend indicator
export function TrendSparkline({
  data,
  showTrend = true,
  className,
  ...sparklineProps
}: SparklineProps & {
  showTrend?: boolean
}) {
  if (!data || data.length < 2) return <Sparkline data={data || []} {...sparklineProps} />

  const trend = data[data.length - 1] - data[0]
  const isPositive = trend > 0
  const trendColor = isPositive ? "#22C55E" : "#DC2626"

  return (
    <div className={cn("relative", className)}>
      <Sparkline
        data={data}
        color={showTrend ? trendColor : sparklineProps.color}
        className="w-full"
        {...sparklineProps}
      />
      {showTrend && (
        <div className={cn(
          "absolute -top-1 -right-1 w-2 h-2 rounded-full",
          isPositive ? "bg-success" : "bg-destructive"
        )} />
      )}
    </div>
  )
}