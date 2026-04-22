"use client"

import { cn } from "@/lib/utils"
import React, { useEffect, useRef, useState } from "react"

interface GlobePoint {
  id: string
  lat: number
  lng: number
  city: string
  temperature: number
  active: boolean
  color: string
}

interface GlobeProps {
  className?: string
  points?: GlobePoint[]
  autoRotate?: boolean
}

export function Globe({
  className,
  points = [],
  autoRotate = true
}: GlobeProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>(0)
  const [rotation, setRotation] = useState(0)
  const [isHovered, setIsHovered] = useState(false)

  // Default points for demo
  const defaultPoints: GlobePoint[] = [
    { id: "paris", lat: 48.8566, lng: 2.3522, city: "Paris", temperature: 18, active: true, color: "#22C55E" },
    { id: "london", lat: 51.5074, lng: -0.1278, city: "London", temperature: 15, active: true, color: "#22C55E" },
    { id: "nyc", lat: 40.7128, lng: -74.0060, city: "New York", temperature: 22, active: false, color: "#F59E0B" },
    { id: "tokyo", lat: 35.6762, lng: 139.6503, city: "Tokyo", temperature: 25, active: true, color: "#22C55E" },
    { id: "sydney", lat: -33.8688, lng: 151.2093, city: "Sydney", temperature: 20, active: false, color: "#DC2626" },
    { id: "moscow", lat: 55.7558, lng: 37.6176, city: "Moscow", temperature: 5, active: true, color: "#22C55E" },
    { id: "dubai", lat: 25.2048, lng: 55.2708, city: "Dubai", temperature: 35, active: false, color: "#F59E0B" },
    { id: "mumbai", lat: 19.0760, lng: 72.8777, city: "Mumbai", temperature: 28, active: true, color: "#22C55E" }
  ]

  const globePoints = points.length > 0 ? points : defaultPoints

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const devicePixelRatio = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()

    canvas.width = rect.width * devicePixelRatio
    canvas.height = rect.height * devicePixelRatio

    ctx.scale(devicePixelRatio, devicePixelRatio)
    canvas.style.width = rect.width + "px"
    canvas.style.height = rect.height + "px"

    const centerX = rect.width / 2
    const centerY = rect.height / 2
    const radius = Math.min(centerX, centerY) * 0.8

    const drawGlobe = (currentRotation: number) => {
      ctx.clearRect(0, 0, rect.width, rect.height)

      // Draw globe outline
      ctx.beginPath()
      ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI)
      ctx.strokeStyle = "rgba(34, 197, 94, 0.3)" // accent color
      ctx.lineWidth = 2
      ctx.stroke()

      // Draw grid lines (longitude)
      for (let i = 0; i < 8; i++) {
        const angle = (i * Math.PI) / 4 + currentRotation
        const x1 = centerX + Math.cos(angle) * radius
        const y1 = centerY + Math.sin(angle) * radius
        const x2 = centerX - Math.cos(angle) * radius
        const y2 = centerY - Math.sin(angle) * radius

        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.strokeStyle = "rgba(34, 197, 94, 0.1)"
        ctx.lineWidth = 1
        ctx.stroke()
      }

      // Draw grid lines (latitude)
      for (let i = 1; i < 4; i++) {
        const y = centerY + (radius * (i - 2)) / 2
        const ellipseWidth = Math.sqrt(radius * radius - Math.pow((y - centerY), 2)) * 2

        ctx.beginPath()
        ctx.ellipse(centerX, y, ellipseWidth / 2, 0, 0, 0, 2 * Math.PI)
        ctx.strokeStyle = "rgba(34, 197, 94, 0.1)"
        ctx.lineWidth = 1
        ctx.stroke()
      }

      // Draw points
      globePoints.forEach((point) => {
        // Convert lat/lng to 3D coordinates
        const lat = (point.lat * Math.PI) / 180
        const lng = ((point.lng + currentRotation * 180 / Math.PI) * Math.PI) / 180

        const x3d = Math.cos(lat) * Math.cos(lng)
        const y3d = Math.sin(lat)
        const z3d = Math.cos(lat) * Math.sin(lng)

        // Only draw points on the visible hemisphere
        if (z3d > 0) {
          const x2d = centerX + x3d * radius
          const y2d = centerY - y3d * radius

          // Draw point
          ctx.beginPath()
          ctx.arc(x2d, y2d, point.active ? 6 : 4, 0, 2 * Math.PI)
          ctx.fillStyle = point.color
          ctx.fill()

          // Draw glow effect for active points
          if (point.active) {
            ctx.beginPath()
            ctx.arc(x2d, y2d, 12, 0, 2 * Math.PI)
            const gradient = ctx.createRadialGradient(x2d, y2d, 0, x2d, y2d, 12)
            gradient.addColorStop(0, point.color + "40")
            gradient.addColorStop(1, point.color + "00")
            ctx.fillStyle = gradient
            ctx.fill()
          }

          // Draw city label
          ctx.fillStyle = "#FFFFFF"
          ctx.font = "12px 'JetBrains Mono', monospace"
          ctx.fillText(point.city, x2d + 10, y2d - 5)

          // Draw temperature
          ctx.fillStyle = point.color
          ctx.font = "10px 'JetBrains Mono', monospace"
          ctx.fillText(`${point.temperature}°C`, x2d + 10, y2d + 8)
        }
      })
    }

    const animate = () => {
      if (autoRotate && !isHovered) {
        setRotation(prev => prev + 0.005)
      }
      drawGlobe(rotation)
      animationRef.current = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [rotation, autoRotate, isHovered, globePoints])

  return (
    <div className={cn("relative overflow-hidden rounded-lg", className)}>
      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-grab active:cursor-grabbing"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        style={{ background: "radial-gradient(circle, rgba(34, 197, 94, 0.05) 0%, transparent 70%)" }}
      />

      {/* Legend */}
      <div className="absolute bottom-2 left-2 space-y-1 text-xs font-mono">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success"></div>
          <span className="text-success">Active Markets</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-warning"></div>
          <span className="text-warning">Monitoring</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-destructive"></div>
          <span className="text-destructive">Inactive</span>
        </div>
      </div>
    </div>
  )
}