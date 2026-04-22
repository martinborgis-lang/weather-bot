"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, queryKeys, BotStatus, Market, Forecast } from "@/lib/api";
import { Position, Trade, Signal, Stats } from "@/lib/types";

// Stats hook
export const useStats = () => useQuery({
  queryKey: queryKeys.stats,
  queryFn: () => apiClient.getStats(),
});

// Positions hooks
export const usePositions = () => useQuery({
  queryKey: queryKeys.positions,
  queryFn: () => apiClient.getPositions(),
});

export const usePositionsDetailed = () => useQuery({
  queryKey: queryKeys.positionsDetailed,
  queryFn: () => apiClient.getPositionsDetailed(),
});

// Trades hook
export const useTrades = () => useQuery({
  queryKey: queryKeys.trades,
  queryFn: () => apiClient.getTrades(),
});

// Signals hook
export const useSignals = () => useQuery({
  queryKey: queryKeys.signals,
  queryFn: () => apiClient.getSignals(),
});

// Bot status hook (more frequent updates)
export const useBotStatus = () => useQuery({
  queryKey: queryKeys.botStatus,
  queryFn: () => apiClient.getBotStatus(),
  refetchInterval: 5000, // Every 5 seconds for status
});

// Markets hook
export const useMarkets = () => useQuery({
  queryKey: queryKeys.markets,
  queryFn: () => apiClient.getMarkets(),
});

// Forecasts hook
export const useForecasts = () => useQuery({
  queryKey: queryKeys.forecasts,
  queryFn: () => apiClient.getForecasts(),
});

// Bot control mutations
export const usePauseBot = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.pauseBot(),
    onSuccess: () => {
      // Invalidate bot status to reflect the change
      queryClient.invalidateQueries({ queryKey: queryKeys.botStatus });
    },
  });
};

export const useResumeBot = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.resumeBot(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.botStatus });
    },
  });
};

export const useForceCycle = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.forceCycle(),
    onSuccess: () => {
      // Invalidate all data since a forced cycle might update everything
      queryClient.invalidateQueries({ queryKey: queryKeys.botStatus });
      queryClient.invalidateQueries({ queryKey: queryKeys.positions });
      queryClient.invalidateQueries({ queryKey: queryKeys.trades });
      queryClient.invalidateQueries({ queryKey: queryKeys.signals });
    },
  });
};

// Combined hook for dashboard overview
export const useDashboardData = () => {
  const stats = useStats();
  const botStatus = useBotStatus();
  const positions = usePositionsDetailed();
  const trades = useTrades();

  return {
    stats,
    botStatus,
    positions,
    trades,
    isLoading: stats.isLoading || botStatus.isLoading || positions.isLoading || trades.isLoading,
    isError: stats.isError || botStatus.isError || positions.isError || trades.isError,
  };
};