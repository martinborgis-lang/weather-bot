"use client"

import { cn } from "@/lib/utils"
import React, { useEffect, useState, useRef, useCallback } from "react"
import { Command, Search, Terminal, Globe, BarChart3, Settings, Home, TrendingUp } from "lucide-react"

interface CommandItem {
  id: string
  label: string
  shortcut?: string
  icon?: React.ComponentType<{ className?: string }>
  category: string
  action?: () => void
  href?: string
}

interface CommandPaletteProps {
  className?: string
}

export function CommandPalette({ className }: CommandPaletteProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const commands: CommandItem[] = [
    {
      id: "home",
      label: "Go to Home",
      shortcut: "⌘H",
      icon: Home,
      category: "Navigation",
      href: "/"
    },
    {
      id: "dashboard",
      label: "Open Dashboard",
      shortcut: "⌘D",
      icon: BarChart3,
      category: "Navigation",
      href: "/dashboard"
    },
    {
      id: "globe",
      label: "View Global Markets",
      shortcut: "⌘G",
      icon: Globe,
      category: "Views",
      action: () => {
        // Scroll to globe section in dashboard
        const globeElement = document.querySelector('[title="Global Markets"]')
        globeElement?.scrollIntoView({ behavior: 'smooth' })
      }
    },
    {
      id: "terminal",
      label: "Open Terminal",
      shortcut: "⌘T",
      icon: Terminal,
      category: "Tools",
      action: () => {
        console.log("Terminal opened")
      }
    },
    {
      id: "performance",
      label: "Performance Overview",
      shortcut: "⌘P",
      icon: TrendingUp,
      category: "Analytics",
      action: () => {
        const perfElement = document.querySelector('[title="Performance Overview"]')
        perfElement?.scrollIntoView({ behavior: 'smooth' })
      }
    },
    {
      id: "settings",
      label: "Bot Settings",
      shortcut: "⌘,",
      icon: Settings,
      category: "Configuration",
      action: () => {
        console.log("Settings opened")
      }
    },
    {
      id: "search-markets",
      label: "Search Weather Markets",
      shortcut: "⌘F",
      icon: Search,
      category: "Search",
      action: () => {
        console.log("Market search opened")
      }
    }
  ]

  const filteredCommands = commands.filter(command =>
    command.label.toLowerCase().includes(query.toLowerCase()) ||
    command.category.toLowerCase().includes(query.toLowerCase())
  )

  const groupedCommands = filteredCommands.reduce((acc, command) => {
    if (!acc[command.category]) {
      acc[command.category] = []
    }
    acc[command.category].push(command)
    return acc
  }, {} as Record<string, CommandItem[]>)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      setIsOpen(prev => !prev)
      if (!isOpen) {
        setTimeout(() => inputRef.current?.focus(), 100)
      }
    }

    if (isOpen) {
      if (e.key === "Escape") {
        setIsOpen(false)
        setQuery("")
        setSelectedIndex(0)
      } else if (e.key === "ArrowDown") {
        e.preventDefault()
        setSelectedIndex(prev =>
          prev < filteredCommands.length - 1 ? prev + 1 : 0
        )
      } else if (e.key === "ArrowUp") {
        e.preventDefault()
        setSelectedIndex(prev =>
          prev > 0 ? prev - 1 : filteredCommands.length - 1
        )
      } else if (e.key === "Enter") {
        e.preventDefault()
        const selectedCommand = filteredCommands[selectedIndex]
        if (selectedCommand) {
          executeCommand(selectedCommand)
        }
      }
    }
  }, [isOpen, filteredCommands, selectedIndex])

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [handleKeyDown])

  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  const executeCommand = (command: CommandItem) => {
    if (command.href) {
      window.location.href = command.href
    } else if (command.action) {
      command.action()
    }
    setIsOpen(false)
    setQuery("")
    setSelectedIndex(0)
  }

  if (!isOpen) {
    return (
      <div className={cn("fixed bottom-4 right-4 z-50", className)}>
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-surface/80 backdrop-blur-sm border border-accent/30 rounded-lg text-sm font-mono neon-border hover:neon-glow transition-all"
        >
          <Command className="h-4 w-4" />
          <span>⌘K</span>
        </button>
      </div>
    )
  }

  return (
    <div className={cn("fixed inset-0 z-50 flex items-start justify-center pt-[20vh]", className)}>
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={() => setIsOpen(false)}
      />

      {/* Command Palette */}
      <div className="relative w-full max-w-2xl mx-4 bg-surface/95 backdrop-blur-md border border-accent/30 rounded-xl shadow-2xl neon-border overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 p-4 border-b border-accent/20">
          <Search className="h-5 w-5 text-accent" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search commands or navigate..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none font-mono"
          />
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
            <kbd className="px-2 py-1 bg-accent/20 rounded">ESC</kbd>
            <span>to close</span>
          </div>
        </div>

        {/* Commands */}
        <div className="max-h-96 overflow-y-auto">
          {Object.keys(groupedCommands).length === 0 ? (
            <div className="p-8 text-center text-muted-foreground font-mono">
              No commands found for "{query}"
            </div>
          ) : (
            Object.entries(groupedCommands).map(([category, categoryCommands], categoryIndex) => (
              <div key={category} className={categoryIndex > 0 ? "border-t border-accent/10" : ""}>
                <div className="px-4 py-2 text-xs font-mono text-accent/80 bg-accent/5">
                  {category}
                </div>
                {categoryCommands.map((command, index) => {
                  const globalIndex = filteredCommands.indexOf(command)
                  const isSelected = globalIndex === selectedIndex

                  return (
                    <button
                      key={command.id}
                      onClick={() => executeCommand(command)}
                      className={cn(
                        "w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent/10 transition-colors",
                        isSelected && "bg-accent/20 neon-glow"
                      )}
                    >
                      {command.icon && (
                        <command.icon className="h-4 w-4 text-accent flex-shrink-0" />
                      )}
                      <span className="flex-1 font-mono">{command.label}</span>
                      {command.shortcut && (
                        <kbd className="px-2 py-1 text-xs bg-accent/20 rounded font-mono">
                          {command.shortcut}
                        </kbd>
                      )}
                    </button>
                  )
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-accent/20 bg-accent/5">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <kbd className="px-1 py-0.5 bg-accent/20 rounded">↑</kbd>
                <kbd className="px-1 py-0.5 bg-accent/20 rounded">↓</kbd>
                <span>navigate</span>
              </div>
              <div className="flex items-center gap-1">
                <kbd className="px-1 py-0.5 bg-accent/20 rounded">⏎</kbd>
                <span>select</span>
              </div>
            </div>
            <div className="text-accent">Quantum Terminal Command Palette</div>
          </div>
        </div>
      </div>
    </div>
  )
}