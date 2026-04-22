"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        refetchInterval: 30000,  // refresh toutes les 30s
        refetchOnWindowFocus: true,
        retry: 2,
        staleTime: 10000, // 10s before data becomes stale
      },
    },
  }));

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}