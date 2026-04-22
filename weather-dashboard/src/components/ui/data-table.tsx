"use client"

import { cn } from "@/lib/utils"
import React, { useState, useMemo } from "react"
import { ChevronUp, ChevronDown, Search, Filter, MoreHorizontal, TrendingUp, TrendingDown } from "lucide-react"

export interface Column<T> {
  key: keyof T | "actions"
  label: string
  sortable?: boolean
  width?: string
  render?: (value: any, row: T, index: number) => React.ReactNode
  align?: "left" | "center" | "right"
}

export interface DataTableProps<T> {
  data: T[]
  columns: Column<T>[]
  className?: string
  searchable?: boolean
  filterable?: boolean
  sortable?: boolean
  pagination?: boolean
  pageSize?: number
  striped?: boolean
  compact?: boolean
  glowing?: boolean
}

export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  className,
  searchable = true,
  filterable = false,
  sortable = true,
  pagination = false,
  pageSize = 10,
  striped = true,
  compact = false,
  glowing = true
}: DataTableProps<T>) {
  const [searchQuery, setSearchQuery] = useState("")
  const [sortConfig, setSortConfig] = useState<{
    key: keyof T | null
    direction: "asc" | "desc"
  }>({ key: null, direction: "asc" })
  const [currentPage, setCurrentPage] = useState(1)

  // Filter data based on search query
  const filteredData = useMemo(() => {
    if (!searchQuery) return data

    return data.filter(item =>
      Object.values(item).some(value =>
        String(value).toLowerCase().includes(searchQuery.toLowerCase())
      )
    )
  }, [data, searchQuery])

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortConfig.key || !sortable) return filteredData

    return [...filteredData].sort((a, b) => {
      const aValue = a[sortConfig.key!]
      const bValue = b[sortConfig.key!]

      if (aValue < bValue) {
        return sortConfig.direction === "asc" ? -1 : 1
      }
      if (aValue > bValue) {
        return sortConfig.direction === "asc" ? 1 : -1
      }
      return 0
    })
  }, [filteredData, sortConfig, sortable])

  // Paginate data
  const paginatedData = useMemo(() => {
    if (!pagination) return sortedData

    const startIndex = (currentPage - 1) * pageSize
    return sortedData.slice(startIndex, startIndex + pageSize)
  }, [sortedData, currentPage, pageSize, pagination])

  const handleSort = (key: keyof T) => {
    if (!sortable) return

    setSortConfig(prev => ({
      key,
      direction:
        prev.key === key && prev.direction === "asc" ? "desc" : "asc"
    }))
  }

  const totalPages = pagination ? Math.ceil(sortedData.length / pageSize) : 1

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header with search and filters */}
      {(searchable || filterable) && (
        <div className="flex items-center justify-between gap-4">
          {searchable && (
            <div className="relative max-w-sm">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-surface/50 border border-accent/30 rounded-lg text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-colors"
              />
            </div>
          )}

          {filterable && (
            <button className="flex items-center gap-2 px-3 py-2 bg-surface/50 border border-accent/30 rounded-lg text-sm hover:bg-accent/10 transition-colors">
              <Filter className="h-4 w-4" />
              Filters
            </button>
          )}
        </div>
      )}

      {/* Table */}
      <div className={cn(
        "relative overflow-hidden rounded-lg border border-accent/30",
        glowing && "neon-border"
      )}>
        <div className="overflow-x-auto">
          <table className="w-full">
            {/* Header */}
            <thead className="bg-accent/10 border-b border-accent/20">
              <tr>
                {columns.map((column, index) => (
                  <th
                    key={String(column.key)}
                    className={cn(
                      "px-4 py-3 text-left text-xs font-medium text-accent uppercase tracking-wider",
                      column.align === "center" && "text-center",
                      column.align === "right" && "text-right",
                      column.sortable && sortable && "cursor-pointer hover:bg-accent/20 select-none transition-colors",
                      compact && "px-2 py-2",
                      column.width && `w-[${column.width}]`
                    )}
                    onClick={() => column.sortable && sortable && handleSort(column.key as keyof T)}
                  >
                    <div className="flex items-center gap-1">
                      {column.label}
                      {column.sortable && sortable && (
                        <div className="flex flex-col">
                          <ChevronUp
                            className={cn(
                              "h-3 w-3 -mb-1",
                              sortConfig.key === column.key && sortConfig.direction === "asc"
                                ? "text-accent"
                                : "text-muted-foreground/50"
                            )}
                          />
                          <ChevronDown
                            className={cn(
                              "h-3 w-3",
                              sortConfig.key === column.key && sortConfig.direction === "desc"
                                ? "text-accent"
                                : "text-muted-foreground/50"
                            )}
                          />
                        </div>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>

            {/* Body */}
            <tbody className="bg-surface/30 divide-y divide-accent/10">
              {paginatedData.map((row, rowIndex) => (
                <tr
                  key={rowIndex}
                  className={cn(
                    "hover:bg-accent/10 transition-colors",
                    striped && rowIndex % 2 === 0 && "bg-accent/5",
                    glowing && "hover:neon-glow"
                  )}
                >
                  {columns.map((column, colIndex) => (
                    <td
                      key={String(column.key)}
                      className={cn(
                        "px-4 py-3 text-sm font-mono",
                        column.align === "center" && "text-center",
                        column.align === "right" && "text-right",
                        compact && "px-2 py-2"
                      )}
                    >
                      {column.render
                        ? column.render(row[column.key], row, rowIndex)
                        : String(row[column.key] || "-")
                      }
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          {/* Empty state */}
          {paginatedData.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <div className="text-lg font-medium mb-2">No data found</div>
              <div className="text-sm">
                {searchQuery ? `No results for "${searchQuery}"` : "No data to display"}
              </div>
            </div>
          )}
        </div>

        {/* Cyberpunk scanlines effect */}
        {glowing && (
          <div
            className="absolute inset-0 pointer-events-none opacity-5"
            style={{
              backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(34, 197, 94, 0.1) 2px, rgba(34, 197, 94, 0.1) 4px)",
            }}
          />
        )}
      </div>

      {/* Pagination */}
      {pagination && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Showing {(currentPage - 1) * pageSize + 1} to{" "}
            {Math.min(currentPage * pageSize, sortedData.length)} of{" "}
            {sortedData.length} entries
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm border border-accent/30 rounded hover:bg-accent/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                className={cn(
                  "px-3 py-1 text-sm border border-accent/30 rounded transition-colors",
                  page === currentPage
                    ? "bg-accent text-background"
                    : "hover:bg-accent/10"
                )}
              >
                {page}
              </button>
            ))}

            <button
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm border border-accent/30 rounded hover:bg-accent/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// Predefined table for weather trading data
export interface WeatherPosition {
  market: string
  city: string
  temperature: string
  side: "YES" | "NO"
  entry: number
  current: number
  pnl: number
  pnlPct: number
  status: "active" | "resolved" | "expired"
}

export function WeatherPositionsTable({
  positions,
  className
}: {
  positions?: WeatherPosition[]
  className?: string
}) {
  const demoData: WeatherPosition[] = positions || [
    {
      market: "Paris-18C-2024-04-23",
      city: "Paris",
      temperature: "18°C",
      side: "YES",
      entry: 0.65,
      current: 0.72,
      pnl: 45.50,
      pnlPct: 12.4,
      status: "active"
    },
    {
      market: "London-15C-2024-04-22",
      city: "London",
      temperature: "15°C",
      side: "NO",
      entry: 0.55,
      current: 0.48,
      pnl: -23.10,
      pnlPct: -6.8,
      status: "active"
    },
    {
      market: "NYC-22C-2024-04-21",
      city: "New York",
      temperature: "22°C",
      side: "YES",
      entry: 0.70,
      current: 0.85,
      pnl: 67.20,
      pnlPct: 18.2,
      status: "resolved"
    },
    {
      market: "Tokyo-25C-2024-04-20",
      city: "Tokyo",
      temperature: "25°C",
      side: "NO",
      entry: 0.40,
      current: 0.35,
      pnl: 31.80,
      pnlPct: 9.5,
      status: "resolved"
    }
  ]

  const columns: Column<WeatherPosition>[] = [
    {
      key: "city",
      label: "City",
      sortable: true,
      render: (value, row) => (
        <div className="font-medium text-foreground">{value}</div>
      )
    },
    {
      key: "temperature",
      label: "Target Temp",
      sortable: true,
      align: "center",
      render: (value, row) => (
        <span className="px-2 py-1 bg-accent/20 rounded-full text-accent font-mono text-xs">
          {value}
        </span>
      )
    },
    {
      key: "side",
      label: "Side",
      sortable: true,
      align: "center",
      render: (value, row) => (
        <span className={cn(
          "px-2 py-1 rounded-full text-xs font-mono",
          value === "YES" ? "bg-success/20 text-success" : "bg-destructive/20 text-destructive"
        )}>
          {value}
        </span>
      )
    },
    {
      key: "entry",
      label: "Entry Price",
      sortable: true,
      align: "right",
      render: (value) => `$${value.toFixed(3)}`
    },
    {
      key: "current",
      label: "Current Price",
      sortable: true,
      align: "right",
      render: (value) => `$${value.toFixed(3)}`
    },
    {
      key: "pnl",
      label: "P&L",
      sortable: true,
      align: "right",
      render: (value, row) => (
        <div className={cn(
          "flex items-center justify-end gap-1",
          value >= 0 ? "text-success" : "text-destructive"
        )}>
          {value >= 0 ? (
            <TrendingUp className="h-3 w-3" />
          ) : (
            <TrendingDown className="h-3 w-3" />
          )}
          ${Math.abs(value).toFixed(2)}
        </div>
      )
    },
    {
      key: "pnlPct",
      label: "P&L %",
      sortable: true,
      align: "right",
      render: (value) => (
        <span className={value >= 0 ? "text-success" : "text-destructive"}>
          {value >= 0 ? "+" : ""}{value.toFixed(1)}%
        </span>
      )
    },
    {
      key: "status",
      label: "Status",
      sortable: true,
      align: "center",
      render: (value) => (
        <span className={cn(
          "px-2 py-1 rounded-full text-xs font-mono",
          value === "active" ? "bg-accent/20 text-accent" :
          value === "resolved" ? "bg-success/20 text-success" :
          "bg-muted/20 text-muted-foreground"
        )}>
          {value.charAt(0).toUpperCase() + value.slice(1)}
        </span>
      )
    },
    {
      key: "actions",
      label: "",
      width: "50px",
      render: (_, row) => (
        <button className="p-1 hover:bg-accent/20 rounded transition-colors">
          <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
        </button>
      )
    }
  ]

  return (
    <DataTable
      data={demoData}
      columns={columns}
      className={className}
      searchable={true}
      sortable={true}
      striped={true}
      glowing={true}
    />
  )
}