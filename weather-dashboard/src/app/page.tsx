import { MetricCard } from "@/components/ui/metric-card"
import { Button } from "@/components/ui/button"
import { BackgroundBeams } from "@/components/ui/background-beams"
import { AnimatedGradientText } from "@/components/ui/animated-gradient-text"
import { CommandPalette } from "@/components/ui/command-palette"

export default function HomePage() {
  return (
    <BackgroundBeams className="min-h-screen">
      <div className="flex min-h-screen items-center justify-center p-8">
        <div className="max-w-4xl w-full space-y-8">
          {/* Hero Section */}
          <div className="text-center space-y-6">
            <h1 className="text-6xl font-bold glitch" data-text="QUANTUM WEATHER TERMINAL">
              <AnimatedGradientText>
                QUANTUM WEATHER TERMINAL
              </AnimatedGradientText>
            </h1>
            <p className="text-xl text-muted-foreground font-mono">
              Advanced Weather Trading Bot Dashboard
            </p>
          </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <MetricCard
            title="Total Exposure"
            value="$2,450"
            change={12.5}
            changeType="positive"
            trend={[10, 15, 12, 18, 25, 22, 30]}
            animated
          />
          <MetricCard
            title="Open Positions"
            value={7}
            change={-5.2}
            changeType="negative"
            trend={[20, 18, 15, 12, 10, 8, 7]}
            animated
          />
          <MetricCard
            title="Success Rate"
            value="68.3%"
            change={3.1}
            changeType="positive"
            trend={[60, 62, 65, 63, 67, 69, 68]}
            animated
          />
        </div>

        {/* Action Buttons */}
        <div className="flex justify-center gap-4">
          <Button variant="neon" size="lg" asChild>
            <a href="/dashboard">Enter Dashboard</a>
          </Button>
          <Button variant="outline" size="lg">
            View Status
          </Button>
        </div>

        <p className="text-sm text-muted-foreground text-center">
          Design system initialized • Next.js 15 • Tailwind CSS v4 • shadcn/ui components
        </p>
        </div>
      </div>

      <CommandPalette />
    </BackgroundBeams>
  );
}
