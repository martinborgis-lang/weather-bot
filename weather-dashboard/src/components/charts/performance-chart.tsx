"use client"

import { cn } from "@/lib/utils"
import React, { useState, useEffect } from "react"
import { TrendingUp, TrendingDown } from "lucide-react"

interface DataPoint {
  timestamp: string
  value: number
  label?: string
  x?: number
  y?: number
}

interface PerformanceChartProps {
  data: DataPoint[]
  className?: string
  height?: number
  showGrid?: boolean
  showTooltip?: boolean
  color?: string
  fillColor?: string
  animated?: boolean
}

export function PerformanceChart({
  data,
  className,
  height = 200,
  showGrid = true,
  showTooltip = true,
  color = "#22C55E",
  fillColor = "#22C55E20",
  animated = true
}: PerformanceChartProps) {
  const [hoveredPoint, setHoveredPoint] = useState<DataPoint | null>(null)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })

  // Demo data if none provided
  const chartData = data.length > 0 ? data : [
    { timestamp: "2024-01-01", value: 1000, label: "Start" },
    { timestamp: "2024-01-02", value: 1050, label: "+5%" },
    { timestamp: "2024-01-03", value: 980, label: "-2%" },
    { timestamp: "2024-01-04", value: 1120, label: "+12%" },
    { timestamp: "2024-01-05", value: 1240, label: "+24%" },
    { timestamp: "2024-01-06", value: 1180, label: "+18%" },
    { timestamp: "2024-01-07", value: 1340, label: "+34%" },
  ]

  const width = 400
  const padding = 40

  const minValue = Math.min(...chartData.map(d => d.value))
  const maxValue = Math.max(...chartData.map(d => d.value))
  const valueRange = maxValue - minValue || 1

  const points = chartData.map((item, index) => {
    const x = padding + (index / (chartData.length - 1)) * (width - padding * 2)
    const y = padding + (1 - (item.value - minValue) / valueRange) * (height - padding * 2)
    return { ...item, x, y }
  })

  const pathD = points.reduce((path, point, index) => {
    if (index === 0) {
      return `M ${point.x} ${point.y}`
    }
    const prevPoint = points[index - 1]
    const cpx1 = prevPoint.x + (point.x - prevPoint.x) * 0.5
    const cpx2 = point.x - (point.x - prevPoint.x) * 0.5
    return `${path} C ${cpx1} ${prevPoint.y}, ${cpx2} ${point.y}, ${point.x} ${point.y}`
  }, "")

  const areaD = `${pathD} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left

    // Find closest point
    let closestPoint = points[0]
    let minDistance = Math.abs(x - closestPoint.x)

    for (const point of points) {
      const distance = Math.abs(x - point.x)
      if (distance < minDistance) {
        minDistance = distance
        closestPoint = point
      }
    }

    setHoveredPoint(closestPoint)
    setMousePos({ x: e.clientX, y: e.clientY })
  }

  const performance = ((chartData[chartData.length - 1].value - chartData[0].value) / chartData[0].value) * 100
  const isPositive = performance > 0

  return (
    <div className={cn("relative", className)}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="overflow-visible cursor-crosshair"
        onMouseMove={showTooltip ? handleMouseMove : undefined}
        onMouseLeave={() => setHoveredPoint(null)}
      >
        <defs>
          <linearGradient id="performance-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0.05" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Grid lines */}
        {showGrid && (
          <g className="opacity-20">
            {/* Horizontal grid */}
            {Array.from({ length: 5 }, (_, i) => {
              const y = padding + (i / 4) * (height - padding * 2)
              return (
                <line
                  key={`h-${i}`}
                  x1={padding}
                  y1={y}
                  x2={width - padding}
                  y2={y}
                  stroke={color}
                  strokeWidth="1"
                  strokeDasharray="2,2"
                />
              )
            })}
            {/* Vertical grid */}
            {points.map((point, i) => (
              <line
                key={`v-${i}`}
                x1={point.x}
                y1={padding}
                x2={point.x}
                y2={height - padding}
                stroke={color}
                strokeWidth="1"
                strokeDasharray="2,2"
                opacity="0.3"
              />
            ))}
          </g>
        )}

        {/* Area fill */}
        <path
          d={areaD}
          fill="url(#performance-gradient)"
          className={animated ? "transition-all duration-1000 ease-out" : ""}
        />

        {/* Main line */}
        <path
          d={pathD}
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          filter="url(#glow)"
          className={animated ? "transition-all duration-1000 ease-out" : ""}
        />

        {/* Data points */}
        {points.map((point, index) => (
          <circle
            key={index}
            cx={point.x}
            cy={point.y}
            r="4"
            fill={color}
            stroke="white"
            strokeWidth="2"
            className={cn(
              "transition-all duration-200",
              hoveredPoint?.timestamp === point.timestamp ? "r-6 opacity-100" : "opacity-70"
            )}
            style={{
              animationDelay: animated ? `${index * 100}ms` : undefined
            }}
          />
        ))}

        {/* Hover line */}
        {hoveredPoint && (
          <line
            x1={hoveredPoint.x}
            y1={padding}
            x2={hoveredPoint.x}
            y2={height - padding}
            stroke={color}
            strokeWidth="1"
            strokeDasharray="4,4"
            opacity="0.8"
          />
        )}
      </svg>

      {/* Performance indicator */}
      <div className="absolute top-4 left-4 flex items-center gap-2 bg-surface/80 backdrop-blur-sm rounded-lg px-3 py-2 border border-accent/30">
        {isPositive ? (
          <TrendingUp className="h-4 w-4 text-success" />
        ) : (
          <TrendingDown className="h-4 w-4 text-destructive" />
        )}
        <span className={cn(
          "font-mono text-sm font-medium",
          isPositive ? "text-success" : "text-destructive"
        )}>
          {performance > 0 ? "+" : ""}{performance.toFixed(1)}%
        </span>
      </div>

      {/* Tooltip */}
      {showTooltip && hoveredPoint && (
        <div
          className="fixed z-50 bg-surface/95 backdrop-blur-sm border border-accent/30 rounded-lg px-3 py-2 text-sm font-mono shadow-lg pointer-events-none neon-border"
          style={{
            left: mousePos.x + 10,
            top: mousePos.y - 50
          }}
        >
          <div className="text-accent">{new Date(hoveredPoint.timestamp).toLocaleDateString()}</div>
          <div className="text-foreground font-semibold">${hoveredPoint.value.toFixed(2)}</div>
          {hoveredPoint.label && (
            <div className={cn(
              "text-xs",
              hoveredPoint.label.startsWith('+') ? "text-success" : "text-destructive"
            )}>
              {hoveredPoint.label}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Real-time performance chart
export function RealtimePerformanceChart({
  initialValue = 1000,
  updateInterval = 3000,
  maxDataPoints = 50,
  ...chartProps
}: {
  initialValue?: number
  updateInterval?: number
  maxDataPoints?: number
} & Omit<PerformanceChartProps, 'data'>) {
  const [data, setData] = useState<DataPoint[]>([
    {
      timestamp: new Date().toISOString(),
      value: initialValue,
      label: "Start"
    }
  ])

  useEffect(() => {
    const interval = setInterval(() => {
      setData(prev => {
        const lastValue = prev[prev.length - 1].value
        const change = (Math.random() - 0.45) * 50 // Slightly positive bias
        const newValue = Math.max(0, lastValue + change)

        const changePercent = ((newValue - lastValue) / lastValue * 100)
        const label = changePercent > 0 ? `+${changePercent.toFixed(1)}%` : `${changePercent.toFixed(1)}%`

        const newPoint = {
          timestamp: new Date().toISOString(),
          value: newValue,
          label
        }

        const newData = [...prev, newPoint]
        return newData.slice(-maxDataPoints)
      })
    }, updateInterval)

    return () => clearInterval(interval)
  }, [updateInterval, maxDataPoints])

  return <PerformanceChart data={data} animated {...chartProps} />
}