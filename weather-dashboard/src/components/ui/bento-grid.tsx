"use client"

import { cn } from "@/lib/utils"
import React from "react"

export interface BentoGridProps {
  children: React.ReactNode
  className?: string
}

export function BentoGrid({ children, className }: BentoGridProps) {
  return (
    <div
      className={cn(
        "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-[200px] md:auto-rows-[250px]",
        className
      )}
    >
      {children}
    </div>
  )
}

export interface BentoCardProps {
  title: string
  description?: string
  header?: React.ReactNode
  icon?: React.ComponentType<{ className?: string }>
  className?: string
  children?: React.ReactNode
  size?: "sm" | "md" | "lg" | "xl"
}

export function BentoCard({
  title,
  description,
  header,
  icon: Icon,
  className,
  children,
  size = "md"
}: BentoCardProps) {
  const sizeClasses = {
    sm: "row-span-1 col-span-1",
    md: "row-span-1 col-span-1 md:col-span-1",
    lg: "row-span-2 col-span-1 md:col-span-2",
    xl: "row-span-2 col-span-1 md:col-span-2 lg:col-span-3"
  }

  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-xl border bg-surface/80 p-6 hover:shadow-md transition-all duration-300 hover:neon-border",
        sizeClasses[size],
        className
      )}
    >
      {header && (
        <div className="mb-4 h-24 w-full rounded-lg bg-gradient-to-br from-accent/20 to-accent/5 flex items-center justify-center">
          {header}
        </div>
      )}

      <div className="flex flex-col justify-between h-full">
        <div>
          <div className="flex items-center gap-2 mb-2">
            {Icon && <Icon className="h-5 w-5 text-accent" />}
            <h3 className="font-semibold text-lg neon-glow">{title}</h3>
          </div>

          {description && (
            <p className="text-muted-foreground text-sm mb-4">
              {description}
            </p>
          )}
        </div>

        {children && (
          <div className="mt-auto">
            {children}
          </div>
        )}
      </div>

      {/* Cyberpunk corner accent */}
      <div className="absolute top-0 right-0 h-8 w-8 border-t-2 border-r-2 border-accent/50 opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="absolute bottom-0 left-0 h-8 w-8 border-b-2 border-l-2 border-accent/50 opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  )
}