"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { CommandPalette } from "@/components/ui/command-palette"

interface DashboardLayoutProps {
  children: React.ReactNode
  sidebar?: React.ReactNode
  header?: React.ReactNode
  className?: string
}

export function DashboardLayout({
  children,
  sidebar,
  header,
  className,
}: DashboardLayoutProps) {
  return (
    <div className={cn("flex h-screen bg-background", className)}>
      {/* Sidebar */}
      {sidebar && (
        <aside className="w-64 border-r border-border bg-surface/50 overflow-y-auto">
          {sidebar}
        </aside>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        {header && (
          <header className="border-b border-border bg-surface/30 px-6 py-4">
            {header}
          </header>
        )}

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>

      {/* Command Palette */}
      <CommandPalette />
    </div>
  )
}

// Header component for consistent styling
export function DashboardHeader({
  title,
  description,
  actions,
  className
}: {
  title: string
  description?: string
  actions?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex items-center justify-between", className)}>
      <div>
        <h1 className="text-2xl font-bold neon-glow">{title}</h1>
        {description && (
          <p className="text-muted-foreground font-mono text-sm">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}

// Sidebar navigation component
export function SidebarNav({
  items,
  className
}: {
  items: Array<{
    title: string
    href: string
    icon?: React.ComponentType<{ className?: string }>
    active?: boolean
  }>
  className?: string
}) {
  return (
    <nav className={cn("space-y-2", className)}>
      {items.map((item) => (
        <a
          key={item.href}
          href={item.href}
          className={cn(
            "flex items-center gap-3 px-4 py-2 text-sm font-medium rounded-md transition-colors",
            item.active
              ? "bg-accent/20 text-accent border-l-2 border-accent"
              : "text-muted-foreground hover:text-foreground hover:bg-surface/50"
          )}
        >
          {item.icon && <item.icon className="h-4 w-4" />}
          {item.title}
        </a>
      ))}
    </nav>
  )
}