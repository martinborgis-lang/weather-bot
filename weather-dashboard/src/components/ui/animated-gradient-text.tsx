"use client"

import { cn } from "@/lib/utils"
import React from "react"

interface AnimatedGradientTextProps {
  children: React.ReactNode
  className?: string
}

export function AnimatedGradientText({
  children,
  className
}: AnimatedGradientTextProps) {
  return (
    <span
      className={cn(
        "animate-gradient bg-gradient-to-r from-accent via-success to-accent bg-[length:var(--bg-size)_100%] bg-clip-text text-transparent",
        className
      )}
      style={{
        "--bg-size": "400%",
        animation: "gradient 4s ease-in-out infinite",
      } as React.CSSProperties}
    >
      {children}
      <style jsx>{`
        @keyframes gradient {
          0%, 100% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
        }
      `}</style>
    </span>
  )
}