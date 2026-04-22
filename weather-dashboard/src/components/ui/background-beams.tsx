"use client"

import { cn } from "@/lib/utils"
import React, { useEffect, useRef, useState } from "react"

export interface BackgroundBeamsProps {
  className?: string
  children?: React.ReactNode
}

export function BackgroundBeams({ className, children }: BackgroundBeamsProps) {
  const [beams, setBeams] = useState<Array<{ id: string; left: string; animationDelay: string; duration: string }>>([])
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const generateBeams = () => {
      const newBeams = Array.from({ length: 20 }, (_, i) => ({
        id: `beam-${i}`,
        left: `${Math.random() * 100}%`,
        animationDelay: `${Math.random() * 3}s`,
        duration: `${3 + Math.random() * 3}s`
      }))
      setBeams(newBeams)
    }

    generateBeams()
  }, [])

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative overflow-hidden bg-background",
        className
      )}
    >
      {/* Animated beams */}
      <div className="absolute inset-0 pointer-events-none">
        {beams.map((beam) => (
          <div
            key={beam.id}
            className="absolute top-0 h-full w-px bg-gradient-to-b from-transparent via-accent to-transparent opacity-20"
            style={{
              left: beam.left,
              animation: `beam-animation ${beam.duration} ease-in-out infinite`,
              animationDelay: beam.animationDelay,
            }}
          />
        ))}
      </div>

      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-background via-background/95 to-background pointer-events-none" />

      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>

      <style jsx>{`
        @keyframes beam-animation {
          0% {
            opacity: 0;
            transform: translateY(-100%);
          }
          50% {
            opacity: 1;
          }
          100% {
            opacity: 0;
            transform: translateY(100vh);
          }
        }
      `}</style>
    </div>
  )
}