"use client"

import { BotControls } from "@/components/ui/bot-controls"
import { DashboardLayout, DashboardHeader } from "@/components/layout/dashboard-layout"
import { Button } from "@/components/ui/button"
import { Settings, Download, AlertTriangle } from "lucide-react"

export default function ControlsPage() {
  return (
    <DashboardLayout
      header={
        <DashboardHeader
          title="Bot Controls"
          description="Manage your weather trading bot operations"
          actions={
            <div className="flex gap-2">
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Export Logs
              </Button>
              <Button variant="outline" size="sm">
                <Settings className="h-4 w-4 mr-2" />
                Configuration
              </Button>
              <Button variant="destructive" size="sm">
                <AlertTriangle className="h-4 w-4 mr-2" />
                Emergency Stop
              </Button>
            </div>
          }
        />
      }
    >
      <div className="space-y-6">
        {/* Bot Controls */}
        <BotControls
          onStart={() => console.log("Bot started")}
          onPause={() => console.log("Bot paused")}
          onStop={() => console.log("Bot stopped")}
          onRestart={() => console.log("Bot restarted")}
          onSettings={() => console.log("Settings opened")}
        />
      </div>
    </DashboardLayout>
  )
}