import { WeatherPositionsTable } from "@/components/ui/data-table"
import { DashboardLayout, DashboardHeader } from "@/components/layout/dashboard-layout"
import { Button } from "@/components/ui/button"
import { Plus, Download, Filter } from "lucide-react"

export default function PositionsPage() {
  return (
    <DashboardLayout
      header={
        <DashboardHeader
          title="Trading Positions"
          description="Manage your weather prediction positions"
          actions={
            <div className="flex gap-2">
              <Button variant="outline" size="sm">
                <Filter className="h-4 w-4 mr-2" />
                Filter
              </Button>
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
              <Button variant="neon" size="sm">
                <Plus className="h-4 w-4 mr-2" />
                New Position
              </Button>
            </div>
          }
        />
      }
    >
      <div className="space-y-6">
        {/* Positions Table */}
        <WeatherPositionsTable className="w-full" />
      </div>
    </DashboardLayout>
  )
}