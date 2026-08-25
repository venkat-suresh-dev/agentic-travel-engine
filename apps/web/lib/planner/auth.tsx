"use client";

import { useAuth } from "@clerk/nextjs";
import { createContext, useContext } from "react";

type GetToken = () => Promise<string | null>;

const PlannerTokenContext = createContext<GetToken>(async () => null);

const isPlaywrightMode = process.env.NEXT_PUBLIC_PLAYWRIGHT === "1";

function ClerkPlannerTokenProvider({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth();

  return (
    <PlannerTokenContext.Provider value={getToken}>
      {children}
    </PlannerTokenContext.Provider>
  );
}

export function PlannerTokenProvider({ children }: { children: React.ReactNode }) {
  if (isPlaywrightMode) {
    return (
      <PlannerTokenContext.Provider value={async () => "playwright-token"}>
        {children}
      </PlannerTokenContext.Provider>
    );
  }

  return <ClerkPlannerTokenProvider>{children}</ClerkPlannerTokenProvider>;
}

export function usePlannerToken(): GetToken {
  return useContext(PlannerTokenContext);
}

export function isPlannerAuthEnabled(): boolean {
  return !isPlaywrightMode && Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
}
