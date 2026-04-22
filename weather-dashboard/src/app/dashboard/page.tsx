import { BentoGrid, BentoCard } from "@/components/ui/bento-grid"
import { MetricCard } from "@/components/ui/metric-card"
import { DashboardLayout, DashboardHeader } from "@/components/layout/dashboard-layout"
import { Button } from "@/components/ui/button"
import { Globe } from "@/components/ui/globe"
import { Terminal, TerminalWidget } from "@/components/ui/terminal"
import { PerformanceChart, RealtimePerformanceChart } from "@/components/charts/performance-chart"
import { WeatherPositionsTable } from "@/components/ui/data-table"
import { BotControlsWidget } from "@/components/ui/bot-controls"

export default function DashboardPage() {
  return (
    <DashboardLayout
      header={
        <DashboardHeader
          title="Quantum Weather Terminal"
          description="Real-time weather trading bot monitoring"
          actions={
            <div className="flex gap-2">
              <Button variant="neon" size="sm">Live</Button>
              <Button variant="outline" size="sm">Settings</Button>
            </div>
          }
        />
      }
    >
      <div className="space-y-6">
        {/* Main Bento Grid */}
        <BentoGrid className="min-h-[600px]">
          {/* Large Performance Card with Chart */}
          <BentoCard
            title="Performance Overview"
            description="Real-time trading bot performance"
            size="lg"
            header={
              <div className="h-32 w-full">
                <RealtimePerformanceChart
                  className="w-full h-full"
                  height={128}
                  initialValue={2000}
                  updateInterval={3000}
                  maxDataPoints={20}
                />
              </div>
            }
          >
            <div className="grid grid-cols-3 gap-4">
              <div>
                <div className="text-2xl font-mono">$2,450</div>
                <div className="text-xs text-muted-foreground">Portfolio Value</div>
              </div>
              <div>
                <div className="text-2xl font-mono text-success">+24.3%</div>
                <div className="text-xs text-muted-foreground">Total Return</div>
              </div>
              <div>
                <div className="text-2xl font-mono text-accent">68.3%</div>
                <div className="text-xs text-muted-foreground">Win Rate</div>
              </div>
            </div>
          </BentoCard>

          {/* Bot Controls */}
          <BentoCard
            title="Bot Controls"
            description="Monitor and control bot status"
            size="md"
            header={
              <div className="w-12 h-12 rounded-full bg-success/20 border-2 border-success animate-pulse flex items-center justify-center">
                <div className="w-4 h-4 rounded-full bg-success"></div>
              </div>
            }
          >
            <BotControlsWidget />
          </BentoCard>

          {/* Quick Stats Grid */}
          <BentoCard
            title="Quick Stats"
            size="md"
          >
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm">Open Positions</span>
                <span className="font-mono">7</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Success Rate</span>
                <span className="font-mono text-success">68.3%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Avg Hold Time</span>
                <span className="font-mono">4.2h</span>
              </div>
            </div>
          </BentoCard>

          {/* Risk Metrics */}
          <BentoCard
            title="Risk Management"
            description="Current exposure and limits"
            size="md"
            header={
              <div className="text-3xl font-mono">
                <span className="text-warning">12%</span>
                <span className="text-xs text-muted-foreground ml-2">of bankroll</span>
              </div>
            }
          >
            <div className="w-full bg-surface/50 rounded-full h-2">
              <div className="bg-gradient-to-r from-success to-warning h-2 rounded-full" style={{width: '12%'}}></div>
            </div>
          </BentoCard>

          {/* Live Terminal */}
          <BentoCard
            title="Live Terminal"
            description="Real-time bot activity logs"
            size="md"
          >
            <TerminalWidget maxLines={4} />
          </BentoCard>

          {/* Globe Visualization */}
          <BentoCard
            title="Global Markets"
            description="Active weather monitoring locations"
            size="lg"
            header={
              <div className="h-full w-full">
                <Globe className="h-full w-full" />
              </div>
            }
          >
            <div className="text-xs text-muted-foreground">
              8 cities • 97 temperature ranges • Real-time monitoring
            </div>
          </BentoCard>
        </BentoGrid>

        {/* Secondary Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard
            title="Total Exposure"
            value="$2,450"
            change={12.5}
            changeType="positive"
            animated
          />
          <MetricCard
            title="Available Capital"
            value="$37,550"
            change={-2.1}
            changeType="negative"
            animated
          />
          <MetricCard
            title="Daily P&L"
            value="$127"
            change={8.4}
            changeType="positive"
            animated
          />
          <MetricCard
            title="Win Rate"
            value="68.3%"
            change={1.2}
            changeType="positive"
            animated
          />
        </div>

        {/* Positions Table Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold neon-glow">Recent Positions</h2>
            <Button variant="outline" size="sm" asChild>
              <a href="/positions">View All</a>
            </Button>
          </div>
          <WeatherPositionsTable />
        </div>

        {/* Full Terminal Section */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold neon-glow">Live System Logs</h2>
          <Terminal height="h-80" />
        </div>
      </div>
    </DashboardLayout>
  )
}